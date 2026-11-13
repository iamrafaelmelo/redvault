from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import html
import pickle
from pathlib import Path

from flask import request

from labkit import Lab

lab = Lab("SHIPLOG", accent="#22d3ee")
app = lab.app

_FLAG_FILE = Path("/tmp/redvault-server-deserialization-pickle.txt")
_FLAG_FILE.write_text(lab.flag("flag") + "\n")


def render_notice(message: str) -> str:
    return f'<div class="flash ok">{html.escape(message)}</div>'


class SessionNotice:
    """Banner queued by the operator dashboard and stored in the state cookie."""

    def __init__(self, message: str) -> None:
        self.message = message

    # VULNERABLE: the state cookie is unpickled on every request, and the values
    # it carries are then asked to render themselves. Anything the pickle can
    # construct is therefore loaded *and invoked* by the application.
    def render(self) -> str:
        return render_notice(self.message)


# Signed state cookies. The signing key is a constant that also ships in the
# public SDK sample, so the signature cannot authenticate the writer.
SESSION_KEY = b"shiplog-session-key-2026"


def sign(blob: bytes) -> str:
    return hmac.new(SESSION_KEY, blob, hashlib.sha256).hexdigest()


def encode(payload: dict) -> str:
    blob = pickle.dumps(payload, protocol=4)
    return f"{sign(blob)}.{base64.urlsafe_b64encode(blob).decode()}"


def current_session() -> dict | None:
    raw = request.cookies.get("shiplog_state", "")
    if "." not in raw:
        return None
    signature, _, encoded = raw.partition(".")
    try:
        blob = base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4))
    except (binascii.Error, ValueError):
        return None
    if not hmac.compare_digest(sign(blob), signature):
        return None
    try:
        state = pickle.loads(blob)  # noqa: S301 - intentionally vulnerable
    except Exception:  # noqa: BLE001 - tampered state
        return None
    return state if isinstance(state, dict) else None


def shell(title: str, body: str, nav: str | None = None) -> object:
    if nav is None:
        nav = '<a href="/">Shipments</a><a href="/login">Sign in</a><a href="/docs/session-format.txt">API</a>'
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">SHIPLOG // SHIPMENT TRACKING</div><h1>{title}</h1></div>{body}',
        nav=nav,
    )


@app.get("/")
def index():
    state = current_session()
    if not state:
        return shell(
            "Shipment tracking",
            """<div class="panel"><h2>Track your consignments</h2>
            <p>Sign in with the demo account to see the manifest of your shipments.</p>
            <p class="note">Demo credentials: <code>ops</code> / <code>shiplog-2026</code>. The session is a signed state
            cookie; the format is documented at <a href="/docs/session-format.txt">/docs/session-format.txt</a>.</p></div>""",
        )
    banner = ""
    for notice in state.get("notices") or []:
        # The dashboard stores SessionNotice objects; the SDK example stores
        # already-rendered strings. Anything else is coerced for display.
        render = getattr(notice, "render", None)
        if callable(render):
            banner += render()
        elif isinstance(notice, bytes):
            banner += html.escape(notice.decode(errors="replace"))
        else:
            banner += html.escape(str(notice))
    if lab.flag("flag") in banner:
        lab.objective_async("flag", "a forged pickle cookie executed on load and rendered the host secret")
    rows = "".join(
        f"<li><code>{html.escape(str(row.get('id', '?')))}</code> · {html.escape(str(row.get('route', '?')))} · "
        f"<span class='dim'>{html.escape(str(row.get('status', '?')))}</span></li>"
        for row in state.get("shipments") or []
        if isinstance(row, dict)
    )
    return shell(
        "Your shipments",
        f"""{banner}<div class="panel"><h2>Signed in as {html.escape(str(state.get("user")))}</h2>
        <ul class="list">{rows or '<li class="dim">No shipments.</li>'}</ul></div>
        <div class="panel"><h2>Session state</h2>
        <p>Role: <code>{html.escape(str(state.get("role")))}</code> · API exports: <code>/exports</code></p>
        <p class="note">State cookies are signed with HMAC-SHA256 (<code>shiplog-state-v1</code>).</p></div>""",
    )


def login_state() -> dict:
    return {
        "user": "ops",
        "role": "operator",
        "shipments": [
            {"id": "SL-8841", "route": "Rotterdam → Lagos", "status": "in transit"},
            {"id": "SL-9027", "route": "Singapore → Sydney", "status": "customs hold"},
        ],
        # The dashboard keeps the typed object so the banner can be styled.
        "notices": [SessionNotice("Two shipments need documents before customs release.")],
    }


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if user == "ops" and password == "shiplog-2026":
            response = lab.redirect("/")
            response.set_cookie("shiplog_state", encode(login_state()), httponly=True, samesite="Lax", path="/")
            return response
        return shell("Sign-in failed", '<div class="flash err">Invalid credentials.</div>')
    return shell(
        "Sign in",
        """<div class="panel"><h2>Operator sign-in</h2>
        <form method="post" action="/login"><label>Username</label><input name="username" value="ops">
        <label>Password</label><input name="password" type="password" value="shiplog-2026">
        <p><button type="submit">Open tracking</button></p></form></div>""",
    )


@app.get("/docs/session-format.txt")
def session_format():
    """Public SDK note describing the cookie layout."""
    return (
        "shiplog-state-v1\n"
        "cookie: shiplog_state=<hmac-sha256-hex>.<base64 pickle protocol 4 dict>\n"
        "state keys: user, role, shipments[], notices[] (objects with render())\n"
        "--\n"
        "SDK sample key (rotation log, DO NOT reuse in production): shiplog-session-key-2026\n"
        "Run scripts/session_dump.py to inspect a cookie server-side.\n"
    ), 200, {"Content-Type": "text/plain; charset=utf-8"}


@app.get("/exports")
def exports():
    state = current_session()
    if not state:
        return lab.redirect("/login")
    return {
        "user": state.get("user"),
        "role": state.get("role"),
        "count": len(state.get("notices") or []),
    }


if __name__ == "__main__":
    lab.run()