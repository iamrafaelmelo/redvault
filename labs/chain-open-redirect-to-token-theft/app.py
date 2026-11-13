from __future__ import annotations

import html
import json
import secrets
import time
from datetime import datetime, timezone
from urllib.parse import unquote, urlsplit

from flask import request

from labkit import Lab

lab = Lab("WAYPOINT SSO", accent="#4fd1c5")
app = lab.app

COOKIE = "wpsession"
CLIENTS = {
    "wayfinder-web": {
        "name": "Wayfinder Web",
        # VULNERABLE: the redirect target is registered from the request itself,
        # so any caller can make the client point at an arbitrary origin.
        "redirect_uri": "http://127.0.0.1:{port}/callback",
        "trusted": ["127.0.0.1"],
    }
}
LEDGER = lab.state_dir / "referrer-ledger.jsonl"
TOKENS: dict[str, dict] = {}
AUTHORIZATION_CODES: dict[str, dict] = {}
SESSIONS: dict[str, str] = {}

lab.write_state("accounts.json", json.dumps({"operator": {"password": "Waypoint-2026!", "display": "Nadia Okoye"}}))


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ledger(entry: dict) -> None:
    with LEDGER.open("a") as handle:
        handle.write(json.dumps(entry) + "\n")


def ledger_entries() -> list[dict]:
    try:
        lines = LEDGER.read_text().splitlines()
    except OSError:
        return []
    entries = []
    for line in lines:
        try:
            entries.append(json.loads(line))
        except ValueError:
            continue
    return entries


def shell(title: str, body: str, nav: str | None = None) -> object:
    if nav is None:
        nav = (
            '<a href="/">Home</a><a href="/authorize">Authorize</a>'
            '<a href="/clients">Clients</a><a href="/logs">Referrer log</a><a href="/capture">Capture</a>'
        )
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">WAYPOINT // SINGLE SIGN-ON</div><h1>{title}</h1></div>{body}',
        nav=nav,
    )


def active_uri(client: dict) -> str:
    """The URI /authorize hands the authorization code to.

    A pending (unapproved) redirect saved by /clients takes precedence: support
    staff asked for it to be used immediately so they can finish integration
    before the allow-list review completes.
    """
    return (client.get("pending") or client["redirect_uri"]).format(port=lab.port)


def default_uri() -> str:
    return active_uri(CLIENTS["wayfinder-web"])


def split_target(uri: str) -> dict:
    parts = urlsplit(uri)
    return {"host": parts.hostname or "", "path": parts.path or "/", "scheme": parts.scheme}


def issue_token(user: str, client: str) -> str:
    token = "wp_" + secrets.token_urlsafe(24)
    TOKENS[token] = {"user": user, "client": client, "scope": "profile flag:read", "issued": now(), "used": False}
    return token


@app.get("/")
def index():
    sessions = "".join(f'<li><code>{html.escape(sid)}</code> · <span class="dim">{html.escape(user)}</span></li>' for sid, user in list(SESSIONS.items())[:6])
    return shell(
        "Waypoint single sign-on",
        f"""<div class="panel"><h2>OAuth-style platform login</h2>
        <p>Wayfinder Web starts every login at <code>/authorize</code>. The returned access token is placed in the URL
        fragment and handed to the registered redirect URI.</p>
        <p><a class="btn" href="/authorize">Start a login</a> <a class="btn btn-ghost" href="/clients">Registered clients</a></p>
        <p class="note">Operator sessions issue tokens with the <code>flag:read</code> scope.</p></div>
        <div class="panel"><h2>Active sessions</h2><ul class="list">{sessions or '<li class="dim">No sessions yet.</li>'}</ul></div>""",
    )


