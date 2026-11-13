from __future__ import annotations

import html
import json
import re
import secrets
from datetime import datetime, timezone

from flask import request

from labkit import Lab

lab = Lab("LANTERN LEDGER", accent="#f6ad55")
app = lab.app

USERS = lab.state_dir / "users.json"
COMMENTS = lab.state_dir / "comments.json"
CAPTURED: list[str] = []

# The moderator bot's session value: random per start, stored next to the user db
# so the platform bot and the console agree on it.
ADMIN_COOKIE = "admin_session"
_key_file = lab.state_dir / "bot-session.txt"
if not _key_file.exists():
    _key_file.write_text("at-" + secrets.token_hex(16))
ADMIN_KEY = _key_file.read_text().strip()

lab.write_state(
    "users.json",
    json.dumps(
        {
            "admin": {"password": secrets.token_urlsafe(18), "role": "admin"},
            "editor": {"password": "Lantern-2026!", "role": "editor"},
            "guest": {"password": "guest", "role": "member"},
        },
        indent=2,
    ),
)
lab.write_state("comments.json", json.dumps([]))

XSS_PROBE = re.compile(r"<[a-z!/][^>]*(?:on\w+\s*=|script|javascript:)", re.IGNORECASE)


def users() -> dict:
    return json.loads(lab.read_state("users.json") or "{}")


def save_users(data: dict) -> None:
    lab.write_state("users.json", json.dumps(data, indent=2))


def comments() -> list[dict]:
    try:
        return json.loads(lab.read_state("comments.json") or "[]")
    except ValueError:
        return []


def save_comments(rows: list[dict]) -> None:
    lab.write_state("comments.json", json.dumps(rows, indent=2))


def is_admin() -> bool:
    return request.cookies.get(ADMIN_COOKIE, "") == ADMIN_KEY


def shell(title: str, body: str, nav: str | None = None) -> object:
    if nav is None:
        nav = '<a href="/">Articles</a><a href="/comments">Comments</a><a href="/admin">Admin</a><a href="/report">Report to moderator</a>'
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">LANTERN // LEDGER</div><h1>{title}</h1></div>{body}',
        nav=nav,
    )


ARTICLES = {
    "lantern-1": {
        "title": "Reading a city by its lamps",
        "body": "Lamp posts were never only about light. They mark crossings, quiet squares and the edges of old districts.",
    },
    "lantern-2": {
        "title": "Found objects, found stories",
        "body": "A collection of small things people left on windowsills — and what they turned out to mean.",
    },
}


@app.get("/")
def index():
    cards = "".join(
        f'<div class="panel"><h3><a href="/article/{slug}">{html.escape(article["title"])}</a></h3>'
        f'<p>{html.escape(article["body"][:140])}…</p></div>'
        for slug, article in ARTICLES.items()
    )
    return shell("Lantern Ledger", f'<div class="grid">{cards}</div>')


@app.get("/article/<slug>")
def article(slug: str):
    item = ARTICLES.get(slug)
    if not item:
        return shell("Not found", '<div class="flash err">No such article.</div>', nav='<a href="/">Articles</a>'), 404
    rows = [row for row in comments() if row["article"] == slug]
    # VULNERABLE: stored comment bodies are interpolated without escaping.
    rendered = "".join(
        f'<div class="panel"><h3>{html.escape(row["author"])}</h3><p>{row["body"]}</p>'
        f'<span class="tag">{html.escape(row["created"])}</span></div>'
        for row in rows
    )
    return shell(
        item["title"],
        f'<div class="panel"><p>{html.escape(item["body"])}</p></div>'
        f"""<div class="panel"><h2>Leave a comment</h2>
        <form method="post" action="/comments">
          <input type="hidden" name="article" value="{html.escape(slug)}">
          <label>Name</label><input name="author" value="reader">
          <label>Comment</label><textarea name="body" rows="4" placeholder="Share a thought"></textarea>
          <p><button type="submit">Post comment</button></p>
        </form></div>{rendered or '<p class="dim">No comments yet.</p>'}""",
    )


