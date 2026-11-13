from __future__ import annotations

import html
import mimetypes
import secrets
import time
from pathlib import Path

from flask import Response, request

from labkit import Lab

lab = Lab("ORBITPROFILE", accent="#f2a65a")
app = lab.app

MEDIA = lab.state_dir / "media"
MEDIA.mkdir(parents=True, exist_ok=True)
PROFILES: dict[str, dict[str, str]] = {}
SESSION_TOKENS: set[str] = set()
CAPTURED: list[str] = []

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/gif", "image/svg+xml"}
ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg"}

REAL_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000d49444154789c6360000000020001e221bc330000000049454e44ae426082"
)


def shell(title: str, body: str, status: int = 200) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">ORBITPROFILE // PUBLIC PROFILE</div><h1>{title}</h1>'
        "<p>Share who you are with the community: a headline, a bio and one avatar. Uploads are"
        " validated before they reach the public media bucket.</p></div>" + body,
        nav='<a href="/">My profile</a><a href="/media/readme.txt">Media bucket</a>',
        status=status,
    )


def ensure_profile(name: str) -> dict[str, str]:
    profile = PROFILES.setdefault(
        name,
        {
            "headline": "Explorer",
            "bio": "Hello from OrbitProfile.",
            "avatar": "",
        },
    )
    return profile


def issue_session() -> str:
    token = secrets.token_urlsafe(18)
    SESSION_TOKENS.add(token)
    return token


@app.route("/", methods=["GET", "POST"])
@app.route("/profile", methods=["GET", "POST"])
def profile():
    notice = ""
    profile_data = ensure_profile("guest")
    if request.method == "POST":
        if "avatar" in request.files:
            upload = request.files["avatar"]
            if not upload or not upload.filename:
                notice = '<div class="flash err">Choose an avatar file.</div>'
            else:
                content_type = (upload.mimetype or "").lower()
                suffix = Path(upload.filename).suffix.lower()
                # VULNERABLE: Content-Type OR extension is enough. The client supplied
                # values are never reconciled with each other or with the bytes.
                if content_type not in ALLOWED_TYPES and suffix not in ALLOWED_EXTS:
                    notice = (
                        '<div class="flash err">Avatar rejected: send an image Content-Type '
                        f'(<code>{html.escape(content_type)}</code>) or an image extension '
                        f'(<code>{html.escape(suffix)}</code>).</div>'
                    )
                else:
                    raw = upload.read()
                    # VULNERABLE: the suffix is honoured as the stored type. When the
                    # markup is really HTML the bucket keeps a stylesheet name, so the
                    # resource loads as CSS even in browsers that enforce nosniff.
                    stored_suffix = ".css" if raw.lstrip()[:1] == b"<" else suffix
                    name = f"{secrets.token_hex(8)}{stored_suffix}"
                    (MEDIA / name).write_bytes(raw)
                    profile_data["avatar"] = name
                    notice = (
                        f'<div class="flash ok">Avatar stored as <a href="/media/{html.escape(name)}">/media/{html.escape(name)}</a>.</div>'
                    )
        else:
            profile_data["headline"] = request.form.get("headline", "Explorer")[:80]
            profile_data["bio"] = request.form.get("bio", "")[:400]
            notice = '<div class="flash ok">Profile updated.</div>'
    avatar_html = ""
    if profile_data["avatar"]:
        avatar_html = f'<img class="avatar" src="/media/{html.escape(profile_data["avatar"])}" alt="avatar" width="240">'
    return shell(
        "Public profile",
        f"""<div class="panel"><h2>Identity</h2>
        <h3>{html.escape(profile_data["headline"])}</h3>
        <p>{html.escape(profile_data["bio"])}</p>{avatar_html}</div>
        <div class="panel"><h2>Edit profile</h2>
        <form method="post" enctype="multipart/form-data">
          <label>Headline</label><input name="headline" maxlength="80" placeholder="Explorer">
          <label>Bio</label><textarea name="bio" rows="3"></textarea>
          <label>Avatar (PNG, JPEG, GIF or SVG)</label><input type="file" name="avatar" accept="image/*">
          <p><button type="submit">Save profile</button></p>
        </form>{notice}
        <p class="note">Limits: 2 MB, max dimensions 4096x4096, MIME must start with <code>image/</code>.</p></div>""",
    )


@app.get("/media/readme.txt")
def media_readme():
    return Response(
        "OrbitProfile media bucket\nFiles are served straight from the bucket with the type\n"
        "the bucket records at upload time.\n",
        mimetype="text/plain",
    )


@app.post("/login")
def login():
    response = shell("Signed in", '<div class="flash ok">Session issued.</div>')
    response.set_cookie("orbit_sid", issue_session(), httponly=False, samesite="Lax")
    return response


@app.get("/session")
def session_info():
    # JSON session endpoint. Same-origin script only: browsers send Sec-Fetch-Site
    # from the page itself and cross-site requests are refused.
    site = request.headers.get("Sec-Fetch-Site", "same-origin")
    token = request.cookies.get("orbit_sid", "")
    if site not in {"same-origin", "none"}:
        return Response('{"error":"cross-origin session read blocked"}', status=403, mimetype="application/json")
    if token not in SESSION_TOKENS:
        token = issue_session()
        body = Response(
            '{"user":"mvance","role":"member","flag":"%s"}' % lab.flag("flag"),
            mimetype="application/json",
        )
        body.set_cookie("orbit_sid", token, httponly=False, samesite="Lax")
        return body
    return Response(
        '{"user":"mvance","role":"member","flag":"%s"}' % lab.flag("flag"),
        mimetype="application/json",
    )


@app.route("/collect", methods=["GET", "POST"])
def collect():
    # Values arrive as the `c` query parameter so collectors can send any text;
    # raw request bodies are accepted too for scripted clients.
    value = request.args.get("c", "") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
        if lab.flag("flag") in value:
            lab.objective_async("flag", "uploaded HTML/SVG avatar was served inline as text/html and read /session")
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(
        f'<li><code>{html.escape(value)}</code></li>'
        f'<li class="dim">raw: <code>{html.escape(value.encode("unicode_escape").decode())}</code></li>'
        for value in CAPTURED
    ) or '<li class="dim">Nothing captured yet.</li>'
    return shell("Captured data", f'<div class="panel"><h2>Collector</h2><ul class="list">{rows}</ul></div>')


@app.get("/media/<path:name>")
def media(name: str):
    target = (MEDIA / name)
    try:
        raw = target.read_bytes()
    except OSError:
        return Response("Not found", status=404, mimetype="text/plain")
    # VULNERABLE: the bucket derives the response type from the stored file name
    # instead of re-sniffing the bytes, so a ".css" file full of HTML is served
    # as text/html, and any stored image extension is guessed from the suffix only.
    # The owner enabled MIME sniffing while debugging a preview feature.
    guessed, _ = mimetypes.guess_type(str(target))
    guessed = guessed or "application/octet-stream"
    if guessed == "image/svg+xml" or guessed.startswith("text/"):
        guessed = "text/html"
    return Response(
        raw,
        mimetype=guessed,
        headers={
            "X-Content-Type-Options": "sniff-off-disabled",
            "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'",
            "Cache-Control": "no-store",
        },
    )


if __name__ == "__main__":
    lab.run()