from __future__ import annotations

import html
import uuid
from pathlib import Path

from flask import request

from labkit import Lab

lab = Lab("EDGELINE", accent="#c084fc")
app = lab.app

CACHE: dict[str, str] = {}
CAPTURED: list[str] = []


def shell(title: str, body: str, nav: str | None = None) -> object:
    if nav is None:
        nav = '<a href="/home">Home</a><a href="/report">Review bot</a><a href="/captured">Captured data</a><a href="/cache">Cache state</a>'
    return lab.page(title, f'<div class="hero"><div class="kicker">EDGELINE // STATIC EDGE</div><h1>{title}</h1></div>{body}', nav=nav)


@app.get("/")
def index():
    return lab.redirect("/home")


@app.get("/home")
def home():
    host = request.headers.get("X-Forwarded-Host", "127.0.0.1")
    if "/home" in CACHE:
        body = CACHE["/home"]
        cache_state = "HIT"
    else:
        # VULNERABLE: the response varies on X-Forwarded-Host, but the cache key
        # is only the path. The header is also reflected without encoding.
        body = f"""<div class="hero"><div class="kicker">EDGELINE // STATIC EDGE</div>
        <h1>Welcome to the field console</h1>
        <p class="brand-banner">Served for host: {host}</p></div>
        <div class="panel"><h2>Sensor fleet</h2><p>All regional sensors are reporting on schedule.</p>
        <p class="note">Anonymous visitors receive the shared edge cache. Preview hosts are rendered in the banner.</p></div>"""
        CACHE["/home"] = body
        cache_state = "MISS"
    response = lab.app.response_class(
        shell("Field console", body).get_data(as_text=True),
        mimetype="text/html",
    )
    response.headers["X-Cache"] = cache_state
    return response


@app.get("/cache")
def cache_view():
    key = html.escape(CACHE.get("/home", ""))
    body = f'<div class="panel"><h2>Cache entry for /home</h2><pre>{key or "(empty)"}</pre></div>'
    return shell("Edge cache state", body)


@app.route("/report", methods=["GET", "POST"])
def report():
    notice = ""
    if request.method == "POST":
        result = lab.bot("/home", cookies=[{"name": "admin_session", "value": lab.flag("flag")}], wait=2.0)
        notice = f'<div class="flash {"ok" if result.get("ok") else "err"}">Bot visit: {result.get("ok") and "completed" or result.get("error", "failed")}</div>'
    return shell(
        "Review bot",
        f"""<div class="panel"><h2>Review the edge page</h2>
        <p>The review bot opens <code>/home</code> with a readable <code>admin_session</code> cookie. It sees whatever the cache currently serves.</p>
        <form method="post"><button type="submit">Send review bot</button></form>{notice}
        <p class="note">The collector records values at <code>/collect</code>. Inspect <a href="/cache">/cache</a> to see the stored entry.</p></div>""",
    )


@app.route("/collect", methods=["GET", "POST"])
def collect():
    value = request.args.get("c", "") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
        if lab.flag("flag") in value:
            lab.objective_async("flag", "cached XSS exfiltrated the admin session cookie")
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(f'<li><code>{html.escape(value)}</code></li>' for value in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'
    return shell("Captured data", f'<div class="panel"><h2>Exfiltration collector</h2><ul class="list">{rows}</ul></div>')


@app.get("/reset-cache")
def reset_cache():
    CACHE.clear()
    return lab.redirect("/home")


if __name__ == "__main__":
    lab.run()