from __future__ import annotations

import html
import secrets
import time
from urllib.parse import quote, urlparse

from flask import request

from labkit import Lab

lab = Lab("MISTRAL ID", accent="#5eead4")
app = lab.app

# Edge cache shared by every visitor. Keyed by path only: the tenant label and
# edge suffix header that shape the absolute links are not part of the key.
CACHE: dict[str, tuple[str, float]] = {}
CAPTURED: list[str] = []
RESETS: dict[str, dict[str, str]] = {}

DEFAULT_HOST = f"127.0.0.1:{lab.port}"
TTL = 300.0


def brand(title: str) -> str:
    return f'<div class="hero"><div class="kicker">MISTRAL ID // IDENTITY EDGE</div><h1>{html.escape(title)}</h1></div>'


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f"{brand(title)}{body}",
        nav='<a href="/">Home</a><a href="/login">Sign in</a><a href="/reset">Reset</a><a href="/sso/start">SSO</a><a href="/cache">Cache</a>',
    )


# --------------------------------------------------------------------------
# Absolute URL builder
# --------------------------------------------------------------------------
# The canonical absolute URL is derived from the request so regional
# deployments link back to their own public name.
#
# VULNERABLE: a tenant label (unkeyed query parameter) and an edge suffix
# (unkeyed request header) are trusted to build every absolute link, without an
# allow-list. Neither value is part of the cache key, so one request controls
# where every later visitor is sent.
def edge_base() -> str:
    tenant = (request.args.get("tenant") or "").strip()
    suffix = (request.headers.get("X-Edge-Suffix") or "").strip()
    if tenant or suffix:
        host = ".".join(part for part in (tenant, suffix) if part)
        return f"http://{host}"
    proto = (request.environ.get("HTTP_X_FORWARDED_PROTO") or "http").split(",")[0].strip() or "http"
    host = request.environ.get("HTTP_HOST") or DEFAULT_HOST
    return f"{proto}://{host}"


def cache_headers(response, state: str):
    response.headers["X-Cache"] = state
    response.headers["X-Cache-Key"] = "/home"
    response.headers["Cache-Control"] = f"public, max-age={int(TTL)}"
    return response


def from_cache(key: str, render) -> tuple[str, str]:
    now = time.monotonic()
    entry = CACHE.get(key)
    if entry and entry[1] > now:
        return entry[0], "HIT"
    body = render()
    CACHE[key] = (body, now + TTL)
    return body, "MISS"


# --------------------------------------------------------------------------
# Pages
# --------------------------------------------------------------------------
@app.get("/")
def index():
    return shell(
        "Identity at the edge",
        f"""<div class="panel"><h2>Welcome to Mistral ID</h2>
        <p>The shared edge cache serves anonymous pages to every region. Recovery e-mails are generated with absolute links and the edge renders its canonical base for previews.</p></div>
        <div class="grid3">
        <div class="panel"><h3>Support</h3><p class="dim">Self-service and account recovery.</p></div>
        <div class="panel"><h3>SSO</h3><p class="dim">One identity for every tenant app.</p></div>
        <div class="panel"><h3>Status</h3><p class="dim">All regions operational.</p></div>
        </div>
        <div class="panel"><h2>Edge preview</h2>
        <p>Preview a regional rollout by supplying a tenant label and the edge suffix the operator registered:</p>
        <pre>Preview base URL: {html.escape(edge_base())}</pre>
        <p class="note">Known tenant hosts: <code>www.mistral-id.example</code> · <code>login.mistral-id.example</code> · <code>sso.mistral-id.example</code></p></div>""",
    )


@app.get("/home")
def home():
    # VULNERABLE: the anonymous page is cached by path only, yet it embeds
    # absolute links built from the unkeyed tenant label / suffix header.
    # Cached responses must be fully rendered HTML before they go into the map.
    base = edge_base()

    def render() -> str:
        body = f"""<div class="panel"><h2>Welcome back</h2>
        <p class="brand-banner">Canonical site: <code id="canonical">{base}/</code></p>
        <p>Continue to the dashboard: <a href="{base}/dashboard">Go to your dashboard</a></p>
        <ul class="list">
          <li><a href="{base}/settings">Account settings</a></li>
          <li><a href="{base}/reset">Forgot your password?</a></li>
          <li><a href="{base}/sso/start?continue=/dashboard">Sign in with SSO</a></li>
        </ul>
        <p class="note">The edge caches this page for {int(TTL)} seconds per deploy.</p></div>"""
        return shell("Account home", body).get_data(as_text=True)

    document, state = from_cache("/home", render)
    return cache_headers(lab.app.response_class(document, mimetype="text/html"), state)


@app.get("/dashboard")
def dashboard():
    token = request.cookies.get("identity_token", "")
    if lab.flag("flag") in token:
        lab.objective_async("flag", "victim followed the poisoned dashboard link to the attacker collector")
    return shell(
        "Dashboard",
        f"""<div class="panel"><h2>Your account</h2>
        <p>Signed in as <code>ops-owner</code>.</p>
        <p class="green">Identity token:</p><pre>{html.escape(token) or "(no token in this browser)"}</pre>
        <p class="note">Run <code>document.cookie</code> or read <code>/me</code> — the token is scoped to this host.</p></div>""",
    )


