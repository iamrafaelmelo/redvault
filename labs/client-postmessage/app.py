from __future__ import annotations

from flask import request

from labkit import Lab

lab = Lab("MESSAGE PIER", accent="#70c1b3")
app = lab.app

CAPTURED: list[str] = []

VICTIM = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Message Pier · Victim</title>
<style>body{margin:0;background:#0b0c0d;color:#e9ecef;font-family:system-ui,sans-serif;padding:30px}.card{border:1px solid #2b2e33;background:#121316;padding:22px;max-width:700px;margin:auto}h1{font-size:22px}#msg{border:1px dashed #41454d;padding:16px;margin-top:16px;min-height:50px;color:#aab0b9}</style>
</head><body><div class="card"><div style="font-family:monospace;font-size:10px;color:#70c1b3">MESSAGE PIER // RECEIVER</div>
<h1>Preview receiver</h1><p>This window accepts preview messages from the pier.</p><div id="msg">Waiting for a preview…</div></div>
<script>
  window.addEventListener("message", (event) => {
    // VULNERABLE: checks origin but trusts the message body as HTML.
    if (event.origin === window.location.origin && event.data && event.data.type === "preview") {
      document.getElementById("msg").innerHTML = String(event.data.html || "");
    }
  });
</script></body></html>"""

EXPLOIT = """<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Message Pier · Preview sender</title>
<style>body{margin:0;background:#0b0c0d;color:#e9ecef;font-family:system-ui,sans-serif;padding:30px}.card{border:1px solid #2b2e33;background:#121316;padding:22px;max-width:800px;margin:auto}iframe{width:100%;height:260px;border:1px solid #41454d;background:#08090a;margin-top:16px}code{color:#ff9aa6}</style>
</head><body><div class="card"><div style="font-family:monospace;font-size:10px;color:#70c1b3">MESSAGE PIER // SENDER</div>
<h1>Preview sender</h1><p>The sender opens the receiver and posts the `x` value as a preview.</p>
<iframe id="frame" src="/victim"></iframe></div>
<script>
  const frame = document.getElementById("frame");
  const value = new URLSearchParams(location.search).get("x") || "<p>No preview supplied.</p>";
  frame.addEventListener("load", () => {
    frame.contentWindow.postMessage({type: "preview", html: value}, window.location.origin);
  });
</script></body></html>"""


def shell(title: str, body: str) -> object:
    return lab.page(title, f'<div class="hero"><div class="kicker">MESSAGE PIER // PREVIEW</div><h1>{title}</h1></div>{body}', nav='<a href="/victim">Receiver</a><a href="/exploit">Sender</a><a href="/report">Bot</a><a href="/captured">Captured</a>')


@app.get("/victim")
def victim():
    return lab.app.response_class(VICTIM, mimetype="text/html")


@app.get("/exploit")
def exploit():
    return lab.app.response_class(EXPLOIT, mimetype="text/html")


@app.route("/report", methods=["GET", "POST"])
def report():
    notice = ""
    if request.method == "POST":
        path = request.form.get("path", "/exploit").strip()
        if not path.startswith("/") or "://" in path:
            notice = '<div class="flash err">Submit a local path beginning with `/`.</div>'
        else:
            result = lab.bot(path, cookies=[{"name": "review_session", "value": lab.flag("flag")}], wait=2.5)
            notice = f'<div class="flash {"ok" if result.get("ok") else "err"}">Bot visit: {result.get("ok") and "completed" or result.get("error", "failed")}</div>'
    return shell(
        "Review bot",
        f'''<div class="panel"><h2>Open a preview link</h2>
        <p>The reviewer opens your local sender URL with a readable privileged cookie.</p>
        <form method="post"><label>Local path</label><input name="path" value="/exploit?x=%3Cp%3Ehello%3C%2Fp%3E" size="90">
        <p><button type="submit">Send reviewer</button></p></form>{notice}
        <p class="note">The receiver checks `event.origin` but inserts the message body with `innerHTML`. Origin trust is not content safety.</p></div>''',
    )


@app.get("/collect")
def collect():
    value = request.args.get("c", "") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
        if lab.flag("flag") in value:
            lab.objective_async("flag", "reviewer cookie exfiltrated through postMessage HTML injection")
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(f"<li><code>{value}</code></li>" for value in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'
    return shell("Captured data", f'<div class="panel"><h2>Exfiltration collector</h2><ul class="list">{rows}</ul></div>')


if __name__ == "__main__":
    lab.run()
