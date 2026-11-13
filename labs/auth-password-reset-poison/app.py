from __future__ import annotations

import html
import secrets
import time

from flask import redirect, request, session

from labkit import Lab

lab = Lab("VELOCITY ID", accent="#8b7cf6")
app = lab.app

USERS: dict[str, dict[str, str]] = {
    "garin": {
        "password": "scooter-2026",
        "email": "garin@velocity.local",
        "role": "analyst",
        "id": "8b2d51a4-6f19-4a57-9f4c-2c1d0e7f3a11",
    },
    "sarah": {
        "password": "S4rah!Ops2026",
        "email": "sarah@velocity.local",
        "role": "admin",
        "id": "1f0c3c1e-7a52-4f5e-8d21-6b0f7c9c7a10",
    },
}

# token -> {"user": target account, "requested_by": account id the requester claimed}
RESET_TOKENS: dict[str, dict[str, str]] = {}
MAILBOX: list[dict[str, str]] = []


def shell(title: str, body: str, nav: str | None = None) -> object:
    if nav is None:
        nav = (
            '<a href="/account">Account</a><a href="/logout">Sign out</a>'
            if session.get("user")
            else '<a href="/">Sign in</a><a href="/forgot">Recovery</a>'
        )
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">VELOCITY // IDENTITY RECOVERY</div><h1>{title}</h1></div>{body}',
        nav=nav,
    )


def public_base() -> str:
    # VULNERABLE: the application reconstructs its own origin from whatever the
    # request says it is, instead of a configured canonical URL.
    scheme = request.headers.get("X-Forwarded-Proto", "http")
    host = request.headers.get("X-Forwarded-Host") or request.headers.get("Host") or request.host
    return f"{scheme}://{host}"


@app.get("/")
def index():
    if session.get("user"):
        return redirect("/account")
    return shell(
        "Velocity ID",
        """<div class="panel"><h2>Staff sign-in</h2>
        <form method="post" action="/login">
          <label>Username</label><input name="username" autocomplete="username">
          <label>Password</label><input name="password" type="password" autocomplete="current-password">
          <p><button type="submit">Sign in</button></p></form>
        <p><a href="/forgot">Forgot your password?</a></p>
        <p class="note">Demo credentials: <code>garin</code> / <code>scooter-2026</code> (field engineer account).</p></div>""",
    )


@app.post("/login")
def login():
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    user = USERS.get(username)
    if user and user["password"] == password:
        session.clear()
        session["user"] = username
        return redirect("/account")
    return shell("Sign-in failed", '<div class="flash err">Invalid username or password.</div>', nav='<a href="/">Sign in</a>')


@app.get("/account")
def account():
    username = session.get("user")
    if not username:
        return redirect("/")
    user = USERS[username]
    extra = ""
    # Business data visible to every analyst: the staff identity directory.
    directory = "".join(
        f'<li>{html.escape(name)} · <span class="dim">{html.escape(data["email"])}</span> · '
        f'<code>{html.escape(data["id"])}</code> · {html.escape(data["role"])}</li>'
        for name, data in USERS.items()
    )
    if user["role"] == "admin":
        lab.objective_async("flag", "password reset poisoned through Host header, admin session obtained")
        extra = (
            '<div class="panel"><h2>Admin control panel</h2>'
            f'<p>Last weekly compliance export is stored below.</p><pre>{html.escape(lab.flag("flag"))}</pre></div>'
        )
    return shell(
        "Account",
        f"""<div class="panel"><h2>Signed in as {html.escape(username)}</h2>
        <table><tr><th>Email</th><td>{html.escape(user["email"])}</td></tr>
        <tr><th>Role</th><td>{html.escape(user["role"])}</td></tr>
        <tr><th>Account ID</th><td><code>{html.escape(user["id"])}</code></td></tr></table>
        <p class="note">New starters can be looked up by account ID in the staff directory. The ID is a random
        identifier and is not considered a secret by the identity team.</p>
        <h3>Staff identity directory</h3><ul class="list">{directory}</ul></div>{extra}""",
    )


