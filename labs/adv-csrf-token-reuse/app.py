from __future__ import annotations

import html
import secrets

from flask import request

from labkit import Lab

lab = Lab("GRAYTIDE", accent="#8b9df7")
app = lab.app

SESSIONS: dict[str, dict] = {}
CALLBACKS: list[dict] = []
# Every token the preview page has ever published.
PUBLIC_LEDGER: set[str] = set()

PUBLIC_EMAILS = [
    ("press@graytide.example", "Press desk", "media"),
    ("billing@graytide.example", "Billing notifications", "finance"),
    ("devrel@graytide.example", "Developer relations", "community"),
]


def shell(title: str, body: str, nav: str | None = None) -> object:
    if nav is None:
        nav = '<a href="/">Site</a><a href="/preview">Public preview</a><a href="/account">Account</a><a href="/callback-log">Callback log</a>'
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">GRAYTIDE // CUSTOMER CLOUD</div><h1>{title}</h1></div>{body}',
        nav=nav,
    )


def session_of():
    sid = request.cookies.get("sid", "")
    return SESSIONS.get(sid) if sid else None


def issue_token() -> str:
    return "csrf_" + secrets.token_urlsafe(18)


def token_is_known(supplied: str) -> bool:
    """Accept any token this service has ever issued."""
    if not supplied.startswith("csrf_"):
        return False
    return supplied in PUBLIC_LEDGER or any(record["csrf"] == supplied for record in SESSIONS.values())


def account_page(record: dict, notice: str = "") -> object:
    return shell(
        "Your account",
        f"""<div class="panel"><h2>Signed in as {html.escape(record["email"])}</h2>
        <p>Role: <code>{record["role"]}</code> · Display name: <code>{html.escape(record["display"])}</code></p></div>
        <div class="panel"><h2>Notification e-mail</h2>
        <form method="post" action="/change-email">
          <input type="hidden" name="csrf" value="{record["csrf"]}">
          <label>New e-mail</label><input name="email" value="{html.escape(record["email"])}">
          <p><button type="submit">Update e-mail</button></p>
        </form>{notice}
        <p class="note">Update forms carry a token. The service accepts a token when it recognises the value it issued.</p></div>""",
    )


@app.get("/")
def index():
    return shell(
        "Customer cloud",
        """<div class="panel"><h2>Graytide workspace</h2>
        <p>Customer operations for every team. Public profiles and the press kit are open to everyone.</p>
        <ul class="list">
          <li><a href="/preview">Public profile preview (no sign-in)</a></li>
          <li><a href="/login">Sign in to your workspace</a></li>
        </ul></div>""",
    )


@app.get("/login")
def login_form():
    return shell(
        "Sign in",
        """<div class="panel"><h2>Workspace sign-in</h2>
        <form method="post" action="/login">
          <label>Work e-mail</label><input name="email" value="quinn@acme.test">
          <label>Password</label><input name="password" type="password" value="harbor-2026">
          <p><button type="submit">Continue</button></p></form></div>""",
    )


@app.post("/login")
def login():
    email = request.form.get("email", "").strip().lower()
    if not email or not request.form.get("password"):
        return shell("Sign in", '<div class="flash err">Invalid credentials.</div>'), 401
    sid = secrets.token_urlsafe(18)
    SESSIONS[sid] = {"email": email, "display": email.split("@")[0], "role": "member", "csrf": issue_token()}
    response = lab.redirect("/account")
    response.set_cookie("sid", sid, httponly=True, samesite="Lax", path="/")
    return response


@app.get("/account")
def account():
    record = session_of()
    if not record:
        return lab.redirect("/login")
    notice = ""
    message = request.args.get("msg", "")
    if message == "changed":
        notice = f'<div class="flash ok">Notification e-mail changed to {html.escape(record["email"])}.</div>'
    elif message == "bad-token":
        notice = '<div class="flash err">The form token is missing or is not recognised.</div>'
    return account_page(record, notice)


@app.post("/change-email")
def change_email():
    record = session_of()
    if not record:
        return shell("Sign in required", '<div class="flash err">Your session expired. Sign in again.</div>'), 401

    supplied = request.form.get("csrf") or request.headers.get("X-CSRF-Token") or request.cookies.get("csrf", "")
    # VULNERABLE: the token is any value the service once issued. It is not
    # bound to the session cookie, never expires, is published on a public page
    # and is accepted from a form field or a cookie.
    if not supplied or not token_is_known(supplied):
        return lab.redirect("/account?msg=bad-token")

    email = request.form.get("email", "").strip()[:120] or record["email"]
    previous = record["email"]
    record["email"] = email
    CALLBACKS.append({"event": "email.changed", "email": email, "delivered": len(CALLBACKS) + 1})
    if lab.flag("flag") in email:
        lab.objective_async("flag", "cross-site e-mail change accepted with a token from another session")
    return lab.redirect("/account?msg=changed")


@app.get("/preview")
def preview():
    token = issue_token()
    PUBLIC_LEDGER.add(token)
    cards = "".join(
        f'<div class="panel"><h3>{html.escape(name)}</h3><p><code>{html.escape(email)}</code> · {html.escape(team)}</p></div>'
        for email, name, team in PUBLIC_EMAILS
    )
    # VULNERABLE: the public page ships a live form token to anonymous visitors
    # and the authenticated endpoint accepts it.
    return shell(
        "Public profile preview",
        f'<div class="flash">Previewing the public press kit. <span class="mono">form-token: <code id="ft">{token}</code></span></div>'
        '<div class="grid3">' + cards + '</div>'
        '<div class="panel"><h2>Embed this preview</h2>'
        '<form method="post" action="/preview"><label>Your site URL</label><input name="site" placeholder="https://example.test">'
        '<p><button type="submit">Generate badge</button></p></form></div>',
    )


@app.post("/preview")
def preview_badge():
    site = request.form.get("site", "").strip()[:300]
    return shell(
        "Badge snippet",
        f'<div class="panel"><h2>Badge snippet</h2><pre>&lt;script&gt;Graytide.badge({html.escape(site)!r})&lt;/script&gt;</pre></div>',
    )


@app.get("/api/session")
def api_session():
    record = session_of()
    if not record:
        return {"authenticated": False}
    return {"authenticated": True, "email": record["email"], "display": record["display"], "role": record["role"]}


@app.get("/callback-log")
def callback_log():
    rows = "".join(
        f'<li><code>{html.escape(item["event"])}</code> · {html.escape(item["email"])} · <span class="dim">delivery {item["delivered"]}</span></li>'
        for item in CALLBACKS
    ) or '<li class="dim">No integration deliveries yet.</li>'
    return shell("Callback log", f'<div class="panel"><h2>Workspace integration deliveries</h2><ul class="list">{rows}</ul></div>')


if __name__ == "__main__":
    lab.run()