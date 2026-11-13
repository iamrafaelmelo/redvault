from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone

from flask import request

from labkit import Lab

lab = Lab("ORCHARD TENANCY", accent="#68d391")
app = lab.app

COOKIE = "orchard_token"

# VULNERABLE: the signing secret is a common weak value from a public wordlist.
JWT_SECRET = b"sunshine"

# The wordlist served at /static/wordlist.txt — a realistic sample of the weakest
# secrets seen in the wild; JWT_SECRET is one of them.
WORDLIST = [
    "123456", "password", "12345678", "qwerty", "123456789", "12345", "1234",
    "111111", "1234567", "dragon", "123123", "baseball", "abc123", "football",
    "monkey", "letmein", "sunshine", "iloveyou", "trustno1", "1234567890",
    "superman", "qazwsx", "shadow", "master", "666666", "mustang", "michael",
    "jennifer", "hello", "freedom", "whatever", "ninja", "azerty", "loveme",
    "charlie", "donald", "qwerty123", "zaq1zaq1", "secret", "secretkey",
    "changeme", "jwtsecret", "supersecret", "s3cr3t", "development", "devsecret",
    "company2024", "hunter2", "password1", "admin",
]

# VULNERABLE: the admin password is stored in clear next to the tenant notes in
# the same SQLite file, reachable by any UNION over the tenancy query.
ADMIN_PASSWORD = secrets.token_urlsafe(18)
ADMIN_OWNER = "orchard-admin"

schema = """
CREATE TABLE IF NOT EXISTS tenants (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    property TEXT NOT NULL,
    rent_cents INTEGER NOT NULL,
    notes TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS staff (
    id INTEGER PRIMARY KEY,
    username TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL
);
"""
seed = [
    f"INSERT INTO staff (username, password, role) VALUES ('admin', '{ADMIN_PASSWORD}', 'admin');",
    "INSERT INTO staff (username, password, role) VALUES ('agent', 'Orchard-2026!', 'agent');",
    "INSERT INTO staff (username, password, role) VALUES ('maintenance', 'keys-2024', 'staff');",
    "INSERT INTO tenants (username, property, rent_cents, notes) VALUES ('tenant_a', 'Maple 4B', 185000, 'Deposit received');",
    "INSERT INTO tenants (username, property, rent_cents, notes) VALUES ('tenant_b', 'Birch 2A', 162000, 'Payment plan approved');",
    f"INSERT INTO tenants (username, property, rent_cents, notes) VALUES ('{ADMIN_OWNER}', 'Orchard HQ', 0, 'Internal — owner account');",
]
lab.init_db("orchard.db", schema, seed)

def b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode()


def unb64url(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def issue(sub: str, role: str) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT", "kid": "default"}, separators=(",", ":")).encode())
    claims = {
        "sub": sub,
        "role": role,
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=8)).timestamp()),
    }
    payload = b64url(json.dumps(claims, separators=(",", ":")).encode())
    body = f"{header}.{payload}"
    return f"{body}.{b64url(hmac.new(JWT_SECRET, body.encode(), hashlib.sha256).digest())}"


