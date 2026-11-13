from __future__ import annotations

from flask import redirect, request, session

from labkit import Lab

lab = Lab("LEDGERLINE CRM", accent="#b28bdc")
app = lab.app

schema = """
CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT NOT NULL, password TEXT NOT NULL);
CREATE TABLE activity (id INTEGER PRIMARY KEY, username TEXT NOT NULL, message TEXT NOT NULL);
CREATE TABLE vault (id INTEGER PRIMARY KEY, secret TEXT NOT NULL);
"""
seed = [f"INSERT INTO vault (secret) VALUES ('{lab.flag('flag')}');"]
lab.init_db("ledger.db", schema, seed)


def shell(title: str, body: str) -> object:
    nav = '<a href="/reports">Reports</a><a href="/logout">Logout</a>' if session.get("uid") else '<a href="/">Register</a>'
    return lab.page(title, f'<div class="hero"><div class="kicker">LEDGERLINE // CUSTOMER RECORDS</div><h1>{title}</h1></div>{body}', nav=nav)


@app.route("/", methods=["GET", "POST"])
def index():
    if session.get("uid"):
        return redirect("/reports")
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if not username or len(username) > 90 or len(password) < 6:
            error = '<div class="flash err">Username required (max 90), password at least 6 characters.</div>'
        else:
            conn = lab.db("ledger.db")
            try:
                # First write is parameterized. The username is stored as data.
                cur = conn.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, password))
                conn.commit()
                session["uid"] = cur.lastrowid
                conn.close()
                return redirect("/reports")
            except Exception as exc:
                conn.close()
                error = f'<div class="flash err">Registration failed: {exc}</div>'
    return shell(
        "Create account",
        f"""<div class="panel"><h2>Register</h2>
        <form method="post"><label>Username</label><input name="username" placeholder="analyst">
        <label>Password</label><input name="password" type="password">
        <p><button type="submit">Create account</button></p></form>{error}
        <p class="note">Accounts are created with a parameterized INSERT. Later reports use the stored username in a different query.</p></div>""",
    )


@app.get("/reports")
def reports():
    uid = session.get("uid")
    if not uid:
        return redirect("/")
    conn = lab.db("ledger.db")
    user = conn.execute("SELECT username FROM users WHERE id = ?", (uid,)).fetchone()
    if not user:
        conn.close()
        session.clear()
        return redirect("/")
    username = user["username"]
    error = ""
    rows = []
    try:
        # VULNERABLE: the previously stored username is interpreted as SQL later.
        sql = f"SELECT message FROM activity WHERE username = '{username}'"
        rows = conn.execute(sql).fetchall()
    except Exception as exc:
        error = f'<div class="flash err">Report query failed: {exc}</div>'
    finally:
        conn.close()
    if not rows and not error:
        error = '<div class="flash">No activity has been recorded for this account yet.</div>'
    messages = "".join(f'<li>{row["message"]}</li>' for row in rows)
    return shell(
        "Account activity",
        f'<div class="panel"><h2>Report for {username}</h2><p class="dim">Stored username is used to look up your activity.</p><ul class="list">{messages}</ul></div>{error}',
    )


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


if __name__ == "__main__":
    lab.run()
