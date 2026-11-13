from __future__ import annotations

from flask import redirect, request, session

from labkit import Lab

lab = Lab("CACHELINE", accent="#7c9ef5")
app = lab.app

CACHE: dict[str, tuple[str, str]] = {}
USERS = {"alice": "alice123"}


def account_page() -> str:
    return f'''<div class="panel"><h2>Private account · alice</h2>
    <p>Statement period: November 2026 · Balance $18,420.00</p>
    <p class="green">Vault credential:</p><pre>{lab.flag("flag")}</pre>
    <p class="note">This page is personalized and must never be returned from a shared cache.</p></div>'''


def layout(title: str, body: str) -> object:
    nav = '<a href="/account">Account</a><a href="/logout">Logout</a>' if session.get("user") else '<a href="/">Login</a>'
    return lab.page(title, f'<div class="hero"><div class="kicker">CACHELINE // PRIVATE BANKING</div><h1>{title}</h1></div>{body}', nav=nav)


@app.get("/")
def index():
    if session.get("user"):
        return redirect("/account")
    return layout(
        "Account login",
        """<div class="panel"><h2>Private banking</h2><form method="post" action="/login">
        <label>Username</label><input name="username" value="alice">
        <label>Password</label><input name="password" type="password" value="alice123">
        <p><button type="submit">Sign in</button></p></form>
        <p class="note">The edge cache is configured to store static-looking account paths (`.css`).</p></div>""",
    )


@app.post("/login")
def login():
    if USERS.get(request.form.get("username")) == request.form.get("password"):
        session["user"] = "alice"
        return redirect("/account")
    return layout("Login failed", '<div class="flash err">Invalid credentials.</div>')


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


def serve_account(cache_key: str | None = None):
    if not session.get("user"):
        if cache_key and cache_key in CACHE:
            html, owner = CACHE[cache_key]
            response = lab.app.response_class(html, mimetype="text/html")
            response.headers["X-Cache"] = f"HIT · cached for {owner}"
            return response
        return redirect("/")
    html = layout("Private account", account_page()).get_data(as_text=True)
    response = lab.app.response_class(html, mimetype="text/html")
    response.headers["X-Cache"] = "MISS"
    if cache_key:
        # VULNERABLE: caches a personalized response under a static-looking URL.
        CACHE[cache_key] = (html, session["user"])
    return response


@app.get("/account")
def account():
    return serve_account()


@app.get("/account/<path:asset>")
def account_asset(asset: str):
    key = request.path
    if session.get("user") and key.endswith(".css"):
        return serve_account(key)
    if key in CACHE:
        return serve_account(key)
    return redirect("/")


if __name__ == "__main__":
    lab.run()
