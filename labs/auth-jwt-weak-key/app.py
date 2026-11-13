from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone

from flask import redirect, request

from labkit import Lab

lab = Lab("HELIOS GATEWAY", accent="#54b689")
app = lab.app

JWT_SECRET = b"sunshine"
COOKIE = "helios_token"


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
    signature = b64url(hmac.new(JWT_SECRET, body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


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


def page(body: str, title: str) -> object:
    return lab.page(title, f'<div class="hero"><div class="kicker">HELIOS // TOKEN GATEWAY</div><h1>{title}</h1></div>{body}', nav='<a href="/">Home</a><a href="/admin">Admin</a><a href="/wordlist.txt">secrets.txt</a>')


@app.get("/")
def index():
    claims = verify(request.cookies.get(COOKIE, ""))
    if not claims:
        return page(
            """<div class="panel"><h2>Guest access</h2><p>Sign in to receive a short-lived HS256 token.</p>
            <form method="post" action="/login"><label>Username</label><input name="username" value="guest">
            <p><button type="submit">Issue token</button></p></form>
            <p class="note">The signing key is not a user secret. It is rotated by the platform team.</p></div>""",
            "Helios Gateway",
        )
    admin_link = '<p><a class="btn" href="/admin">Open admin area</a></p>' if claims.get("role") == "admin" else ""
    return page(
        f'<div class="panel"><h2>Token active</h2><p>Subject: <code>{claims.get("sub")}</code> · Role: <code>{claims.get("role")}</code></p>{admin_link}</div>',
        "Token gateway",
    )


@app.post("/login")
def login():
    username = request.form.get("username", "guest").strip() or "guest"
    token = issue(username[:40], "user")
    response = redirect("/")
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax")
    return response


@app.get("/wordlist.txt")
def wordlist():
    return lab.app.response_class("sunshine\nsecret\nchangeme\nhunter2\nhelios\n", mimetype="text/plain")


@app.get("/admin")
def admin():
    claims = verify(request.cookies.get(COOKIE, ""))
    if not claims or claims.get("role") != "admin":
        return page('<div class="flash err">Administrator role required.</div>', "Access denied")
    return page(
        f'<div class="panel"><h2>Operator control</h2><p class="green">Role check passed.</p><pre>{lab.flag("flag")}</pre></div>',
        "Admin",
    )


if __name__ == "__main__":
    lab.run()
