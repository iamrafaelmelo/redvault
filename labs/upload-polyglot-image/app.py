from __future__ import annotations

import html
import json
import secrets
from pathlib import Path

from flask import Response, request

from labkit import Lab

lab = Lab("TRAILMARK", accent="#5ec8a6")
app = lab.app

GALLERY = lab.state_dir / "gallery"
GALLERY.mkdir(parents=True, exist_ok=True)
CAPTURED: list[str] = []
PHOTOS: list[dict[str, str]] = []

MAGIC = {
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/jpeg": b"\xff\xd8\xff",
    "image/gif": b"GIF89a",
}


def sniff(raw: bytes) -> str | None:
    for declared, signature in MAGIC.items():
        if raw.startswith(signature):
            return declared
    if raw.startswith(b"GIF87a"):
        return "image/gif"
    return None


def shell(title: str, body: str, status: int = 200) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">TRAILMARK // PHOTO GALLERY</div><h1>{title}</h1>'
        "<p>TrailMarker field logs share a photo per checkpoint. The gallery validates every"
        " upload by reading its file signature before it accepts it.</p></div>" + body,
        nav='<a href="/">Gallery</a><a href="/session">Session</a>',
        status=status,
    )


@app.route("/", methods=["GET", "POST"])
def index():
    notice = ""
    if request.method == "POST":
        upload = request.files.get("photo")
        if not upload or not upload.filename:
            notice = '<div class="flash err">Attach a photo to upload.</div>'
        else:
            raw = upload.read()
            if len(raw) > 2_000_000:
                notice = '<div class="flash err">Photos must be under 2 MB.</div>'
            else:
                # VULNERABLE: only the first bytes are inspected. Everything after the
                # magic number is stored and later served from this origin.
                detected = sniff(raw)
                if not detected:
                    notice = '<div class="flash err">Signature check failed: PNG, JPEG or GIF required.</div>'
                else:
                    name = f"{secrets.token_hex(8)}.{detected.split('/')[1]}"
                    (GALLERY / name).write_bytes(raw)
                    PHOTOS.append({"name": name, "declared": detected, "original": upload.filename[:80]})
                    notice = f'<div class="flash ok">Photo accepted ({detected}) as <a href="/gallery/{html.escape(name)}">{html.escape(name)}</a>.</div>'
    cards = "".join(
        f'<div class="panel"><h3>{html.escape(photo["original"])}</h3>'
        f'<a href="/gallery/{html.escape(photo["name"])}">{html.escape(photo["name"])}</a>'
        f'<p class="dim">{html.escape(photo["declared"])}</p></div>'
        for photo in reversed(PHOTOS)
    ) or '<div class="panel dim">No checkpoints shared yet.</div>'
    return shell(
        "Trail checkpoints",
        f"""<div class="panel"><h2>Share a checkpoint</h2>
        <form method="post" enctype="multipart/form-data">
          <label>Photo</label><input type="file" name="photo" accept="image/png,image/jpeg,image/gif">
          <p><button type="submit">Validate and publish</button></p></form>{notice}
        <p class="note">The validator reads the first bytes of the file and labels the upload. Files
        are served back from this origin so the gallery can render them directly.</p></div>
        <div class="grid3">{cards}</div>""",
    )


@app.get("/session")
def session_endpoint():
    # JSON session endpoint, readable by the gallery page only: browser-initiated
    # cross-site reads are refused so third-party pages cannot read it.
    site = request.headers.get("Sec-Fetch-Site", "same-origin")
    if site not in {"same-origin", "none"}:
        return Response('{"error":"cross-origin session read blocked"}', status=403, mimetype="application/json")
    payload = {
        "user": "kestrel",
        "role": "curator",
        "flag": lab.flag("flag"),
    }
    response = Response(json.dumps(payload), mimetype="application/json")
    response.set_cookie("trail_session", "curator-kestrel", httponly=False, samesite="Lax")
    return response


@app.route("/collect", methods=["GET", "POST"])
def collect():
    value = request.args.get("c", "") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
        if lab.flag("flag") in value:
            lab.objective_async("flag", "polyglot image passed the signature check and ran same-origin script")
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(f"<li><code>{html.escape(value)}</code></li>" for value in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'
    return shell("Captured data", f'<div class="panel"><h2>Collector</h2><ul class="list">{rows}</ul></div>')


@app.get("/gallery/<path:name>")
def gallery_file(name: str):
    target = (GALLERY / name).resolve()
    if GALLERY.resolve() not in target.parents or not target.is_file():
        return Response("Not found", status=404, mimetype="text/plain")
    suffix = target.suffix.lower()
    # VULNERABLE: the response type comes from the name picked at upload time from
    # the sniffed header, but the bytes are whatever followed that header. A GIF
    # polyglot is therefore served as a GIF document and browsers render the HTML
    # tail of the file as markup.
    mimetype = {
        ".gif": "text/html",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
    }.get(suffix, "application/octet-stream")
    return Response(
        target.read_bytes(),
        mimetype=mimetype,
        headers={
            "X-Content-Type-Options": "sniffing-disabled-by-cdn-normalisation",
            "Content-Disposition": "inline",
            "Cache-Control": "no-store",
        },
    )


if __name__ == "__main__":
    lab.run()