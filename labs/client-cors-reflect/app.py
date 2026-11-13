from __future__ import annotations

from flask import jsonify, redirect, request, session

from labkit import Lab

lab = Lab("SIGNAL DESK", accent="#5e8ee6")
app = lab.app

USERS = {"alice": "alice123"}


def add_cors_headers(response):
    origin = request.headers.get("Origin")
    # VULNERABLE: reflects any caller-supplied origin and allows credentialed reads.
    response.headers["Access-Control-Allow-Origin"] = origin or "*"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Requested-With"
    return response


def shell(title: str, body: str) -> object:
    nav = '<a href="/dashboard">Dashboard</a><a href="/logout">Sign out</a>' if session.get("user") else '<a href="/login">Sign in</a>'
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">SIGNAL DESK // ACCOUNT API</div><h1>{title}</h1>'
        '<p>Partner dashboards read account data directly from the browser API.</p></div>' + body,
        nav=nav,
    )


@app.get("/")
def index():
    return redirect("/dashboard" if session.get("user") else "/login")


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if USERS.get(username) == password:
            session["user"] = username
            return redirect("/dashboard")
        error = '<div class="flash err">Invalid credentials.</div>'
    return shell(
        "Sign in",
        f'''<div class="panel"><h2>Account access</h2>
        <form method="post" action="/login">
        <label>Username</label><input name="username" value="alice">
        <label>Password</label><input name="password" type="password" value="alice123">
        <p><button type="submit">Sign in</button></p></form>{error}
        <p class="note">Demo account: <code>alice</code> / <code>alice123</code>. Partner dashboards call <code>/api/me</code> with credentials.</p></div>''',
    )


@app.get("/dashboard")
def dashboard():
    if not session.get("user"):
        return redirect("/login")
    return shell(
        "Account dashboard",
        f'''<div class="panel"><h2>Signed in as {session["user"]}</h2>
        <p>The browser account widget fetches <code>/api/me</code> and renders the JSON response.</p>
        <pre>fetch("/api/me", {{credentials: "include"}}).then(r =&gt; r.json())</pre>
        <p class="note">This endpoint is shared with partner dashboards hosted on other origins. The API trusts the browser's Origin header.</p></div>''',
    )


@app.route("/api/me", methods=["GET", "OPTIONS"])
def me():
    if request.method == "OPTIONS":
        response = lab.app.response_class("", status=204)
        return add_cors_headers(response)
    if session.get("user") != "alice":
        return add_cors_headers(jsonify({"error": "authentication required"}))
    return add_cors_headers(
        jsonify(
            {
                "user": "alice",
                "role": "analyst",
                "email": "alice@signal-desk.example",
                "clearance": "vault-reader",
                "flag": lab.flag("flag"),
            }
        )
    )


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    lab.run()
