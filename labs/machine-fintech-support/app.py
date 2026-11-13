from __future__ import annotations

import secrets
import subprocess
from pathlib import Path

from flask import jsonify, redirect, request, session

from labkit import Lab

lab = Lab("FINCH SUPPORT", accent="#3f8cff")
app = lab.app

Path("/tmp/fintech-root.txt").write_text(lab.flag("root") + "\n")

USERS: dict[str, dict[str, str]] = {
    "analyst": {"password": "Support2026!", "role": "analyst", "display": "Mara Voss"},
    "admin": {"password": secrets.token_urlsafe(24), "role": "admin", "display": "Platform Admin"},
}
CASES: dict[int, dict[str, object]] = {
    1: {
        "id": 1,
        "owner": "analyst",
        "subject": "Card replacement · account 4417",
        "status": "open",
        "note": "Customer verified by callback. Replacement queued.",
    },
    2: {
        "id": 2,
        "owner": "admin",
        "subject": "Privileged recovery · platform admin",
        "status": "escalated",
        "note": "Recovery link requested by security. Do not share outside the response team.",
    },
}
RESET_TOKENS: dict[str, str] = {}
OPS_TOKEN = secrets.token_urlsafe(20)


def shell(title: str, body: str) -> object:
    nav = '<a href="/portal">Portal</a><a href="/logout">Logout</a>' if session.get("user") else '<a href="/">Support login</a>'
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">FINCH // CUSTOMER SUPPORT</div><h1>{title}</h1>'
        "<p>Case management, recovery and platform operations for Finch Financial.</p></div>" + body,
        nav=nav,
    )


@app.get("/")
def index():
    if session.get("user"):
        return redirect("/portal")
    return shell(
        "Support sign-in",
        """<div class="panel"><h2>Response team access</h2>
        <form method="post" action="/login"><label>Username</label><input name="username">
        <label>Password</label><input name="password" type="password">
        <p><button type="submit">Sign in</button></p></form>
        <p class="note">Support accounts are provisioned by the response team. The onboarding backup is not linked from this page.</p></div>""",
    )


@app.get("/robots.txt")
def robots():
    return lab.app.response_class(
        "User-agent: *\nDisallow: /backup/\nDisallow: /admin/\n",
        mimetype="text/plain",
    )


@app.get("/backup/support.json")
def backup():
    return jsonify(
        {
            "service": "finch-support-onboarding",
            "analyst_user": "analyst",
            "analyst_password": "Support2026!",
            "note": "Remove this backup after the response rotation.",
        }
    )


@app.post("/login")
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    record = USERS.get(username)
    if record and record["password"] == password:
        session.clear()
        session["user"] = username
        session["role"] = record["role"]
        return redirect("/portal")
    return shell(
        "Sign-in failed",
        '<div class="flash err">Invalid support credentials.</div><p><a href="/">Try again</a></p>',
    )


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.get("/portal")
def portal():
    if not session.get("user"):
        return redirect("/")
    user = session["user"]
    record = USERS[user]
    rows = "".join(
        f'<div class="panel"><h3>Case #{case["id"]} · {case["subject"]}</h3>'
        f'<p>{case["note"]}</p><span class="tag">{case["status"]}</span> '
        f'<a class="mono" href="/api/cases/{case["id"]}">API view</a></div>'
        for case in CASES.values()
    )
    flag_block = (
        f'<div class="panel"><h2>Analyst flag</h2><pre>{lab.flag("user")}</pre>'
        "<p>Case APIs are available to authenticated staff. Ownership is enforced by the client, according to the migration notes.</p></div>"
        if user == "analyst"
        else '<div class="panel"><h2>Admin recovery complete</h2><p>The platform administration console is available at <a href="/admin">/admin</a>.</p></div>'
    )
    return shell(
        f"Portal · {record['display']}",
        f'<div class="panel"><h2>Open cases</h2><p>Signed in as <code>{user}</code> · role <code>{record["role"]}</code>.</p></div>'
        + flag_block
        + rows,
    )