@app.route("/authorize", methods=["GET", "POST"])
def authorize():
    client_id = request.values.get("client_id", "wayfinder-web")
    client = CLIENTS.get(client_id)
    error = ""
    if not client:
        return shell("Unknown client", '<div class="flash err">Unknown client_id.</div>', nav='<a href="/">Home</a>')
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        accounts = json.loads(lab.read_state("accounts.json") or "{}")
        account = accounts.get(username)
        if account and account["password"] == password:
            session_id = secrets.token_urlsafe(18)
            SESSIONS[session_id] = username
            code = secrets.token_urlsafe(20)
            redirect_uri = request.form.get("redirect_uri") or active_uri(client)
            AUTHORIZATION_CODES[code] = {
                "user": username,
                "client": client_id,
                "redirect_uri": redirect_uri,
                "created": time.time(),
            }
            # VULNERABLE: the consent screen bounces to the stored (attacker chosen)
            # redirect_uri and carries the authorization code in the query string.
            return lab.page(
                "Consent granted",
                f'<div class="hero"><div class="kicker">WAYPOINT // CONSENT</div><h1>Consent granted</h1></div>'
                f'<div class="panel"><p>Redirecting to <code>{redirect_uri}</code>…</p>'
                f'<p class="note">Authorization code: <code>{code}</code></p></div>'
                f"<meta http-equiv='refresh' content='0;url={redirect_uri}?code={code}'>".replace("&", "&amp;"),
                nav='<a href="/">Home</a>',
            )
        error = '<div class="flash err">Invalid credentials. The demo account is <code>operator</code> / <code>Waypoint-2026!</code>.</div>'
    target = request.values.get("redirect_uri") or default_uri()
    return shell(
        "Authorize Wayfinder Web",
        f"""<div class="panel"><h2>Sign in to continue</h2>
        <form method="post" action="/authorize">
          <input type="hidden" name="client_id" value="{html.escape(client_id)}">
          <input type="hidden" name="redirect_uri" value="{html.escape(target)}">
          <label>Username</label><input name="username" value="operator">
          <label>Password</label><input name="password" type="password" value="Waypoint-2026!">
          <p><button type="submit">Authorize</button></p>
        </form>{error}
        <p class="note">Redirect target: <code>{html.escape(target)}</code></p></div>""",
    )


@app.get("/callback")
@app.get("/oauth/callback")
def callback():
    """Client callback. The token lives in the fragment, invisible to the server."""
    code = request.args.get("code", "")
    entry = AUTHORIZATION_CODES.get(code)
    if not entry:
        return shell("Callback", '<div class="flash err">No valid authorization code in this callback.</div>')
    token = issue_token(entry["user"], entry["client"])
    del AUTHORIZATION_CODES[code]
    return shell(
        "Wayfinder Web callback",
        f"""<div class="panel"><h2>Completing sign-in</h2>
        <p>The code was exchanged for an access token. As with every OAuth 2.0 implicit flow the token is appended
        to the URL fragment, which the server never receives.</p>
        <p class="note">Served at <code>/callback</code> — a generic endpoint, deliberately reachable on any loopback host.</p>
        <script>
          localStorage.setItem("wayfinder_token", {json.dumps(token)});
          history.replaceState(null, "", "/callback#access_token={token}&token_type=bearer&expires_in=3600");
          document.getElementById("frag") && (document.getElementById("frag").textContent = location.href);
        </script>
        <p class="note" id="frag"></p></div>""",
    )


