from __future__ import annotations

import uuid
from pathlib import Path

from flask import redirect, request

from labkit import Lab

lab = Lab("AVATAR DOCK", accent="#d98cb3")
app = lab.app

UPLOADS = lab.state_dir / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
CAPTURED: list[str] = []


def shell(title: str, body: str) -> object:
    return lab.page(title, f'<div class="hero"><div class="kicker">AVATAR DOCK // PROFILE ASSETS</div><h1>{title}</h1></div>{body}', nav='<a href="/">Upload</a><a href="/report">Review bot</a><a href="/captured">Captured data</a>')


@app.get("/")
def index():
    avatars = sorted(UPLOADS.glob("*.svg"))
    rows = "".join(f'<li><a href="/avatar/{p.name}">{p.name}</a></li>' for p in avatars) or "<li>No avatars uploaded.</li>"
    return shell(
        "Avatar dock",
        f'''<div class="panel"><h2>Upload an avatar</h2>
        <form method="post" action="/upload" enctype="multipart/form-data">
          <label>SVG avatar</label><input type="file" name="avatar" accept="image/svg+xml,.svg">
          <p><button type="submit">Upload avatar</button></p></form>
        <p class="note">SVG is accepted for crisp profile art. Files are served with the original XML content type.</p></div>
        <div class="panel"><h2>Stored assets</h2><ul class="list">{rows}</ul></div>''',
    )


@app.post("/upload")
def upload():
    file = request.files.get("avatar")
    if not file or not file.filename:
        return shell("Upload failed", '<div class="flash err">Choose an SVG file.</div>')
    if not file.filename.lower().endswith(".svg"):
        return shell("Upload failed", '<div class="flash err">Only `.svg` avatars are accepted.</div>')
    name = f"{uuid.uuid4().hex[:12]}.svg"
    path = UPLOADS / name
    file.save(path)
    return redirect(f"/avatar/{name}")


@app.get("/avatar/<name>")
def avatar(name: str):
    path = (UPLOADS / Path(name).name).resolve()
    if not str(path).startswith(str(UPLOADS.resolve())) or not path.exists():
        return shell("Missing asset", '<div class="flash err">No such avatar.</div>', )
    content = path.read_text(errors="replace")
    response = lab.app.response_class(content, mimetype="image/svg+xml")
    response.headers["Content-Disposition"] = f'inline; filename="{path.name}"'
    return response


@app.route("/report", methods=["GET", "POST"])
def report():
    notice = ""
    if request.method == "POST":
        path = request.form.get("path", "/").strip()
        if not path.startswith("/") or "://" in path:
            notice = '<div class="flash err">Submit a local path beginning with `/`.</div>'
        else:
            result = lab.bot(path, cookies=[{"name": "admin_session", "value": lab.flag("flag")}], wait=2.0)
            notice = f'<div class="flash {"ok" if result.get("ok") else "err"}">Bot visit: {result.get("ok") and "completed" or result.get("error", "failed")}</div>'
    return shell(
        "Moderation bot",
        f'''<div class="panel"><h2>Manual asset review</h2>
        <p>The moderator opens uploaded assets directly in Chromium to verify they render correctly. The moderator has a readable session cookie.</p>
        <form method="post"><label>Asset path</label><input name="path" value="/avatar/" size="60">
        <p><button type="submit">Send moderator</button></p></form>{notice}</div>''',
    )


@app.get("/collect")
def collect():
    value = request.args.get("c", "") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
        if lab.flag("flag") in value:
            lab.objective_async("flag", "moderator cookie exfiltrated through SVG upload")
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(f"<li><code>{value}</code></li>" for value in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'
    return shell("Captured data", f'<div class="panel"><h2>Exfiltration collector</h2><ul class="list">{rows}</ul></div>')


if __name__ == "__main__":
    lab.run()
