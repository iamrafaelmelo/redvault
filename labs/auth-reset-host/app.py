from __future__ import annotations

import secrets

from flask import redirect, request, session

from labkit import Lab

lab = Lab("MERIDIAN ID", accent="#c9a227")
app = lab.app

USERS = {
    "analyst": {"password": "analyst123", "email": "analyst@meridian.local"},
    "admin": {"password": "unset-admin-password", "email": "admin@meridian.local"},
}
RESET_TOKENS: dict[str, str] = {}
OUTBOX: list[dict] = []


def layout(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">MERIDIAN // IDENTITY RECOVERY</div><h1>{title}</h1></div>{body}',
        nav='<a href="/">Login</a><a href="/outbox">Mail sink</a>',
    )


@app.get("/")
def index():
    if session.get("user"):
        return redirect("/account")
    return layout(
        "Meridian ID",
        """<div class="panel"><h2>Account access</h2>
        <form method="post" action="/login"><label>Username</label><input name="username">
        <label>Password</label><input name="password" type="password"><p><button type="submit">Log in</button></p></form>
        <p><a href="/forgot">Forgot password?</a></p></div>""",
    )


@app.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if username in USERS and USERS[username]["password"] == password:
        session["user"] = username
        return redirect("/account")
    return layout("Login failed", '<div class="flash err">Invalid username or password.</div>')


@app.get("/account")
def account():
    user = session.get("user")
    if not user:
        return redirect("/")
    extra = ""
    if user == "admin":
        extra = f'<div class="panel"><h2>Admin control plane</h2><pre>{lab.flag("flag")}</pre></div>'
    return layout(
        "Account",
        f'<div class="panel"><h2>Signed in as {user}</h2><p>Email: {USERS[user]["email"]}</p>{extra}</div>',
    )


@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "GET":
        return layout(
            "Password recovery",
            """<div class="panel"><h2>Recover access</h2>
            <form method="post"><label>Account email</label><input name="email" type="email" placeholder="name@meridian.local">
            <p><button type="submit">Send reset link</button></p></form>
            <p class="note">The mail sink is exposed in this training environment. Inspect the generated message at `/outbox`.</p></div>""",
        )
    email = request.form.get("email", "").strip().lower()
    username = next((name for name, data in USERS.items() if data["email"] == email), None)
    if not username:
        return layout("Recovery requested", '<div class="flash">If the account exists, a message has been queued.</div>')
    token = secrets.token_urlsafe(24)
    RESET_TOKENS[token] = username
    # VULNERABLE: trusts an inbound header when constructing the reset URL.
    host = request.headers.get("X-Forwarded-Host", request.host)
    link = f"http://{host}/reset/{token}"
    OUTBOX.insert(0, {"to": email, "subject": "Reset your Meridian ID", "link": link, "token": token})
    return redirect("/outbox")


@app.get("/outbox")
def outbox():
    messages = "".join(
        f'<div class="panel"><div class="mono dim">TO: {m["to"]} · {m["subject"]}</div><p><a href="{m["link"]}">{m["link"]}</a></p></div>'
        for m in OUTBOX
    ) or '<div class="panel"><p>No messages queued.</p></div>'
    return layout(
        "Local mail sink",
        f'<div class="flash">Training-only mail catcher. Trigger a recovery, then inspect the generated link.</div>{messages}',
    )


@app.route("/reset/<token>", methods=["GET", "POST"])
def reset(token: str):
    username = RESET_TOKENS.get(token)
    if not username:
        return layout("Invalid link", '<div class="flash err">The reset token is invalid or already used.</div>')
    if request.method == "GET":
        return layout(
            "Choose a new password",
            f'''<div class="panel"><h2>Reset access for {username}</h2>
            <form method="post"><label>New password</label><input name="password" type="password">
            <p><button type="submit">Set password</button></p></form></div>''',
        )
    password = request.form.get("password", "")
    if len(password) < 8:
        return layout("Weak password", '<div class="flash err">Use at least 8 characters.</div>')
    USERS[username]["password"] = password
    del RESET_TOKENS[token]
    return layout("Password changed", '<div class="flash ok">The password was updated. <a href="/">Sign in</a>.</div>')


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    lab.run()
