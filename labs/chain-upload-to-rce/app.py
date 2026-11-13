from __future__ import annotations

import uuid
from pathlib import Path

from flask import redirect, render_template_string, request

from labkit import Lab

lab = Lab("MERIDIAN CMS", accent="#f08a4b")
app = lab.app

FLAG_FILE = Path("/tmp/redvault-three-doors.txt")
FLAG_FILE.write_text(lab.flag("flag") + "\n")

PLUGINS = lab.state_dir / "plugins"
STATIC = lab.state_dir / "static"
PLUGINS.mkdir(parents=True, exist_ok=True)
STATIC.mkdir(parents=True, exist_ok=True)
(STATIC / "index.html").write_text("<html><body><h1>Meridian static site</h1><p>No build yet.</p></body></html>\n")


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">MERIDIAN // STATIC SITE CMS</div><h1>{title}</h1></div>{body}',
        nav='<a href="/">Site</a><a href="/editor">Editor</a><a href="/static/index.html">Build output</a>',
    )


@app.get("/")
def index():
    return shell(
        "Meridian",
        """<div class="panel"><h2>Static site CMS</h2>
        <p>Editors upload plugin fragments, preview a template and publish the static build.</p>
        <p class="note">The editor console is reachable from the internal network only in production.</p></div>""",
    )


@app.get("/editor")
def editor():
    # VULNERABLE: no role check on the editor surface.
    files = sorted(path.name for path in PLUGINS.iterdir())
    listing = "".join(f"<li>{name}</li>" for name in files) or '<li class="dim">No plugins uploaded.</li>'
    return shell(
        "Editor console",
        f"""<div class="panel"><h2>Upload a plugin fragment</h2>
        <form method="post" action="/editor/upload" enctype="multipart/form-data">
          <label>Plugin file</label><input type="file" name="file">
          <p><button type="submit">Upload plugin</button></p></form>
        <p class="note">Accepted: any text fragment. The filename is preserved for the include path.</p></div>
        <div class="panel"><h2>Plugin directory</h2><ul class="list">{listing}</ul></div>
        <div class="panel"><h2>Publish</h2>
        <p>POST <code>/publish</code> with a `template` field. The publishing worker compiles it and writes <code>/static/index.html</code>.</p></div>""",
    )


@app.post("/editor")
@app.post("/editor/upload")
@app.post("/upload")
def upload():
    file = request.files.get("file")
    if not file or not file.filename:
        return shell("Upload failed", '<div class="flash err">Choose a plugin file.</div>')
    name = file.filename.replace("\\", "/").split("/")[-1] or f"{uuid.uuid4().hex}.txt"
    (PLUGINS / name).write_text(file.read().decode("utf-8", "replace"))
    return redirect("/editor")


@app.post("/publish")
def publish():
    template = request.form.get("template", "") or request.form.get("body", "")
    if not template:
        return shell("Publish", '<div class="flash err">A template is required.</div>')
    try:
        # VULNERABLE: the publishing worker compiles the submitted template.
        rendered = render_template_string(template)
    except Exception:  # noqa: BLE001 - surfaced as a generic build error
        return shell("Publish failed", '<div class="flash err">Build error: template could not be rendered.</div>')
    page = f"<html><body><!-- meridian build -->\n{rendered}\n</body></html>\n"
    (STATIC / "index.html").write_text(page)
    if lab.flag("flag") in rendered:
        lab.objective_async("flag", "publishing worker rendered a template that read the root flag")
    return shell(
        "Publish complete",
        f'<div class="flash ok">Build written to <a href="/static/index.html">/static/index.html</a>.</div>',
    )


@app.get("/static/index.html")
def static_index():
    return lab.app.response_class((STATIC / "index.html").read_text(), mimetype="text/html")


if __name__ == "__main__":
    lab.run()