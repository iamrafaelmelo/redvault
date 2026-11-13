from __future__ import annotations

import html
import threading
import time

from flask import request

from labkit import Lab

lab = Lab("MERIDIAN COUPONS", accent="#4fd1c5")
app = lab.app

BALANCE = 25                 # campaign settlement wallet, shared by the desk
COUPON_PRICE = 1500          # cashback value of one FOUNDER40 redemption
FOUNDER_TIER = 10000         # founder vault opens at this settlement balance
COUPON = {"code": "FOUNDER40", "uses_left": 4}
REDEEM_LOG: list[str] = []
LOG_LOCK = threading.Lock()  # only guards the log list, not the coupon counter


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">MERIDIAN // COUPON ENGINE</div><h1>{title}</h1></div>{body}',
        nav='<a href="/">Desk</a><a href="/coupons">Coupon desk</a><a href="/api/coupons/status">Status API</a><a href="/vault">Founder vault</a>',
    )


@app.get("/")
def index():
    with LOG_LOCK:
        recent = "".join(f"<li>{html.escape(entry)}</li>" for entry in REDEEM_LOG[:6]) or "<li>No redemptions yet.</li>"
    return shell(
        "Coupon desk",
        f'''<div class="panel"><h2>Settlement balance: {BALANCE} credits</h2>
        <p>Every coupon redemption settles its cashback into the campaign settlement wallet. The
        founder vault opens once the settlement balance reaches the founder tier of {FOUNDER_TIER} credits.
        Only a handful of FOUNDER40 uses remain, so the remaining budget is far below that tier.</p>
        <h3>Recent redemptions</h3><ul class="list">{recent}</ul>
        <p class="note">Redemptions are serialized by the fraud-service check before the credit settles.</p></div>''',
    )


@app.get("/coupons")
def coupons_page():
    with LOG_LOCK:
        used = len(REDEEM_LOG)
    return shell(
        "Redeem a coupon",
        f'''<div class="panel"><h2>FOUNDER40</h2>
        <p class="mono">Cashback {COUPON_PRICE} credits · {COUPON["uses_left"]} uses left</p>
        <form method="post" action="/api/coupons/redeem"><label>Coupon code</label>
        <input name="code" value="FOUNDER40"><p><button type="submit">Redeem coupon</button></p></form>
        <h3>Campaign API</h3>
        <p class="mono">POST /api/coupons/redeem {"{code}"} · GET /api/coupons/status</p>
        <p>Redemptions settled so far: {used}.</p></div>''',
    )


@app.get("/api/coupons/status")
def status():
    return {"code": COUPON["code"], "uses_left": COUPON["uses_left"], "value": COUPON_PRICE, "balance": BALANCE}


@app.post("/api/coupons/redeem")
def redeem():
    global BALANCE
    payload = request.get_json(silent=True) or {}
    code = (request.form.get("code") or payload.get("code") or "").strip().upper()
    if code != COUPON["code"]:
        return {"ok": False, "error": "unknown coupon"}, 400
    # VULNERABLE: check-then-act on the shared campaign counter, no atomic decrement.
    if COUPON["uses_left"] <= 0:
        return {"ok": False, "error": "coupon exhausted"}, 409
    # The fraud service "verifies" the redemption before the credit settles.
    time.sleep(0.05)
    COUPON["uses_left"] -= 1
    BALANCE += COUPON_PRICE
    with LOG_LOCK:
        REDEEM_LOG.insert(0, f"FOUNDER40 settled {COUPON_PRICE} credits (settlement balance {BALANCE})")
    return {"ok": True, "credited": COUPON_PRICE, "balance": BALANCE, "uses_left": COUPON["uses_left"]}


@app.get("/vault")
def vault():
    if BALANCE >= FOUNDER_TIER:
        lab.objective_async("flag", "coupon counter raced past its remaining-uses limit; founder tier reached")
        return shell(
            "Founder vault unlocked",
            f'''<div class="flash ok">Settlement balance {BALANCE} credits reached the founder tier.</div>
            <div class="panel"><h2>Founder vault</h2><pre>{lab.flag("flag")}</pre></div>''',
        )
    return shell(
        "Founder vault locked",
        f'''<div class="flash err">Settlement balance {BALANCE} credits. The founder vault opens at {FOUNDER_TIER}.</div>
        <p class="note">Remaining campaign budget: {COUPON["uses_left"]} uses.</p>''',
    )


if __name__ == "__main__":
    lab.run()