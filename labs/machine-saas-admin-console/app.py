from __future__ import annotations

import base64
import hashlib
import hmac
import html
import json
import secrets
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from flask import jsonify, redirect, request, session

from labkit import Lab

lab = Lab("ORBIT CONSOLE", accent="#4fd1c5")
app = lab.app

# The console keeps its staff JWT in a first-party cookie, so the console, the
# API and the admin tools all read the same bearer claims.
SESSION_COOKIE = "orbit_session"

ROOT_FILE = Path("/tmp/orbit-root.txt")
ROOT_FILE.write_text(lab.flag("root") + "\n")

WORKER_TOKEN = secrets.token_urlsafe(20)
WEBHOOK_SECRET = b"orbit-sso-rotation-2026"

# Public onboarding bundle that the platform team forgot to remove. The JWT
# signing secret inside it is the whole point of stage 2.
PUBLIC_JWT_SECRET = "orbit-console-jwt-2025!"

schema = """
CREATE TABLE tenants (id VARCHAR PRIMARY KEY, name TEXT NOT NULL, plan TEXT NOT NULL, mrr INTEGER NOT NULL);
CREATE TABLE members (id VARCHAR PRIMARY KEY, tenant_id VARCHAR NOT NULL, email TEXT NOT NULL, role TEXT NOT NULL, invited_by TEXT);
CREATE TABLE audit (id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, actor TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL);
"""

tenants = [
    (("t_9f21", "Northwind Freight", "enterprise", 18400)),
    (("t_2c88", "Halcyon Health", "scale", 9600)),
    (("t_77ab", "Kite & Anchor Studio", "starter", 290)),
    (("t_0d54", "Silverpine Retail", "scale", 7100)),
    (("t_5e60", "Cobalt Ledger Group", "enterprise", 22150)),
]

members = [
    (("m_101", "t_9f21", "priya.raman@northwind.example", "owner", "initech-provisioner")),
    (("m_102", "t_9f21", "dev.ops@northwind.example", "admin", "priya.raman@northwind.example")),
    (("m_103", "t_2c88", "claims-team@halcyon.example", "member", "initech-provisioner")),
    (("m_104", "t_77ab", "studio@kiteanchor.example", "owner", "self-signup")),
    (("m_105", "t_0d54", "it@silverpine.example", "admin", "initech-provisioner")),
    (("m_106", "t_5e60", "security@cobaltledger.example", "owner", "initech-provisioner")),
    (("m_107", "t_5e60", "payroll@cobaltledger.example", "member", "security@cobaltledger.example")),
    (("m_108", "t_2c88", "billing@halcyon.example", "member", "claims-team@halcyon.example")),
]

audit_rows = [
    ("2026-11-09T08:12:04Z", "support.ops@orbit.internal", "session.login", "staff console session accepted"),
    ("2026-11-09T08:20:51Z", "support.ops@orbit.internal", "tenant.lookup", "viewed t_9f21 billing summary"),
    ("2026-11-09T09:02:13Z", "system", "worker.diagnostics", "edge-worker-01 answered /worker/ping"),
    ("2026-11-09T09:04:02Z", "system", "worker.diagnostics", "edge-worker-02 missed heartbeat, retried ok"),
    ("2026-11-09T10:41:37Z", "deploy-bot", "release", "console 2026.11.3 rolled out to prod"),
    ("2026-11-09T11:15:20Z", "support.ops@orbit.internal", "export.request", "requested tenant CSV for finance review"),
]

seed = [f"INSERT INTO tenants VALUES {t};" for t in tenants]
seed += [f"INSERT INTO members VALUES {m};" for m in members]
seed += [
    "INSERT INTO audit (ts, actor, action, detail) VALUES "
    + ", ".join(f"('{ts}', '{actor}', '{action}', '{detail}')" for ts, actor, action, detail in audit_rows)
    + ";"
]

lab.init_db("orbit.db", schema, seed)


