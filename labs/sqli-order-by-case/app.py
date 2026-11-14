from __future__ import annotations

import os
import re
import sqlite3
import uuid

from flask import request

from labkit import Lab

lab = Lab("ORCHARD CATALOG", accent="#7fbf6a")
app = lab.app

SCHEMA = """
CREATE TABLE products (
  id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  category TEXT NOT NULL,
  price_cents INTEGER NOT NULL,
  stock INTEGER NOT NULL
);
CREATE TABLE vault (
  id INTEGER PRIMARY KEY,
  secret TEXT NOT NULL
);
"""

SEED = [
    "INSERT INTO products (name,category,price_cents,stock) VALUES ('Aurora Lamp','lighting',12900,14);",
    "INSERT INTO products (name,category,price_cents,stock) VALUES ('Basalt Mug','kitchen',1800,52);",
    "INSERT INTO products (name,category,price_cents,stock) VALUES ('Cedar Stool','furniture',8900,7);",
    "INSERT INTO products (name,category,price_cents,stock) VALUES ('Driftwood Shelf','furniture',15400,3);",
    "INSERT INTO products (name,category,price_cents,stock) VALUES ('Ember Kettle','kitchen',6200,21);",
    "INSERT INTO products (name,category,price_cents,stock) VALUES ('Fern Planter','decor',3400,38);",
    "INSERT INTO products (name,category,price_cents,stock) VALUES ('Grove Print','decor',2900,44);",
    "INSERT INTO products (name,category,price_cents,stock) VALUES ('Haven Throw','textiles',7300,18);",
    "INSERT INTO products (name,category,price_cents,stock) VALUES ('Iris Cushion','textiles',2600,61);",
    "INSERT INTO products (name,category,price_cents,stock) VALUES ('Juniper Tray','kitchen',4100,26);",
    f"INSERT INTO vault (secret) VALUES ('{lab.flag('flag')}');",
]

lab.init_db("catalog.db", SCHEMA, SEED)

# Internal analytics run on a separate connection so long reports never block
# the storefront's read connection.
_ANALYTICS: dict[str, sqlite3.Connection] = {}
_WORD = re.compile(r"[^\s,()';%*\"=\-<>!|&]+")


def shell(title: str, body: str, status: int = 200) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">ORCHARD // PUBLIC CATALOG</div><h1>{title}</h1>'
        '<p>Home goods, sorted the way you like them. Orders ship from the Orchard warehouse in 2 days.</p></div>'
        + body,
        nav='<a href="/">Catalog</a><a href="/search">Search</a><a href="/api/products?sort=name&dir=asc">API</a>',
        status=status,
    )


def normalize_sort(sort: str) -> str:
    # Tab-completion helper: the storefront keeps the last segment typed after
    # a comma so half-finished multi-column sorts still render.
    if "," in sort:
        return sort.rsplit(",", 1)[-1].strip()
    return sort


def query_products(sort: str, direction: str) -> list[sqlite3.Row]:
    conn = lab.db("catalog.db")
    try:
        # VULNERABLE: sort column and direction are interpolated into ORDER BY.
        sql = (
            "SELECT id, name, category, price_cents, stock FROM products "
            f"ORDER BY {sort} {direction}"
        )
        return conn.execute(sql).fetchall()
    finally:
        conn.close()


def run_analytics(sort: str) -> dict[str, object]:
    """Rank the catalog for the public "top sellers" widget.

    The report runs on a private analytics connection so the integration suite
    can never hold the storefront's handles. It only ranks, so the worst an
    odd sort can do is reorder the same products.
    """
    url = os.environ.get("LAB_DATABASE_URL", "")
    if url.startswith("file:") and "mode=ro" in url:
        key = os.environ.get("LAB_STATE_DIR", "default") + "|" + url
        conn = _ANALYTICS.get(key)
        if conn is None:
            conn = sqlite3.connect(url, uri=True, timeout=5, check_same_thread=False)
            _ANALYTICS[key] = conn
    else:
        key = os.environ.get("LAB_STATE_DIR", "default") + "|" + str(lab.state_dir / "catalog.db")
        conn = _ANALYTICS.get(key)
        if conn is None:
            conn = lab.db("catalog.db")
            _ANALYTICS[key] = conn
    terms = " ".join(_WORD.findall(sort or "")) or "id"
    sql = f"SELECT name, category FROM products ORDER BY {terms} ASC"
    rows = conn.execute(sql).fetchall()
    return {
        "job": uuid.uuid4().hex[:8],
        "sql": sql,
        "ranked": [{"rank": i + 1, "name": r[0], "category": r[1]} for i, r in enumerate(rows)],
    }


def direction_clause(raw: str) -> str:
    # The storefront keeps a custom ordering suffix in the direction field, so
    # anything that is not plain "desc" is passed through verbatim.
    return "desc" if raw.lower() == "desc" else raw


