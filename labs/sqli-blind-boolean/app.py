from __future__ import annotations

from flask import request

from labkit import Lab

lab = Lab("GREYLOCK DIRECTORY", accent="#9a7bff")
app = lab.app

schema = """
CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL);
CREATE TABLE vault (id INTEGER PRIMARY KEY, secret TEXT NOT NULL);
"""
seed = [
    "INSERT INTO users (username) VALUES ('alice');",
    "INSERT INTO users (username) VALUES ('bob');",
    "INSERT INTO users (username) VALUES ('carol');",
    f"INSERT INTO vault (secret) VALUES ('{lab.flag('flag')}');",
]
lab.init_db("directory.db", schema, seed)


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">GREYLOCK // STAFF DIRECTORY</div><h1>{title}</h1></div>{body}',
    )


@app.get("/lookup")
def lookup():
    username = request.args.get("username", "")
    outcome = ""
    matched = ""

    if username:
        conn = lab.db("directory.db")
        try:
            # VULNERABLE: the lookup concatenates the username into SQL.
            sql = f"SELECT id, username FROM users WHERE username = '{username}'"
            row = conn.execute(sql).fetchone()
            if row is not None:
                outcome = '<div class="flash ok">Account found</div>'
                matched = f'<p>Record: <code>{row["username"]}</code> · id {row["id"]}</p>'
            else:
                outcome = '<div class="flash err">No account found</div>'
        except Exception:
            outcome = '<div class="flash err">No account found</div>'
        finally:
            conn.close()

    return shell(
        "Directory lookup",
        f"""<div class="panel"><h2>Find a colleague</h2>
        <form method="get" action="/lookup">
          <label>Username</label><input name="username" value="{username}" placeholder="alice">
          <p><button type="submit">Look up</button></p>
        </form>
        <p class="note">The oracle only returns whether a record exists. Query errors are hidden.</p></div>
        {outcome}{matched}""",
    )


if __name__ == "__main__":
    lab.run()
