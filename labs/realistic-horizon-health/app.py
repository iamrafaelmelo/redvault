from __future__ import annotations

import subprocess
from pathlib import Path

from flask import jsonify, redirect, request, session

from labkit import Lab

lab = Lab("HORIZON HEALTH", accent="#3aa6a0")
app = lab.app

Path("/tmp/horizon-root.txt").write_text(lab.flag("root") + "\n")
SUPPORT_KEY = "horizon-support-7d2f"
PATIENTS = {
    1: {"name": "Camila Ortega", "unit": "Cardiology", "note": "Routine follow-up scheduled."},
    2: {"name": "Daniel Brooks", "unit": "Radiology", "note": "Imaging review complete."},
    3: {"name": "Alicia Morgan", "unit": "Executive Health", "note": "Restricted chart.", "flag": True},
}


def shell(title: str, body: str) -> object:
    nav = '<a href="/portal">Portal</a><a href="/logout">Logout</a>' if session.get("support") else '<a href="/">Home</a><a href="/support">Support</a>'
    return lab.page(title, f'<div class="hero"><div class="kicker">HORIZON // HEALTH OPERATIONS</div><h1>{title}</h1></div>{body}', nav=nav)


@app.get("/")
def index():
    return shell(
        "Horizon Health",
        """<div class="panel"><h2>Care operations platform</h2><p>Patient flow, imaging and support integrations for regional clinics.</p>
        <p class="note">The public site links only the marketing pages. Support deployments are handled by a separate gateway.</p></div>""",
    )


@app.get("/robots.txt")
def robots():
    return lab.app.response_class("User-agent: *\nDisallow: /support/backup/\nDisallow: /portal/admin/\n", mimetype="text/plain")


@app.get("/support")
def support():
    return shell(
        "Support integration",
        f'''<div class="panel"><h2>Internal support session</h2>
        <p>The support gateway accepts a deployment API key from the backup bundle and issues a short-lived local session.</p>
        <pre>GET /api/internal/support/session
Header: X-Support-Key: &lt;deployment key&gt;</pre>
        <p class="note">Backup bundle path: `/support/backup/deploy.json`.</p></div>''',
    )


@app.get("/support/backup/deploy.json")
def deploy():
    return jsonify(
        {
            "service": "horizon-support",
            "environment": "regional-prod",
            "support_api_key": SUPPORT_KEY,
            "warning": "Deployment bundle retained for rollback. Restrict access before publishing.",
        }
    )


@app.get("/api/internal/support/session")
def support_session():
    key = request.headers.get("X-Support-Key", "")
    if key != SUPPORT_KEY:
        return jsonify({"error": "invalid deployment key"}), 401
    session["support"] = True
    session["operator"] = "regional-support"
    return jsonify(
        {
            "ok": True,
            "operator": "regional-support",
            "api_flag": lab.flag("api"),
            "scope": "patient-records:read, admin-tools:legacy",
            "warning": "This integration was not intended to issue browser sessions.",
        }
    )


@app.get("/portal")
def portal():
    if not session.get("support"):
        return shell("Portal locked", '<div class="flash err">Support session required.</div>')
    links = "".join(f'<li><a href="/portal/patients/{pid}">Patient {pid}</a> · {data["name"]}</li>' for pid, data in PATIENTS.items())
    return shell(
        "Regional support portal",
        f'''<div class="panel"><h2>Patient directory</h2><ul class="list">{links}</ul>
        <p>The portal shows the patient IDs assigned to your regional queue. The record route does not re-check the queue.</p></div>
        <div class="panel"><h2>Administrative tools</h2><p><a href="/portal/admin/tools">Open legacy network tools</a> · The support scope includes legacy admin tools.</p></div>''',
    )


@app.get("/portal/patients/<int:pid>")
def patient(pid: int):
    if not session.get("support"):
        return shell("Access denied", '<div class="flash err">Support session required.</div>')
    data = PATIENTS.get(pid)
    if not data:
        return shell("Patient missing", '<div class="flash err">No such patient.</div>')
    flag = f'<div class="panel"><h2>Restricted chart</h2><pre>{lab.flag("user")}</pre></div>' if data.get("flag") else ""
    return shell(
        f'Patient · {data["name"]}',
        f'<div class="panel"><h2>{data["name"]}</h2><p>Unit: {data["unit"]}</p><p>{data["note"]}</p></div>{flag}',
    )


@app.route("/portal/admin/tools", methods=["GET", "POST"])
def admin_tools():
    if not session.get("support"):
        return shell("Access denied", '<div class="flash err">Support session required.</div>')
    # BFLA: support scope claims admin tools, but there is no separate role check.
    output = ""
    if request.method == "POST":
        host = request.form.get("host", "127.0.0.1")
        # VULNERABLE: legacy tool shell interpolation.
        command = f"getent hosts {host} 2>&1 || true"
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=8)
            output = (result.stdout or "") + (result.stderr or "")
        except subprocess.TimeoutExpired:
            output = "tool timed out"
        if lab.flag("root") in output:
            lab.objective_async("root", "legacy admin tool executed a shell command and exposed the root flag")
    return shell(
        "Legacy network tools",
        f'''<div class="panel"><h2>Diagnostic lookup</h2>
        <form method="post"><label>Host</label><input name="host" value="127.0.0.1">
        <p><button type="submit">Run lookup</button></p></form>
        <p class="note">The tool runs as the support service account. Private runtime files are mounted for legacy compatibility.</p></div>
        {f'<div class="panel"><h2>Output</h2><pre>{output}</pre></div>' if output else ''}''',
    )


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    lab.run()
