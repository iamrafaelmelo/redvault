from __future__ import annotations

import sqlite3

from flask import request

from labkit import Lab

lab = Lab("HELPDESK NIMBUS", accent="#f0a04b")
app = lab.app

SCHEMA = """
CREATE TABLE users (
  id INTEGER PRIMARY KEY,
  username TEXT NOT NULL UNIQUE,
  email TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'customer',
  api_token TEXT NOT NULL
);
CREATE TABLE tickets (
  id INTEGER PRIMARY KEY,
  owner TEXT NOT NULL,
  subject TEXT NOT NULL,
  status TEXT NOT NULL
);
"""

SEED = [
    "INSERT INTO users (username,email,role,api_token) VALUES ('mara','mara@nimbus-support.io','admin','tok_mara_8f21');",
    "INSERT INTO users (username,email,role,api_token) VALUES ('jules','jules@nimbus-support.io','agent','tok_jules_3c90');",
    "INSERT INTO users (username,email,role,api_token) VALUES ('alice','alice@customer.test','customer','tok_alice_55bd');",
    "INSERT INTO users (username,email,role,api_token) VALUES ('bob','bob@customer.test','customer','tok_bob_c1e4');",
    "INSERT INTO tickets (owner,subject,status) VALUES ('alice','Cannot reset password','open');",
    "INSERT INTO tickets (owner,subject,status) VALUES ('bob','Invoice copy request','resolved');",
]

lab.init_db("helpdesk.db", SCHEMA, SEED)


def shell(title: str, body: str, status: int = 200) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">NIMBUS // SUPPORT DESK</div><h1>{title}</h1>'
        '<p>Customer lookups and account tooling for the Nimbus support crew.</p></div>' + body,
        nav='<a href="/">Support</a><a href="/admin">Admin</a><a href="/staff">Staff</a>',
        status=status,
    )


@app.get("/")
def index():
    return shell(
        "Support workspace",
        """<div class="panel"><h2>Customer lookup</h2>
        <form method="get" action="/lookup">
          <label>Customer username</label><input name="username" placeholder="alice">
          <p><button type="submit">Look up account</button></p>
        </form>
        <p class="note">Lookup runs against the support database. Reminder: customer usernames are unique and
        must be typed exactly as registered.</p></div>
        <div class="panel"><h2>Internal tooling</h2>
        <p>Administrators can review the platform roster at <a href="/admin">/admin</a>. Agents can list their
        own queue at <a href="/staff">/staff</a>.</p></div>""",
    )


@app.get("/lookup")
def lookup():
    username = request.args.get("username", "").strip()
    rows_html = ""
    error = ""
    note = ""
    if username:
        conn = lab.db("helpdesk.db")
        try:
            # VULNERABLE: the whole script is built by concatenation and run with
            # executescript, so a `;` in the username starts a second statement.
            script = (
                "SELECT id, username, email, role FROM users "
                f"WHERE username = '{username}'"
            )
            conn.executescript(script)
            # The script returns nothing (executescript), so the match is
            # re-read with a parameterless statement built the same unsafe way.
            rows = conn.execute(
                "SELECT id, username, email, role FROM users "
                f"WHERE username = '{username.split(';')[0]}'"
            ).fetchall()
            if rows:
                body = "".join(
                    f"<tr><td>{r['id']}</td><td>{r['username']}</td><td>{r['email']}</td>"
                    f"<td><span class='tag'>{r['role']}</span></td></tr>"
                    for r in rows
                )
                rows_html = (
                    "<div class='panel'><h2>Matches</h2><table><thead><tr><th>ID</th><th>Username</th>"
                    f"<th>Email</th><th>Role</th></tr></thead><tbody>{body}</tbody></table></div>"
                )
            else:
                note = "<div class='flash err'>No customer matched that username.</div>"
        except sqlite3.Error as exc:
            error = f"<div class='flash err'>Lookup failed: {exc}</div>"
        finally:
            conn.close()
    return shell(
        "Customer lookup",
        f"""<div class="panel"><h2>Look up a customer</h2>
        <form method="get" action="/lookup">
          <label>Customer username</label><input name="username" value="{username}">
          <p><button type="submit">Look up account</button></p>
        </form>{note}{error}</div>{rows_html}""",
    )


def _session_user() -> sqlite3.Row | None:
    token = request.args.get("token", "") or request.cookies.get("nimbus_token", "")
    if not token:
        return None
    conn = lab.db("helpdesk.db")
    try:
        row = conn.execute("SELECT * FROM users WHERE api_token = ?", (token,)).fetchone()
        return row
    finally:
        conn.close()


@app.get("/admin")
def admin():
    user = _session_user()
    if user is None:
        return shell(
            "Admin roster",
            "<div class='flash err'>Admin session required. Sign in with your API token: "
            "<code>/admin?token=...</code></div>",
            status=403,
        )
    if user["role"] != "admin":
        return shell(
            "Admin roster",
            f"<div class='flash err'>Access denied: <b>{user['username']}</b> has role "
            f"<code>{user['role']}</code>. Administrator role required.</div>",
            status=403,
        )
    conn = lab.db("helpdesk.db")
    try:
        users = conn.execute("SELECT id, username, email, role FROM users ORDER BY id").fetchall()
    finally:
        conn.close()
    lab.objective_async("flag", f"stacked UPDATE promoted {user['username']} to admin")
    rows = "".join(
        f"<tr><td>{u['id']}</td><td>{u['username']}</td><td>{u['email']}</td><td>{u['role']}</td></tr>"
        for u in users
    )
    return shell(
        "Admin roster",
        f"""<div class="panel"><h2>Authenticated as {user['username']} (admin)</h2>
        <table><thead><tr><th>ID</th><th>Username</th><th>Email</th><th>Role</th></tr></thead>
        <tbody>{rows}</tbody></table></div>
        <div class="panel"><h2>Platform flag</h2>
        <pre>{lab.flag('flag')}</pre>
        <p class="note">Roster export of privileged identities for the support audit.</p></div>""",
    )


@app.get("/staff")
def staff():
    user = _session_user()
    if user is None:
        return shell(
            "Agent queue",
            "<div class='flash err'>Sign in with your API token: <code>/staff?token=...</code></div>",
            status=403,
        )
    conn = lab.db("helpdesk.db")
    try:
        tickets = conn.execute(
            "SELECT id, subject, status FROM tickets WHERE owner = ?", (user["username"],)
        ).fetchall()
    finally:
        conn.close()
    rows = "".join(f"<tr><td>{t['id']}</td><td>{t['subject']}</td><td>{t['status']}</td></tr>" for t in tickets)
    return shell(
        "Agent queue",
        f"""<div class="panel"><h2>Queue for {user['username']} ({user['role']})</h2>
        <table><thead><tr><th>#</th><th>Subject</th><th>Status</th></tr></thead><tbody>{rows or '<tr><td colspan=3>No tickets.</td></tr>'}</tbody></table></div>""",
    )


if __name__ == "__main__":
    lab.run()