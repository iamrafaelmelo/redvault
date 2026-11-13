from __future__ import annotations

import html
import subprocess
from pathlib import Path

from flask import request

from labkit import Lab

lab = Lab("PULSEGRID", accent="#7bd88f")
app = lab.app

FLAG_FILE = Path("/tmp/redvault-blind-cmdi-flag.txt")
FLAG_FILE.write_text(lab.flag("flag") + "\n")
CAPTURED: list[str] = []


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">PULSEGRID // RESOLVER OPERATIONS</div><h1>{title}</h1>'
        '<p>Queue a name-resolution check for the field network. Worker output is retained internally.</p></div>' + body,
        nav='<a href="/">Diagnostics</a><a href="/captured">Captured data</a><a href="/health">Health</a>',
    )


def queue_diagnostic() -> bool:
    host = request.form.get("host", "")
    if not host:
        data = request.get_json(silent=True) or {}
        host = str(data.get("host", ""))
    if not host:
        return False
    # VULNERABLE: the host field is interpolated into a shell command. Only the
    # queue acknowledgement is shown, so command output is blind to the caller.
    command = f"getent hosts {host} 2>&1 || true"
    try:
        subprocess.run(command, shell=True, capture_output=True, text=True, timeout=8)
    except subprocess.TimeoutExpired:
        pass
    return True


@app.route("/", methods=["GET", "POST"])
@app.route("/diagnostics", methods=["GET", "POST"])
def diagnostics():
    queued = False
    if request.method == "POST":
        queued = queue_diagnostic()
    notice = (
        '<div class="flash ok">Diagnostic queued. The resolver worker runs asynchronously; raw output is not returned.</div>'
        if queued
        else ""
    )
    return shell(
        "Resolver diagnostics",
        f"""
        <div class="panel">
          <h2>Queue a host check</h2>
          <p>The worker runs <code>getent hosts &lt;host&gt;</code> from the operations account. Results are written to the internal queue, not to this page.</p>
          <form method="post" action="/">
            <label>Host or address</label>
            <input name="host" value="127.0.0.1" placeholder="127.0.0.1">
            <p><button type="submit">Queue diagnostic</button></p>
          </form>
          {notice}
        </div>
        <div class="panel">
          <h2>Worker status</h2>
          <p class="mono dim">queue: diagnostic-worker-02 · mode: blind · retention: internal</p>
          <p class="note">The service account can read temporary diagnostic artifacts in <code>/tmp</code>.</p>
        </div>
        """,
    )


@app.get("/collect")
def collect():
    value = request.args.get("c", "") or request.get_data(as_text=True)
    flag = lab.flag("flag")
    # curl treats braces as URL globbing and strips them from a shell-expanded
    # flag, so restore the literal braces before recording the exfiltration.
    if value and value == flag.replace("{", "").replace("}", ""):
        value = flag
    if value:
        CAPTURED.append(value[:4000])
        if flag in value:
            lab.objective_async("flag", "blind command injection exfiltrated the flag file")
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(f"<li><code>{html.escape(value)}</code></li>" for value in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'
    return shell(
        "Captured data",
        f'<div class="panel"><h2>Collector inbox</h2><p>Data received by the out-of-band collector.</p><ul class="list">{rows}</ul></div>',
    )


if __name__ == "__main__":
    lab.run()
