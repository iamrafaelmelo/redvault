from __future__ import annotations

from flask import jsonify, request, session

from labkit import Lab

lab = Lab("LEDGERLINE", accent="#4fc3a1")
app = lab.app

USERS = {
    "analyst": {"password": "analyst123", "role": "analyst", "display": "Avery Cole"},
}

ITEMS = ["Signal cable", "Field battery", "Antenna mast", "Weatherproof case", "Uplink module", "Ground stake"]
ORDERS = [
    {
        "id": f"ORD-{2000 + index}",
        "owner": "analyst",
        "item": ITEMS[index % len(ITEMS)],
        "quantity": 1 + index % 3,
        "total": round(18.5 + index * 4.75, 2),
        "status": "delivered" if index % 4 else "processing",
        "placed": f"2026-10-{(index % 28) + 1:02d}",
    }
    for index in range(24)
]
ORDERS.append(
    {
        "id": "ORD-9001",
        "owner": "admin",
        "item": "Vault access renewal",
        "quantity": 1,
        "total": 0.0,
        "status": "internal",
        "placed": "2026-11-12",
        "internal_ref": lab.flag("flag"),
        "note": "Settlement credential — do not expose on the analyst console.",
    }
)

ANALYST_COUNT = sum(1 for order in ORDERS if order["owner"] == "analyst")


def shell(title: str, body: str, nav_extra: str = "") -> object:
    nav = '<a href="/">Console</a><a href="/api/orders?limit=2&amp;offset=0">Orders API</a><a href="/health">Health</a>' + nav_extra
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">LEDGERLINE // ORDER ANALYTICS</div><h1>{title}</h1>'
        '<p>Recent order activity for the field operations team.</p></div>' + body,
        nav=nav,
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        data = request.get_json(silent=True) if request.is_json else request.form
        if not isinstance(data, dict):
            data = request.form
        username = str(data.get("username", "")).strip()
        password = str(data.get("password", ""))
        account = USERS.get(username)
        if account and account["password"] == password:
            session["user"] = username
            if request.is_json:
                return jsonify({"ok": True, "user": username, "role": account["role"]})
            return lab.redirect("/")
        error = '<div class="flash err">Invalid analyst credentials.</div>'
        if request.is_json:
            return jsonify({"error": "invalid credentials"}), 401
    if session.get("user"):
        return lab.redirect("/")
    return shell(
        "Analyst sign-in",
        f"""
        <div class="panel">
          <h2>Order console access</h2>
          <p class="dim">Demo account: <code>analyst</code> / <code>analyst123</code></p>
          <form method="post">
            <label>Username</label><input name="username" autocomplete="username" value="analyst">
            <label>Password</label><input name="password" type="password" autocomplete="current-password">
            <p><button type="submit">Sign in</button></p>
          </form>
          {error}
        </div>
        """,
    )


@app.get("/logout")
def logout():
    session.clear()
    return lab.redirect("/")


@app.get("/")
def index():
    if not session.get("user"):
        return lab.redirect("/login")
    return shell(
        "Order console",
        """
        <div class="panel">
          <h2>Your recent orders</h2>
          <p>The console requests a small page from the orders API. Pagination is controlled by `limit` and `offset`.</p>
          <pre id="orders" class="dim">Loading...</pre>
          <p><button id="next" class="btn-ghost" type="button">Load next page</button></p>
        </div>
        <script>
        let offset = 0;
        async function load() {
          const target = document.getElementById('orders');
          const response = await fetch(`/api/orders?limit=2&offset=${offset}`);
          const data = await response.json();
          target.textContent = JSON.stringify(data, null, 2);
        }
        document.getElementById('next').addEventListener('click', () => { offset += 2; load(); });
        load();
        </script>
        """,
        nav_extra='<a href="/logout">Logout</a>',
    )


@app.get("/api/orders")
def orders():
    user = session.get("user")
    if not user:
        return jsonify({"error": "authentication required"}), 401

    try:
        limit = int(request.args.get("limit", "2"))
        offset = int(request.args.get("offset", "0"))
    except ValueError:
        return jsonify({"error": "limit and offset must be integers"}), 400

    limit = max(0, min(limit, 1000))
    offset = max(0, offset)

    if limit >= 500:
        # VULNERABLE: the bulk reconciliation path pages the full order table
        # and never reapplies the analyst ownership filter.
        page = ORDERS[offset : offset + limit]
        total = len(ORDERS)
    else:
        owned = [order for order in ORDERS if order["owner"] == user]
        page = owned[offset : offset + limit]
        total = len(owned)

    return jsonify(
        {
            "orders": page,
            "count": len(page),
            "total": total,
            "limit": limit,
            "offset": offset,
            "owner_filter": "skipped" if limit >= 500 else "analyst",
        }
    )


if __name__ == "__main__":
    lab.run()
