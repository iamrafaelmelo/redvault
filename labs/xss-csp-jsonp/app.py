from __future__ import annotations

import html
import json
from urllib.parse import unquote

from flask import Response, request

from labkit import Lab

lab = Lab("NORTHWIRE", accent="#6ea8fe")
app = lab.app

CSP = "default-src 'self'; script-src 'self' https://cdn.example; object-src 'none'; base-uri 'none'; frame-ancestors 'self'"
CALLERS = {"dashboard": True, "widget": True, "public": True}
CAPTURED: list[str] = []
FEED: list[dict[str, str]] = []

CARDS = [
    {"id": "relay", "title": "Relay status", "body": "All regional relays are reporting nominal latency."},
    {"id": "audit", "title": "Audit window", "body": "Quarterly access review opens on Monday 09:00 UTC."},
]


def page(title: str, body: str, csp: str = CSP) -> Response:
    response = lab.page(
        title,
        f'<div class="hero"><div class="kicker">NORTHWIRE // OPERATIONS FEED</div><h1>{title}</h1>'
        "<p>Operational bulletins for the Northwind relay network. The console runs under a strict"
        " Content-Security-Policy; the dashboard cards are loaded from an allow-listed JSONP feed.</p></div>" + body,
        nav='<a href="/">Feed</a><a href="/admin">Admin</a><a href="/report">Bot preview</a><a href="/captured">Captured</a>',
    )
    response.headers["Content-Security-Policy"] = csp
    return response


@app.get("/")
def index():
    posts = "".join(
        f'<div class="panel"><h3>{html.escape(card["title"])}</h3><p>{html.escape(card["body"])}</p></div>' for card in CARDS
    )
    # VULNERABLE: bulletins are stored and rendered without encoding.
    feed = "".join(
        f'<div class="panel"><h3>{item["title"]}</h3><p>{item["body"]}</p></div>' for item in reversed(FEED)
    )
    return page(
        "Operations feed",
        f"""<div class="panel"><h2>Post a bulletin</h2>
        <form method="post" action="/post">
          <label>Title</label><input name="title" placeholder="Shift handover">
          <label>Body</label><textarea name="body" rows="3"></textarea>
          <p><button type="submit">Publish bulletin</button></p>
        </form>
        <p class="note">Bulletins are reviewed by the duty operator through the admin console.</p></div>
        {feed}
        <h2>Standing cards</h2>
        <div id="widgets"></div>
        <script src="/api/jsonp?callback=renderCards"></script>{posts}""",
    )


@app.post("/post")
def post():
    item = {
        "title": request.form.get("title", "Shift handover")[:120] or "Shift handover",
        "body": request.form.get("body", "")[:4000],
    }
    if item["body"]:
        FEED.append(item)
    return page("Bulletin published", '<div class="flash ok">Bulletin queued for the current shift.</div>')


@app.get("/api/jsonp")
def jsonp():
    callback = request.args.get("callback", "")
    name = unquote(callback)
    if not name:
        return Response(json.dumps({"cards": CARDS}), mimetype="application/json")
    if not name.isidentifier() and not all(part.isidentifier() for part in name.split(".")):
        # VULNERABLE: only the shape is checked. Any reference the identifier can
        # reach (for example `window.name`) is allowed, so the JSONP endpoint becomes
        # a script sink for an attacker-chosen expression that the page will run.
        return Response("/* invalid callback */", mimetype="application/javascript")
    body = f"{name}({json.dumps({'cards': CARDS, 'source': 'northwire-feed'})});"
    return Response(body, mimetype="application/javascript", headers={"X-Content-Type-Options": "nosniff"})


@app.get("/admin")
def admin():
    site = request.headers.get("Sec-Fetch-Site", "same-origin")
    token = request.cookies.get("duty_session", "")
    payload = {"user": "duty-operator", "role": "admin", "flag": lab.flag("flag")}
    if site not in {"same-origin", "none"}:
        return Response('{"error":"cross-origin read blocked"}', status=403, mimetype="application/json")
    if not token:
        response = Response(json.dumps(payload), mimetype="application/json")
        response.set_cookie("duty_session", "duty-operator", httponly=False, samesite="Lax")
        return response
    return Response(json.dumps(payload), mimetype="application/json")


@app.get("/admin.html")
def admin_page():
    return page(
        "Admin console",
        """<div class="panel"><h2>Duty operator</h2>
        <p>Bulletins awaiting review:</p><ul class="list" id="queue"></ul>
        <script src="/api/jsonp?callback=renderQueue"></script>
        <p class="note">The console renders bulletins in an isolated context.</p></div>""",
    )


@app.route("/report", methods=["GET", "POST"])
def report():
    message = ""
    if request.method == "POST":
        result = lab.bot("/admin.html", cookies=[{"name": "duty_session", "value": lab.flag("flag")}], wait=2.0)
        message = f'<div class="flash {"ok" if result.get("ok") else "err"}">Bot visit: {result.get("ok") and "completed" or result.get("error", "failed")}</div>'
    return page(
        "Duty operator bot",
        f"""<div class="panel"><h2>Trigger a review</h2>
        <p>The duty bot opens <code>/admin.html</code> with a readable <code>duty_session</code> cookie.
        The console keeps the strict CSP; only allow-listed scripts run.</p>
        <form method="post"><button type="submit">Send duty bot</button></form>{message}
        <p class="note">Values reported to <code>/collect</code> appear under <a href="/captured">Captured</a>.</p></div>""",
    )


@app.route("/collect", methods=["GET", "POST"])
def collect():
    value = request.args.get("c", "") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
        if lab.flag("flag") in value:
            lab.objective_async("flag", "JSONP callback sink executed in the admin console under the strict CSP")
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(f"<li><code>{html.escape(value)}</code></li>" for value in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'
    return page("Captured data", f'<div class="panel"><h2>Collector</h2><ul class="list">{rows}</ul></div>')


if __name__ == "__main__":
    lab.run()