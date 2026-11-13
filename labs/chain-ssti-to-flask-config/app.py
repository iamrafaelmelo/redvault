from __future__ import annotations

import html
import secrets

from flask import render_template_string, request, session
from markupsafe import escape

from labkit import Lab

lab = Lab("TERRAFORM DESK", accent="#63b3ed")
app = lab.app

# Real Flask-signed cookie sessions. The key lives in app.config so the template
# context exposes it through config — that is the SSTI-to-session chain.
app.secret_key = "terraform-" + secrets.token_urlsafe(24)
app.config.update(
    SESSION_COOKIE_NAME="tf_session",
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    ADMIN_ACCESS_CODE="ops-" + secrets.token_hex(8),
)
app.config["FLAG_SERVICE"] = "terraform-flagd://127.0.0.1/"

TEMPLATES = {
    "welcome": (
        "Welcome aboard, {name}! Your {{ team }} workspace is provisioned. "
        "Cost alerts go to {email}."
    ),
    "renewal": (
        "Hi {name}, your Terraform Desk plan renews on the 1st. "
        "Questions? Reply to {email}."
    ),
}
EMAILS: dict[str, str] = {}


def shell(title: str, body: str, nav: str | None = None) -> object:
    if nav is None:
        nav = '<a href="/">Composer</a><a href="/admin">Admin</a><a href="/login">Sign in</a>'
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">TERRAFORM // MESSAGE DESK</div><h1>{title}</h1></div>{body}',
        nav=nav,
    )


@app.get("/")
def index():
    user = session.get("user")
    if not user:
        return shell(
            "Terraform Desk",
            """<div class="panel"><h2>Provisioning notifications</h2>
            <p>Every workspace change sends an operator notification. Templates are rendered
            with the request data so the team can preview them before a rollout.</p>
            <p><a class="btn" href="/login">Sign in</a></p>
            <p class="note">Template variables: <code>{{ name }}</code>, <code>{{ email }}</code>,
            <code>{{ template }}</code>.</p></div>""",
        )
    return compose(user)


@app.get("/login")
def login_form():
    return shell(
        "Sign in",
        """<div class="panel"><h2>Operator login</h2>
        <form method="post" action="/login"><label>Username</label><input name="username" value="operator">
        <label>Password</label><input name="password" type="password" value="Terraform-2026!">
        <p><button type="submit">Sign in</button></p></form></div>""",
    )


@app.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if username and password == "Terraform-2026!":
        session.clear()
        session["user"] = username[:40]
        session["role"] = "operator"
        return lab.redirect("/")
    return shell("Login failed", '<div class="flash err">Invalid credentials. Demo: <code>operator</code> / <code>Terraform-2026!</code>.</div>', nav='<a href="/login">Sign in</a>')


def compose(user: str) -> object:
    raw_name = request.values.get("name", user)
    raw_email = request.values.get("email", "ops@terraform-desk.local")
    template = request.values.get("template", "welcome")
    body_text = TEMPLATES.get(template, TEMPLATES["welcome"]).format(name=raw_name, email=raw_email)
    rendered = ""
    error = ""
    try:
        # VULNERABLE: the preview pipeline renders the operator's data through
        # render_template_string, handing the template whatever context it carries.
        rendered = render_template_string(body_text, name=raw_name, email=raw_email)
    except Exception as exc:  # noqa: BLE001 - preview errors shown in the UI
        error = f'<div class="flash err">Render error: <code>{escape(type(exc).__name__)}: {escape(str(exc))[:500]}</code></div>'
    if lab.flag("flag") in rendered:
        lab.objective_async("flag", "SSTI leaked app.config SECRET_KEY and the forged cookie reached /admin")
    return shell(
        "Message composer",
        f"""<div class="panel"><h2>Preview a notification</h2>
        <form method="get" action="/">
          <label>Template</label><select name="template">
            <option value="welcome"{" selected" if template == "welcome" else ""}>Workspace welcome</option>
            <option value="renewal"{" selected" if template == "renewal" else ""}>Renewal reminder</option>
          </select>
          <label>Recipient name</label><input name="name" value="{escape(raw_name)}">
          <label>Recipient email</label><input name="email" value="{escape(raw_email)}">
          <p><button type="submit">Render preview</button></p>
        </form>{error}</div>
        <div class="panel"><h2>Rendered</h2><p>{rendered}</p></div>
        <p class="note">Signed in as <code>{escape(str(session.get("user")))}</code> · session cookie
        <code>tf_session</code> is a Flask SecureCookieSession.</p>""",
    )


@app.get("/admin")
def admin():
    if session.get("is_admin") is not True:
        return shell(
            "Admin",
            '<div class="flash err">Administrator session required.</div>'
            '<p class="note">The admin console trusts the signed session claim <code>is_admin</code>.</p>',
            nav='<a href="/">Composer</a><a href="/login">Sign in</a>',
        ), 403
    return shell(
        "Admin console",
        f"""<div class="panel"><h2>Workspace control</h2>
        <p>Session: <code>{escape(str(session.get("user")))}</code> · admin claim verified.</p>
        <pre>{lab.flag("flag")}</pre></div>""",
    )


@app.get("/debug/session")
def debug_session():
    """Development helper: shows the decoded (unverified-looking) session claims."""
    return {
        "cookie": app.config["SESSION_COOKIE_NAME"],
        "interface": "flask.sessions.SecureCookieSessionInterface",
        "claims": {key: session[key] for key in session.keys()},
    }


@app.post("/logout")
def logout():
    session.clear()
    return lab.redirect("/login")


if __name__ == "__main__":
    lab.run()