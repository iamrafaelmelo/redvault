from __future__ import annotations

from flask import redirect, request, session

from labkit import Lab

lab = Lab("CIVIC REGISTRY", accent="#d97757")
app = lab.app

USERS = {
    "alice": {"password": "alice123", "display": "Alice", "department": "Research", "role": "member"},
    "admin": {"password": "not-used", "display": "Registry Admin", "department": "Operations", "role": "admin"},
}


def shell(title: str, body: str) -> object:
    nav = '<a href="/profile">Profile</a><a href="/logout">Logout</a>' if session.get("user") else '<a href="/">Login</a>'
    return lab.page(title, f'<div class="hero"><div class="kicker">CIVIC // REGISTRY</div><h1>{title}</h1></div>{body}', nav=nav)


@app.get("/")
def index():
    if session.get("user"):
        return redirect("/profile")
    return shell(
        "Registry access",
        """<div class="panel"><h2>Sign in</h2><form method="post" action="/login">
        <label>Username</label><input name="username" value="alice"><label>Password</label><input name="password" type="password" value="alice123">
        <p><button type="submit">Sign in</button></p></form></div>""",
    )


@app.post("/login")
def login():
    username = request.form.get("username", "")
    data = USERS.get(username)
    if data and data["password"] == request.form.get("password", ""):
        session["user"] = username
        return redirect("/profile")
    return shell("Login failed", '<div class="flash err">Invalid credentials.</div>')


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/profile", methods=["GET", "POST"])
def profile():
    username = session.get("user")
    if not username:
        return redirect("/")
    data = USERS[username]
    if request.method == "POST":
        data["display"] = request.form.get("display", data["display"])[:80]
        data["department"] = request.form.get("department", data["department"])[:80]
        # VULNERABLE: binds a privileged field from user-controlled input.
        if "role" in request.form:
            data["role"] = request.form.get("role", data["role"])
        return redirect("/profile")
    admin = ""
    if data["role"] == "admin":
        admin = f'<div class="panel"><h2>Registry administration</h2><p class="green">Admin role active.</p><pre>{lab.flag("flag")}</pre></div>'
    return shell(
        f"Profile · {username}",
        f'''<div class="panel"><h2>{data["display"]}</h2><p>Department: {data["department"]} · Role: <code>{data["role"]}</code></p>
        <form method="post">
          <label>Display name</label><input name="display" value="{data["display"]}">
          <label>Department</label><input name="department" value="{data["department"]}">
          <p><button type="submit">Save profile</button></p>
        </form>
        <p class="note">The form exposes only the two profile fields. The update handler accepts more.</p></div>{admin}''',
    )


if __name__ == "__main__":
    lab.run()
