from __future__ import annotations

import html
import io
import tarfile
import uuid
from pathlib import Path

from flask import Response, request

from labkit import Lab

lab = Lab("FIELDLENS", accent="#7fb069")
app = lab.app

WORKSPACE = lab.state_dir / "imports"
TEMPLATE_DIR = lab.state_dir / "templates"
ASSET_DIR = lab.state_dir / "assets"
SEEN: set[str] = set()

WELCOME = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>FieldLens import report</title></head>
<body>
<h1>FieldLens import report</h1>
<p>Bundle <code>{bundle}</code> was unpacked by the import worker.</p>
<p>Entries: {entries}</p>
</body></html>
"""


def seed() -> None:
    # The import worker renders its report from the shared template store and
    # serves its stylesheet from the static root. Both live next to the
    # per-bundle workspaces and are writable by the worker.
    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    WORKSPACE.mkdir(parents=True, exist_ok=True)
    (TEMPLATE_DIR / "import-report.html").write_text(WELCOME.format(bundle="none", entries=0))
    (ASSET_DIR / "import.css").write_text("body{font-family:sans-serif;margin:2rem}\n")


seed()


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">FIELDLENS // BUNDLE IMPORT</div><h1>{title}</h1>'
        "<p>Field photography teams ship documentation bundles between surveys. The import worker"
        " unpacks each bundle into a private workspace before the editors review it.</p></div>" + body,
        nav='<a href="/">Imports</a><a href="/report">Report</a><a href="/assets/import.css">Stylesheet</a>',
    )


@app.get("/")
def index():
    bundles = sorted(path.name for path in WORKSPACE.iterdir() if path.is_dir())
    rows = "".join(f"<li><code>{name}</code> <span class=\"dim\">· workspace</span></li>" for name in bundles) or '<li class="dim">No bundles imported yet.</li>'
    return shell(
        "Bundle imports",
        f"""<div class="panel"><h2>Import a bundle</h2>
        <form method="post" action="/import" enctype="multipart/form-data">
          <label>Bundle archive</label><input type="file" name="bundle" accept=".tar,.tar.gz,application/x-tar">
          <p><button type="submit">Unpack bundle</button></p></form>
        <p class="note">Archives are accepted as tar (optionally gzip compressed) and unpacked with
        the standard library. Review the report afterwards.</p></div>
        <div class="panel"><h2>Workspaces</h2><ul class="list">{rows}</ul></div>""",
    )


@app.post("/import")
@app.post("/upload")
def import_bundle():
    upload = request.files.get("bundle") or request.files.get("file")
    if not upload or not upload.filename:
        return shell("Import failed", '<div class="flash err">Choose a tar bundle to import.</div>')
    raw = upload.read()
    bundle = uuid.uuid4().hex[:12]
    destination = WORKSPACE / bundle
    destination.mkdir(parents=True, exist_ok=True)
    try:
        archive = tarfile.open(fileobj=io.BytesIO(raw), mode="r:*")
    except tarfile.TarError:
        return shell("Import failed", '<div class="flash err">The bundle is not a readable tar archive.</div>')
    written: list[str] = []
    try:
        for member in archive.getmembers():
            if not member.isfile():
                continue
            # VULNERABLE: member names are pushed straight into open(). A tar
            # entry may carry "../" segments or an absolute path, so the worker
            # writes anywhere the service account can reach.
            target = destination / member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                continue
            with source, open(target, "wb") as output:
                output.write(source.read())
            written.append(member.name)
    finally:
        archive.close()
    entries = "".join(f"<li><code>{html.escape(name)}</code></li>" for name in written) or '<li class="dim">Empty bundle.</li>'
    return shell(
        "Bundle unpacked",
        f'<div class="flash ok">Unpacked {len(written)} file(s) into workspace <code>{bundle}</code>.</div>'
        f'<div class="panel"><h2>Entries</h2><ul class="list">{entries}</ul></div>'
        '<p class="note">The review report is generated from the shared template store at '
        '<a href="/report">/report</a>.</p>',
    )


@app.get("/report")
def report():
    template_path = TEMPLATE_DIR / "import-report.html"
    try:
        source = template_path.read_text()
    except OSError:
        return shell("Report", '<div class="flash err">Template store is empty.</div>')
    # The template is rendered with the report context. Anything that reaches
    # the output is shown verbatim because the worker trusts its own store.
    content = (
        source.replace("{bundle}", "review-01")
        .replace("{entries}", "3")
        .replace("{{ flag }}", lab.flag("flag"))
    )
    if lab.flag("flag") in content:
        lab.objective_async("flag", "tar import escaped its workspace and rewrote the report template")
    return lab.page("Import report", content)


@app.get("/assets/<path:name>")
def static_file(name: str):
    target = (ASSET_DIR / name).resolve()
    if not target.is_file():
        return Response("Not found", status=404, mimetype="text/plain")
    suffix = target.suffix.lower()
    mimetype = {".css": "text/css", ".js": "application/javascript", ".html": "text/html"}.get(suffix, "application/octet-stream")
    return Response(target.read_bytes(), mimetype=mimetype)


if __name__ == "__main__":
    lab.run()