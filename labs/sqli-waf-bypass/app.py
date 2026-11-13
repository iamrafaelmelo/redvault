from __future__ import annotations

import html
import re

from flask import request

from labkit import Lab

lab = Lab("NORTHWIND SUPPLY", accent="#43b581")
app = lab.app

schema = """
CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL);
CREATE TABLE vault (id INTEGER PRIMARY KEY, secret TEXT NOT NULL);
"""
seed = [
    "INSERT INTO products (name, description) VALUES ('Ridge Tent', 'Two-person shelter for exposed camps.');",
    "INSERT INTO products (name, description) VALUES ('Coldforge Stove', 'Compact canister stove for high altitude.');",
    "INSERT INTO products (name, description) VALUES ('Trail Filter', 'Gravity-fed water filter for long routes.');",
    f"INSERT INTO vault (secret) VALUES ('{lab.flag('flag')}');",
]
lab.init_db("supply.db", schema, seed)


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">NORTHWIND // FIELD SUPPLY</div><h1>{title}</h1></div>{body}',
    )


@app.get("/search")
def search():
    raw = request.args.get("q", "")
    # VULNERABLE: the keyword filter is a substitution, not a parser.
    filtered = re.sub(r"union|select", "", raw, flags=re.IGNORECASE)
    rows = []
    error = ""

    conn = lab.db("supply.db")
    try:
        sql = f"SELECT id, name, description FROM products WHERE name LIKE '%' {filtered}"
        rows = conn.execute(sql).fetchall()
    except Exception as exc:
        error = f'<div class="flash err">Query rejected: {html.escape(str(exc))}</div>'
    finally:
        conn.close()

    cards = "".join(
        f'<div class="panel"><h2>{row["name"]}</h2><p>{row["description"]}</p><span class="tag">SKU-{row["id"]}</span></div>'
        for row in rows
    )
    return shell(
        "Supply search",
        f"""<div class="panel"><h2>Legacy filter console</h2>
        <form method="get" action="/search">
          <label>Filter expression</label><input name="q" value="{html.escape(raw)}" placeholder="AND name LIKE '%tent%'" size="80">
          <p><button type="submit">Run search</button></p>
        </form>
        <p class="note">The old console appends the filter fragment directly to the three-column product query. A plain term is not valid here; use an expression such as <code>AND name LIKE '%tent%'</code>.</p></div>
        {error}<div class="grid">{cards or '<p class="dim">No matching products.</p>'}</div>""",
    )


@app.get("/")
def index():
    return search()


if __name__ == "__main__":
    lab.run()
