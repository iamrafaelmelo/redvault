from __future__ import annotations

import secrets
import subprocess
from pathlib import Path

from flask import jsonify, redirect, request, session

from labkit import Lab

lab = Lab("NEXUS COMMERCE", accent="#ee6c4d")
app = lab.app

Path("/tmp/nexus-root.txt").write_text(lab.flag("root") + "\n")
OPS_TOKEN = secrets.token_urlsafe(20)


def shell(title: str, body: str) -> object:
    nav = '<a href="/">Store</a><a href="/support">Support</a><a href="/logout">Logout</a>' if session.get("user") else '<a href="/">Store</a><a href="/support">Support login</a>'
    return lab.page(title, f'<div class="hero"><div class="kicker">NEXUS // COMMERCE PLATFORM</div><h1>{title}</h1><p>Field equipment, checkout and support operations.</p></div>{body}', nav=nav)


@app.get("/")
def index():
    return shell(
        "Nexus storefront",
        """<div class="grid"><div class="panel"><h2>Trail systems</h2><p>Modular field kits for long deployments.</p></div>
        <div class="panel"><h2>Support operations</h2><p>Staff tools for order review and deployment diagnostics.</p></div></div>
        <p class="note">Staff entry points are not linked from the storefront. The deployment workspace retains a migration backup.</p>""",
    )


@app.get("/robots.txt")
def robots():
    return lab.app.response_class("User-agent: *\nDisallow: /workspace/\nDisallow: /support/\n", mimetype="text/plain")


@app.get("/workspace/backup.json")
def backup():
    return jsonify(
        {
            "service": "nexus-support-migration",
            "support_user": "mira",
            "support_password": "FieldSupport!",
            "note": "Remove before the workspace is published.",
        }
    )


@app.route("/support", methods=["GET", "POST"])
def support_login():
    error = ""
    if request.method == "POST":
        if request.form.get("username") == "mira" and request.form.get("password") == "FieldSupport!":
            session["user"] = "mira"
            return redirect("/support")
        error = '<div class="flash err">Invalid support credentials.</div>'
    if session.get("user"):
        return shell(
            "Support console",
            f'''<div class="panel"><h2>Support session · mira</h2>
            <p>Your support flag is unlocked:</p><pre>{lab.flag("user")}</pre>
            <p>The migration export endpoint is available at <a href="/api/v1/admin/export">/api/v1/admin/export</a>.</p></div>
            <div class="panel"><h2>Operations</h2><p>Export includes a short-lived ops token for diagnostics. The support role was never given an admin permission — but the route forgot to check.</p></div>''',
        )
    return shell(
        "Support login",
        f'''<div class="panel"><h2>Staff access</h2><form method="post">
        <label>Username</label><input name="username"><label>Password</label><input name="password" type="password">
        <p><button type="submit">Sign in</button></p></form>{error}
        <p class="note">Support staff credentials are provisioned by the migration workspace.</p></div>''',
    )


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.get("/api/v1/admin/export")
def export():
    if not session.get("user"):
        return jsonify({"error": "support authentication required"}), 401
    # BFLA: no admin role check.
    return jsonify(
        {
            "export": "orders-and-ops",
            "requested_by": session["user"],
            "api_flag": lab.flag("api"),
            "ops_token": OPS_TOKEN,
            "diagnostics": "/diagnostics?token=<ops_token>&host=127.0.0.1",
        }
    )


@app.route("/diagnostics", methods=["GET", "POST"])
def diagnostics():
    token = request.values.get("token", "")
    output = ""
    error = ""
    if token != OPS_TOKEN:
        error = '<div class="flash err">A valid ops token is required. Export it from the support API.</div>'
    elif request.method == "POST":
        host = request.form.get("host", "127.0.0.1")
        # VULNERABLE: shell interpolation in the operations console.
        command = f"getent hosts {host} 2>&1 || true"
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=8)
            output = (result.stdout or "") + (result.stderr or "")
        except subprocess.TimeoutExpired:
            output = "diagnostic timed out"
        if lab.flag("root") in output:
            lab.objective_async("root", "root flag file read through diagnostics command injection")
    form = f'''<div class="panel"><h2>Network diagnostics</h2>
    <form method="post"><input type="hidden" name="token" value="{token}">
    <label>Host</label><input name="host" value="127.0.0.1"><p><button type="submit">Run diagnostic</button></p></form>
    <p class="note">The service account can read /tmp/nexus-root.txt.</p></div>''' if token == OPS_TOKEN else ""
    return shell(
        "Operations diagnostics",
        f'{error}{form}{f"<div class=\"panel\"><h2>Output</h2><pre>{output}</pre></div>" if output else ""}',
    )


if __name__ == "__main__":
    lab.run()