@app.route("/comments", methods=["GET", "POST"])
def comment_list():
    notice = ""
    if request.method == "POST":
        article = request.form.get("article", "lantern-1")
        author = request.form.get("author", "reader").strip()[:60] or "reader"
        body = request.form.get("body", "").strip()[:4000]
        if body:
            rows = comments()
            rows.append(
                {
                    "id": len(rows) + 1,
                    "article": article if article in ARTICLES else "lantern-1",
                    "author": author,
                    "body": body,
                    "created": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
                }
            )
            save_comments(rows)
            notice = '<div class="flash ok">Comment posted.</div>'
        else:
            notice = '<div class="flash err">A comment body is required.</div>'
    return shell(
        "Recent comments",
        f'{notice}<div class="panel"><ul class="list">'
        + "".join(
            f'<li><b>{html.escape(row["author"])}</b> on <a href="/article/{html.escape(row["article"])}">'
            f'{html.escape(row["article"])}</a> · {html.escape(row["body"][:80])}</li>'
            for row in reversed(comments()[-20:])
        )
        + "</ul></div>",
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        account = users().get(username)
        if account and account["password"] == password:
            response = lab.redirect("/admin" if account["role"] == "admin" else "/comments")
            response.set_cookie(ADMIN_COOKIE if account["role"] == "admin" else "lantern_user", username, httponly=True, samesite="lax")
            return response
        error = '<div class="flash err">Invalid credentials. The demo editor account is <code>editor</code> / <code>Lantern-2026!</code>.</div>'
    return shell(
        "Sign in",
        f"""<div class="panel"><h2>Editor sign-in</h2>
        <form method="post"><label>Username</label><input name="username" value="editor">
        <label>Password</label><input name="password" type="password" value="Lantern-2026!">
        <p><button type="submit">Sign in</button></p></form>{error}</div>""",
    )


@app.get("/admin")
def admin():
    if not is_admin():
        return shell("Staff area", '<div class="flash err">Moderator session required.</div>', nav='<a href="/">Articles</a><a href="/login">Sign in</a>')
    editors = [name for name, account in users().items() if account["role"] in {"admin", "editor"}]
    return shell(
        "Moderator console",
        f"""<div class="panel"><h2>Staff roster</h2>
        <p>Editors: {', '.join(f'<code>{html.escape(name)}</code>' for name in editors)}</p>
        <p class="note">The moderator bot reviews reported comments with a staff cookie.</p></div>
        <div class="panel"><h2>Promote a reader</h2>
        <p>The moderator console shows a promotion form. It posts to <code>/admin/promote</code> with the reader
        to upgrade — there is no anti-CSRF token in this build.</p>
        <form method="post" action="/admin/promote">
          <label>Username</label><input name="username" value="guest">
          <label>Role</label><select name="role"><option>editor</option><option>admin</option></select>
          <p><button type="submit">Promote</button></p>
        </form></div>""",
    )


@app.post("/admin/promote")
def promote():
    # VULNERABLE: state-changing endpoint with no CSRF token and no re-auth; the
    # only gate is the moderator cookie, which a cross-site form can ride on.
    if not is_admin():
        return shell("Denied", '<div class="flash err">Moderator session required.</div>', nav='<a href="/">Articles</a>'), 403
    username = request.form.get("username", request.values.get("user", "")).strip()
    role = request.form.get("role", "editor").strip()
    people = users()
    if username not in people:
        return shell("Promotion failed", '<div class="flash err">Unknown user.</div>', nav='<a href="/">Articles</a>'), 404
    if role not in {"editor", "admin"}:
        role = "editor"
    people[username]["role"] = role
    save_users(people)
    body = (
        f'<div class="panel"><h2>Promotion applied</h2>'
        f'<p><code>{html.escape(username)}</code> now has the <code>{html.escape(role)}</code> role.</p>'
    )
    if role == "admin":
        lab.objective_async("flag", f"cross-site request promoted {username} to admin")
        body += f'<p class="note">Administrator grant recorded.</p><pre>{lab.flag("flag")}</pre>'
    body += "</div>"
    return shell("Promotion complete", body, nav='<a href="/">Articles</a><a href="/staff">Staff</a>')


@app.get("/staff")
def staff():
    if not is_admin():
        return shell("Staff", '<div class="flash err">Moderator session required.</div>', nav='<a href="/">Articles</a><a href="/login">Sign in</a>')
    admins = [name for name, account in users().items() if account["role"] == "admin"]
    roster = "".join(f'<li><code>{html.escape(name)}</code> · {html.escape(users()[name]["role"])}</li>' for name in sorted(users()))
    flag = f'<pre>{lab.flag("flag")}</pre>' if "guest" in admins or "reader" in admins else '<p class="dim">No self-service promotions pending.</p>'
    return shell(
        "Staff roster",
        f'<div class="panel"><h2>Accounts</h2><ul class="list">{roster}</ul>{flag}</div>',
    )


@app.route("/report", methods=["GET", "POST"])
def report():
    message = ""
    if request.method == "POST":
        link = request.form.get("link", "").strip() or "/article/lantern-1"
        result = lab.bot(link, cookies=[{"name": ADMIN_COOKIE, "value": ADMIN_KEY}], wait=2.0)
        message = (
            '<div class="flash ok">Bot visit: completed</div>'
            if result.get("ok")
            else f'<div class="flash err">Bot visit: {html.escape(str(result.get("error", "failed")))}</div>'
        )
    return shell(
        "Report to moderator",
        f"""<div class="panel"><h2>Ask a moderator to review</h2>
        <p>The moderator bot opens the page you report with its staff cookie. Comments render raw HTML in the
        article view.</p>
        <form method="post" action="/report">
          <label>Article link</label><input name="link" value="/article/lantern-1">
          <p><button type="submit">Send moderator bot</button></p>
        </form>{message}
        <p class="note">Reported pages that the bot loads are logged at <code>/collect</code>.</p></div>""",
    )


@app.route("/collect", methods=["GET", "POST"])
def collect():
    value = request.args.get("c") or request.args.get("d") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
        if lab.flag("flag") in value:
            lab.objective_async("flag", "moderator data exfiltrated from the stored comment")
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(f'<li><code>{html.escape(value)}</code></li>' for value in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'
    return shell("Captured data", f'<div class="panel"><h2>Collector</h2><ul class="list">{rows}</ul></div>')


@app.get("/robots.txt")
def robots():
    return lab.app.response_class("User-agent: *\nDisallow: /admin\nDisallow: /staff\n", mimetype="text/plain")


if __name__ == "__main__":
    lab.run()