def render_catalog() -> object:
    sort = request.args.get("sort", "name")
    direction = request.args.get("dir", "asc")
    sql_sort = normalize_sort(sort)
    error = ""
    rows: list[sqlite3.Row] = []
    try:
        rows = query_products(sql_sort, direction_clause(direction))
    except sqlite3.Error as exc:
        error = f"<div class='flash err'>Could not sort the catalog: {exc}</div>"
    items = "".join(
        f"<tr><td>{r['id']}</td><td>{r['name']}</td><td>{r['category']}</td>"
        f"<td>${r['price_cents'] / 100:.2f}</td><td>{r['stock']}</td></tr>"
        for r in rows
    )
    options = "".join(
        f"<option value='{c}'{' selected' if c == sort else ''}>{c}</option>" for c in
        ["name", "category", "price_cents", "stock", "id"]
    )
    first_html = ""
    if rows:
        first = rows[0]
        first_html = f"<p class='mono dim'>First row: #{first['id']} · {first['name']}</p>"
    return shell(
        "Catalog",
        f"""<div class="panel"><h2>Sort the catalog</h2>
        <form method="get" action="/">
          <label>Sort by</label>
          <select name="sort">{options}</select>
          <label>Direction</label>
          <select name="dir"><option value="asc"{' selected' if direction == 'asc' else ''}>asc</option>
          <option value="desc"{' selected' if direction == 'desc' else ''}>desc</option></select>
          <p><button type="submit">Apply</button></p>
        </form>{error}</div>
        <table><thead><tr><th>ID</th><th>Name</th><th>Category</th><th>Price</th><th>Stock</th></tr></thead>
        <tbody>{items or '<tr><td colspan=5>No rows returned. Adjust the sort.</td></tr>'}</tbody></table>{first_html}""",
    )


@app.get("/")
def index():
    return render_catalog()


@app.post("/")
def index_post():
    return render_catalog()


@app.get("/api/products")
def api_products():
    sort = request.args.get("sort", "name")
    direction = request.args.get("dir", "asc")
    sql_sort = normalize_sort(sort)
    try:
        rows = query_products(sql_sort, direction_clause(direction))
    except sqlite3.Error as exc:
        return {"error": str(exc)}, 500
    return {
        "sort": sql_sort,
        "dir": direction,
        "count": len(rows),
        "products": [
            {"id": r["id"], "name": r["name"], "category": r["category"],
             "price": r["price_cents"] / 100, "stock": r["stock"]}
            for r in rows
        ],
    }


@app.get("/api/analytics/sort")
def analytics_sort():
    sort = request.args.get("sort", "name")
    try:
        return run_analytics(sort)
    except sqlite3.Error as exc:
        return {"error": str(exc)}, 500


@app.post("/verify")
def verify():
    payload = request.get_json(silent=True) if request.is_json else {}
    submitted = str(request.form.get("secret") or (payload or {}).get("secret") or "").strip()
    if submitted and submitted == lab.flag("flag"):
        lab.objective_async("flag", "ORDER BY sort oracle recovered the vault secret")
        return shell(
            "Secret verified",
            "<div class='flash ok'>Correct. The vault secret matches the one you extracted through the sort oracle.</div>"
            f"<div class='panel'><h2>Vault release</h2><p class='mono dim'>secret: {submitted}</p>"
            f"<pre>{lab.flag('flag')}</pre></div>",
        )
    return shell(
        "Secret rejected",
        "<div class='flash err'>That value does not match the vault secret.</div>",
        status=400,
    )


@app.get("/search")
def search():
    q = request.args.get("q", "").strip()
    rows: list[sqlite3.Row] = []
    if q:
        conn = lab.db("catalog.db")
        try:
            # Correctly parameterised — the search box is not the injection point.
            rows = conn.execute(
                "SELECT id, name, category, price_cents FROM products "
                "WHERE name LIKE ? OR category LIKE ? ORDER BY name",
                (f"%{q}%", f"%{q}%"),
            ).fetchall()
        finally:
            conn.close()
    items = "".join(
        f"<tr><td>{r['id']}</td><td>{r['name']}</td><td>{r['category']}</td></tr>" for r in rows
    )
    return shell(
        "Search",
        f"""<div class="panel"><h2>Search products</h2>
        <form method="get" action="/search"><label>Query</label>
        <input name="q" value="{q}" placeholder="lamp"><p><button type="submit">Search</button></p></form>
        <table><thead><tr><th>ID</th><th>Name</th><th>Category</th></tr></thead>
        <tbody>{items or '<tr><td colspan=3>No matches.</td></tr>'}</tbody></table></div>""",
    )


if __name__ == "__main__":
    lab.run()