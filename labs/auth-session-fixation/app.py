from __future__ import annotations

import secrets

from flask import redirect, request

from labkit import Lab

lab = Lab("HELIOS DESK", accent="#f6ad55")
app = lab.app

USERS = {"alice": "alice123"}
SESSIONS: dict[str, dict] = {}


def shell(title: str, body: str, status: int = 200) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">HELIOS // SUPPORT DESK</div><h1>{title}</h1>'
        "<p>Customer operations and account tooling for the Helios support team.</p></div>"
        f"{body}",
        nav='<a href="/">Home</a><a href="/login">Sign in</a><a href="/account">Account</a>',
        status=status,
    )


def set_sid(response: object, sid: str) -> object:
    response.set_cookie("sid", sid, httponly=True, samesite="Lax")
    return response


def login_form(error: str = "") -> object:
    return shell(
        "Sign in",
        f"""<div class="panel"><h2>Support account</h2>
        <form method="post" action="/login">
          <label>Username</label><input name="username" autocomplete="username">
          <label>Password</label><input name="password" type="password" autocomplete="current-password">
          <p><button type="submit">Authenticate</button></p>
        </form>
        {error}
        <p class="note">The desk supports a `sid` query parameter so shared kiosk links can pre-create a session. Demo account: alice / alice123.</p></div>""",
    )


@app.get("/")
def index():
    sid = request.cookies.get("sid", "")
    user = SESSIONS.get(sid, {}).get("user") if sid else None
    if user:
        body = f'<div class="panel"><h2>Welcome back, {user}</h2><p>Your support session is active.</p><p><a class="btn" href="/account">Open account</a></p></div>'
    else:
        body = '<div class="panel"><h2>Helios support desk</h2><p>Sign in to review customer account state and internal support flags.</p><p><a class="btn" href="/login">Sign in</a></p></div>'
    return shell("Helios support desk", body)


@app.get("/login")
def login_page():
    sid = request.args.get("sid") or request.cookies.get("sid")
    if not sid:
        sid = secrets.token_urlsafe(18)
    # VULNERABLE: the session identifier is accepted from the client.
    SESSIONS.setdefault(sid, {"user": None})
    return set_sid(login_form(), sid)


@app.post("/login")
def login_submit():
    sid = request.args.get("sid") or request.form.get("sid") or request.cookies.get("sid")
    if not sid:
        sid = secrets.token_urlsafe(18)
    session_data = SESSIONS.setdefault(sid, {"user": None})
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if USERS.get(username) == password:
        # VULNERABLE: the pre-authentication session ID is retained after login.
        session_data["user"] = username
        return set_sid(redirect("/account"), sid)
    return set_sid(login_form('<div class="flash err">Invalid username or password.</div>'), sid)


@app.get("/account")
def account():
    sid = request.cookies.get("sid") or request.args.get("sid", "")
    session_data = SESSIONS.get(sid, {}) if sid else {}
    user = session_data.get("user")
    if not user:
        return shell(
            "Authentication required",
            '<div class="flash err">Sign in to view this account.</div><p><a href="/login">Go to sign in</a></p>',
            status=401,
        )
    return shell(
        "Account",
        f"""<div class="panel"><h2>Signed in as {user}</h2>
        <p>Email: alice@helios.local · Role: support agent</p>
        <p>The account vault is unlocked for authenticated support staff.</p>
        <pre>{lab.flag("flag")}</pre></div>""",
    )


@app.get("/logout")
def logout():
    sid = request.cookies.get("sid", "")
    SESSIONS.pop(sid, None)
    response = redirect("/")
    response.delete_cookie("sid")
    return response


if __name__ == "__main__":
    lab.run()
