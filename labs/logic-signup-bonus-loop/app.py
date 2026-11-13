from __future__ import annotations

import html

from flask import request, session

from labkit import Lab

lab = Lab("KILN SIGNUP", accent="#f0a04b")
app = lab.app

SIGNUP_BONUS = 250
PASS_PRICE = 2000
START_BALANCE = 0


def wallet() -> int:
    if "balance" not in session:
        session["balance"] = START_BALANCE
    if "welcomed" not in session:
        session["welcomed"] = 0
    return int(session["balance"])


def shell(title: str, body: str) -> object:
    balance = wallet()
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">KILN // ONBOARDING</div><h1>{title}</h1>'
        f'<p>Account balance: <strong class="green">{balance} credits</strong></p></div>{body}',
        nav='<a href="/">Onboarding</a><a href="/api/welcome">Welcome API</a><a href="/store">Store</a>',
    )


@app.get("/")
def index():
    return shell(
        "Onboarding checklist",
        f'''<div class="panel"><h2>Welcome to Kiln</h2>
        <p>Every new account receives a one-time welcome bonus of {SIGNUP_BONUS} credits. The bonus is
        delivered by the onboarding API when the client calls <code>/api/welcome</code> once after signup.</p>
        <p class="mono">GET /api/welcome</p>
        <p>It is documented as "call once" because the client retries on a slow network. The backend
        treats every call as a fresh onboarding event.</p>
        <p><a class="btn" href="/api/welcome">Trigger onboarding</a></p></div>
        <div class="panel"><h2>Benefits</h2>
        <p>The artisan founder pass costs {PASS_PRICE} credits and cannot be bought with a single bonus.</p>
        <p><a class="btn-ghost btn" href="/store">Open store</a></p></div>''',
    )


@app.get("/api/welcome")
def welcome():
    # VULNERABLE: the signup bonus is granted on every call, not once per account.
    balance = wallet()
    balance += SIGNUP_BONUS
    session["balance"] = balance
    session["welcomed"] = int(session.get("welcomed", 0)) + 1
    return {"ok": True, "bonus": SIGNUP_BONUS, "balance": balance, "welcome_events": session["welcomed"]}


@app.get("/store")
def store():
    balance = wallet()
    return shell(
        "Artisan store",
        f'''<div class="panel"><h2>Artisan founder pass</h2>
        <p class="mono">{PASS_PRICE} credits</p>
        <p>Unlocks the founder locker holding the vendor onboarding credential.</p>
        <form method="post" action="/store/buy"><input type="hidden" name="item" value="founder-pass">
        <p><button type="submit">Buy founder pass</button></p></form>
        <p class="note">Available balance: {balance} credits.</p></div>''',
    )


@app.post("/store/buy")
def buy():
    item = (request.form.get("item") or "").strip()
    balance = wallet()
    if item != "founder-pass":
        return shell("Unknown item", '<div class="flash err">That item is not in the catalog.</div>')
    if balance < PASS_PRICE:
        return shell(
            "Declined",
            f'<div class="flash err">Insufficient credits: the pass costs {PASS_PRICE}, you have {balance}.</div>',
        )
    session["balance"] = balance - PASS_PRICE
    lab.objective_async("flag", "signup bonus claimed repeatedly for the same account")
    return shell(
        "Founder locker",
        f'''<div class="flash ok">Founder pass issued. Balance: {session["balance"]} credits.</div>
        <div class="panel"><h2>Founder locker</h2><pre>{lab.flag("flag")}</pre></div>''',
    )


@app.get("/orders")
def orders():
    return shell(
        "Orders",
        f'''<div class="panel"><h2>Onboarding events</h2><p>{html.escape(str(session.get("welcomed", 0)))} welcome events recorded.</p></div>''',
    )


if __name__ == "__main__":
    lab.run()