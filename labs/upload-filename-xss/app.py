from __future__ import annotations

import uuid
from pathlib import Path
from urllib.parse import quote

from flask import request

from labkit import Lab

lab = Lab("DROPZONE", accent="#f6a05b")
app = lab.app

UPLOADS = lab.state_dir / "uploads"
UPLOADS.mkdir(parents=True, exist_ok=True)
CAPTURED: list[str] = []
SPAWN_PX = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000000020001e221bc330000000049454e44ae426082"
)


from markupsafe import Markup


def shell(title: str, body: str, nav: str | None = None) -> object:
    if nav is None:
        nav = '<a href="/">Gallery</a><a href="/report">Review bot</a><a href="/captured">Captured data</a>'
    return lab.page(title, f'<div class="hero"><div class="kicker">DROPZONE // ASSET DOCK</div><h1>{title}</h1></div>{body}', nav=nav)


@app.get("/")
def index():
    stored = sorted(path.name for path in UPLOADS.iterdir() if path.is_file())
    return shell(
        "Asset gallery",
        f"""<div class="panel"><h2>Upload an asset</h2>
        <form method="post" action="/upload" enctype="multipart/form-data">
        <label>Image</label><input type="file" name="file" accept="image/*">
        <p><button type="submit">Upload</button></p></form>
        <p class="note">Original filenames are preserved for the field team. Raw image bytes or stored SVG assets are accepted. The reviewer bot opens this gallery with a readable session cookie.</p></div>
        <div class="panel"><h2>Gallery</h2><ul class="list">{Markup(gallery_rows(stored))}</ul></div>""",
    )


def gallery_rows(stored: list[str]) -> str:
    """Asset listing: names are rendered verbatim for the field team."""
    if not stored:
        return '<li class="dim">No assets yet.</li>'
    return "".join(f'<li><code>{name}</code> · <a href="/file/{quote(name)}">open</a></li>' for name in stored)


@app.post("/upload")
def upload():
    file = request.files.get("file")
    if not file or not file.filename:
        return shell("Upload failed", '<div class="flash err">Choose a file.</div>')
    data = file.read()
    probe = data[:16].lstrip()
    if probe.startswith(b"<"):
        body = data.decode("utf-8", "replace")
        if "</" not in body.replace(">", "> "):
            return shell("Upload failed", '<div class="flash err">Only image bytes are accepted.</div>')
    elif not data.startswith(b"\x89PNG\r\n\x1a\n") and not data.startswith(b"\xff\xd8"):
        return shell("Upload failed", '<div class="flash err">Only image bytes are accepted.</div>')
    suffix = ".png" if data.startswith(b"\x89PNG") else ".jpg"
    # VULNERABLE: the original filename is persisted and later rendered as HTML.
    # Current Werkzeug strips surrounding whitespace from display names, which
    # would hide the bug, so the multipart header is read in the same way the
    # legacy uploader did: raw bytes, only directory separators normalized.
    # Current Werkzeug strips leading whitespace from display names, which would
    # hide the bug; the original multipart name is sent by the edge proxy in a
    # request header so the legacy behavior is preserved.
    original = request.headers.get("X-Original-Filename", "").encode("latin-1", "ignore").decode("utf-8", "ignore")
    raw_name = original or f" {file.filename}"
    name = raw_name.replace("\\", "/").split("/")[-1][:200]
    if not name.lower().endswith((".png", ".jpg", ".jpeg")):
        name = f"{name}{suffix}"
    (UPLOADS / name).write_bytes(data)
    return lab.redirect("/")


@app.get("/file/<path:name>")
def file_view(name: str):
    path = (UPLOADS / Path(name).name).resolve()
    if not str(path).startswith(str(UPLOADS.resolve())) or not path.exists():
        return shell("Missing file", '<div class="flash err">No such asset.</div>')
    response = lab.app.response_class(path.read_bytes(), mimetype="image/png" if path.suffix == ".png" else "image/jpeg")
    response.headers["Content-Disposition"] = f'attachment; filename="{uuid.uuid4().hex}{path.suffix}"'
    return response


@app.route("/report", methods=["GET", "POST"])
def report():
    notice = ""
    if request.method == "POST":
        result = lab.bot("/", cookies=[{"name": "reviewer_session", "value": lab.flag("flag")}], wait=2.0)
        notice = f'<div class="flash {"ok" if result.get("ok") else "err"}">Bot visit: {result.get("ok") and "completed" or result.get("error", "failed")}</div>'
    return shell(
        "Review bot",
        f"""<div class="panel"><h2>Review the gallery</h2>
        <p>The reviewer opens the gallery with a readable <code>reviewer_session</code> cookie.</p>
        <form method="post"><button type="submit">Send review bot</button></form>{notice}</div>""",
    )


@app.route("/collect", methods=["GET", "POST"])
def collect():
    value = request.args.get("c", "") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
        if lab.flag("flag") in value:
            lab.objective_async("flag", "reviewer cookie exfiltrated through filename XSS")
    return ("", 204)


def CAPTURED_ROWS() -> str:
    return "".join(f'<li><code>{value}</code></li>' for value in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'


@app.get("/captured")
def captured():
    rows = CAPTURED_ROWS()
    return shell("Captured data", f'<div class="panel"><h2>Exfiltration collector</h2><ul class="list">{rows}</ul></div>')


if __name__ == "__main__":
    lab.run()