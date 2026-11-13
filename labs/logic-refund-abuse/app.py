from __future__ import annotations

from flask import request, session

from labkit import Lab

lab = Lab("REFUND LOOP", accent="#d3a33a")
app = lab.app

CATALOG = {
    "sensor": {"name": "Field sensor", "price": 100, "blurb": "A compact environmental sensor for remote deployments."},
    "vault": {"name": "Vault access pass", "price": 200, "blurb": "One-time credential for the equipment vault."},
}


def account() -> tuple[int, list[dict]]:
    if "balance" not in session:
        session["balance"] = 150
        session["orders"] = []
    return int(session["balance"]), list(session.get("orders", []))


def shell(title: str, body: str) -> object:
    balance, orders = account()
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">REFUND LOOP // FIELD SUPPLY</div><h1>{title}</h1>'
        f'<p>Account balance: <strong class="green">{balance} credits</strong> · Orders: {len(orders)}</p></div>{body}',
        nav='<a href="/">Store</a><a href="/orders">Order history</a>',
    )


def storefront(notice: str = "") -> object:
    balance, orders = account()
    cards = "".join(
        f'''<div class="panel"><h2>{product["name"]}</h2>
        <p>{product["blurb"]}</p>
        <p class="mono">{product["price"]} credits</p>
        <form method="post" action="/buy"><input type="hidden" name="item" value="{sku}">
        <p><button type="submit">Buy {product["name"].lower()}</button></p></form></div>'''
        for sku, product in CATALOG.items()
    )
    last = f'''<p class="mono">Last order #{orders[-1]["id"]} · {CATALOG[orders[-1]["item"]]["name"]} · {orders[-1]["price"]} credits</p>
    <form method="post" action="/refund"><p><button type="submit">Refund last order</button></p></form>''' if orders else '<p class="dim">No orders to refund.</p>'
    return shell(
        "Field supply store",
        f'''{notice}<div class="grid">{cards}</div>
        <div class="panel"><h2>Refund desk</h2>
        <p>The refund desk credits the most recent order back to your balance. Each order is supposed to be refundable once.</p>
        {last}</div>''',
    )


@app.get("/")
def index():
    return storefront()


@app.get("/orders")
def orders_page():
    balance, orders = account()
    rows = "".join(
        f'<tr><td>#{order["id"]}</td><td>{CATALOG[order["item"]]["name"]}</td><td>{order["price"]} credits</td>'
        f'<td><span class="tag">{"REFUNDED" if order.get("refunded") else "PAID"}</span></td></tr>'
        for order in reversed(orders)
    ) or '<tr><td colspan="4" class="dim">No orders yet.</td></tr>'
    return shell(
        "Order history",
        f'''<div class="panel"><h2>Orders</h2>
        <table><thead><tr><th>Order</th><th>Item</th><th>Amount</th><th>Status</th></tr></thead><tbody>{rows}</tbody></table>
        <p class="note">Refund status is informational. The refund desk keeps its own record of recent activity.</p></div>''',
    )


@app.route("/buy", methods=["POST"])
@app.route("/purchase", methods=["POST"])
@app.route("/order", methods=["POST"])
def buy():
    item = (request.form.get("item") or request.form.get("sku") or "").strip().lower()
    if item not in CATALOG:
        return storefront('<div class="flash err">Unknown catalog item.</div>')
    balance, orders = account()
    product = CATALOG[item]
    if balance < product["price"]:
        return storefront(
            f'<div class="flash err">Insufficient balance: {product["name"]} costs {product["price"]} credits, '
            f'your balance is {balance}.</div>'
        )
    balance -= product["price"]
    orders.append({"id": len(orders) + 1, "item": item, "price": product["price"], "refunded": False})
    session["balance"] = balance
    session["orders"] = orders
    if item == "vault":
        return shell(
            "Vault access granted",
            f'''<div class="panel"><h2>Equipment vault</h2>
            <p>The vault accepted your pass. The inventory control system returned the access credential below.</p>
            <pre>{lab.flag("flag")}</pre>
            <p class="note">Pass purchases are final. Refunds do not revoke an issued vault credential.</p></div>''',
        )
    return storefront(f'<div class="flash ok">Purchased {product["name"]} for {product["price"]} credits.</div>')


@app.route("/refund", methods=["GET", "POST"])
def refund():
    balance, orders = account()
    if not orders:
        return storefront('<div class="flash err">There is no order to refund.</div>')
    last = orders[-1]
    # VULNERABLE: credits the last order without marking it refunded or removing it.
    session["balance"] = balance + int(last["price"])
    session["refunds"] = int(session.get("refunds", 0)) + 1
    return storefront(
        f'<div class="flash ok">Refunded order #{last["id"]} ({CATALOG[last["item"]]["name"]}) '
        f'for {last["price"]} credits.</div>'
    )


if __name__ == "__main__":
    lab.run()
