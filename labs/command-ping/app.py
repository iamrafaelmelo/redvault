from __future__ import annotations

import subprocess
from pathlib import Path

from flask import request

from labkit import Lab

lab = Lab("NETPULSE", accent="#52b788")
app = lab.app

Path("/tmp/redvault-command-flag.txt").write_text(lab.flag("flag") + "\n")


def shell(title: str, body: str) -> object:
    return lab.page(title, f'<div class="hero"><div class="kicker">NETPULSE // CONNECTIVITY</div><h1>{title}</h1></div>{body}', nav='<a href="/">Probe</a>')


@app.route("/", methods=["GET", "POST"])
def index():
    output = ""
    host = request.form.get("host", "") if request.method == "POST" else ""
    if request.method == "POST":
        # VULNERABLE: shell metacharacters in host are passed to /bin/sh.
        command = f"getent hosts {host} 2>&1 || true"
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=8)
            output = (result.stdout or "") + (result.stderr or "")
        except subprocess.TimeoutExpired:
            output = "probe timed out"
        if lab.flag("flag") in output:
            lab.objective_async("flag", "command injection read the service flag file")
    return shell(
        "Connectivity probe",
        f"""<div class="panel"><h2>Resolve a host</h2><p>Runs a local name-resolution check from the service host.</p>
        <form method="post"><label>Hostname or address</label><input name="host" value="{host}" placeholder="127.0.0.1">
        <p><button type="submit">Run probe</button></p></form>
        <p class="note">The probe is a shell pipeline. The service account can read a private temporary file.</p></div>
        {f'<div class="panel"><h2>Probe output</h2><pre>{output}</pre></div>' if output else ''}""",
    )


if __name__ == "__main__":
    lab.run()