@app.route("/forgot", methods=["GET", "POST"])
def forgot():
    if request.method == "GET":
        return shell(
            "Password recovery",
            """<div class="panel"><h2>Reset your password</h2>
            <form method="post"><label>Work email</label><input name="email" type="email" placeholder="name@velocity.local">
            <label>Account ID (optional)</label><input name="user_id" placeholder="account UUID from your profile">
            <p><button type="submit">Email me a reset link</button></p></form>
            <p class="note">The account ID comes pre-filled by the mobile app. Links are generated against the origin
            the request arrived on so the mail works behind our load balancer. The relay lives at <code>/mail</code>
            in this training environment.</p></div>""",
            nav='<a href="/">Sign in</a><a href="/mail">Mail relay</a>',
        )
    email = request.form.get("email", "").strip().lower()
    claimed_id = request.form.get("user_id", "").strip()
    username = next((name for name, data in USERS.items() if data["email"] == email), None)
    # The mobile client looks accounts up by their opaque directory ID.
    if claimed_id:
        username = next((name for name, data in USERS.items() if data["id"] == claimed_id), username)
    if not username:
        # Keep the response identical whether or not the account exists.
        return shell(
            "Recovery requested",
            '<div class="flash ok">If that address belongs to a Velocity account, a reset link is on its way.</div>',
            nav='<a href="/">Sign in</a><a href="/mail">Mail relay</a>',
        )
    token = secrets.token_urlsafe(24)
    # VULNERABLE: the token is registered for the account that owns the e-mail
    # address; the caller-supplied account ID is only stored, never checked.
    RESET_TOKENS[token] = {"user": username, "requested_by": claimed_id}
    link = f"{public_base()}/reset?token={token}"
    MAILBOX.insert(
        0,
        {
            "to": email,
            "subject": "Reset your Velocity ID password",
            "received": time.strftime("%Y-%m-%d %H:%M:%S"),
            "link": link,
            "token": token,
        },
    )
    return shell(
        "Recovery requested",
        '<div class="flash ok">If that address belongs to a Velocity account, a reset link is on its way.</div>'
        '<p><a class="btn" href="/mail">Open the mail relay</a></p>',
        nav='<a href="/">Sign in</a><a href="/mail">Mail relay</a>',
    )


@app.get("/mail")
def mail():
    messages = "".join(
        f"""<div class="panel">
        <div class="mono dim">From relay@velocity.local · {html.escape(m["received"])}</div>
        <h3>{html.escape(m["subject"])}</h3>
        <table><tr><th>To</th><td>{html.escape(m["to"])}</td></tr>
        <tr><th>Reset link</th><td><code>{html.escape(m["link"])}</code></td></tr></table></div>"""
        for m in MAILBOX
    ) or '<div class="panel"><p>No messages in the relay.</p></div>'
    return shell(
        "Mail relay",
        f'<div class="flash">Outbound SMTP is captured here in this training environment. Newest first.</div>{messages}',
        nav='<a href="/">Sign in</a><a href="/forgot">Recovery</a>',
    )


@app.route("/reset", methods=["GET", "POST"])
def reset():
    token = request.args.get("token", "") or request.form.get("token", "")
    record = RESET_TOKENS.get(token)
    if not record:
        return shell("Invalid link", '<div class="flash err">This reset link is invalid or has already been used.</div>', nav='<a href="/">Sign in</a>')
    username = record["user"]
    if request.method == "GET":
        return shell(
            "Choose a new password",
            f"""<div class="panel"><h2>Reset password for {html.escape(username)}</h2>
            <form method="post"><input type="hidden" name="token" value="{html.escape(token)}">
            <label>New password</label><input name="password" type="password">
            <label>Repeat password</label><input name="password2" type="password">
            <p><button type="submit">Update password</button></p></form></div>""",
            nav='<a href="/">Sign in</a>',
        )
    password = request.form.get("password", "")
    confirm = request.form.get("password2", request.form.get("password", ""))
    if len(password) < 8:
        return shell("Weak password", '<div class="flash err">The password must be at least 8 characters.</div>', nav='<a href="/">Sign in</a>')
    if password != confirm:
        return shell("Mismatch", '<div class="flash err">The two passwords do not match.</div>', nav='<a href="/">Sign in</a>')
    USERS[username]["password"] = password
    RESET_TOKENS.pop(token, None)
    session.clear()
    session["user"] = username
    session.modified = True
    return shell(
        "Password updated",
        '<div class="flash ok">Your password has been changed and this browser is signed in.</div>'
        '<p><a class="btn" href="/account">Open account</a></p>',
        nav='<a href="/account">Account</a><a href="/mail">Mail relay</a>',
    )


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    lab.run()