from __future__ import annotations

import io
import shutil
import uuid
import zipfile
from pathlib import Path

from flask import redirect, render_template_string, request

from labkit import Lab

lab = Lab("THEMEFORGE", accent="#9b7ede")
app = lab.app

THEMES = lab.state_dir / "themes"
TEMPLATES = lab.state_dir / "templates"
THEMES.mkdir(parents=True, exist_ok=True)
TEMPLATES.mkdir(parents=True, exist_ok=True)
REPORT_TEMPLATE = TEMPLATES / "report.html"
REPORT_TEMPLATE.write_text("<section><h2>Theme report</h2><p>Prepared for {{ user }}.</p></section>\n")


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">THEMEFORGE // PACKAGE STUDIO</div><h1>{title}</h1>'
        "<p>Upload and inspect portable theme packages for the field console.</p></div>" + body,
        nav='<a href="/">Studio</a><a href="/report">Report</a>',
    )


@app.get("/")
def index():
    packs = sorted(path.name for path in THEMES.iterdir() if path.is_dir())
    rows = "".join(f"<li><code>{name}</code></li>" for name in packs) or '<li class="dim">No packages uploaded.</li>'
    return shell(
        "Theme packages",
        f"""<div class="panel"><h2>Upload a package</h2>
        <form method="post" action="/upload" enctype="multipart/form-data">
          <label>ZIP package</label><input type="file" name="package" accept=".zip,application/zip">
          <p><button type="submit">Extract package</button></p></form>
        <p class="note">Packages are extracted into a per-upload workspace. The report template is loaded from the service template store.</p></div>
        <div class="panel"><h2>Extracted packages</h2><ul class="list">{rows}</ul></div>""",
    )


@app.post("/upload")
def upload():
    package = request.files.get("package")
    if not package or not package.filename:
        return shell("Upload failed", '<div class="flash err">Choose a ZIP package.</div>')
    try:
        archive = zipfile.ZipFile(io.BytesIO(package.read()))
    except zipfile.BadZipFile:
        return shell("Upload failed", '<div class="flash err">The package is not a valid ZIP archive.</div>')
    token = uuid.uuid4().hex[:12]
    destination = THEMES / token
    destination.mkdir(parents=True, exist_ok=True)
    written = []
    for info in archive.infolist():
        if info.is_dir():
            continue
        # VULNERABLE: archive names are joined without normalization or containment checks.
        target = destination / info.filename
        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as source, open(target, "wb") as output:
            shutil.copyfileobj(source, output)
        written.append(info.filename)
    return shell(
        "Package extracted",
        f'<div class="flash ok">Extracted {len(written)} file(s) into package <code>{token}</code>.</div>'
        f'<div class="panel"><h2>Entries</h2><ul class="list">{"".join(f"<li><code>{name}</code></li>" for name in written)}</ul></div>',
    )


@app.get("/report")
def report():
    try:
        source = REPORT_TEMPLATE.read_text()
        rendered = render_template_string(source, user="operator", flag=lab.flag("flag"))
    except Exception as exc:  # noqa: BLE001 - surfaced as a report error
        rendered = f'<div class="flash err">Report error: {exc}</div>'
    if lab.flag("flag") in rendered:
        lab.objective_async("flag", "zip-slip overwrote the report template and rendered the flag")
    return shell("Theme report", f'<div class="panel">{rendered}</div>')


if __name__ == "__main__":
    lab.run()
