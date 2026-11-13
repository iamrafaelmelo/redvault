from __future__ import annotations

import html
import secrets

from flask import make_response, redirect, request

from labkit import Lab

lab = Lab("HALCYON WORKSPACE", accent="#38bdf8")
app = lab.app

USERS: dict[str, dict[str, str]] = {
    "nora": {"password": "nora-unlock-2026", "role": "engineer"},
    "ops": {"password": "0perations!2026", "role": "admin"},
}

# Pending first factors. The cookie only carries an opaque handle; the password
# check result is kept server-side.
PENDING: dict[str, str] = {}
SESSIONS: dict[str, str] = {}
OTP_CODES = {"123456"}


def shell(title: str, body: str, nav: str | None = None) -> object:
    if nav is None:
        nav = '<a href="/">Sign in</a><a href="/help/mfa">MFA help</a>'
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">HALCYON // SINGLE SIGN-ON</div><h1>{title}</h1></div>{body}',
        nav=nav,
    )


def session_user() -> str | None:
    handle = request.cookies.get("sid", "")
    return SESSIONS.get(handle)


@app.get("/")
def index():
    user = session_user()
    if user:
        return redirect("/dashboard")
    return shell(
        "Halcyon Workspace",
        """<div class="panel"><h2>Sign in</h2>
        <form method="post" action="/login">
          <label>Username</label><input name="username" autocomplete="username">
          <label>Password</label><input name="password" type="password" autocomplete="current-password">
          <p><button type="submit">Continue</button></p></form>
        <p class="note">Passwords are verified first; the second factor is requested on the next screen.
        Demo account: <code>nora</code> / <code>nora-unlock-2026</code>.</p></div>""",
    )


@app.post("/login")
def login():
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    user = USERS.get(username)
    if not (user and user["password"] == password):
        return shell("Sign-in failed", '<div class="flash err">Invalid username or password.</div>')

    challenge = secrets.token_urlsafe(18)
    PENDING[challenge] = username
    resp = make_response(redirect("/mfa"))
    resp.set_cookie("challenge", challenge, httponly=True, samesite="Lax")
    # VULNERABLE: after the password the server issues a state cookie that the
    # client is trusted to send back unchanged once MFA has been satisfied.
    resp.set_cookie("mfa", "required", httponly=False, samesite="Lax")
    return resp


@app.route("/mfa", methods=["GET", "POST"])
def mfa():
    challenge = request.cookies.get("challenge", "")
    pending_user = PENDING.get(challenge)
    notice = ""
    if request.method == "POST":
        code = request.form.get("code", "").strip()
        if pending_user and code in OTP_CODES:
            handle = secrets.token_urlsafe(18)
            SESSIONS[handle] = pending_user
            PENDING.pop(challenge, None)
            resp = make_response(redirect("/dashboard"))
            resp.set_cookie("sid", handle, httponly=True, samesite="Lax")
            # The flow completion is recorded on the client-visible flag cookie.
            resp.set_cookie("mfa", "complete", httponly=False, samesite="Lax")
            return resp
        notice = '<div class="flash err">That code is not valid. Check your authenticator app.</div>'
    return shell(
        "Second factor",
        f"""<div class="panel"><h2>Verify it is you</h2>
        <p>Signed in as <code>{html.escape(pending_user or "unknown")}</code> — enter the 6-digit code from your authenticator.</p>
        <form method="post"><label>Authentication code</label><input name="code" inputmode="numeric" autocomplete="one-time-code">
        <p><button type="submit">Verify</button></p></form>{notice}
        <p class="note">Training environment authenticator code: <code>123456</code>.</p></div>""",
    )


@app.get("/dashboard")
def dashboard():
    challenge = request.cookies.get("challenge", "")
    mfa_cookie = request.cookies.get("mfa", "")
    header_verified = request.headers.get("X-MFA-Verified", "").lower() in {"true", "1", "yes"}
    user = session_user()

    if user is None and challenge in PENDING and (mfa_cookie == "complete" or header_verified):
        # Shortcut used by the native client and the service worker: the client
        # reports back that the second factor has already been satisfied.
        handle = secrets.token_urlsafe(18)
        SESSIONS[handle] = PENDING.pop(challenge)
        resp = make_response(redirect("/dashboard"))
        resp.set_cookie("sid", handle, httponly=True, samesite="Lax")
        return resp

    if user is None:
        return shell(
            "Second factor required",
            '<div class="flash">Multi-factor authentication has not been completed for this session.</div>'
            '<p><a class="btn" href="/">Start over</a></p>',
        )

    role = USERS[user]["role"]
    flag = ""
    if role == "admin":
        lab.objective_async("flag", "MFA state cookie forged to complete the second factor")
        flag = f'<div class="panel"><h2>Operations vault</h2><pre>{html.escape(lab.flag("flag"))}</pre></div>'
    return shell(
        "Dashboard",
        f"""<div class="panel"><h2>Workspace · {html.escape(user)}</h2>
        <p>Role: <span class="tag">{html.escape(role)}</span> · MFA: <span class="green">verified</span></p>
        <p>Infrastructure alerts, on-call handovers and saved queries are available in this workspace.</p></div>{flag}""",
        nav='<a href="/dashboard">Dashboard</a><a href="/logout">Sign out</a>',
    )


@app.get("/help/mfa")
def help_mfa():
    return shell(
        "Multi-factor help",
        """<div class="panel"><h2>Clients and MFA</h2>
        <p>Web sessions keep the authentication state in the <code>mfa</code> cookie. The desktop client and service
        worker instead attach <code>X-MFA-Verified: true</code> to requests after the authenticator prompt succeeds,
        because those runtimes cannot always write cookies. The dashboard accepts either signal.</p>
        <p>The server also remembers outstanding first-factor challenges as opaque handles in the <code>challenge</code>
        cookie. Once the second factor succeeds, that handle is upgraded to a full session.</p></div>""",
    )


@app.get("/logout")
def logout():
    resp = make_response(redirect("/"))
    for name in ("sid", "mfa", "challenge"):
        resp.delete_cookie(name)
    return resp


if __name__ == "__main__":
    lab.run()