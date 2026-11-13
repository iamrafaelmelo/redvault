from __future__ import annotations

import secrets

from flask import redirect, request, session

from labkit import Lab

lab = Lab("PARSEC LOGIN", accent="#f0555f")
app = lab.app

schema = """
CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL, password TEXT NOT NULL);
"""
seed = [
    f"INSERT INTO users (username, password) VALUES ('admin', '{secrets.token_urlsafe(24)}');",
    "INSERT INTO users (username, password) VALUES ('alice', 'alice123');",
]
lab.init_db("users.db", schema, seed)


def shell(title: str, body: str) -> object:
    return lab.page(title, f'<div class="hero"><div class="kicker">PARSEC // CUSTOMER ACCESS</div><h1>{title}</h1></div>{body}')


@app.route("/", methods=["GET", "POST"])
def index():
    if session.get("user") == "admin":
        return shell(
            "Admin session",
            f'<div class="panel"><h2>Authenticated as administrator</h2><p class="green">The query returned an administrative row.</p><pre>{lab.flag("flag")}</pre></div>',
        )
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        conn = lab.db("users.db")
        try:
            # VULNERABLE: credentials are concatenated into the SQL text.
            row = conn.execute(
                f"SELECT id, username FROM users WHERE username = '{username}' AND password = '{password}'"
            ).fetchone()
            if row and row["username"] == "admin":
                session["user"] = "admin"
                return redirect("/")
            if row:
                error = f'<div class="flash ok">Query matched account: {row["username"]}. Only admin receives the flag.</div>'
            else:
                error = '<div class="flash err">No matching account.</div>'
        except Exception as exc:
            error = f'<div class="flash err">SQL error: {exc}</div>'
        finally:
            conn.close()
    return shell(
        "Sign in",
        f"""<div class="panel"><h2>Customer login</h2>
        <form method="post">
          <label>Username</label><input name="username" autocomplete="username">
          <label>Password</label><input name="password" type="password" autocomplete="current-password">
          <p><button type="submit">Authenticate</button></p>
        </form>{error}<p class="note">The login form is the only exposed authentication surface.</p></div>""",
    )


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    lab.run()