@app.get("/me")
def me():
    token = request.cookies.get("identity_token", "")
    if lab.flag("flag") in token:
        lab.objective_async("flag", "victim identity token read through the session API")
    return {"identity_token": token, "user": "ops-owner" if token else None}


@app.get("/settings")
def settings():
    return shell("Account settings", '<div class="panel"><p>Notification preferences are managed by your tenant administrator.</p></div>')


@app.get("/reset")
def reset():
    return shell(
        "Password reset",
        """<div class="panel"><h2>Forgot your password?</h2>
        <form method="post" action="/login"><label>Work e-mail</label>
        <input name="email" value="analyst@mistral-id.example">
        <p><button type="submit">Send reset link</button></p></form>
        <p class="note">Links are absolute and built from the edge cache host.</p></div>""",
    )


@app.post("/login")
def login():
    email = request.form.get("email", "") or "analyst@mistral-id.example"
    session_id = secrets.token_urlsafe(16)
    RESETS[session_id] = {"email": email}
    # VULNERABLE: the recovery link is generated from the same unvalidated edge
    # base, so a request with a forged tenant label mails a victim to the
    # attacker's host.
    link = f"{edge_base()}/reset/confirm?t={session_id}"
    return shell(
        "Recovery e-mail sent",
        f"""<div class="flash ok">Message delivered to {html.escape(email)}.</div>
        <div class="panel"><h2>Mail preview (dev relay)</h2>
        <p>Reset your password:</p><pre>{link}</pre></div>""",
    )


@app.get("/reset/confirm")
def reset_confirm():
    token = request.args.get("t", "")
    record = RESETS.get(token)
    if not record:
        return shell("Reset failed", '<div class="flash err">Unknown or expired reset token.</div>')
    return shell(
        "Reset confirmed",
        f'<div class="flash ok">Password reset approved for {html.escape(record["email"])}.</div>',
    )


@app.get("/sso/start")
def sso_start():
    # VULNERABLE: the SSO authorize URL is seeded with a redirect target taken
    # from the same unvalidated edge base.
    ticket = secrets.token_urlsafe(8)
    return lab.app.redirect(f"/sso/authorize?ticket={ticket}&redirect_uri={edge_base()}/dashboard", code=302)


@app.get("/sso/authorize")
def sso_authorize():
    # VULNERABLE: any redirect_uri host is accepted, and the approve form posts
    # that target back without an allow-list.
    redirect_uri = request.args.get("redirect_uri", "/dashboard")
    ticket = request.args.get("ticket", secrets.token_urlsafe(8))
    target_host = urlparse(redirect_uri).netloc or "same-origin"
    safe_uri = html.escape(redirect_uri)
    return shell(
        "Authorize application",
        f"""<div class="panel"><h2>Continue to {html.escape(target_host)}</h2>
        <p>The site <b>Mistral ID</b> is requesting the identity token for <code>ops-owner</code>.</p>
        <p class="dim">Redirect target: <code>{safe_uri}</code></p>
        <form method="post" action="/sso/authorize">
          <input type="hidden" name="redirect_uri" value="{safe_uri}">
          <input type="hidden" name="ticket" value="{html.escape(ticket)}">
          <p><button type="submit">Approve and continue</button></p>
        </form></div>""",
    )


@app.post("/sso/authorize")
def sso_approve():
    redirect_uri = request.form.get("redirect_uri", "/dashboard")
    if not redirect_uri.startswith(("http://", "https://", "/")):
        return shell("Rejected", '<div class="flash err">Invalid redirect target.</div>'), 400
    token = request.cookies.get("identity_token", "")
    location = f"{redirect_uri}{'&' if '?' in redirect_uri else '?'}identity_token={quote(token)}"
    if lab.flag("flag") in token:
        lab.objective_async("flag", "one-click SSO approval forwarded the identity token to a foreign host")
    return lab.app.redirect(location, code=302)


@app.get("/cache")
def cache_view():
    now = time.monotonic()
    rows = "".join(
        f'<li><code>{html.escape(key)}</code> · <span class="dim">ttl {max(0, int(expires - now))}s</span></li>'
        for key, (_, expires) in CACHE.items()
    ) or '<li class="dim">Cache is empty.</li>'
    stored = CACHE.get("/home")
    preview = f'<h3>Stored /home body</h3><pre>{html.escape(stored[0])}</pre>' if stored else ""
    return shell(
        "Edge cache state",
        f'<div class="panel"><h2>Edge cache (path-keyed)</h2><ul class="list">{rows}</ul>{preview}</div>'
        '<p><a href="/cache/reset">Purge cache</a></p>',
    )


@app.get("/cache/reset")
def cache_reset():
    CACHE.clear()
    return lab.redirect("/cache")


@app.get("/collect")
def collect():
    value = request.args.get("c", "") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
        if lab.flag("flag") in value:
            lab.objective_async("flag", "victim identity token arrived at the attacker collector")
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(f'<li><code>{html.escape(v)}</code></li>' for v in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'
    return shell("Captured data", f'<div class="panel"><h2>Attacker collector</h2><ul class="list">{rows}</ul></div>')


if __name__ == "__main__":
    lab.run()