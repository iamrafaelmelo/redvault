from __future__ import annotations

from flask import request

from labkit import Lab

lab = Lab("KITE CATALOG", accent="#57b6d9")
app = lab.app

schema = """
CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL);
CREATE TABLE vault (id INTEGER PRIMARY KEY, secret TEXT NOT NULL);
"""
seed = [
    "INSERT INTO products (name, description) VALUES ('Aero Kite', 'Light wind wing, 3m span.');",
    "INSERT INTO products (name, description) VALUES ('Storm Kite', 'Reinforced sail for coastal gusts.');",
    "INSERT INTO products (name, description) VALUES ('Bar Harness', 'Four-line control bar and harness.');",
    f"INSERT INTO vault (secret) VALUES ('{lab.flag('flag')}');",
]
lab.init_db("catalog.db", schema, seed)


def shell(title: str, body: str) -> object:
    return lab.page(title, f'<div class="hero"><div class="kicker">KITE // FIELD CATALOG</div><h1>{title}</h1><p>Search the field catalog by product name or description.</p></div>{body}')


@app.get("/")
def index():
    query = request.args.get("q", "")
    rows = []
    error = ""
    if query:
        conn = lab.db("catalog.db")
        try:
            # VULNERABLE: three columns are selected from a SQL string built with input.
            sql = f"SELECT id, name, description FROM products WHERE name LIKE '%{query}%' OR description LIKE '%{query}%'"
            rows = conn.execute(sql).fetchall()
        except Exception as exc:
            error = f'<div class="flash err">Query error: {exc}</div>'
        finally:
            conn.close()
    cards = "".join(
        f'<div class="panel"><h2>{row["name"]}</h2><p>{row["description"]}</p><span class="tag">SKU-{row["id"]}</span></div>'
        for row in rows
    )
    return shell(
        "Field catalog",
        f'''<div class="panel"><form method="get"><label>Search</label><input name="q" value="{query}" placeholder="kite">
        <p><button type="submit">Search catalog</button></p></form></div>{error}<div class="grid">{cards or '<p class="dim">Search for a product to begin.</p>'}</div>''',
    )


if __name__ == "__main__":
    lab.run()
