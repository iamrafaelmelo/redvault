from __future__ import annotations

import html
import json
import secrets

from flask import Response, jsonify, request

from labkit import Lab

lab = Lab("NONCE CONSOLE", accent="#f2a65a")
app = lab.app

CAPTURED: list[str] = []

# The console reads its telemetry sinks from a JSON endpoint. The endpoint
# reflects the `callback` parameter inside a script block that carries the very
# nonce the page allows, i.e. a classic nonce-reuse / JSONP-style gadget.
SINKS = {
    "primary": "https://telemetry.corp.internal/v1/ingest",
    "fallback": "https://telemetry-backup.corp.internal/v1/ingest",
}


def shell(title: str, body: str, nav: str | None = None) -> object:
    if nav is None:
        nav = '<a href="/">Console</a><a href="/api/sinks">Sinks</a><a href="/report">Bot</a><a href="/captured">Captured</a>'
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">NONCE // CONTENT CONSOLE</div><h1>{title}</h1></div>{body}',
        nav=nav,
    )


def csp(nonce: str) -> dict[str, str]:
    policy = (
        "default-src 'none'; "
        f"script-src 'nonce-{nonce}'; "
        "style-src 'self'; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'none'"
    )
    return {
        "Content-Security-Policy": policy,
        "X-Content-Type-Options": "nosniff",
    }


@app.get("/")
def index():
    nonce = secrets.token_urlsafe(16)
    body = f"""<div class="panel"><h2>Content delivery console</h2>
    <p class="lead">Every page served by this console ships a strict nonce-based CSP. Only scripts
    carrying the per-response nonce <code>{html.escape(nonce)}</code> are allowed to run.</p>
    <div class="terminal"><span class="p">$</span> curl -s '/api/sinks?callback=demo' <span class="dim"># legacy widget feed</span></div>
    <ul class="list">
      <li>Primary ingest sink · <code>{html.escape(SINKS["primary"])}</code></li>
      <li>Fallback ingest sink · <code>{html.escape(SINKS["fallback"])}</code></li>
    </ul>
    <p class="note">The JSON feed answers with <code>callback(payload)</code> wrapped in a script block so
    older widgets can load it with a plain <code>&lt;script src&gt;</code> tag. The console re-serves that
    bootstrap below with the page nonce:</p>
    <div id="bootstrap"></div></div>
    <script nonce="{nonce}">window.__CONSOLE_NONCE__ = "{nonce}";</script>
    <script nonce="{nonce}">
      fetch('/api/sinks?callback=window.__sinks=').then(function (r) {{ return r.text(); }}).then(function (t) {{
        var m = /<script[^>]*>([\\s\\S]*)<\\/script>/.exec(t);
        var s = document.createElement('script');
        s.setAttribute('nonce', window.__CONSOLE_NONCE__);   // reuse the page nonce
        s.textContent = m ? m[1] : t;
        document.getElementById('bootstrap').appendChild(s);
      }});
    </script>"""
    response = lab.page(
        "Content console",
        body,
        nav="<a href='/'>Console</a><a href='/api/sinks'>Sinks</a><a href='/report'>Bot</a><a href='/captured'>Captured</a>",
    )
    for key, value in csp(nonce).items():
        response.headers[key] = value
    return response


@app.get("/api/sinks")
def api_sinks():
    nonce = secrets.token_urlsafe(16)
    callback = request.args.get("callback", "").strip()
    payload = json.dumps(SINKS, separators=(",", ":"))
    if callback:
        # VULNERABLE: the parameter is reflected verbatim into a script block that
        # is stamped with the current page nonce, so CSP allows whatever lands there.
        inner = f"{callback}({payload})"
    else:
        inner = payload
    body = (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<title>Sinks</title></head><body>"
        f'<script nonce="{nonce}">{inner}</script>'
        "</body></html>"
    )
    response = Response(body, mimetype="text/html")
    for key, value in csp(nonce).items():
        response.headers[key] = value
    return response


@app.get("/api/sinks.json")
def api_sinks_json():
    # Hardened sibling endpoint kept for the new widgets: no callback, JSON only.
    return jsonify(SINKS)


@app.route("/report", methods=["GET", "POST"])
def report():
    notice = ""
    if request.method == "POST":
        path = request.form.get("path", "/").strip()
        if not path.startswith("/") or "://" in path:
            notice = '<div class="flash err">Submit a local path beginning with `/`.</div>'
        else:
            result = lab.bot(path, cookies=[{"name": "console_session", "value": lab.flag("flag")}], wait=2.0)
            notice = f'<div class="flash {"ok" if result.get("ok") else "err"}">Bot visit: {result.get("ok") and "completed" or result.get("error", "failed")}</div>'
    return shell(
        "Console bot",
        f"""<div class="panel"><h2>Send the console bot</h2>
        <p>The operator bot opens a local path with its readable <code>console_session</code> cookie.
        The target page must be allowed to run its scripts, so the nonce gadget is the whole game.</p>
        <form method="post"><label>Local path</label><input name="path" value="/api/sinks?callback=demo" size="80">
        <p><button type="submit">Send bot</button></p></form>{notice}
        <p class="note">Exfiltration lands in <code>/collect?c=...</code> and is listed at <code>/captured</code>.</p></div>""",
    )


@app.get("/collect")
def collect():
    value = request.args.get("c", "") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
        if lab.flag("flag") in value:
            lab.objective_async("flag", "console session cookie exfiltrated through the nonce JSONP gadget")
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(f"<li><code>{html.escape(value)}</code></li>" for value in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'
    return shell("Captured data", f'<div class="panel"><h2>Exfiltration collector</h2><ul class="list">{rows}</ul></div>')


if __name__ == "__main__":
    lab.run()