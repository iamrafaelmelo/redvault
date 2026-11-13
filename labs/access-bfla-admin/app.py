from __future__ import annotations

from flask import jsonify, redirect, request, session

from labkit import Lab

lab = Lab("GRIDLINE OPS", accent="#e0a52b")
app = lab.app


def shell(title: str, body: str) -> object:
    return lab.page(title, f'<div class="hero"><div class="kicker">GRIDLINE // OPS CONSOLE</div><h1>{title}</h1></div>{body}', nav='<a href="/">Console</a><a href="/logout">Logout</a>')


@app.get("/")
def index():
    if not session.get("user"):
        return shell(
            "Ops console",
            """<div class="panel"><h2>Shift login</h2><form method="post" action="/login">
            <label>Username</label><input name="username" value="analyst"><label>Password</label><input name="password" type="password" value="analyst123">
            <p><button type="submit">Start shift</button></p></form></div>""",
        )
    return shell(
        "Operations",
        f'<div class="panel"><h2>Welcome, {session["user"]}</h2><p>Your role: <code>{session.get("role", "viewer")}</code></p><p>The interface hides administrative actions. Internal consumers call the export endpoint directly.</p></div>',
    )


@app.post("/login")
def login():
    if request.form.get("username") == "analyst" and request.form.get("password") == "analyst123":
        session["user"] = "analyst"
        session["role"] = "viewer"
        return redirect("/")
    return shell("Login failed", '<div class="flash err">Invalid credentials.</div>')


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.get("/admin/audit/export")
def export_audit():
    # VULNERABLE: route assumes it is only linked from an admin-only page.
    if not session.get("user"):
        return jsonify({"error": "authentication required"}), 401
    return jsonify(
        {
            "export": "nightly-audit",
            "requested_by": session.get("user"),
            "role": session.get("role"),
            "record": "admin-export",
            "vault_note": lab.flag("flag"),
        }
    )


if __name__ == "__main__":
    lab.run()
