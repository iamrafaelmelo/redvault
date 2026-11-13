from __future__ import annotations

import os
from pathlib import Path

from flask import request

from labkit import Lab

lab = Lab("DOCVAULT", accent="#c08a4f")
app = lab.app

DOCS = Path(__file__).resolve().parent / "docs"
lab.write_state("flag.txt", lab.flag("flag") + "\n")


def shell(title: str, body: str) -> object:
    return lab.page(title, f'<div class="hero"><div class="kicker">DOCVAULT // DOCUMENT READER</div><h1>{title}</h1></div>{body}', nav='<a href="/">Documents</a><a href="/read?file=welcome.txt">welcome.txt</a>')


@app.get("/")
def index():
    files = sorted(p.name for p in DOCS.iterdir() if p.is_file())
    rows = "".join(f'<li><a href="/read?file={name}">{name}</a></li>' for name in files)
    return shell(
        "Document reader",
        f'<div class="panel"><h2>Available documents</h2><ul class="list">{rows}</ul><p class="note">The reader resolves paths relative to the document directory.</p></div>',
    )


@app.get("/read")
def read_file():
    name = request.args.get("file", "welcome.txt")
    # VULNERABLE: path joining does not confine the result to DOCS.
    path = os.path.join(str(DOCS), name)
    try:
        content = Path(path).read_text(errors="replace")
    except Exception as exc:
        return shell("Read failed", f'<div class="flash err">Could not read <code>{name}</code>: {exc}</div>')
    if lab.flag("flag") in content:
        lab.objective_async("flag", "private state file read through path traversal")
    return shell(
        f"Document · {name}",
        f'<div class="panel"><h2>{name}</h2><pre>{content}</pre></div>',
    )


if __name__ == "__main__":
    lab.run()
