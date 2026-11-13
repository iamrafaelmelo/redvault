from __future__ import annotations

from flask import jsonify, redirect, request, session

from labkit import Lab

lab = Lab("WATCHTOWER", accent="#e0a52b")
app = lab.app

USERS = {
    "analyst": {"password": "analyst123", "role": "analyst"},
}


def shell(title: str, body: str, nav: str | None = None) -> object:
    if nav is None:
        nav = (
            '<a href="/">Console</a><a href="/admin">Admin</a><a href="/logout">Logout</a>'
            if session.get("user")
            else '<a href="/">Login</a>'
        )
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">WATCHTOWER // OPERATIONS</div><h1>{title}</h1></div>{body}',
        nav=nav,
    )


@app.before_request
def guard_admin_reads():
    if request.method == "GET" and (request.path == "/admin" or request.path.startswith("/admin/")):
        if session.get("role") != "admin":
            return lab.page(
                "Read access denied",
                """<div class="hero"><div class="kicker">WATCHTOWER // OPERATIONS</div><h1>Read access denied</h1></div>
                <div class="flash err">403 — GET access to /admin requires the administrator role.</div>
                <p class="note">The rule denies the read path before the route executes.</p>""",
                nav='<a href="/">Console</a><a href="/logout">Logout</a>',
                status=403,
            )


@app.get("/")
def index():
    if not session.get("user"):
        return shell(
            "Shift login",
            """<div class="panel"><h2>Analyst console</h2><form method="post" action="/login">
            <label>Username</label><input name="username" value="analyst" autocomplete="username">
            <label>Password</label><input name="password" type="password" value="analyst123" autocomplete="current-password">
            <p><button type="submit">Start shift</button></p></form>
            <p class="note">Demo credentials are prefilled for this isolated lab.</p></div>""",
        )
    return shell(
        "Operations",
        f"""<div class="panel"><h2>Welcome, {session["user"]}</h2>
        <p>Role: <code>{session.get("role", "analyst")}</code></p>
        <p>The admin console is read-only for analysts. Internal jobs are supposed to call the export action with a write request.</p></div>""",
    )


@app.post("/login")
def login():
    data = request.get_json(silent=True) if request.is_json else request.form
    data = data or {}
    username = str(data.get("username", ""))
    password = str(data.get("password", ""))
    user = USERS.get(username)
    if user and user["password"] == password:
        session.clear()
        session["user"] = username
        session["role"] = user["role"]
        if request.is_json:
            return jsonify({"ok": True, "user": username, "role": user["role"]})
        return redirect("/")
    if request.is_json:
        return jsonify({"error": "invalid credentials"}), 401
    return shell("Sign-in failed", '<div class="flash err">Invalid username or password.</div>', nav='<a href="/">Login</a>')


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/admin", methods=["GET", "POST"])
def admin():
    if not session.get("user"):
        return redirect("/")

    if request.method == "GET":
        # The read path checks the role; the write path below does not.
        if session.get("role") != "admin":
            return lab.page(
                "Read access denied",
                '<div class="flash err">Administrator role required.</div>',
                status=403,
            )
        return shell(
            "Admin console",
            f'<div class="panel"><h2>Nightly settlement</h2><pre>{lab.flag("flag")}</pre></div>',
        )

    # VULNERABLE: POST reaches the administrative action without a role check.
    return shell(
        "Admin console",
        f"""<div class="panel"><h2>Nightly settlement</h2>
        <p class="green">Administrative export executed by {session["user"]}.</p>
        <pre>{lab.flag("flag")}</pre>
        <p class="note">The request method changed; the authorization decision did not.</p></div>""",
    )


@app.route("/admin/export", methods=["GET", "POST"])
def admin_export():
    if not session.get("user"):
        return jsonify({"error": "authentication required"}), 401

    if request.method == "GET":
        if session.get("role") != "admin":
            return jsonify({"error": "administrator role required"}), 403
        return jsonify({"export": "settlement", "requested_by": session["user"], "flag": lab.flag("flag")})

    # VULNERABLE: the export route only enforces authorization on GET.
    return jsonify(
        {
            "export": "settlement",
            "requested_by": session["user"],
            "role": session.get("role"),
            "flag": lab.flag("flag"),
        }
    )


if __name__ == "__main__":
    lab.run()
