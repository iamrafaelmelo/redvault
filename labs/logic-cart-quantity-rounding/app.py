from __future__ import annotations

import html
import math

from flask import request, session

from labkit import Lab

lab = Lab("CARTPOINT", accent="#5fb3f0")
app = lab.app

WALLET = 500
CATALOG = {
    "ink": {"name": "Ink refill", "price": 0.125, "bulk_unit": 1000.0},
    "desk": {"name": "Standing desk", "price": 349.0, "bulk_unit": 1000.0},
    "usb": {"name": "USB-C dock", "price": 89.0, "bulk_unit": 1000.0},
    "flag-pass": {"name": "Archive access pass", "price": 4000.0, "bulk_unit": 1000.0},
}


def cart() -> list[dict]:
    if "cart" not in session:
        session["cart"] = []
    return list(session["cart"])


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">CARTPOINT // STOREFRONT</div><h1>{title}</h1></div>{body}',
        nav='<a href="/">Store</a><a href="/cart">Cart</a>',
    )


@app.get("/")
def index():
    items = cart()
    cards = "".join(
        f'''<div class="panel"><h3>{p["name"]}</h3><p class="mono">{p["price"]:.3f} credits</p>
        <form method="post" action="/cart/add"><input type="hidden" name="sku" value="{sku}">
        <label>Quantity</label><input name="qty" value="1"><p><button type="submit">Add to cart</button></p></form></div>'''
        for sku, p in CATALOG.items()
    )
    return shell(
        "Storefront",
        f'''<div class="panel"><p>Logged-in wallet: {WALLET} credits. Bulk pricing is recalculated at checkout
        from the unit price and the submitted quantity using the finance margin formula.</p></div>
        <div class="grid">{cards}</div>
        <p><a class="btn-ghost btn" href="/cart">View cart ({len(items)})</a></p>''',
    )


@app.post("/cart/add")
def add():
    sku = (request.form.get("sku") or "").strip()
    if sku not in CATALOG:
        return shell("Unknown SKU", '<div class="flash err">That product does not exist.</div>')
    try:
        qty = float(request.form.get("qty", "1"))
    except ValueError:
        return shell("Invalid quantity", '<div class="flash err">Quantity must be a number.</div>')
    # VULNERABLE: only zero is rejected; negative and fractional quantities pass.
    if qty == 0:
        return shell("Invalid quantity", '<div class="flash err">Quantity must not be zero.</div>')
    items = cart()
    items.append({"sku": sku, "qty": qty})
    session["cart"] = items
    return shell(
        "Added to cart",
        f'<div class="flash ok">Added {qty:g} × {CATALOG[sku]["name"]}.</div><p><a href="/cart">Go to checkout</a></p>',
    )


def quote(items: list[dict]) -> tuple[float, list[str]]:
    """Finance margin formula: positive lines bill at the unit price, negative
    lines are settled as a pro-rated bulk margin credit."""
    lines: list[str] = []
    total = 0.0
    for entry in items:
        product = CATALOG[entry["sku"]]
        qty = float(entry["qty"])
        if qty > 0:
            line = product["price"] * qty
            lines.append(f"{product['name']} × {qty:g} = {line:.2f}")
        else:
            # VULNERABLE: negative quantities are paid out as a pro-rated bulk
            # margin credit instead of being rejected.
            line = product["bulk_unit"] * qty
            lines.append(f"{product['name']} × {qty:g} (bulk margin adjustment) = {line:.2f}")
        total += line
    return total, lines


def payable_of(items: list[dict]) -> tuple[int, float, list[str]]:
    raw, lines = quote(items)
    # VULNERABLE: the float subtotal is truncated to whole credits before the
    # balance check, so every fraction of a credit is silently discarded.
    return math.trunc(raw), raw, lines


@app.get("/cart")
def cart_page():
    items = cart()
    if not items:
        return shell("Cart", '<div class="panel"><p class="dim">Your cart is empty.</p></div>')
    payable, raw, lines = payable_of(items)
    rows = "".join(f"<li>{html.escape(line)}</li>" for line in lines)
    return shell(
        "Cart",
        f'''<div class="panel"><h2>Cart</h2><ul class="list">{rows}</ul>
        <p class="mono">Subtotal: {raw:.4f} credits</p>
        <p class="mono">Payable after finance rounding: {payable} credits</p>
        <form method="post" action="/checkout"><p><button type="submit">Pay {payable} credits</button></p></form></div>''',
    )


@app.post("/checkout")
def checkout():
    items = cart()
    if not items:
        return shell("Checkout", '<div class="flash err">Your cart is empty.</div>')
    payable, raw, lines = payable_of(items)
    skus = {entry["sku"] for entry in items}
    # VULNERABLE: the wallet is only compared against the truncated total, and a
    # zero or negative total is accepted as a successful payment.
    if payable > WALLET:
        return shell(
            "Payment declined",
            f'<div class="flash err">Card declined: payable {payable} credits exceeds wallet {WALLET}.</div>',
        )
    session["cart"] = []
    if "flag-pass" in skus:
        lab.objective_async("flag", f"checkout accepted a payable total of {payable} credits")
        return shell(
            "Order confirmed",
            f'''<div class="flash ok">Payment of {payable} credits accepted. Order released.</div>
            <div class="panel"><h2>Archive access pass</h2><pre>{lab.flag("flag")}</pre></div>''',
        )
    names = ", ".join(sorted(CATALOG[s]["name"] for s in skus))
    return shell(
        "Order confirmed",
        f'<div class="flash ok">Payment of {payable} credits accepted for {html.escape(names)}.</div>',
    )


if __name__ == "__main__":
    lab.run()