@app.get("/api/cases/<int:case_id>")
def case_api(case_id: int):
    if not session.get("user"):
        return jsonify({"error": "authentication required"}), 401
    case = CASES.get(case_id)
    if not case:
        return jsonify({"error": "case not found"}), 404
    # VULNERABLE: object ownership is not checked. Analyst can read admin case 2.
    payload = dict(case)
    if case_id == 2:
        token = secrets.token_urlsafe(24)
        RESET_TOKENS[token] = "admin"
        payload["reset_token"] = token
        payload["recovery_target"] = "admin"
        payload["note"] = "Recovery token minted for the platform administrator."
    return jsonify(payload)


@app.route("/reset", methods=["GET", "POST"])
def reset():
    message = ""
    if request.method == "POST":
        username = request.form.get("username", "")
        token = request.form.get("token", "")
        password = request.form.get("password", "")
        if RESET_TOKENS.get(token) == username and len(password) >= 12:
            USERS[username]["password"] = password
            RESET_TOKENS.pop(token, None)
            message = '<div class="flash ok">Password reset complete. <a href="/">Sign in</a></div>'
        else:
            message = '<div class="flash err">Invalid or expired recovery token.</div>'
    return shell(
        "Recovery",
        f"""<div class="panel"><h2>Platform recovery</h2>
        <form method="post"><label>Username</label><input name="username" value="admin">
        <label>Recovery token</label><input name="token"><label>New password (12+ chars)</label>
        <input name="password" type="password"><p><button type="submit">Reset password</button></p></form>
        {message}<p class="note">Recovery tokens are created by support case escalation.</p></div>""",
    )


@app.get("/admin")
def admin():
    if session.get("role") != "admin":
        return shell("Forbidden", '<div class="flash err">Administrator role required.</div>'), 403
    return shell(
        "Platform administration",
        f"""<div class="panel"><h2>Admin session</h2>
        <p>API export: <a href="/api/admin/export">/api/admin/export</a></p>
        <p>Diagnostics token: <code>{OPS_TOKEN}</code></p>
        <p><a href="/admin/diagnostics?token={OPS_TOKEN}">Open diagnostics console</a></p></div>""",
    )


@app.get("/api/admin/export")
def admin_export():
    if session.get("role") != "admin":
        return jsonify({"error": "administrator role required"}), 403
    return jsonify(
        {
            "service": "finch-platform",
            "export": "recovery-cases",
            "api_flag": lab.flag("api"),
            "diagnostics_token": OPS_TOKEN,
        }
    )


@app.route("/admin/diagnostics", methods=["GET", "POST"])
def diagnostics():
    token = request.values.get("token", "")
    if token != OPS_TOKEN:
        return shell("Forbidden", '<div class="flash err">A valid diagnostics token is required.</div>'), 403
    output = ""
    error = ""
    if request.method == "POST":
        host = request.form.get("host", "127.0.0.1")
        # VULNERABLE: operator input is interpolated into a shell command.
        command = f"getent hosts {host} 2>&1 || true"
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=8)
            output = (result.stdout or "") + (result.stderr or "")
        except subprocess.TimeoutExpired:
            output = "diagnostic timed out"
        if lab.flag("root") in output:
            lab.objective_async("root", "root flag read through admin diagnostics command injection")
    return shell(
        "Operations diagnostics",
        f"""<div class="panel"><h2>Resolve a support host</h2>
        <p>The console runs as the service account. The recovery key is staged in <code>/tmp/fintech-root.txt</code>.</p>
        <form method="post"><input type="hidden" name="token" value="{token}">
        <label>Host</label><input name="host" value="127.0.0.1">
        <p><button type="submit">Run diagnostic</button></p></form>{error}</div>
        {f'<div class="panel"><h2>Output</h2><pre>{output}</pre></div>' if output else ''}""",
    )


if __name__ == "__main__":
    lab.run()
