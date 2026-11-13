from __future__ import annotations

import json
import secrets
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

from flask import jsonify, redirect, request, session

from labkit import Lab

lab = Lab("WAYLINE LOGISTICS", accent="#e8a13a")
app = lab.app

Path("/tmp/logistics-root.txt").write_text(lab.flag("root") + "\n")

USERS = {"customer": {"password": "track2026", "display": "Harbor Supply Co."}}
CARRIER_TOKEN = secrets.token_urlsafe(24)
DISPATCH_TOKEN = secrets.token_urlsafe(22)
SHIPMENTS = [
    {"id": "WL-4417", "status": "in transit", "route": "Santos → Rotterdam", "eta": "2026-11-19"},
    {"id": "WL-4418", "status": "customs", "route": "Rotterdam → Oslo", "eta": "2026-11-21"},
]


def shell(title: str, body: str) -> object:
    nav = '<a href="/portal">Portal</a><a href="/logout">Logout</a>' if session.get("user") else '<a href="/">Customer login</a><a href="/api/docs">API docs</a>'
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">WAYLINE // LOGISTICS CONTROL</div><h1>{title}</h1>'
        "<p>Shipment visibility and carrier integrations for regional freight.</p></div>" + body,
        nav=nav,
    )


@app.get("/")
def index():
    if session.get("user"):
        return redirect("/portal")
    return shell(
        "Customer login",
        """<div class="panel"><h2>Freight visibility</h2>
        <form method="post" action="/login"><label>Customer</label><input name="username" value="customer">
        <label>Password</label><input name="password" type="password">
        <p><button type="submit">Sign in</button></p></form>
        <p class="note">Integration credentials are documented for the carrier sandbox at <a href="/api/docs">/api/docs</a>.</p></div>""",
    )


@app.get("/api/docs")
def docs():
    return jsonify(
        {
            "service": "wayline-tracking",
            "version": "v1",
            "demo_account": {"username": "customer", "password": "track2026"},
            "endpoints": {
                "GET /api/v1/track?carrier=<url>": "Fetch a carrier tracking payload through the preview proxy.",
                "GET /api/v1/shipments": "List shipments for an authenticated customer.",
            },
            "notes": "The preview proxy adds the internal carrier identity header. Carrier URLs are validated against the localhost deny-list.",
        }
    )


@app.post("/login")
def login():
    user = request.form.get("username", "")
    record = USERS.get(user)
    if record and record["password"] == request.form.get("password", ""):
        session.clear()
        session["user"] = user
        return redirect("/portal")
    return shell("Login failed", '<div class="flash err">Invalid customer credentials.</div><p><a href="/">Try again</a></p>')


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.get("/portal")
def portal():
    if not session.get("user"):
        return redirect("/")
    rows = "".join(
        f'<div class="panel"><h3>{item["id"]} · {item["status"]}</h3><p>{item["route"]}</p><span class="tag">ETA {item["eta"]}</span></div>'
        for item in SHIPMENTS
    )
    return shell(
        "Customer portal",
        f'<div class="panel"><h2>Visibility flag</h2><pre>{lab.flag("user")}</pre>'
        '<p>The tracking proxy is available at <code>/api/v1/track?carrier=&lt;url&gt;</code>.</p></div>' + rows,
    )


@app.get("/api/v1/shipments")
def shipments():
    if not session.get("user"):
        return jsonify({"error": "authentication required"}), 401
    return jsonify({"customer": session["user"], "shipments": SHIPMENTS})


@app.get("/api/v1/track")
def track():
    if not session.get("user"):
        return jsonify({"error": "authentication required"}), 401
    carrier = request.args.get("carrier", "")
    parsed = urlparse(carrier)
    if parsed.scheme not in {"http", "https"}:
        return jsonify({"error": "a valid carrier URL is required"}), 400
    if "localhost" in (parsed.hostname or "").lower():
        return jsonify({"error": "localhost is blocked by the carrier deny-list"}), 400
    try:
        req = urllib.request.Request(carrier, headers={"X-Carrier-Proxy": CARRIER_TOKEN})
        with urllib.request.urlopen(req, timeout=5) as response:
            body = response.read(200_000).decode("utf-8", "replace")
    except (urllib.error.URLError, ValueError, TimeoutError, OSError) as exc:
        return jsonify({"error": f"carrier fetch failed: {exc}"}), 502
    return shell(
        "Carrier preview",
        f'<div class="panel"><h2>Upstream response</h2><pre>{body}</pre></div>'
        f'<p class="note">Fetched by the WAYLINE service from <code>{carrier}</code>.</p>',
    )


@app.get("/internal/carrier")
def internal_carrier():
    if request.headers.get("X-Carrier-Proxy") != CARRIER_TOKEN:
        return jsonify({"error": "carrier proxy identity required"}), 403
    return jsonify(
        {
            "service": "wayline-dispatch-internal",
            "api_flag": lab.flag("api"),
            "dispatch_token": DISPATCH_TOKEN,
            "note": "Dispatch console token. Remove before the carrier migration is published.",
        }
    )


@app.route("/dispatch/console", methods=["GET", "POST"])
def dispatch_console():
    token = request.values.get("token", "")
    if token != DISPATCH_TOKEN:
        return shell("Forbidden", '<div class="flash err">A valid dispatch token is required.</div>'), 403
    output = ""
    if request.method == "POST":
        host = request.form.get("host", "127.0.0.1")
        # VULNERABLE: shell interpolation in an internal dispatch diagnostic.
        command = f"getent hosts {host} 2>&1 || true"
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=8)
            output = (result.stdout or "") + (result.stderr or "")
        except subprocess.TimeoutExpired:
            output = "dispatch diagnostic timed out"
        if lab.flag("root") in output:
            lab.objective_async("root", "root flag read through dispatch command injection")
    return shell(
        "Dispatch console",
        f"""<div class="panel"><h2>Carrier host diagnostic</h2>
        <p>The dispatch service account can read <code>/tmp/logistics-root.txt</code>.</p>
        <form method="post"><input type="hidden" name="token" value="{token}">
        <label>Carrier host</label><input name="host" value="127.0.0.1">
        <p><button type="submit">Resolve host</button></p></form></div>
        {f'<div class="panel"><h2>Output</h2><pre>{output}</pre></div>' if output else ''}""",
    )


if __name__ == "__main__":
    lab.run()
