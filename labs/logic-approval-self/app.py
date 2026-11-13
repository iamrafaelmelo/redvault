from __future__ import annotations

import html
import threading

from flask import request, session

from labkit import Lab

lab = Lab("LEDGER LANE PA", accent="#8b7df0")
app = lab.app

USERS = {
    "mara": {"password": "Mara!2026", "role": "requester", "expenses": []},
    "opfern": {"password": "Op!Desk2026", "role": "both", "expenses": []},
}
REQUESTS: list[dict] = []
LOCK = threading.Lock()
BUDGET = 500


def current_user() -> str | None:
    return session.get("user")


def shell(title: str, body: str) -> object:
    user = current_user()
    nav = '<a href="/">Home</a><a href="/login">Sign in</a>'
    if user:
        nav = f'<a href="/dashboard">Dashboard</a><a href="/requests">Requests</a><a href="/logout">Sign out ({html.escape(user)})</a>'
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">LEDGER LANE // PAYOUT DESK</div><h1>{title}</h1></div>{body}',
        nav=nav,
    )


@app.get("/")
def index():
    return shell(
        "Payout desk",
        '''<div class="panel"><h2>Expense reimbursement</h2>
        <p>Requesters file reimbursements. Approvers sign them off. Payouts above the petty-cash limit
        require two separate officers: whoever files the request and whoever signs it. The approval
        endpoint checks the approver role before it releases the voucher.</p>
        <p class="mono">opfern / Op!Desk2026 — treasury officer (requester + approver duties)</p>
        <p><a class="btn" href="/login">Sign in</a></p></div>''',
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = (request.form.get("username") or "").strip().lower()
        password = request.form.get("password") or ""
        account = USERS.get(username)
        if account and account["password"] == password:
            session.clear()
            session["user"] = username
            return lab.redirect("/dashboard")
        error = '<div class="flash err">Invalid credentials.</div>'
    return shell(
        "Sign in",
        f'''{error}<div class="panel"><form method="post" action="/login">
        <label>Username</label><input name="username">
        <label>Password</label><input name="password" type="password">
        <p><button type="submit">Sign in</button></p></form></div>''',
    )


@app.get("/logout")
def logout():
    session.clear()
    return lab.redirect("/")


@app.get("/dashboard")
def dashboard():
    user = current_user()
    if not user:
        return lab.redirect("/login")
    account = USERS[user]
    mine = [r for r in REQUESTS if r["requester"] == user]
    rows = "".join(
        f'<tr><td>#{r["id"]}</td><td>{html.escape(r["title"])}</td><td>{r["amount"]:.2f}</td>'
        f'<td>{html.escape(r["status"])}</td><td>{html.escape(r["approved_by"] or "—")}</td></tr>'
        for r in mine
    ) or '<tr><td colspan="5" class="dim">No requests yet.</td></tr>'
    form = ""
    if account["role"] in ("requester", "both"):
        form = '''<div class="panel"><h2>New reimbursement</h2><form method="post" action="/requests">
        <label>Title</label><input name="title" value="Client dinner">
        <label>Amount</label><input name="amount" value="420">
        <p><button type="submit">File request</button></p></form></div>'''
    else:
        form = '<div class="panel"><h2>Approver console</h2><p>Open <a href="/requests">the request queue</a> to review pending reimbursements.</p></div>'
    if account["role"] == "both":
        form += '<div class="panel"><h2>Officer notice</h2><p>You hold requester and approver duties. Company policy requires a second officer to sign off your own filings.</p></div>'
    return shell(
        f"{user}'s dashboard",
        f'''<div class="panel"><h2>Role: {html.escape(account["role"])}</h2>
        <p>Department petty-cash budget left: {BUDGET} credits.</p></div>
        {form}
        <div class="panel"><h2>My requests</h2>
        <table><thead><tr><th>ID</th><th>Title</th><th>Amount</th><th>Status</th><th>Approved by</th></tr></thead><tbody>{rows}</tbody></table></div>''',
    )


@app.route("/requests", methods=["GET", "POST"])
def requests_view():
    user = current_user()
    if not user:
        return lab.redirect("/login")
    account = USERS[user]
    message = ""
    if request.method == "POST":
        if account["role"] not in ("requester", "both"):
            return shell("Forbidden", '<div class="flash err">Requester role required to file reimbursements.</div>')
        try:
            amount = float(request.form.get("amount", "0"))
        except ValueError:
            amount = 0.0
        title = (request.form.get("title") or "Reimbursement").strip()[:80]
        if amount <= 0:
            return shell("Invalid", '<div class="flash err">Amount must be positive.</div>')
        with LOCK:
            rid = len(REQUESTS) + 1
            REQUESTS.append({"id": rid, "requester": user, "title": title, "amount": amount, "status": "PENDING", "approved_by": ""})
        message = f'<div class="flash ok">Request #{rid} filed for {amount:.2f}.</div>'
    rows = "".join(
        f'''<tr><td>#{r["id"]}</td><td>{html.escape(r["requester"])}</td><td>{html.escape(r["title"])}</td>
        <td>{r["amount"]:.2f}</td><td>{html.escape(r["status"])}</td>
        <td>{"" if r["status"] != "PENDING" else f"""<form method="post" action="/requests/{r["id"]}/approve"><button class="btn-sm" type="submit">Approve</button></form>"""}</td></tr>'''
        for r in REQUESTS
    ) or '<tr><td colspan="6" class="dim">Queue is empty.</td></tr>'
    return shell(
        "Reimbursement queue",
        f'''{message}<div class="panel"><h2>Pending approvals</h2>
        <table><thead><tr><th>ID</th><th>Requester</th><th>Title</th><th>Amount</th><th>Status</th><th></th></tr></thead><tbody>{rows}</tbody></table>
        <p class="note">Approvers sign off requests. Large reimbursements are released as a payout voucher.</p></div>''',
    )


@app.post("/requests/<int:rid>/approve")
def approve(rid: int):
    global BUDGET
    user = current_user()
    if not user:
        return lab.redirect("/login")
    account = USERS[user]
    if account["role"] not in ("approver", "both"):
        return shell("Forbidden", '<div class="flash err">Approver role required.</div>')
    target = next((r for r in REQUESTS if r["id"] == rid), None)
    if target is None:
        return shell("Not found", '<div class="flash err">No such request.</div>', )
    if target["status"] != "PENDING":
        return shell("Already processed", f'<div class="flash err">Request #{rid} is {html.escape(target["status"])}.</div>')
    # VULNERABLE: no check that the approver differs from the requester (segregation of duties).
    with LOCK:
        target["status"] = "APPROVED"
        target["approved_by"] = user
        BUDGET -= int(target["amount"])
        requester_wallet = USERS[target["requester"]]
        requester_wallet["expenses"].append(target)
    payout = (
        f'<div class="panel"><h2>Payout voucher</h2>'
        f'<p>Request #{rid} · {html.escape(target["title"])} · {target["amount"]:.2f} credits</p>'
        f'<p class="note">Released to {html.escape(target["requester"])} and approved by {html.escape(user)}.</p>'
    )
    if target["amount"] >= 400:
        lab.objective_async("flag", f"requester {target['requester']} approved their own reimbursement")
        payout += f'<h3>Large payout release token</h3><pre>{lab.flag("flag")}</pre>'
    payout += "</div>"
    return shell(f"Request #{rid} approved", payout)


if __name__ == "__main__":
    lab.run()