@app.route("/clients", methods=["GET", "POST"])
def clients():
    message = ""
    if request.method == "POST":
        client_id = request.form.get("client_id", "wayfinder-web").strip()
        uri = request.form.get("redirect_uri", "").strip()
        target = split_target(uri)
        if client_id not in CLIENTS:
            message = '<div class="flash err">Unknown client.</div>'
        elif not uri:
            message = '<div class="flash err">A redirect URI is required.</div>'
        elif target["host"] in CLIENTS[client_id]["trusted"] and target["path"].startswith("/oauth/callback"):
            # This is the only path that registers anything permanently.
            CLIENTS[client_id]["redirect_uri"] = uri
            message = f'<div class="flash ok">Redirect URI registered: <code>{html.escape(uri)}</code></div>'
        else:
            # VULNERABLE: the "pending review" redirect is stored even for hosts the
            # allow-list rejects. It is persisted exactly as supplied (including the
            # leading-slashes trick "/\t/" style payloads) and reused by the next
            # authorization request.
            CLIENTS[client_id]["pending"] = uri
            message = (
                '<div class="flash err">Host not in the allow-list. The URI was saved as a '
                f'<b>pending redirect</b> and will be used by the next authorization until an admin approves it.</div>'
                f'<p class="note">Stored pending redirect: <code>{html.escape(uri)}</code></p>'
            )
    rows = "".join(
        f'<tr><td><code>{html.escape(client_id)}</code></td><td><code>{html.escape(active_uri(client))}</code></td>'
        f'<td><code>{html.escape(client.get("pending", "—"))}</code></td>'
        f'<td>{"allow-list" if "127.0.0.1" in client["trusted"] else "external"}</td></tr>'
        for client_id, client in CLIENTS.items()
    )
    return shell(
        "Registered clients",
        f"""<div class="panel"><h2>OAuth client registry</h2>
        <table><tr><th>Client</th><th>Active redirect</th><th>Pending redirect</th><th>Trust</th></tr>{rows}</table></div>
        <div class="panel"><h2>Update a client</h2>
        <form method="post" action="/clients">
          <label>Client ID</label><input name="client_id" value="wayfinder-web">
          <label>Redirect URI</label><input name="redirect_uri" value="http://127.0.0.1:{lab.port}/oauth/callback/wayfinder">
          <p><button type="submit">Save redirect</button></p>
        </form>{message}</div>""",
    )


@app.get("/logs")
def logs():
    entries = list(reversed(ledger_entries()))[:40]
    rows = "".join(
        f'<tr><td><code>{html.escape(item.get("ts", ""))}</code></td><td>{html.escape(item.get("source", ""))}</td>'
        f'<td><code>{html.escape(item.get("referrer", ""))}</code></td></tr>'
        for item in entries
    ) or '<tr><td colspan="3" class="dim">The referrer log is empty.</td></tr>'
    return shell(
        "Referrer log",
        f"""<div class="panel"><h2>Inbound navigation log</h2>
        <p>The edge logs the <code>Referer</code> header of every page load in the client application.</p>
        <table><tr><th>Timestamp</th><th>Source</th><th>Referrer</th></tr>{rows}</table></div>
        <p class="note">The client's own callback script posts its <code>document.referrer</code> here through <code>/beacon</code>.</p>""",
    )


@app.route("/beacon", methods=["GET", "POST"])
def beacon():
    """Client-side analytics endpoint: real browsers report document.referrer."""
    referrer = request.values.get("referrer") or request.headers.get("Referer", "")
    source = request.values.get("source", "callback-script")
    ledger({"ts": now(), "source": source[:40], "referrer": referrer[:2000]})
    return ("", 204)