def db():
    return lab.db("orbit.db")


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def sign_token(claims: dict) -> str:
    header = b64url(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    payload = b64url(json.dumps(claims, separators=(",", ":")).encode())
    body = f"{header}.{payload}"
    signature = b64url(hmac.new(PUBLIC_JWT_SECRET.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


def decode_token(token: str) -> dict | None:
    try:
        header_b64, payload_b64, signature = token.split(".")
    except ValueError:
        return None
    body = f"{header_b64}.{payload_b64}"
    expected = b64url(hmac.new(PUBLIC_JWT_SECRET.encode(), body.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, signature):
        return None
    try:
        padded = payload_b64 + "=" * (-len(payload_b64) % 4)
        claims = json.loads(base64.urlsafe_b64decode(padded))
    except (ValueError, json.JSONDecodeError):
        return None
    return claims if isinstance(claims, dict) else None


ROLE_LABEL = {"staff": "Support staff", "admin": "Platform administrator"}


def current_session() -> dict | None:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        return None
    claims = decode_token(token)
    if not claims or claims.get("role") not in ROLE_LABEL:
        return None
    return claims


def shell(title: str, body: str, status: int = 200) -> object:
    claims = current_session()
    if claims:
        nav = (
            '<a href="/console">Console</a><a href="/console/export">Tenant export</a>'
            '<a href="/console/admin">Administration</a><a href="/logout">Sign out</a>'
        )
    else:
        nav = '<a href="/">Sign in</a><a href="/status">Status</a><a href="/docs">Docs</a>'
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">ORBIT // SAAS ADMIN CONSOLE</div><h1>{title}</h1>'
        "<p>Tenant provisioning, subscription billing and platform operations for Orbit Cloud.</p></div>" + body,
        nav=nav,
        status=status,
    )


@app.get("/")
def index():
    if current_session():
        return redirect("/console")
    return shell(
        "Console sign-in",
        """<div class="panel"><h2>Staff access</h2>
        <form method="post" action="/login"><label>Work email</label><input name="username">
        <label>Password</label><input name="password" type="password">
        <p><button type="submit">Sign in</button></p></form>
        <p class="note">Internal staff accounts are provisioned by Platform Engineering.
        Customers sign in at <code>app.orbit.cloud</code>, not here.</p></div>""",
    )


@app.get("/robots.txt")
def robots():
    return lab.app.response_class(
        "User-agent: *\nAllow: /\nDisallow: /onboarding/\nDisallow: /console/admin/\n",
        mimetype="text/plain",
    )


@app.get("/status")
def status():
    return shell(
        "Platform status",
        """<div class="panel"><h2>All systems nominal</h2>
        <ul class="list">
          <li>Console API · <span class="green">operational</span></li>
          <li>Tenant provisioning · <span class="green">operational</span></li>
          <li>Webhook delivery · <span class="amber">degraded</span> · retrying edge-worker-02</li>
        </ul>
        <p class="note">Incident IC-2291 is being handled by Platform Engineering.</p></div>""",
    )


DOCS_PAGE = """<div class="panel"><h2>Staff console bundle</h2>
<p>Static copy of the internal developer docs used during onboarding. The staff console does not
share routes with the customer app, but the bundle keeps the shared preview for convenience.</p>
<ul class="list">
  <li><a href="/onboarding/README.txt">README.txt</a> — console bootstrap notes</li>
  <li><a href="/onboarding/preview.html">preview.html</a> — staff session bootstrap preview</li>
  <li><a href="/onboarding/app-config.js">app-config.js</a> — legacy frontend build metadata</li>
  <li><a href="/console/dev/health">/console/dev/health</a> — bundle build service health</li>
</ul>
<p class="note">The bundle is served by the docs host. Deployment copies under <code>.git/</code> are not exposed by this server.</p></div>"""


@app.get("/docs")
def docs():
    return shell(
        "Developer docs",
        DOCS_PAGE,
        status=410,
    )


@app.get("/docs/")
def docs_index():
    return shell("Developer docs", DOCS_PAGE)


@app.get("/docs/index.html")
def docs_index_html():
    return shell("Developer docs", DOCS_PAGE)


@app.get("/onboarding/README.txt")
def onboarding_readme():
    return lab.app.response_class(
        "Orbit console onboarding\n"
        "========================\n"
        "\n"
        "1. Bootstrap a support session with the preview page.\n"
        "2. Sign in to the console with the staff credentials issued by\n"
        "   Platform Engineering during the console migration.\n"
        "3. Never share tenant exports outside the finance rotation.\n"
        "\n"
        "questions: #platform-eng\n",
        mimetype="text/plain",
    )


ORBIT_AUDIO_JS = """(function () {
  // Preview build of the staff session bootstrap. Shipped to the public docs host.
  // The demo widget is used by preview.html to seed the console walkthrough login.
  var ORBIT_SESSION_KEY = "orbit.demo.staff_session";
  var ORBIT_AUDIO_RESOURCES = [
    // audio resources for the "orbit ring" console chime
    { id: "ring", source: "/static/audio/orbit-ring.mp3", required: false },
    { id: "confirm", source: "/static/audio/orbit-confirm.mp3", required: false }
  ];

  function orbitRenderAudio() {
    // Only the audio chime is intended to ship. The block below is a leftover
    // from the demo console and is not referenced by the production UI.
    var ORBIT_PREVIEW_WIDGET = {
      "staff_user": "support.ops@orbit.internal",
      "staff_password": "0rb1t-Staff!2025",
      "note": "demo login for the internal console walkthrough"
    };
    return ORBIT_PREVIEW_WIDGET;
  }

  function orbitBoot() {
    var widget = orbitRenderAudio();
    try { window[ORBIT_SESSION_KEY] = widget.staff_user; } catch (e) {}
  }

  if (document.readyState !== "loading") { orbitBoot(); }
  else { document.addEventListener("DOMContentLoaded", orbitBoot); }
})();
"""


@app.get("/onboarding/app-config.js")
def onboarding_js():
    return lab.app.response_class(ORBIT_AUDIO_JS, mimetype="application/javascript")


SECRET_JS = """/** @license Orbit Console preview bundle v1.4.2 (internal build) */
window.OrbitConsole = window.OrbitConsole || {};
window.OrbitConsole.config = {
  apiBase: "/api",
  brand: "Orbit",
  environment: "production",
  // Staff session preview -------------------------------------------------
  // TODO(platform): rotate before the console cut-over. The preview token is
  // minted with this secret on the docs host.
  jwtSecret: "orbit-console-jwt-2025!",
  issuer: "orbit-console",
  defaultRole: "staff",
  featureFlags: { exports: true, diagnostics: true, bulkInvite: false }
};
window.OrbitConsole.previewWidget = function () {
  return {
    staff_user: "support.ops@orbit.internal",
    staff_password: "0rb1t-Staff!2025",
    note: "demo login for the internal console walkthrough"
  };
};
window.OrbitConsole.preview = function () {
  console.info("Orbit preview build", window.OrbitConsole.config.apiBase);
};
"""


@app.get("/onboarding/preview.html")
def onboarding_preview():
    body = f"""<div class="panel"><h2>Staff session bootstrap (preview)</h2>
<p>This preview page helps engineers mint a local staff session while the console SSO
migration is in progress. It is part of the public docs bundle.</p>
<pre>&lt;script src="/onboarding/app-config.js"&gt;&lt;/script&gt;</pre>
<p>The script exposes the preview widget (<code>window.OrbitConsole.previewWidget()</code>) described in <code>README.txt</code>.
Use it to sign in to the console while the SSO cut-over is pending.</p>
<p class="note">Preview build notes:</p>
<pre>{html.escape(SECRET_JS)}</pre></div>"""
    return shell("Session bootstrap preview", body)


@app.get("/console/dev/health")
def console_dev_health():
    return jsonify(
        {
            "service": "orbit-console-build",
            "build": "2026.11.3",
            "environment": "production",
            "docs_bundle": "1.4.2",
            "staff_preview_endpoint": "/onboarding/preview.html",
            "todo": "strip preview credentials before publishing the docs bundle",
        }
    )


@app.post("/api/dev/token")
def dev_token():
    # VULNERABLE: the public preview token endpoint issues signed staff tokens
    # to anyone who knows the documented bootstrap credentials.
    username = request.form.get("username") or (request.get_json(silent=True) or {}).get("username", "")
    password = request.form.get("password") or (request.get_json(silent=True) or {}).get("password", "")
    if username == "support.ops@orbit.internal" and password == "0rb1t-Staff!2025":
        token = sign_token({"sub": "m_support", "email": username, "role": "staff", "iss": "orbit-console-preview"})
        return jsonify({"token": token, "note": "preview token, staff scope"})
    return jsonify({"error": "invalid preview credentials"}), 401


@app.get("/login")
def login_form():
    return redirect("/")


@app.post("/login")
def login():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "")
    if username == "support.ops@orbit.internal" and password == "0rb1t-Staff!2025":
        token = sign_token({"sub": "m_support", "email": username, "role": "staff", "iss": "orbit-console"})
        response = redirect("/console")
        response.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", path="/")
        return response
    return shell(
        "Sign-in failed",
        '<div class="flash err">Invalid staff credentials.</div><p><a href="/">Try again</a></p>',
    )


@app.get("/logout")
def logout():
    session.clear()
    response = redirect("/")
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response


@app.get("/console")
def console():
    claims = current_session()
    if not claims:
        return redirect("/")
    conn = db()
    try:
        tenants_rows = conn.execute("SELECT id, name, plan, mrr FROM tenants ORDER BY mrr DESC").fetchall()
        member_rows = conn.execute(
            "SELECT id, tenant_id, email, role FROM members ORDER BY tenant_id, email LIMIT 6"
        ).fetchall()
        audit_rows_db = conn.execute("SELECT ts, actor, action FROM audit ORDER BY id DESC LIMIT 5").fetchall()
    finally:
        conn.close()
    tenant_html = "".join(
        f"<tr><td class='mono'>{html.escape(row['id'])}</td><td>{html.escape(row['name'])}</td>"
        f"<td><span class='tag'>{html.escape(row['plan'])}</span></td>"
        f"<td>${row['mrr']:,}</td></tr>"
        for row in tenants_rows
    )
    member_html = "".join(
        f"<li><code>{html.escape(row['email'])}</code> <span class='dim'>· {html.escape(row['tenant_id'])}"
        f" · {html.escape(row['role'])}</span></li>"
        for row in member_rows
    )
    audit_html = "".join(
        f"<li><span class='dim mono'>{html.escape(row['ts'])}</span> · {html.escape(row['actor'])}"
        f" · {html.escape(row['action'])}</li>"
        for row in audit_rows_db
    )
    flag_block = ""
    if claims["role"] == "staff":
        flag_block = (
            f'<div class="panel"><h2>Staff access verified</h2><pre>{lab.flag("user")}</pre>'
            "<p>The console session is signed with the preview token. Tenant export is served by the "
            "billing API and is scoped to the administrator role.</p></div>"
        )
    return shell(
        f"Console · {claims['email']}",
        f'<div class="panel"><h2>Signed in</h2><p>Role <code>{html.escape(claims["role"])}</code> · '
        f'issuer <code>{html.escape(str(claims.get("iss")))}</code></p>'
        f'<p><a href="/console/export">Tenant export API</a> · '
        f'<a href="/console/admin">Administration</a></p></div>'
        + flag_block
        + f'<div class="panel"><h2>Tenants</h2><table><tr><th>ID</th><th>Tenant</th><th>Plan</th><th>MRR</th></tr>{tenant_html}</table></div>'
        + f'<div class="panel"><h2>Directory sample</h2><ul class="list">{member_html}</ul></div>'
        + f'<div class="panel"><h2>Recent activity</h2><ul class="list">{audit_html}</ul></div>',
    )


@app.get("/api/me")
def api_me():
    claims = current_session()
    if not claims:
        return jsonify({"error": "authentication required"}), 401
    return jsonify({"me": claims})


@app.get("/console/export")
def console_export_page():
    claims = current_session()
    if not claims:
        return redirect("/")
    sample = ""
    if claims["role"] == "admin":
        sample = f"""<div class="panel"><h2>Export ready</h2>
        <p>GET <code>/api/admin/tenants/export?format=json</code> returns the full billing snapshot
        with the finance hand-off block, including the administrator export key.</p>
        <pre>{lab.flag("api")}</pre>
        <p class="note">Administration console: <a href="/console/admin">/console/admin</a></p></div>"""
    return shell(
        "Tenant export",
        f"""<div class="panel"><h2>Billing export</h2>
        <p>Staff can review a tenant summary through <code>/api/tenant/summary</code>.
        The full finance export is RESTRICTED to <code>admin</code> sessions.</p>
        <pre>GET /api/tenant/summary          # staff scope
GET /api/admin/tenants/export    # admin scope</pre></div>{sample}""",
    )


@app.get("/api/tenant/summary")
def api_tenant_summary():
    claims = current_session()
    if not claims:
        return jsonify({"error": "authentication required"}), 401
    conn = db()
    try:
        count = conn.execute("SELECT COUNT(*) AS n FROM tenants").fetchone()["n"]
        mrr = conn.execute("SELECT SUM(mrr) AS m FROM tenants").fetchone()["m"]
    finally:
        conn.close()
    return jsonify({"requested_by": claims["email"], "tenants": count, "total_mrr": mrr, "export": "summary-only"})


@app.get("/api/admin/tenants/export")
def api_admin_export():
    claims = current_session()
    # VULNERABLE: role is read from the JWT claim without re-checking the issuer
    # (preview tokens were meant to be staff-only) - permissions are bound to a
    # client-controlled claim.
    if not claims or claims.get("role") != "admin":
        return jsonify({"error": "administrator role required"}), 403
    conn = db()
    try:
        rows = conn.execute("SELECT id, name, plan, mrr FROM tenants ORDER BY mrr DESC").fetchall()
    finally:
        conn.close()
    return jsonify(
        {
            "export": "orbit-billing-2026.11",
            "requested_by": claims["email"],
            "tenants": [dict(row) for row in rows],
            "finance_handoff": {
                "api_flag": lab.flag("api"),
                "next": "/console/admin",
                "note": "Administration console diagnostics are scoped to the platform team.",
            },
        }
    )


@app.get("/console/admin")
def console_admin():
    claims = current_session()
    if not claims:
        return redirect("/")
    if claims.get("role") != "admin":
        return shell("Forbidden", '<div class="flash err">Administrator role required.</div>', status=403)
    return shell(
        "Administration",
        f"""<div class="panel"><h2>Platform administrator</h2>
        <p>Signed in as <code>{html.escape(claims["email"])}</code>.</p>
        <ul class="list">
          <li><a href="/api/admin/tenants/export">Billing export API</a></li>
          <li><a href="/console/admin/diagnostics">Webhook diagnostics console</a></li>
        </ul>
        <p class="note">The worker only answers requests that carry the internal dispatch header.</p></div>""",
    )


@app.route("/console/admin/diagnostics", methods=["GET", "POST"])
def admin_diagnostics():
    claims = current_session()
    if not claims:
        return redirect("/")
    if claims.get("role") != "admin":
        return shell("Forbidden", '<div class="flash err">Administrator role required.</div>', status=403)
    submitted = "url" in request.values
    target = request.values.get("url", "").strip()
    if not submitted:
        target = f"http://127.0.0.1:{lab.port}/internal/worker/info"
    fetched = ""
    error = ""
    probe = request.values.get("probe", "")
    if submitted:
        if not target.startswith("http://") and not target.startswith("https://"):
            error = '<div class="flash err">The diagnostics fetcher accepts http(s) URLs only.</div>'
        else:
            full = target
            if probe:
                full += ("&" if "?" in target else "?") + urllib.parse.urlencode({"host": probe})
            try:
                # VULNERABLE: admin-supplied URL is fetched server-side with the
                # internal dispatch identity. Nothing restricts the destination.
                req = urllib.request.Request(full, headers={"X-Orbit-Dispatch": WORKER_TOKEN})
                with urllib.request.urlopen(req, timeout=5) as response:
                    fetched = response.read(200_000).decode("utf-8", "replace")
            except (urllib.error.URLError, ValueError, TimeoutError, OSError) as exc:
                error = f'<div class="flash err">Probe failed: {html.escape(str(exc))}</div>'
    return shell(
        "Webhook diagnostics",
        f"""<div class="panel"><h2>Probe a webhook receiver</h2>
        <p>Delivery workers run behind the platform gateway at
        <code>127.0.0.1:{lab.port}</code> until DNS is migrated. The probe forwards the internal
        dispatch identity so workers reply with their build metadata.</p>
        <form method="post">
          <label>Target URL</label>
          <input name="url" size="90" value="{html.escape(target)}">
          <label>Worker healthcheck host (optional)</label>
          <input name="probe" size="90" value="{html.escape(probe)}" placeholder="edge-worker-01">
          <p><button type="submit">Run probe</button></p>
        </form>
        <p class="note">Worker build metadata is served by <code>/internal/worker/info</code>.</p></div>
        {error}
        {f'<div class="panel"><h2>Response</h2><pre>{html.escape(fetched)}</pre></div>' if fetched else ''}""",
    )


@app.get("/internal/worker/info")
def worker_info():
    if request.headers.get("X-Orbit-Dispatch") != WORKER_TOKEN:
        return jsonify({"error": "internal dispatch identity required"}), 403
    return jsonify(
        {
            "service": "edge-worker-01",
            "region": "eu-central-1",
            "build": "2026.11.3-worker",
            "healthcheck": "/internal/worker/shell?host=<target>",
            "log": "webhook delivery journal: /tmp/orbit-worker.log",
        }
    )


@app.route("/internal/worker/shell", methods=["GET", "POST"])
def worker_shell():
    # Deliberately wrong: the worker shell is mounted next to the build metadata
    # and only requires the dispatch header, not administrator context.
    if request.headers.get("X-Orbit-Dispatch") != WORKER_TOKEN:
        return lab.app.response_class("internal dispatch identity required\n", status=403, mimetype="text/plain")
    host = request.values.get("host", "") or request.get_data(as_text=True)
    if not host:
        return lab.app.response_class("usage: host=<target>\n", mimetype="text/plain")
    # VULNERABLE: the worker resolves the healthcheck host through a shell.
    command = '/usr/bin/getent hosts ' + host
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=8)
        output = (result.stdout or "") + (result.stderr or "")
    except subprocess.TimeoutExpired:
        output = "worker resolution timed out"
    if lab.flag("root") in output:
        lab.objective_async("root", "worker healthcheck command injection read the root file")
    return lab.app.response_class(output, mimetype="text/plain")


if __name__ == "__main__":
    lab.run()