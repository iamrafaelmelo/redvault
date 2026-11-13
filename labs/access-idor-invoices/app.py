from __future__ import annotations

from flask import redirect, request, session

from labkit import Lab

lab = Lab("BRIGHTLINE BILLING", accent="#3d8bfd")
app = lab.app

USERS = {"alice": "alice123", "bob": "bob123", "admin": "admin-not-used"}
INVOICES = {
    1001: {"owner": "alice", "amount": "$42.00", "memo": "Storage plan"},
    1002: {"owner": "bob", "amount": "$88.00", "memo": "Compute plan"},
    1003: {"owner": "admin", "amount": "$1,240.00", "memo": "Internal settlement", "flag": True},
}
WALLET = 0.0


def shell(title: str, body: str) -> object:
    nav = '<a href="/invoices">Invoices</a><a href="/logout">Logout</a>' if session.get("user") else '<a href="/">Login</a>'
    return lab.page(title, f'<div class="hero"><div class="kicker">BRIGHTLINE // BILLING</div><h1>{title}</h1></div>{body}', nav=nav)


@app.get("/")
def index():
    if session.get("user"):
        return redirect("/invoices")
    return shell(
        "Customer portal",
        """<div class="panel"><h2>Sign in</h2><form method="post" action="/login">
        <label>Username</label><input name="username" value="alice"><label>Password</label><input name="password" type="password" value="alice123">
        <p><button type="submit">Access billing</button></p></form><p class="note">Demo credentials are prefilled for this isolated lab.</p></div>""",
    )


@app.post("/login")
def login():
    username = request.form.get("username", "")
    if USERS.get(username) == request.form.get("password", ""):
        session["user"] = username
        return redirect("/invoices")
    return shell("Login failed", '<div class="flash err">Invalid account.</div>')


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.get("/invoices")
def invoices():
    user = session.get("user")
    if not user:
        return redirect("/")
    topics = "".join(
        f'<li><a href="/invoice/{number}">INV-{number}</a> <span class="dim">{data["memo"]}</span></li>'
        for number, data in INVOICES.items()
        if data["owner"] == user
    )
    return shell(
        "Your billing",
        f'<div class="panel"><h2>Invoices for {user}</h2><ul class="list">{topics}</ul>'
        '<p class="note">Invoice numbers are sequential. The object route does not repeat the ownership check.</p></div>',
    )


@app.get("/invoice/<int:number>")
def invoice(number: int):
    user = session.get("user")
    if not user:
        return redirect("/")
    data = INVOICES.get(number)
    if not data:
        return shell("Invoice missing", '<div class="flash err">No invoice with that number.</div>')
    # VULNERABLE: authenticated but no object-level authorization.
    flag = f'<div class="panel"><h2>Internal settlement</h2><pre>{lab.flag("flag")}</pre></div>' if data.get("flag") else ""
    owner_note = "" if data["owner"] == user else f'<div class="flash err">Record owner: {data["owner"]}. Your account: {user}. The server returned it anyway.</div>'
    return shell(
        f"Invoice INV-{number}",
        f'<div class="panel"><h2>INV-{number}</h2><p>{data["memo"]} · {data["amount"]}</p></div>{owner_note}{flag}',
    )


if __name__ == "__main__":
    lab.run()
