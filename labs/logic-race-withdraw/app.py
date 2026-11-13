from __future__ import annotations

import threading
import time

from flask import redirect, request

from labkit import Lab

lab = Lab("PACE BANK", accent="#2a9d8f")
app = lab.app

BALANCE = 1000
LEDGER: list[str] = []
LOCK = threading.Lock()  # only protects the ledger list, not the balance check


def layout(title: str, body: str) -> object:
    return lab.page(title, f'<div class="hero"><div class="kicker">PACE // TREASURY</div><h1>{title}</h1></div>{body}', nav='<a href="/">Account</a><a href="/vault">Vault</a>')


@app.get("/")
def index():
    with LOCK:
        entries = list(LEDGER)
    rows = "".join(f"<li>{entry}</li>" for entry in entries) or "<li>No withdrawals this session.</li>"
    return layout(
        "Treasury account",
        f'''<div class="panel"><h2>Available balance: ${BALANCE}.00</h2>
        <p>The Vault is a separate settlement account reserved for premium operators. It opens only if the treasury balance goes negative — a condition the risk engine says is impossible.</p>
        <form method="post" action="/withdraw"><label>Withdrawal amount</label><input name="amount" value="1000" type="number">
        <p><button type="submit">Request withdrawal</button></p></form>
        <h2>Ledger</h2><ul class="list">{rows}</ul>
        <p class="note">The balance check and deduction are separated by a delay while the risk service is consulted.</p></div>''',
    )


@app.post("/withdraw")
def withdraw():
    global BALANCE
    try:
        amount = int(request.form.get("amount", "0"))
    except ValueError:
        return layout("Invalid request", '<div class="flash err">Amount must be an integer.</div>')
    if amount <= 0:
        return layout("Invalid request", '<div class="flash err">Amount must be positive.</div>')
    if amount > BALANCE:
        return layout("Declined", f'<div class="flash err">Insufficient funds. Available: ${BALANCE}.00.</div>')
    # VULNERABLE: check-then-act race window. The risk check is asynchronous.
    time.sleep(0.35)
    BALANCE -= amount
    with LOCK:
        LEDGER.insert(0, f"-${amount}.00 approved")
    return layout(
        "Withdrawal approved",
        f'<div class="flash ok">${amount}.00 released. Remaining balance: ${BALANCE}.00.</div><p><a href="/">Back to account</a></p>',
    )


@app.get("/vault")
def vault():
    if BALANCE < 0:
        lab.objective_async("flag", "balance went negative through concurrent withdrawal processing")
        return layout(
            "Premium vault unlocked",
            f'<div class="flash ok">Balance ${BALANCE}.00 is negative. Risk invariant broken.</div><div class="panel"><h2>Vault access</h2><pre>{lab.flag("flag")}</pre></div>',
        )
    return layout("Vault locked", f'<div class="flash err">Balance is ${BALANCE}.00. Premium access requires a negative treasury balance.</div>')


if __name__ == "__main__":
    lab.run()
