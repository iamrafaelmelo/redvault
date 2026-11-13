from __future__ import annotations

import base64
import hashlib
import hmac
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import jsonify, redirect, request, session

from labkit import Lab

lab = Lab("MERIDIAN BANK", accent="#d4a537")
app = lab.app

Path("/tmp/meridian-root.txt").write_text(lab.flag("root") + "\n")

JWT_SECRET = b"meridian-dev"
JWT_COOKIE = "meridian_token"

ACCOUNTS = {
    1: {"username": "jordan", "name": "Jordan Lee", "balance": 8420.75, "memo": "Everyday account"},
    2: {"username": "admin", "name": "Meridian Treasury", "balance": 984221.00, "memo": "Internal settlement"},
}


def b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def unb64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue(username: str, role: str) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = b64url(
        json.dumps(
            {"sub": username, "role": role, "iat": int(datetime.now(timezone.utc).timestamp()), "exp": int((datetime.now(timezone.utc) + timedelta(hours=8)).timestamp())},
            separators=(",", ":"),
        ).encode()
    )
    body = f"{header}.{payload}"
    return f"{body}.{b64url(hmac.new(JWT_SECRET, body.encode(), hashlib.sha256).digest())}"


def verify(token: str) -> dict | None:
    try:
        header, payload, signature = token.split(".")
        if json.loads(unb64url(header)).get("alg") != "HS256":
            return None
        expected = b64url(hmac.new(JWT_SECRET, f"{header}.{payload}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, signature):
            return None
        claims = json.loads(unb64url(payload))
        if int(claims.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
            return None
        return claims
    except Exception:
        return None


def shell(title: str, body: str) -> object:
    nav = '<a href="/account">Account</a><a href="/admin">Admin</a><a href="/logout">Logout</a>' if session.get("user") else '<a href="/">Login</a>'
    return lab.page(title, f'<div class="hero"><div class="kicker">MERIDIAN // PRIVATE BANKING</div><h1>{title}</h1></div>{body}', nav=nav)


@app.get("/")
def index():
    if session.get("user"):
        return redirect("/account")
    return shell(
        "Meridian Bank",
        """<div class="panel"><h2>Customer access</h2><form method="post" action="/login">
        <label>Username</label><input name="username" value="jordan"><label>Password</label><input name="password" type="password" value="jordan123">
        <p><button type="submit">Sign in</button></p></form>
        <p class="note">The account API is used by the mobile app. Tokens are HS256 and the platform team is testing a new rotation process.</p></div>""",
    )


@app.post("/login")
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    if username == "jordan" and password == "jordan123":
        session["user"] = "jordan"
        response = redirect("/account")
        response.set_cookie(JWT_COOKIE, issue("jordan", "customer"), httponly=True, samesite="lax")
        return response
    return shell("Login failed", '<div class="flash err">Invalid credentials.</div>')


@app.get("/logout")
def logout():
    session.clear()
    response = redirect("/")
    response.delete_cookie(JWT_COOKIE)
    return response


@app.get("/account")
def account():
    if not session.get("user"):
        return redirect("/")
    return shell(
        "Jordan's account",
        f'''<div class="panel"><h2>Personal account</h2>
        <p>Balance: $8,420.75 · Account 1</p>
        <p>You have a customer JWT for the mobile API. It contains a role claim.</p>
        <pre>{lab.flag("user")}</pre>
        <p class="note">The account API at `/api/accounts/<id>` is authenticated by the session. Try your own account first.</p></div>''',
    )


@app.get("/api/accounts/<int:account_id>")
def account_api(account_id: int):
    if not session.get("user"):
        return jsonify({"error": "authentication required"}), 401
    account = ACCOUNTS.get(account_id)
    if not account:
        return jsonify({"error": "account not found"}), 404
    # VULNERABLE: object-level authorization missing.
    payload = {"id": account_id, "username": account["username"], "name": account["name"], "balance": account["balance"], "memo": account["memo"]}
    if account_id == 2:
        payload["internal_note"] = "JWT signing secret pending rotation: meridian-dev"
        payload["api_flag"] = lab.flag("api")
        payload["settlement"] = "treasury-diagnostics"
    return jsonify(payload)


@app.get("/admin")
def admin():
    claims = verify(request.cookies.get(JWT_COOKIE, ""))
    if not claims or claims.get("role") != "admin":
        return shell("Admin denied", '<div class="flash err">Administrator JWT required. The signature and role claim are both checked.</div>')
    return shell(
        "Treasury administration",
        f'''<div class="panel"><h2>Administrator session</h2><p>Welcome, {claims.get("sub")}.</p>
        <p>The treasury diagnostic worker can reach the bank's internal runtime.</p></div>
        <div class="panel"><h2>Network diagnostics</h2>
        <form method="post" action="/admin/diagnostics"><label>Host</label><input name="host" value="127.0.0.1">
        <p><button type="submit">Run diagnostic</button></p></form>
        <p class="note">Service account can read /tmp/meridian-root.txt.</p></div>''',
    )


@app.post("/admin/diagnostics")
def diagnostics():
    claims = verify(request.cookies.get(JWT_COOKIE, ""))
    if not claims or claims.get("role") != "admin":
        return shell("Admin denied", '<div class="flash err">Administrator JWT required.</div>')
    host = request.form.get("host", "127.0.0.1")
    # VULNERABLE: command injection in the administrative diagnostic worker.
    command = f"getent hosts {host} 2>&1 || true"
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=8)
        output = (result.stdout or "") + (result.stderr or "")
    except subprocess.TimeoutExpired:
        output = "diagnostic timed out"
    if lab.flag("root") in output:
        lab.objective_async("root", "treasury diagnostics executed a shell command and read the root flag")
    return shell(
        "Diagnostics output",
        f'<div class="panel"><h2>Output</h2><pre>{output}</pre></div><p><a href="/admin">Back to admin</a></p>',
    )


if __name__ == "__main__":
    lab.run()
