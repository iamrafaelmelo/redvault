from __future__ import annotations

from flask import redirect, request, session

from labkit import Lab

lab = Lab("TICKETFORGE", accent="#8ecae6")
app = lab.app

PRICE = 400
COUPON_VALUE = 40


def init():
    session.setdefault("coupons", [])


def layout(title: str, body: str) -> object:
    init()
    return lab.page(title, f'<div class="hero"><div class="kicker">TICKETFORGE // VAULT PASS</div><h1>{title}</h1></div>{body}', nav='<a href="/">Pass</a>')


@app.get("/")
def index():
    total = PRICE - COUPON_VALUE * len(session.get("coupons", []))
    used = "".join(f'<li><code>{code}</code> · -${COUPON_VALUE}</li>' for code in session.get("coupons", [])) or "<li>No codes applied.</li>"
    disabled = "disabled" if total > 0 else ""
    return layout(
        "Vault Pass checkout",
        f'''<div class="panel"><h2>Vault Pass — ${PRICE}.00</h2>
        <p>One pass. One settlement. Apply a promotional code before checkout.</p>
        <form method="post" action="/coupon"><label>Promo code</label><input name="code" value="VAULT10">
        <p><button type="submit">Apply code</button></p></form>
        <ul class="list">{used}</ul>
        <p>Total: <strong>${total}.00</strong></p>
        <form method="post" action="/checkout"><button type="submit" {disabled}>Complete purchase</button></form>
        <p class="note">The code is single-use per customer, according to the marketing page. The basket does not enforce it.</p></div>''',
    )


@app.post("/coupon")
def coupon():
    init()
    code = request.form.get("code", "").strip().upper()
    if code != "VAULT10":
        return layout("Invalid code", '<div class="flash err">That promotional code is not active.</div>')
    # VULNERABLE: no duplicate detection and no floor on the resulting total.
    session["coupons"] = session.get("coupons", []) + [code]
    session.modified = True
    return redirect("/")


@app.post("/checkout")
def checkout():
    init()
    total = PRICE - COUPON_VALUE * len(session.get("coupons", []))
    if total > 0:
        return layout("Payment required", f'<div class="flash err">The remaining total is ${total}.00.</div>')
    if not session.get("coupons"):
        return layout("No discount", '<div class="flash err">Apply a code first.</div>')
    flag = lab.flag("flag")
    session["coupons"] = []
    session.modified = True
    return layout(
        "Pass issued",
        f'<div class="flash ok">Coupon stack accepted. Order total ${total}.00.</div><div class="panel"><h2>Vault Pass</h2><pre>{flag}</pre></div>',
    )


if __name__ == "__main__":
    lab.run()
