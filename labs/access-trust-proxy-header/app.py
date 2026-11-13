from __future__ import annotations

import html
import ipaddress
import secrets

from flask import make_response, redirect, request

from labkit import Lab

lab = Lab("OPSGRID", accent="#f59e0b")
app = lab.app

USERS: dict[str, dict[str, str]] = {
    "mei": {"password": "mei-sre-2026", "role": "oncall"},
    "duty-manager": {"password": "unset-service-account", "role": "admin"},
}
SESSIONS: dict[str, str] = {}
AUDIT: list[dict[str, str]] = []

# "Internal" ranges that the edge proxy is allowed to forward from.
INTERNAL_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
]


def shell(title: str, body: str, nav: str | None = None) -> object:
    if nav is None:
        nav = (
            '<a href="/">Status</a><a href="/admin">Admin console</a><a href="/audit">Audit</a><a href="/logout">Sign out</a>'
            if current_user()
            else '<a href="/">Sign in</a>'
        )
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">OPSGRID // INCIDENT RESPONSE</div><h1>{title}</h1></div>{body}',
        nav=nav,
    )


def current_user() -> str | None:
    return SESSIONS.get(request.cookies.get("og_session", ""))


def client_ip() -> str:
    # VULNERABLE: no trusted proxy list. The left-most address of the
    # client-supplied forwarding header is taken as the source of the request.
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    # Requests without a forwarding header never passed through the edge proxy.
    # The API gateway stores the source it observed in this header.
    return request.headers.get("X-Real-Client-IP", "0.0.0.0")


def is_internal(ip: str) -> bool:
    try:
        address = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(address in network for network in INTERNAL_RANGES)


@app.get("/")
def index():
    if current_user():
        return redirect("/status")
    return shell(
        "Opsgrid",
        """<div class="panel"><h2>On-call sign-in</h2>
        <form method="post" action="/login">
          <label>Username</label><input name="username" autocomplete="username">
          <label>Password</label><input name="password" type="password" autocomplete="current-password">
          <p><button type="submit">Sign in</button></p></form>
        <p class="note">Demo account: <code>mei</code> / <code>mei-sre-2026</code>.</p></div>""",
    )


@app.post("/login")
def login():
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    user = USERS.get(username)
    if user and user["password"] == password:
        handle = secrets.token_urlsafe(18)
        SESSIONS[handle] = username
        resp = make_response(redirect("/status"))
        resp.set_cookie("og_session", handle, httponly=True, samesite="Lax")
        return resp
    return shell("Sign-in failed", '<div class="flash err">Invalid credentials.</div>')


@app.get("/status")
def status():
    user = current_user()
    if not user:
        return redirect("/")
    ip = client_ip()
    internal = is_internal(ip)
    note = (
        '<p class="note">Your request arrived from the internal network, so the administrative console is open to you.</p>'
        if internal
        else '<p class="note">Requests from outside the office network are limited to the status board.</p>'
    )
    return shell(
        "Status board",
        f"""<div class="panel"><h2>Cluster status</h2>
        <p>Signed in as <code>{html.escape(user)}</code></p>
        <table><tr><th>Detected source</th><td class="mono">{html.escape(ip)}</td></tr>
        <tr><th>Network</th><td>{"internal" if internal else "external"}</td></tr>
        <tr><th>api-eu-1</th><td class="green">healthy</td></tr>
        <tr><th>api-us-1</th><td class="green">healthy</td></tr></table>{note}</div>""",
    )


@app.get("/admin")
def admin():
    user = current_user()
    if not user:
        return redirect("/")
    ip = client_ip()
    if not is_internal(ip):
        AUDIT.insert(0, {"user": user, "ip": ip, "path": "/admin", "result": "denied"})
        return shell(
            "Admin console",
            f'<div class="flash err">Administrative access is restricted to the internal network. '
            f'Your request was seen from <code>{html.escape(ip)}</code>.</div>',
            nav='<a href="/status">Status</a><a href="/audit">Audit</a>',
        )
    AUDIT.insert(0, {"user": user, "ip": ip, "path": "/admin", "result": "granted"})
    lab.objective_async("flag", "admin console reached by spoofing X-Forwarded-For")
    return shell(
        "Admin console",
        f"""<div class="panel"><h2>Maintenance mode</h2>
        <p>Internal access granted to <code>{html.escape(user)}</code> from <code>{html.escape(ip)}</code>.</p>
        <pre>{html.escape(lab.flag("flag"))}</pre></div>""",
        nav='<a href="/status">Status</a><a href="/audit">Audit</a>',
    )


@app.get("/audit")
def audit():
    if not current_user():
        return redirect("/")
    rows = "".join(
        f"<tr><td>{html.escape(entry['user'])}</td><td class='mono'>{html.escape(entry['ip'])}</td>"
        f"<td>{html.escape(entry['path'])}</td><td>{html.escape(entry['result'])}</td></tr>"
        for entry in AUDIT[:20]
    ) or '<tr><td colspan="4" class="dim">No admin access recorded.</td></tr>'
    return shell(
        "Access audit",
        f'<div class="panel"><h2>Recent admin requests</h2>'
        f'<table><tr><th>User</th><th>Source as parsed</th><th>Path</th><th>Result</th></tr>{rows}</table></div>',
    )


@app.get("/logout")
def logout():
    resp = make_response(redirect("/"))
    resp.delete_cookie("og_session")
    return resp


if __name__ == "__main__":
    lab.run()