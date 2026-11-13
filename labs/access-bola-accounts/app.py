from __future__ import annotations

from flask import jsonify, redirect, request, session

from labkit import Lab

lab = Lab("VAULTLINE API", accent="#8b5cf6")
app = lab.app

ACCOUNTS = {
    1: {"username": "alice", "plan": "Starter", "balance": 240.50, "email": "alice@vaultline.local"},
    2: {"username": "admin", "plan": "Enterprise", "balance": 98210.00, "email": "admin@vaultline.local"},
    3: {"username": "bob", "plan": "Growth", "balance": 1170.00, "email": "bob@vaultline.local"},
}


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">VAULTLINE // PARTNER API</div><h1>{title}</h1></div>{body}',
        nav='<a href="/">Console</a><a href="/api/v1/accounts/1">Account API</a><a href="/logout">Logout</a>',
    )


@app.get("/")
def index():
    if not session.get("user"):
        return shell(
            "Partner console",
            """<div class="panel"><h2>Sign in</h2><form method="post" action="/login">
            <label>Username</label><input name="username" value="alice"><label>Password</label><input name="password" type="password" value="alice123">
            <p><button type="submit">Authenticate</button></p></form><p class="note">Demo credentials are prefilled.</p></div>""",
        )
    return shell(
        "Partner console",
        f'<div class="panel"><h2>Welcome, {session["user"]}</h2><p>Your account record is available at <a href="/api/v1/accounts/1">/api/v1/accounts/1</a>.</p><p>The mobile app calls this endpoint directly. IDs are assigned at onboarding.</p></div>',
    )


@app.post("/login")
def login():
    if request.form.get("username") == "alice" and request.form.get("password") == "alice123":
        session["user"] = "alice"
        return redirect("/")
    return shell("Login failed", '<div class="flash err">Invalid credentials.</div>')


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.get("/api/v1/accounts/<int:account_id>")
def account_api(account_id: int):
    if not session.get("user"):
        return jsonify({"error": "authentication required"}), 401
    account = ACCOUNTS.get(account_id)
    if not account:
        return jsonify({"error": "account not found"}), 404
    payload = dict(account)
    # VULNERABLE: authenticated users can read any account object.
    if account["username"] == "admin":
        payload["private_note"] = lab.flag("flag")
        payload["billing_tier"] = "internal-settlement"
    return jsonify(payload)


if __name__ == "__main__":
    lab.run()
