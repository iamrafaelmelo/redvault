from __future__ import annotations

from flask import request, session

from labkit import Lab

lab = Lab("CHECKOUT FLOW", accent="#4f9d82")
app = lab.app


def checkout_state() -> tuple[list[str], bool, bool]:
    cart = list(session.get("cart", []))
    return cart, bool(session.get("shipping_done")), bool(session.get("payment_done"))


def shell(title: str, body: str) -> object:
    cart, shipping, payment = checkout_state()
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">CHECKOUT FLOW // ORDER DESK</div><h1>{title}</h1>'
        f'<p>Cart: {len(cart)} item(s) · Shipping: {"complete" if shipping else "pending"} · '
        f'Payment: {"complete" if payment else "pending"}</p></div>{body}',
        nav='<a href="/">Catalog</a><a href="/checkout">Checkout</a>',
    )


def steps_panel() -> str:
    cart, shipping, payment = checkout_state()
    return f'''<div class="panel"><h2>Checkout steps</h2>
    <table><tbody>
      <tr><td>1 · Cart</td><td>{"ready" if cart else "empty"}</td>
        <td><a class="btn btn-sm btn-ghost" href="/">Add item</a></td></tr>
      <tr><td>2 · Shipping</td><td>{"complete" if shipping else "not started"}</td>
        <td><form method="post" action="/checkout/shipping"><button class="btn-sm" type="submit">Save shipping</button></form></td></tr>
      <tr><td>3 · Payment</td><td>{"complete" if payment else "not started"}</td>
        <td><form method="post" action="/checkout/payment"><button class="btn-sm" type="submit">Authorize payment</button></form></td></tr>
      <tr><td>4 · Confirm</td><td>{"cart ready" if cart else "waiting for cart"}</td>
        <td><form method="post" action="/checkout/confirm"><button class="btn-sm" type="submit">Place order</button></form></td></tr>
    </tbody></table>
    <p class="note">The order desk expects the steps to be completed in sequence.</p></div>'''


@app.get("/")
def index():
    cart, _, _ = checkout_state()
    items = "".join(f'<li>{item} <span class="tag">CART</span></li>' for item in cart) or '<li class="dim">Your cart is empty.</li>'
    return shell(
        "Field order desk",
        f'''<div class="panel"><h2>Catalog</h2>
        <p>Field kits are assembled after order confirmation.</p>
        <form method="post" action="/cart/add"><input type="hidden" name="item" value="field-kit">
        <p><button type="submit">Add field kit to cart</button></p></form></div>
        <div class="grid"><div class="panel"><h2>Cart</h2><ul class="list">{items}</ul></div>
        <div class="panel"><h2>Current state</h2><p>The order desk tracks shipping and payment separately from the cart.</p>
        <a class="btn" href="/checkout">Open checkout</a></div></div>''',
    )


@app.post("/cart/add")
@app.post("/add")
@app.post("/cart")
def add_item():
    item = (request.form.get("item") or request.form.get("sku") or "field-kit").strip()[:80] or "field-kit"
    cart, _, _ = checkout_state()
    cart.append(item)
    session["cart"] = cart
    return shell("Item added", f'<div class="flash ok">Added <strong>{item}</strong> to the cart.</div>{steps_panel()}')


@app.get("/checkout")
def checkout():
    return shell("Checkout", f'{steps_panel()}<p class="note">Confirming the order sends it to fulfillment.</p>')


@app.post("/checkout/shipping")
def shipping():
    session["shipping_done"] = True
    return shell("Shipping saved", f'<div class="flash ok">Shipping destination recorded.</div>{steps_panel()}')


@app.post("/checkout/payment")
def payment():
    session["payment_done"] = True
    return shell("Payment authorized", f'<div class="flash ok">Payment method authorized.</div>{steps_panel()}')


@app.route("/checkout/confirm", methods=["GET", "POST"])
def confirm():
    cart, _, _ = checkout_state()
    if not cart:
        return shell("Order not ready", f'<div class="flash err">The cart is empty. Add an item before confirming.</div>{steps_panel()}')
    # VULNERABLE: only the cart is checked; shipping and payment state are never verified.
    return shell(
        "Order confirmed",
        f'''<div class="panel"><h2>Fulfillment receipt</h2>
        <p>Order accepted for <strong>{len(cart)} item(s)</strong>. The fulfillment service returned the vault handoff credential:</p>
        <pre>{lab.flag("flag")}</pre>
        <p class="note">Receipt reference: FLOW-{len(cart):02d}. Keep this credential out of customer-visible logs.</p></div>''',
    )


if __name__ == "__main__":
    lab.run()