@app.get("/capture")
def capture():
    token = unquote(request.args.get("token", "")).strip()
    if not token:
        return lab.page(
            "Token exchange",
            '<div class="hero"><div class="kicker">WAYPOINT // TOKEN EXCHANGE</div><h1>Token exchange</h1></div>'
            '<div class="flash err">An access token is required: <code>/capture?token=...</code></div>',
            status=401, nav='<a href="/">Home</a>',
        )
    entry = TOKENS.get(token)
    if not entry:
        return lab.page(
            "Token exchange",
            '<div class="hero"><div class="kicker">WAYPOINT // TOKEN EXCHANGE</div><h1>Token exchange</h1></div>'
            '<div class="flash err">The access token is invalid or expired.</div>',
            status=401, nav='<a href="/">Home</a>',
        )
    if "flag:read" not in entry["scope"]:
        return lab.page(
            "Token exchange",
            '<div class="hero"><div class="kicker">WAYPOINT // TOKEN EXCHANGE</div><h1>Token exchange</h1></div>'
            '<div class="flash err">The token lacks the flag:read scope.</div>',
            status=403, nav='<a href="/">Home</a>',
        )
    if entry["used"]:
        return lab.page(
            "Token exchange",
            '<div class="hero"><div class="kicker">WAYPOINT // TOKEN EXCHANGE</div><h1>Token exchange</h1></div>'
            '<div class="flash err">This token has already been exchanged.</div>',
            status=403, nav='<a href="/">Home</a>',
        )
    # VULNERABLE: whoever holds a valid bearer token can exchange it for the
    # protected secret — there is no client binding on this internal endpoint.
    entry["used"] = True
    lab.objective_async("flag", f"access token {token[:10]}… captured and exchanged")
    tokens = "".join(
        f'<li><code>{html.escape(token[:12])}…</code> <span class="dim">user={html.escape(meta["user"])} '
        f'scope={html.escape(meta["scope"])} issued={html.escape(meta["issued"])} '
        f'{"used" if meta["used"] else "unused"}</span></li>'
        for token, meta in reversed(list(TOKENS.items())[-12:])
    )
    return shell(
        "Token exchange",
        f"""<div class="panel"><h2>Internal capture</h2>
        <p>Internal log ingestion endpoint. The platform accepts an access token in the query string and returns the
        token's protected resource. This endpoint is not intended for browsers.</p>
        <pre>GET /capture?token=&lt;access token&gt;</pre>
        <p class="dim">Without a token the endpoint answers <code>401</code>; a valid one is exchanged for
        the token's protected resource.</p></div>
        <div class="panel"><h2>Exchange result</h2><p>Subject <code>{html.escape(entry["user"])}</code> ·
        scope <code>{html.escape(entry["scope"])}</code></p><pre>{lab.flag("flag")}</pre></div>
        <div class="panel"><h2>Issued tokens</h2><ul class="list">{tokens or '<li class="dim">None yet.</li>'}</ul></div>""",
    )


@app.get("/vault")
def vault():
    token = unquote(request.args.get("token", "")).strip()
    entry = TOKENS.get(token)
    if not token:
        return lab.page("Vault", '<div class="hero"><div class="kicker">WAYPOINT // VAULT</div><h1>Vault</h1></div>'
                                 '<div class="flash err">An access token is required.</div>', status=401,
                        nav='<a href="/">Home</a>')
    if not entry:
        return lab.page("Vault", '<div class="hero"><div class="kicker">WAYPOINT // VAULT</div><h1>Vault</h1></div>'
                                 '<div class="flash err">The access token is invalid or expired.</div>', status=401,
                        nav='<a href="/">Home</a>')
    if "flag:read" not in entry["scope"]:
        return lab.page("Vault", '<div class="hero"><div class="kicker">WAYPOINT // VAULT</div><h1>Vault</h1></div>'
                                 '<div class="flash err">The token lacks the flag:read scope.</div>', status=403,
                        nav='<a href="/">Home</a>')
    if entry["used"]:
        return lab.page("Vault", '<div class="hero"><div class="kicker">WAYPOINT // VAULT</div><h1>Vault</h1></div>'
                                 '<div class="flash err">This token has already been exchanged for the secret.</div>',
                        status=403, nav='<a href="/">Home</a>')
    entry["used"] = True
    lab.objective_async("flag", f"stolen access token {token[:10]}… exchanged at /vault")
    return shell(
        "Operations vault",
        f'<div class="panel"><h2>Secret retrieved</h2><p>Token subject: <code>{html.escape(entry["user"])}</code></p>'
        f'<pre>{lab.flag("flag")}</pre>'
        '<p class="note">The stolen token is single use: re-exchange requires a new authorization.</p></div>',
    )


if __name__ == "__main__":
    lab.run()