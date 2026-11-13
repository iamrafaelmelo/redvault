from __future__ import annotations

import os
from pathlib import Path

from flask import request

from labkit import Lab

lab = Lab("PRISM ARCHIVE", accent="#e02338")
app = lab.app

BASE = Path(__file__).resolve().parent
BACKUPS = BASE / "backups"


def shell(body: str, title: str = "PRISM ARCHIVE") -> str:
    return f"""
    <div class="hero"><div class="kicker">PRISM//PUBLIC ARCHIVE</div><h1>{title}</h1>
    <p>Independent research notes, archived copies and operational ephemera.</p></div>
    {body}
    <p class="dim mono" style="margin-top:26px">archive node 7 · static mirror · last sync 2026-10-31</p>
    """


@app.get("/")
def index():
    return lab.page(
        "Prism Archive",
        shell("""
        <div class="grid">
          <div class="panel"><h2>Field notes</h2><p>Retired infrastructure, migration notes and the occasional unredacted credential.</p>
          <a class="btn-ghost btn" href="/notes">Browse notes</a></div>
          <div class="panel"><h2>Operations</h2><p>Backup exports are kept in the archive so the research team can restore snapshots during migrations.</p></div>
        </div>
        """),
        nav='<a href="/">Home</a><a href="/notes">Notes</a><a href="/robots.txt">robots.txt</a>',
    )


@app.get("/notes")
def notes():
    return lab.page(
        "Notes · PRISM ARCHIVE",
        shell("""
        <div class="panel"><h2>Migration checklist</h2>
        <ul class="list">
          <li>Export the content database before rotating object storage keys.</li>
          <li>Keep a copy of the environment template with the deployment bundle.</li>
          <li>Remove temporary exports after validation — or so the checklist says.</li>
        </ul>
        <p class="note">The 2026 replay left an export under maintenance. It is referenced by the crawler policy.</p></div>
        """),
    )


@app.get("/robots.txt")
def robots():
    return lab.page(
        "robots.txt",
        "<pre>User-agent: *\nDisallow: /backups/\nDisallow: /admin/\n\n# maintenance export retained for replay\n</pre>",
        nav='<a href="/">Home</a>',
    )


@app.get("/backups/")
def backup_index():
    files = sorted(p.name for p in BACKUPS.iterdir() if p.is_file())
    rows = "".join(f'<li><a href="/backups/{name}">{name}</a> <span class="dim">({size} bytes)</span></li>' for name in files for size in [ (BACKUPS / name).stat().st_size ])
    return lab.page(
        "Backup index",
        shell(f'<div class="panel"><h2>Index of /backups</h2><ul class="list">{rows}</ul></div>'),
    )


@app.get("/backups/<path:name>")
def backup_file(name: str):
    path = (BACKUPS / name).resolve()
    if not str(path).startswith(str(BACKUPS.resolve())) or not path.is_file():
        return lab.page("Not found", '<div class="flash err">No such export.</div>', status=404)
    if path.name.endswith(".env"):
        content = path.read_text()
        content = content.replace("__VAULT_FLAG__", lab.flag("flag"))
        return lab.page(path.name, f"<h1>{path.name}</h1><pre>{content}</pre>")
    if path.name.endswith(".db"):
        return lab.page(
            path.name,
            "<h1>content.db.bak</h1><p>Synthetic SQLite database export used by the archive migration.</p>"
            "<pre>SQLite format 3 ...\nCopyright ...</pre>",
        )
    return lab.page(path.name, f"<h1>{path.name}</h1><pre>{path.read_text(errors='replace')}</pre>")


if __name__ == "__main__":
    lab.run()
