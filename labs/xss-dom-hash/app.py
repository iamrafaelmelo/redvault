from __future__ import annotations

from flask import request

from labkit import Lab

lab = Lab("MIRROR DOCS", accent="#54c9a5")
app = lab.app

CAPTURED: list[str] = []

INDEX = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mirror Docs</title>
<style>
body{margin:0;background:#08090a;color:#eef0f3;font-family:system-ui,sans-serif;line-height:1.6}
.shell{max-width:760px;margin:0 auto;padding:32px 22px}.brand{font-family:monospace;color:#54c9a5;letter-spacing:.12em;font-size:11px}
.panel{border:1px solid #26282d;background:#0f1012;padding:20px;margin:18px 0}h1{font-size:28px;margin:10px 0}
code{background:#111215;padding:2px 5px;color:#ff8b9a}.muted{color:#9297a1}
</style></head><body><div class="shell">
<div class="brand">MIRROR//DOCS</div>
<h1>Markdown preview</h1>
<p class="muted">The preview is rendered entirely in the browser from the URL fragment. No server round-trip.</p>
<div class="panel"><div id="preview">Add a fragment to preview a note.</div></div>
<p class="muted">Example: <code>#Hello%20operator</code></p>
<script>
  const preview = document.getElementById("preview");
  function render() {
    const raw = decodeURIComponent(location.hash.slice(1));
    // VULNERABLE: attacker-controlled fragment becomes HTML.
    preview.innerHTML = raw || "Add a fragment to preview a note.";
  }
  window.addEventListener("hashchange", render);
  render();
</script>
</div></body></html>"""


def shell(title: str, body: str) -> object:
    return lab.page(title, f'<div class="hero"><div class="kicker">MIRROR // DOCS</div><h1>{title}</h1></div>{body}', nav='<a href="/">Preview</a><a href="/report">Bot preview</a><a href="/captured">Captured data</a>')


@app.get("/")
def index():
    return lab.app.response_class(INDEX, mimetype="text/html")


@app.route("/report", methods=["GET", "POST"])
def report():
    notice = ""
    if request.method == "POST":
        path = request.form.get("path", "/#Hello").strip()
        if not path.startswith("/") or "://" in path:
            notice = '<div class="flash err">Submit a local path beginning with `/`.</div>'
        else:
            result = lab.bot(path, cookies=[{"name": "review_session", "value": lab.flag("flag")}], wait=2.0)
            notice = f'<div class="flash {"ok" if result.get("ok") else "err"}">Bot visit: {result.get("ok") and "completed" or result.get("error", "failed")}</div>'
    return shell(
        "DOM review bot",
        f'''<div class="panel"><h2>Send a preview URL</h2>
        <p>The reviewer opens your fragment in a browser with a readable privileged cookie.</p>
        <form method="post"><label>Path and fragment</label><input name="path" value="/#Hello" size="80">
        <p><button type="submit">Send bot</button></p></form>{notice}
        <p class="note">A fragment payload can use an image error handler to avoid a closing script problem.</p></div>''',
    )


@app.route("/collect")
def collect():
    value = request.args.get("c", "") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
        if lab.flag("flag") in value:
            lab.objective_async("flag", "reviewer cookie exfiltrated through DOM XSS")
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(f"<li><code>{value}</code></li>" for value in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'
    return shell("Captured data", f'<div class="panel"><h2>Exfiltration collector</h2><ul class="list">{rows}</ul></div>')


if __name__ == "__main__":
    lab.run()
