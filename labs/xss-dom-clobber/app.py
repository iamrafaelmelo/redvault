from __future__ import annotations

import html

from flask import Response, request

from labkit import Lab

lab = Lab("CLOBBER DESK", accent="#8b9dff")
app = lab.app

CAPTURED: list[str] = []
SUBMISSIONS: list[dict[str, str]] = []

DASHBOARD = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Clobber Desk</title>
<style>
body{margin:0;background:#08090a;color:#eef0f3;font-family:system-ui,sans-serif;line-height:1.6}
.shell{max-width:820px;margin:0 auto;padding:28px 22px}
.brand{font-family:monospace;color:#8b9dff;letter-spacing:.12em;font-size:11px}
.panel{border:1px solid #26282d;background:#0f1012;padding:20px;margin:18px 0}
h1{font-size:26px;margin:10px 0}h2{font-size:16px;margin:4px 0 12px}
input,button,select{font:inherit;padding:8px 10px;background:#09090b;border:1px solid #34363c;color:#eef0f3}
button{background:#8b9dff;color:#0b0c10;border-color:#8b9dff;cursor:pointer}
code{background:#111215;padding:1px 4px;color:#ff9aa6}
.muted{color:#9297a1}
</style></head><body><div class="shell">
<div class="brand">CLOBBER//DESK</div>
<h1>Partner referral dashboard</h1>
<p class="muted">Your workspace is rendered from <code>window.store</code>, which is hydrated from the URL fragment
without sanitising the markup. Referral links are rewritten on the client.</p>

<div class="panel"><h2>Your referral link</h2>
<div id="link-box"></div></div>

<div class="panel"><h2>Report a partner abuse</h2>
<p class="muted">Submissions are reviewed by the trust team bot.</p>
<form id="report-form" action="/submit" data-report-endpoint="/submit" data-destination="trust">
  <input name="note" placeholder="Describe the suspicious activity" size="60">
  <button type="submit">Submit report</button>
</form>
</div>
</div>
<script>
  (function () {
    // The referral workspace is hydrated from the URL fragment, exactly like a
    // client-side router. The code below trusts the resulting global scope.
    const store = { user: "guest", referralBase: "/join?ref=guest", destination: "trust" };
    window.store = store;
    const raw = decodeURIComponent(location.hash.slice(1));
    if (raw) {
      document.getElementById("link-box").innerHTML = raw;   // attacker markup lands in the DOM
    }
    // VULNERABLE: named elements shadow `window.config`, `window.store` and even
    // `window.__proto__`; the app reads them as trusted configuration objects.
    const cfg = window.config;                                  // clobbered by id="config"
    const proto = window.__proto__;                             // clobbered by name="__proto__"
    const endpoint = (cfg && (cfg.endpoint || cfg.getAttribute("data-endpoint")))
      || (proto && proto.getAttribute && proto.getAttribute("data-ref")) || store.destination;
    const base = (window.store && window.store.referralBase && window.store.referralBase.href)
      || window.store.referralBase;
    const link = document.createElement("a");
    link.href = base;
    link.textContent = "Invite a partner → " + base;
    if (!document.querySelector("#link-box a")) document.getElementById("link-box").appendChild(link);
    const form = document.getElementById("report-form");
    form.action = endpoint || form.getAttribute("data-report-endpoint");
    if (cfg && cfg.getAttribute && cfg.getAttribute("data-sink")) {
      form.setAttribute("data-sink", cfg.getAttribute("data-sink"));
    }
  })();
</script>
</body></html>"""


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">CLOBBER // DESK</div><h1>{title}</h1></div>{body}',
        nav='<a href="/">Dashboard</a><a href="/preview">Preview</a><a href="/report">Bot</a><a href="/captured">Captured</a>',
    )


@app.get("/")
def index():
    return Response(DASHBOARD, mimetype="text/html")


@app.get("/preview")
def preview():
    note = request.args.get("note", "")
    if note:
        body = f'<div class="panel"><h2>Shared note</h2><p>{note}</p><p class="dim">Trust team preview</p></div>'
    else:
        body = '<div class="panel"><p class="muted">No note selected. Use /preview?note=... to share one.</p></div>'
    return lab.page("Shared preview", body)


@app.get("/submit")
def submit():
    note = request.args.get("note", "")[:2000]
    if note:
        SUBMISSIONS.append({"note": note})
    # The clobbered endpoint receives the victim data as `data` and the bot's cookie as `c`.
    data = request.args.get("data", "")
    if data:
        CAPTURED.append(data[:2000])
        if lab.flag("flag") in data:
            lab.objective_async("flag", "dashboard config clobbered; victim data posted to attacker endpoint")
    return lab.redirect("/submitted")


@app.get("/submitted")
def submitted():
    return shell("Report received", '<div class="flash ok">Thanks — the trust team received your report.</div>')


@app.route("/report", methods=["GET", "POST"])
def report():
    notice = ""
    if request.method == "POST":
        path = request.form.get("path", "/").strip()
        if not path.startswith("/") or "://" in path:
            notice = '<div class="flash err">Submit a local path beginning with `/`.</div>'
        else:
            result = lab.bot(path, cookies=[{"name": "partner_session", "value": lab.flag("flag")}], wait=2.5)
            notice = f'<div class="flash {"ok" if result.get("ok") else "err"}">Bot visit: {result.get("ok") and "completed" or result.get("error", "failed")}</div>'
    return shell(
        "Trust bot",
        f"""<div class="panel"><h2>Send the trust reviewer</h2>
        <p>The reviewer opens a dashboard fragment with a readable <code>partner_session</code> cookie and
        submits the abuse form. The form action is read from a global that named elements can shadow.</p>
        <form method="post"><label>Local path (fragment allowed)</label>
        <input name="path" value="/#" size="90" style="width:100%">
        <p><button type="submit">Send reviewer</button></p></form>{notice}
        <p class="note">Collected data is listed at <code>/captured</code>.</p></div>""",
    )


@app.get("/collect")
def collect():
    value = request.args.get("c", "") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
        if lab.flag("flag") in value:
            lab.objective_async("flag", "partner cookie exfiltrated through DOM clobbering")
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(f"<li><code>{html.escape(value)}</code></li>" for value in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'
    return shell("Captured data", f'<div class="panel"><h2>Exfiltration collector</h2><ul class="list">{rows}</ul></div>')


if __name__ == "__main__":
    lab.run()