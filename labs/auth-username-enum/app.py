from __future__ import annotations

from flask import redirect, request, session

from labkit import Lab

lab = Lab("NORTHSTAR SSO", accent="#d97757")
app = lab.app

USERS = {
    "alice": "alice123",
    "ops": "ranger-ops-77",
    "admin": "Nebula-2024!",
}


def page(body: str, title: str) -> object:
    return lab.page(title, f'<div class="hero"><div class="kicker">NORTHSTAR // IDENTITY</div><h1>{title}</h1></div>{body}', nav='<a href="/">Login</a><a href="/wordlist.txt">wordlist</a>')


@app.get("/")
def index():
    if session.get("user"):
        return redirect("/dashboard")
    return page(
        """<div class="panel"><h2>Operator sign-in</h2>
        <form method="post" action="/login">
          <label>Username</label><input name="username" autocomplete="username">
          <label>Password</label><input name="password" type="password" autocomplete="current-password">
          <p><button type="submit">Authenticate</button></p>
        </form>
        <p class="note">Accounts are provisioned by the identity desk. Username enumeration is a support issue, not a feature.</p></div>""",
        "Sign in",
    )


@app.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if username not in USERS:
        return page(
            '<div class="flash err">No account exists for that username.</div>',
            "Sign in",
        )
    if USERS[username] != password:
        return page(
            '<div class="flash err">Password incorrect for this account.</div>',
            "Sign in",
        )
    session["user"] = username
    return redirect("/dashboard")


@app.get("/wordlist.txt")
def wordlist():
    return lab.app.response_class(
        "alice123\nranger-ops-77\nNebula-2024!\nSpring2025!\nsummer2024\n", mimetype="text/plain"
    )


@app.get("/dashboard")
def dashboard():
    user = session.get("user")
    if not user:
        return redirect("/")
    extra = ""
    if user == "admin":
        extra = f'<div class="panel"><h2>Administrative console</h2><p class="green">Privileged access confirmed.</p><pre>{lab.flag("flag")}</pre></div>'
    return page(
        f'<div class="panel"><h2>Welcome, {user}</h2><p>Your identity token is valid. The account dashboard only displays public operational data.</p>{extra}</div>',
        "Dashboard",
    )


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    lab.run()
