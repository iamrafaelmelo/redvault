from __future__ import annotations

import html
from pathlib import Path

from flask import request
from lxml import etree

from labkit import Lab

lab = Lab("ORDERVAULT", accent="#b48cf2")
app = lab.app

FLAG_FILE = Path("/tmp/redvault-xxe-flag.txt")
FLAG_FILE.write_text(lab.flag("flag") + "\n")

SAMPLE = "<order><id>PO-1042</id><note>Deliver before Friday.</note></order>"


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">ORDERVAULT // DOCUMENT INTAKE</div><h1>{title}</h1>'
        '<p>Import supplier orders as XML. The parser expands document entities so templates can reference shared values.</p></div>' + body,
        nav='<a href="/import">Import</a><a href="/health">Health</a>',
    )


def parse_xml(document: str) -> tuple[str, str]:
    parser = etree.XMLParser(load_dtd=True, resolve_entities=True, no_network=True)
    try:
        root = etree.fromstring(document.encode("utf-8"), parser)
    except (etree.XMLSyntaxError, ValueError) as exc:
        return "", f"XML parse error: {exc}"
    # VULNERABLE: DTD loading and entity resolution are enabled, so an external
    # entity can read local files that the parser process can access.
    rendered = etree.tostring(root, encoding="unicode", pretty_print=True)
    return rendered, ""


@app.get("/")
def index():
    return lab.redirect("/import")


@app.route("/import", methods=["GET", "POST"])
def import_order():
    document = ""
    rendered = ""
    error = ""
    if request.method == "POST":
        document = request.form.get("xml", "")
        if not document:
            body = request.get_json(silent=True)
            if isinstance(body, dict):
                document = str(body.get("xml", ""))
        if not document:
            document = request.get_data(as_text=True)
        if not document.strip():
            error = "No XML document supplied."
        else:
            rendered, error = parse_xml(document)
    notice = f'<div class="flash err">{html.escape(error)}</div>' if error else ""
    output = f'<div class="panel"><h2>Parsed order</h2><pre>{html.escape(rendered)}</pre></div>' if rendered else ""
    return shell(
        "Supplier order import",
        f"""
        <div class="panel">
          <h2>XML intake</h2>
          <p>Paste a supplier order. The importer loads the document DTD and resolves declared entities, matching the legacy template pipeline.</p>
          <form method="post">
            <label>XML document</label>
            <textarea name="xml" rows="9" placeholder="&lt;order&gt;...&lt;/order&gt;">{html.escape(document)}</textarea>
            <p><button type="submit">Parse order</button></p>
          </form>
          {notice}
        </div>
        {output}
        <p class="note">The import worker keeps its private settlement data in <code>/tmp</code>. External network access is disabled during parsing.</p>
        """,
    )


if __name__ == "__main__":
    lab.run()
