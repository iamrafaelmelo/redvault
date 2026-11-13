from __future__ import annotations

import secrets
import urllib.error
import urllib.request
from urllib.parse import urlparse

from flask import request

from labkit import Lab

lab = Lab("IMAGEFETCH", accent="#4fa8d8")
app = lab.app

INTERNAL_TOKEN = secrets.token_urlsafe(24)


def shell(title: str, body: str) -> object:
    return lab.page(title, f'<div class="hero"><div class="kicker">IMAGEFETCH // REMOTE PREVIEW</div><h1>{title}</h1></div>{body}', nav='<a href="/">Fetch</a><a href="/internal/flag">Internal health</a>')


@app.route("/", methods=["GET", "POST"])
def index():
    remote = ""
    error = ""
    url = request.form.get("url", "") if request.method == "POST" else ""
    if request.method == "POST":
        parsed = urlparse(url)
        # VULNERABLE / weak filter: rejects only the literal localhost name.
        if parsed.scheme not in {"http", "https"}:
            error = '<div class="flash err">Only http(s) URLs are accepted.</div>'
        elif "localhost" in (parsed.hostname or "").lower():
            error = '<div class="flash err">localhost is blocked by the preview proxy.</div>'
        else:
            try:
                req = urllib.request.Request(url, headers={"X-Internal-Proxy": INTERNAL_TOKEN})
                with urllib.request.urlopen(req, timeout=4) as response:
                    remote = response.read(200_000).decode("utf-8", "replace")
            except (urllib.error.URLError, ValueError, TimeoutError, OSError) as exc:
                error = f'<div class="flash err">Fetch failed: {exc}</div>'
            if lab.flag("flag") in remote:
                lab.objective_async("flag", "internal metadata reached through SSRF")
    preview = f'<div class="panel"><h2>Remote response</h2><pre>{remote}</pre></div>' if remote else ""
    return shell(
        "Image preview fetcher",
        f"""<div class="panel"><h2>Fetch a remote image</h2>
        <p>The preview service accepts a URL and retrieves it server-side. Current lab listener: <code>127.0.0.1:{lab.port}</code>.</p>
        <form method="post"><label>URL</label><input name="url" value="{url}" size="90" placeholder="http://example.test/image.png">
        <p><button type="submit">Fetch preview</button></p></form>{error}</div>{preview}
        <p class="note">Internal endpoints should only be reachable by the service itself. The fetcher's network location is the service.</p>""",
    )


@app.get("/internal/flag")
def internal_flag():
    remote = request.remote_addr or ""
    if request.headers.get("X-Internal-Proxy") != INTERNAL_TOKEN:
        return {"error": "internal proxy identity required", "remote": remote}, 403
    return {"service": "image-metadata", "scope": "internal", "flag": lab.flag("flag")}


if __name__ == "__main__":
    lab.run()
