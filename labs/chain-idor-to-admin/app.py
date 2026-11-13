from __future__ import annotations

import secrets

from flask import jsonify, redirect, request, session

from labkit import Lab

lab = Lab("ATLAS SUPPORT", accent="#ef8354")
app = lab.app

USERS = {
    1: {"username": "intern", "password": "intern123", "role": "support", "email": "intern@atlas.local"},
    2: {"username": "admin", "password": secrets.token_urlsafe(24), "role": "admin", "email": "admin@atlas.local"},
}
ADMIN_RESET_TOKEN = secrets.token_urlsafe(18)


def layout(title: str, body: str) -> object:
    nav = '<a href="/">Home</a><a href="/api/users/1">Directory API</a><a href="/logout">Logout</a>' if session.get("uid") else '<a href="/">Login</a>'
    return lab.page(title, f'<div class="hero"><div class="kicker">ATLAS // SUPPORT DESK</div><h1>{title}</h1></div>{body}', nav=nav)


@app.get("/")
def index():
    if not session.get("uid"):
        return layout(
            "Support login",
            """<div class="panel"><h2>Support desk</h2><form method="post" action="/login">
            <label>Username</label><input name="username" value="intern">
            <label>Password</label><input name="password" type="password" value="intern123">
            <p><button type="submit">Sign in</button></p></form>
            <p class="note">Support staff can read user records through the directory API. The admin reset endpoint is internal.</p></div>""",
        )
    user = USERS[session["uid"]]
    admin = f'<div class="panel"><h2>Administrative records</h2><pre>{lab.flag("flag")}</pre></div>' if user["role"] == "admin" else ""
    return layout(
        "Support console",
        f'<div class="panel"><h2>Welcome, {user["username"]}</h2><p>Role: {user["role"]}</p><p>The directory API is at `/api/users/<id>`.</p></div>{admin}',
    )


@app.post("/login")
def login():
    username = request.form.get("username", "")
    password = request.form.get("password", "")
    for uid, user in USERS.items():
        if user["username"] == username and user["password"] == password:
            session["uid"] = uid
            return redirect("/")
    return layout("Login failed", '<div class="flash err">Invalid credentials.</div>')


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.get("/api/users/<int:uid>")
def users(uid: int):
    if "uid" not in session:
        return jsonify({"error": "authentication required"}), 401
    user = USERS.get(uid)
    if not user:
        return jsonify({"error": "not found"}), 404
    # VULNERABLE: authenticated support users can read any user object.
    record = {"id": uid, "username": user["username"], "role": user["role"], "email": user["email"]}
    if uid == 2:
        record["account_recovery"] = {
            "provider": "support-manual",
            "reset_token": ADMIN_RESET_TOKEN,
            "note": "Internal migration token. Support should never call this endpoint for the admin record.",
        }
    return jsonify(record)


@app.route("/support/reset", methods=["GET", "POST"])
def support_reset():
    notice = ""
    if request.method == "POST":
        username = request.form.get("username", "")
        token = request.form.get("token", "")
        password = request.form.get("password", "")
        user = next((u for u in USERS.values() if u["username"] == username), None)
        if not user or token != ADMIN_RESET_TOKEN:
            notice = '<div class="flash err">Reset token is invalid for that account.</div>'
        elif len(password) < 8:
            notice = '<div class="flash err">Password must be at least eight characters.</div>'
        else:
            # VULNERABLE: a support migration token resets any account, including admin.
            user["password"] = password
            notice = f'<div class="flash ok">Password reset for {username}. <a href="/">Sign in</a>.</div>'
    return layout(
        "Support-assisted reset",
        f'''<div class="panel"><h2>Account recovery</h2>
        <p>This endpoint is used by the internal migration team. Tokens are issued once and tied to the account.</p>
        <form method="post">
          <label>Username</label><input name="username" value="admin">
          <label>Recovery token</label><input name="token">
          <label>New password</label><input name="password" type="password">
          <p><button type="submit">Reset password</button></p>
        </form>{notice}</div>''',
    )


if __name__ == "__main__":
    lab.run()
