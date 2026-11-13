from __future__ import annotations

import secrets
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from flask import jsonify, request

from labkit import Lab

lab = Lab("LAMPWORK", accent="#e05d5d")
app = lab.app

Path("/tmp/redvault-chain-flag.txt").write_text(lab.flag("flag") + "\n")
PROXY_TOKEN = secrets.token_urlsafe(24)
ADMIN_TOKEN = secrets.token_urlsafe(22)


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">LAMPWORK // SENSOR CONTROL PLANE</div><h1>{title}</h1></div>' + body,
        nav='<a href="/">Fetcher</a><a href="/admin">Admin</a>',
    )


@app.get("/")
def index():
    return shell(
        "Field fetcher",
        """<div class="panel"><h2>Fetch a sensor manifest</h2>
        <p>The fetcher retrieves a URL server-side and adds the internal integration identity so sensor gateways can respond.</p>
        <form method="get" action="/fetch"><label>Manifest URL</label>
        <input name="url" value="http://sensors.internal/manifest.json" size="90">
        <p><button type="submit">Fetch manifest</button></p></form>
        <p class="note">Key rotation endpoints are internal-only and should not be reachable from the public surface.</p></div>""",
    )


@app.get("/fetch")
def fetch():
    url = request.args.get("url", "")
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return shell("Fetch failed", '<div class="flash err">Provide an http(s) URL.</div>')
    try:
        req = urllib.request.Request(url, headers={"X-Internal-Proxy": PROXY_TOKEN})
        with urllib.request.urlopen(req, timeout=5) as response:
            body = response.read(200_000).decode("utf-8", "replace")
    except (urllib.error.URLError, ValueError, TimeoutError, OSError) as exc:
        return shell("Fetch failed", f'<div class="flash err">Fetch failed: {exc}</div>')
    return shell(
        "Manifest response",
        f'<div class="panel"><h2>Fetched</h2><pre>{body}</pre></div><p class="note">Requested by the Lampwork fetcher.</p>',
    )


@app.get("/internal/keys")
def internal_keys():
    if request.headers.get("X-Internal-Proxy") != PROXY_TOKEN:
        return jsonify({"error": "internal proxy identity required"}), 403
    return jsonify(
        {
            "service": "lampwork-key-service",
            "key_version": "2026.11",
            "admin_token": ADMIN_TOKEN,
            "note": "Rotate after the field migration.",
        }
    )


@app.route("/admin", methods=["GET", "POST"])
def admin():
    token = request.headers.get("X-Admin-Token") or request.values.get("token", "")
    if token != ADMIN_TOKEN:
        return shell("Forbidden", '<div class="flash err">A valid admin token is required.</div>'), 403
    output = ""
    if request.method == "POST":
        host = request.form.get("host", "127.0.0.1")
        # VULNERABLE: the admin diagnostic passes the host into a shell command.
        command = f"getent hosts {host} 2>&1 || true"
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=8)
            output = (result.stdout or "") + (result.stderr or "")
        except subprocess.TimeoutExpired:
            output = "diagnostic timed out"
        if lab.flag("flag") in output:
            lab.objective_async("flag", "SSRF to admin token to command injection chain completed")
    return shell(
        "Control plane admin",
        f"""<div class="panel"><h2>Diagnostics</h2>
        <form method="post">
          <input type="hidden" name="token" value="{token}">
          <label>Gateway host</label><input name="host" value="127.0.0.1">
          <p><button type="submit">Run diagnostic</button></p></form>
        <p class="note">Diagnostics run as the sensor service account. Its private artifacts live in /tmp.</p></div>
        {f'<div class="panel"><h2>Output</h2><pre>{output}</pre></div>' if output else ''}""",
    )


@app.post("/admin/diag")
def admin_diag():
    return admin()


if __name__ == "__main__":
    lab.run()