def verify(token: str) -> dict | None:
    try:
        header_b64, payload_b64, signature = token.split(".")
        header = json.loads(unb64url(header_b64))
        if header.get("alg") != "HS256":
            return None
        expected = b64url(hmac.new(JWT_SECRET, f"{header_b64}.{payload_b64}".encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(expected, signature):
            return None
        claims = json.loads(unb64url(payload_b64))
        if int(claims.get("exp", 0)) < int(datetime.now(timezone.utc).timestamp()):
            return None
        return claims
    except Exception:
        return None


def current() -> dict | None:
    return verify(request.cookies.get(COOKIE, ""))


SQL_WORDS = ("union", "select", "from", "sleep", "waitfor", "attach", "pragma", "sqlite_master")


def gateway_blocked() -> bool:
    """The edge WAF drops SQL keywords in the raw query string."""
    raw = request.query_string.decode("latin-1").lower()
    return any(word in raw for word in SQL_WORDS)


def shell(title: str, body: str, nav: str | None = None) -> object:
    if nav is None:
        nav = '<a href="/">Portal</a><a href="/notes">Notes</a><a href="/login">Agent login</a>'
    return shell_page(title, body, nav)


def shell_page(title: str, body: str, nav: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">ORCHARD // TENANCY</div><h1>{title}</h1></div>{body}',
        nav=nav,
    )


@app.get("/")
def index():
    claims = current()
    if not claims:
        return shell(
            "Orchard Tenancy",
            """<div class="panel"><h2>Tenant portal</h2>
            <p>Sign in to view your property, rent schedule and notes. Agents sign in with their staff account.</p>
            <p><a class="btn" href="/login">Agent login</a></p>
            <p class="note">The tenancy API lives at <code>/api/notes?username=</code>.</p></div>""",
        )
    role = html.escape(str(claims.get("role")))
    return shell(
        "Signed in",
        f'<div class="panel"><h2>Welcome, <code>{html.escape(str(claims.get("sub")))}</code></h2>'
        f'<p>Role: <code>{role}</code></p>'
        '<p><a class="btn" href="/notes">Open tenancy notes</a></p></div>',
    )


@app.get("/login")
def login_form():
    return shell(
        "Agent login",
        """<div class="panel"><h2>Staff sign-in</h2>
        <form method="post" action="/login"><label>Username</label><input name="username" value="agent">
        <label>Password</label><input name="password" type="password" value="Orchard-2026!">
        <p><button type="submit">Sign in</button></p></form>
        <p class="note">Signing keys are audited against the operations wordlist at <code>/static/wordlist.txt</code>.</p></div>""",
    )


@app.post("/login")
def login():
    username = request.form.get("username", "agent")
    password = request.form.get("password", "")
    conn = lab.db("orchard.db")
    try:
        row = conn.execute("SELECT username, password, role FROM staff WHERE username = ?", (username,)).fetchone()
    finally:
        conn.close()
    if not row or row["password"] != password:
        return shell("Login failed", '<div class="flash err">Invalid staff credentials. Demo agent: <code>agent</code> / <code>Orchard-2026!</code>.</div>', nav='<a href="/login">Agent login</a>')
    response = lab.redirect("/notes")
    response.set_cookie(COOKIE, issue(row["username"], row["role"]), httponly=True, samesite="lax")
    return response


def read_tenancies(claims: dict) -> tuple[list, str]:
    username = str(claims.get("sub", ""))
    role = str(claims.get("role", "user"))
    conn = lab.db("orchard.db")
    try:
        # VULNERABLE: the verified JWT subject is concatenated into the SQL
        # statement. The edge proxy blocks apostrophes in the query string, but the
        # claim arrives through a signed cookie — second-order injection.
        query = f"SELECT username, property, rent_cents, notes FROM tenants WHERE username = '{username}'"
        rows = conn.execute(query).fetchall()
    except sqlite3.Error as exc:
        return [], str(exc)
    finally:
        conn.close()
    return [dict(row) for row in rows], ""


LABELS = {
    "tenant_a": "Maple 4B · deposit received",
    "tenant_b": "Birch 2A · payment plan",
    ADMIN_OWNER: "Orchard HQ · internal",
}


@app.get("/notes")
def notes():
    if gateway_blocked():
        return shell("Blocked", '<div class="flash err">The edge proxy rejected this request: SQL keywords are not allowed in the query string.</div>', nav='<a href="/">Portal</a>')
    claims = current()
    if not claims:
        return shell("Denied", '<div class="flash err">A valid access token is required.</div>', nav='<a href="/login">Agent login</a>')
    rows, error = read_tenancies(claims)
    if error:
        return shell("Query error", f'<div class="flash err">{html.escape(error)}</div>', nav='<a href="/">Portal</a>')
    cards = "".join(
        f'<div class="panel"><h3>{html.escape(row["username"])}</h3>'
        f'<p>{html.escape(LABELS.get(row["username"], row["property"]))}</p>'
        f'<p>Rent: ${row["rent_cents"] / 100:,.2f} · <span class="dim">{html.escape(str(row["notes"])[:160])}</span></p></div>'
        for row in rows
    )
    admin_block = ""
    if str(claims.get("role")) == "admin":
        # The ops credential grants the protected tenancy summary view.
        lab.objective_async("flag", "JWT secret cracked from wordlist + UNION SQLi at /notes as admin")
        admin_block = (
            '<div class="panel"><h2>Operations summary</h2>'
            f'<pre>{lab.flag("flag")}</pre></div>'
        )
    return shell("Tenancy notes", f'{admin_block}{cards or "<p class=\'dim\'>No tenant records for this account.</p>"}')


@app.get("/api/notes")
def api_notes():
    if gateway_blocked():
        return {"error": "request rejected by edge policy"}, 403
    claims = current()
    if not claims:
        return {"error": "token required"}, 401
    rows, error = read_tenancies(claims)
    if error:
        return {"error": error}, 400
    return {"rows": rows, "count": len(rows)}


@app.get("/static/wordlist.txt")
def wordlist():
    return app.response_class("\n".join(WORDLIST) + "\n", mimetype="text/plain")


@app.get("/static/app.js")
def static_app():
    return app.response_class(
        "// Orchard tenant portal\n"
        "fetch('/api/notes?username=' + encodeURIComponent(localStorage.tenant)).then(r => r.json());\n",
        mimetype="application/javascript",
    )


if __name__ == "__main__":
    lab.run()