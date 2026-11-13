from __future__ import annotations

from flask import jsonify, redirect, request, session

from labkit import Lab

lab = Lab("LEDGERLINE", accent="#4f8cff")
app = lab.app

USERS = {
    "alice": {"password": "alice123", "tenant": "acme"},
}

INVOICES = {
    "acme": [
        {"id": 1, "amount": "$120.00", "memo": "Managed hosting"},
        {"id": 2, "amount": "$45.00", "memo": "Object storage"},
        {"id": 3, "amount": "$18.00", "memo": "DNS zone"},
    ],
    "globex": [
        {"id": 1, "amount": "$980.00", "memo": "Enterprise support"},
        {"id": 2, "amount": "$12,400.00", "memo": "Vault settlement", "flag": True},
    ],
}


def shell(title: str, body: str, nav: str | None = None) -> object:
    if nav is None:
        nav = (
            '<a href="/">Account</a><a href="/api/invoices">Invoices API</a><a href="/logout">Logout</a>'
            if session.get("user")
            else '<a href="/">Login</a>'
        )
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">LEDGERLINE // TENANT BILLING</div><h1>{title}</h1></div>{body}',
        nav=nav,
    )


@app.get("/")
def index():
    if session.get("user"):
        return shell(
            "Billing workspace",
            f"""<div class="panel"><h2>Signed in as {session["user"]}</h2>
            <p>Tenant: <code>{session.get("tenant", "acme")}</code></p>
            <p>The invoices API is used by the tenant dashboard and mobile client.</p>
            <p><a class="btn" href="/api/invoices">Open invoices API</a></p></div>""",
        )
    return shell(
        "Tenant sign-in",
        """<div class="panel"><h2>Customer portal</h2><form method="post" action="/login">
        <label>Username</label><input name="username" value="alice" autocomplete="username">
        <label>Password</label><input name="password" type="password" value="alice123" autocomplete="current-password">
        <p><button type="submit">Sign in</button></p></form>
        <p class="note">Demo credentials are prefilled for this isolated lab.</p></div>""",
    )


@app.post("/login")
def login():
    data = request.get_json(silent=True) if request.is_json else request.form
    data = data or {}
    username = str(data.get("username", ""))
    password = str(data.get("password", ""))
    user = USERS.get(username)
    if user and user["password"] == password:
        session.clear()
        session["user"] = username
        session["tenant"] = user["tenant"]
        if request.is_json:
            return jsonify({"ok": True, "user": username, "tenant": user["tenant"]})
        return redirect("/")
    if request.is_json:
        return jsonify({"error": "invalid credentials"}), 401
    return shell("Sign-in failed", '<div class="flash err">Invalid username or password.</div>', nav='<a href="/">Login</a>')


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.get("/api/invoices")
def invoices():
    user = session.get("user")
    if not user:
        return jsonify({"error": "authentication required"}), 401

    tenant = session.get("tenant", "acme")
    # VULNERABLE: the caller decides which tenant the API should read.
    supplied = request.headers.get("X-Tenant-ID")
    if supplied:
        tenant = supplied.strip()

    records = INVOICES.get(tenant)
    if records is None:
        return jsonify({"error": "unknown tenant", "tenant": tenant}), 404

    result = []
    for record in records:
        item = {"id": record["id"], "amount": record["amount"], "memo": record["memo"]}
        if record.get("flag"):
            item["flag"] = lab.flag("flag")
        result.append(item)

    return jsonify(
        {
            "tenant": tenant,
            "session_tenant": session.get("tenant"),
            "invoices": result,
        }
    )


if __name__ == "__main__":
    lab.run()
