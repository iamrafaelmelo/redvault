from __future__ import annotations

from flask import redirect, request, session

from labkit import Lab

lab = Lab("OPERATOR GATE", accent="#68d391")
app = lab.app

OPERATOR = "operator"
PASSWORD = "operator123"
OTP_CODE = "4815"


def shell(title: str, body: str, status: int = 200) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">OPERATOR // ACCESS GATE</div><h1>{title}</h1>'
        "<p>Two-step authentication for the field operations console.</p></div>"
        f"{body}",
        nav='<a href="/">Home</a><a href="/login">Sign in</a><a href="/verify">Verify</a>',
        status=status,
    )


def verify_form(message: str = "") -> object:
    return shell(
        "Enter verification code",
        f"""<div class="panel"><h2>One-time code</h2>
        <p>A four-digit code was generated for the operator device. Enter it to finish signing in.</p>
        <form method="post" action="/verify">
          <label>Verification code</label><input name="code" inputmode="numeric" maxlength="4" placeholder="0000" autocomplete="one-time-code">
          <p><button type="submit">Verify code</button></p>
        </form>
        {message}
        <p class="note">The demo gateway has no attempt limit configured.</p></div>""",
    )


@app.get("/")
def index():
    if session.get("otp_verified"):
        return shell(
            "Operations console",
            f'<div class="panel"><h2>Authenticated operator session</h2><pre>{lab.flag("flag")}</pre></div>',
        )
    return shell(
        "Operator gate",
        """<div class="panel"><h2>Field operations console</h2>
        <p>Operator access requires a password and a four-digit one-time code.</p>
        <p><a class="btn" href="/login">Sign in</a></p>
        <p class="note">Demo credentials: operator / operator123</p></div>""",
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if username == OPERATOR and password == PASSWORD:
            session.clear()
            session["otp_user"] = OPERATOR
            return verify_form('<div class="flash ok">Password accepted. A code was sent to the operator device.</div>')
        error = '<div class="flash err">Invalid operator credentials.</div>'
    return shell(
        "Operator sign-in",
        f"""<div class="panel"><h2>Step 1 · Password</h2>
        <form method="post" action="/login">
          <label>Username</label><input name="username" autocomplete="username">
          <label>Password</label><input name="password" type="password" autocomplete="current-password">
          <p><button type="submit">Continue</button></p>
        </form>
        {error}
        <p class="note">Demo account: operator / operator123</p></div>""",
    )


@app.route("/verify", methods=["GET", "POST"])
def verify():
    if not session.get("otp_user"):
        return redirect("/login")
    if request.method == "POST":
        code = request.values.get("code", "").strip()
        if code == OTP_CODE:
            session["otp_verified"] = True
            return shell(
                "Verification complete",
                f"""<div class="panel"><h2>Access granted</h2>
                <p class="green">The one-time code was accepted.</p>
                <pre>{lab.flag("flag")}</pre></div>""",
            )
        # VULNERABLE: unlimited incorrect attempts, no delay or lockout.
        return verify_form('<div class="flash err">Incorrect code. Try again.</div>')
    return verify_form()


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    lab.run()
