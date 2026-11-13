from __future__ import annotations

import html
import secrets

from flask import request, session

from labkit import Lab

lab = Lab("ATRIUM INVITES", accent="#59c3a5")
app = lab.app

INVITES: dict[str, dict] = {
    "ATR-ADMIN-7X9Q": {"role": "admin", "email": "security@atrium.example", "claimed_by": None, "active": True},
    "ATR-STAFF-2M4K": {"role": "staff", "email": "ops@atrium.example", "claimed_by": None, "active": True},
}
USERS: dict[str, dict] = {
    "admin": {"password": secrets.token_hex(16), "role": "admin"},
}
SEATS: list[dict] = []


def who() -> str | None:
    return session.get("user")


def shell(title: str, body: str) -> object:
    user = who()
    nav = '<a href="/">Home</a><a href="/invite">Invite</a><a href="/invite/list">Invite list</a>'
    if user:
        nav += f'<a href="/welcome">Welcome</a><a href="/logout">Sign out ({html.escape(user)})</a>'
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">ATRIUM // INVITATION SERVICE</div><h1>{title}</h1></div>{body}',
        nav=nav,
    )


@app.get("/")
def index():
    return shell(
        "Invitation service",
        '''<div class="panel"><h2>Join Atrium</h2>
        <p>Atrium seats are invitation-only. Each invitation is addressed to one person, carries one role,
        and is valid for a single signup.</p>
        <p><a class="btn" href="/register">Redeem an invitation</a></p>
        <p class="note">Invited members receive their role from the invitation record.</p></div>''',
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    error = ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip().lower()
        password = request.form.get("password") or ""
        email = (request.form.get("email") or "").strip().lower()
        token = (request.form.get("token") or "").strip()
        invite = INVITES.get(token)
        if not invite:
            error = '<div class="flash err">Unknown invitation token.</div>'
        elif not invite["active"]:
            error = '<div class="flash err">This invitation is no longer active.</div>'
        elif not username or len(password) < 6 or not email:
            error = '<div class="flash err">Username, email and a 6+ character password are required.</div>'
        elif username in USERS:
            error = '<div class="flash err">That username is taken.</div>'
        else:
            # VULNERABLE: the token is not consumed after use and is not bound to the
            # invited email address; the role is taken straight from the invitation.
            USERS[username] = {"password": password, "role": invite["role"]}
            invite["claimed_by"] = username
            SEATS.append({"username": username, "role": invite["role"], "email": email})
            session.clear()
            session["user"] = username
            return shell(
                "Seat created",
                f'<div class="flash ok">Welcome, {html.escape(username)}. Your role is '
                f'<strong>{html.escape(invite["role"])}</strong>.</div><p><a href="/welcome">Continue</a></p>',
            )
    return shell(
        "Redeem invitation",
        f'''{error}<div class="panel"><form method="post" action="/register">
        <label>Invitation token</label><input name="token" placeholder="ATR-...">
        <label>Username</label><input name="username">
        <label>Email</label><input name="email" type="email">
        <label>Password</label><input name="password" type="password">
        <p><button type="submit">Create seat</button></p></form></div>''',
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip().lower()
        password = request.form.get("password") or ""
        account = USERS.get(username)
        if account and account["password"] == password:
            session.clear()
            session["user"] = username
            return lab.redirect("/welcome")
        error = '<div class="flash err">Invalid credentials.</div>'
    return shell(
        "Sign in",
        f'''{error}<div class="panel"><form method="post" action="/login">
        <label>Username</label><input name="username">
        <label>Password</label><input name="password" type="password">
        <p><button type="submit">Sign in</button></p></form></div>''',
    )


@app.get("/logout")
def logout():
    session.clear()
    return lab.redirect("/")


@app.get("/invite/list")
def invite_list():
    # VULNERABLE: the invitation directory is public and returns raw tokens.
    return {
        "invitations": [
            {
                "token": token,
                "role": info["role"],
                "email": info["email"],
                "claimed_by": info["claimed_by"],
                "active": info["active"],
            }
            for token, info in INVITES.items()
        ]
    }


@app.get("/invite")
def invite_page():
    user = who()
    if not user:
        return lab.redirect("/login")
    token = "ATR-STAFF-" + secrets.token_hex(2).upper()
    INVITES[token] = {"role": "staff", "email": "newhire@atrium.example", "claimed_by": None, "active": True}
    return shell(
        "Invite a colleague",
        f'''<div class="panel"><h2>Invitation issued</h2>
        <p class="mono">Token: {html.escape(token)}</p>
        <p>Share the token with one colleague. It carries the <code>staff</code> role.</p></div>''',
    )


@app.get("/seats")
def seats():
    rows = "".join(
        f'<tr><td>{html.escape(seat["username"])}</td><td>{html.escape(seat["role"])}</td><td>{html.escape(seat["email"])}</td></tr>'
        for seat in SEATS
    ) or '<tr><td colspan="3" class="dim">No seats claimed.</td></tr>'
    return shell(
        "Seat directory",
        f'''<div class="panel"><table><thead><tr><th>User</th><th>Role</th><th>Email</th></tr></thead><tbody>{rows}</tbody></table></div>''',
    )


@app.get("/welcome")
def welcome():
    user = who()
    if not user:
        return lab.redirect("/login")
    account = USERS[user]
    extra = ""
    if account["role"] == "admin":
        lab.objective_async("flag", f"admin invitation token {INVITES['ATR-ADMIN-7X9Q']['claimed_by']} reused")
        extra = (
            '<div class="panel"><h2>Administration</h2>'
            f'<p>The seat was created from a privileged invitation. Control-plane secret:</p><pre>{lab.flag("flag")}</pre></div>'
        )
    else:
        extra = '<div class="panel"><h3>Member area</h3><p>Your seat has member privileges only.</p></div>'
    return shell(
        "Welcome to Atrium",
        f'<div class="flash ok">Signed in as {html.escape(user)} · role {html.escape(account["role"])}</div>{extra}',
    )


if __name__ == "__main__":
    lab.run()