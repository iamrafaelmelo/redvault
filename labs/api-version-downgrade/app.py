from __future__ import annotations

import base64

from flask import jsonify, request

from labkit import Lab

lab = Lab("LEGACY LEDGER", accent="#b58b5b")
app = lab.app


def auth_ok() -> bool:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Basic "):
        return False
    try:
        raw = base64.b64decode(header[6:]).decode()
        return raw == "analyst:analyst123"
    except Exception:
        return False


def shell(title: str, body: str) -> object:
    return lab.page(title, f'<div class="hero"><div class="kicker">LEGACY LEDGER // API VERSIONS</div><h1>{title}</h1></div>{body}', nav='<a href="/">Docs</a><a href="/api/v2/me">v2/me</a><a href="/api/v1/accounts?user=admin">v1 accounts</a>')


@app.get("/")
def index():
    return shell(
        "API documentation",
        """<div class="panel"><h2>v2 — current</h2>
        <p><code>GET /api/v2/me</code> with HTTP Basic auth. Returns a deliberately reduced profile.</p>
        <pre>Authorization: Basic base64(analyst:analyst123)</pre></div>
        <div class="panel"><h2>v1 — deprecated</h2>
        <p>Kept for the mobile migration. Accepts a `user` query parameter and was scheduled for retirement.</p>
        <p class="note">Deprecated does not mean disabled. The old handler still uses the old data model.</p></div>
        <div class="panel"><h2>Demo account</h2><p><code>analyst</code> / <code>analyst123</code></p></div>""",
    )


@app.get("/api/v2/me")
def me_v2():
    if not auth_ok():
        return jsonify({"error": "unauthorized"}), 401
    # Current version: masked and scoped.
    return jsonify(
        {
            "username": "analyst",
            "display_name": "Field Analyst",
            "email": "a***@legacyledger.local",
            "account": {"id": 7, "plan": "standard"},
        }
    )


@app.get("/api/v1/accounts")
def accounts_v1():
    # VULNERABLE: legacy version has no auth and exposes a full account object.
    user = request.args.get("user", "analyst")
    record = {
        "username": user,
        "email": f"{user}@legacyledger.local",
        "account_id": 7 if user == "analyst" else 1,
        "plan": "standard" if user == "analyst" else "internal-settlement",
        "masked_pan": "**** **** **** 1042",
    }
    if user == "admin":
        record["legacy_notes"] = "manual settlement access"
        record["vault_flag"] = lab.flag("flag")
    return jsonify({"version": "v1", "deprecated": True, "account": record})


if __name__ == "__main__":
    lab.run()
