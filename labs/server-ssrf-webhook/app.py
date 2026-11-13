from __future__ import annotations

import secrets
import urllib.error
import urllib.request
from urllib.parse import urlparse

from flask import jsonify, request

from labkit import Lab

lab = Lab("HOOKLINE", accent="#4fa3d8")
app = lab.app

PROXY_TOKEN = secrets.token_urlsafe(24)


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">HOOKLINE // WEBHOOK PREVIEW</div><h1>{title}</h1>'
        '<p>Fetch a partner webhook payload and inspect the response body before deployment.</p></div>' + body,
        nav='<a href="/">Preview</a><a href="/internal/flag">Internal health</a>',
    )


@app.route("/", methods=["GET", "POST"])
def index():
    url = ""
    body = ""
    error = ""
    if request.method == "POST":
        url = request.form.get("url", "").strip()
        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            error = "Provide an http(s) webhook URL."
        elif "localhost" in url.lower() or "127.0.0.1" in url:
            # VULNERABLE: substring deny-list instead of resolved-address validation.
            error = "The preview proxy refuses localhost targets."
        else:
            try:
                req = urllib.request.Request(url, headers={"X-Webhook-Proxy": PROXY_TOKEN})
                with urllib.request.urlopen(req, timeout=5) as response:
                    body = response.read(200_000).decode("utf-8", "replace")
            except (urllib.error.URLError, ValueError, TimeoutError, OSError) as exc:
                error = f"Fetch failed: {exc}"
            if lab.flag("flag") in body:
                lab.objective_async("flag", "loopback reached through alternate notation")
    notice = f'<div class="flash err">{error}</div>' if error else ""
    output = f'<div class="panel"><h2>Upstream response</h2><pre>{body}</pre></div>' if body else ""
    return shell(
        "Webhook preview",
        f"""<div class="panel"><h2>Fetch a webhook</h2>
        <form method="post"><label>Webhook URL</label><input name="url" value="{url}" size="90" placeholder="https://partner.example/webhook">
        <p><button type="submit">Fetch preview</button></p></form>{notice}
        <p class="note">The preview adds the internal integration identity. Loopback targets are blocked by name.</p></div>{output}""",
    )


@app.get("/internal/flag")
def internal_flag():
    if request.headers.get("X-Webhook-Proxy") != PROXY_TOKEN:
        return jsonify({"error": "integration identity required"}), 403
    return jsonify({"service": "hookline-internal", "scope": "integration", "flag": lab.flag("flag")})


if __name__ == "__main__":
    lab.run()