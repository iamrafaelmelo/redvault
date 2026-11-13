from __future__ import annotations

import html
import secrets
from typing import Any
from urllib.parse import parse_qs, parse_qsl, urlsplit

from flask import make_response, redirect, request

from labkit import Lab

lab = Lab("CLEARING CORP", accent="#22d3a6")
app = lab.app

USERS: dict[str, dict[str, object]] = {
    "devon": {"password": "devon-treasury-2026", "role": "treasury", "balance": 1250.00},
    "finance-admin": {"password": "unset-service-account", "role": "admin", "balance": 98000.00},
}
SESSIONS: dict[str, str] = {}
LEDGER: list[dict[str, object]] = [
    {"id": 1, "guard": "devon", "role": "treasury", "action": "INBOUND", "amount": 1250.00, "memo": "Wire · Northwind Ltd"},
    {"id": 2, "guard": "finance-admin", "role": "admin", "action": "INBOUND", "amount": 78400.00, "memo": "Settlement · escrow release"},
]

ALLOWED_ROLES = {"treasury", "analyst"}

# Parameters that the WAF refuses when they appear more than once.
GUARDED = {"amount", "action", "from", "to", "role", "account"}


def shell(title: str, body: str, nav: str | None = None) -> object:
    if nav is None:
        nav = (
            '<a href="/">Console</a><a href="/ledger">Ledger</a><a href="/logout">Sign out</a>'
            if current_user()
            else '<a href="/">Sign in</a>'
        )
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">CLEARING CORP // TREASURY OPS</div><h1>{title}</h1></div>{body}',
        nav=nav,
    )


def current_user() -> str | None:
    return SESSIONS.get(request.cookies.get("cc_session", ""))


def ledger_rows(guard: str) -> str:
    rows = "".join(
        f"<tr><td>#{e['id']}</td><td>{html.escape(str(e['guard']))}</td><td>{html.escape(str(e['action']))}</td>"
        f"<td class='mono'>{e['amount']:,.2f}</td><td>{html.escape(str(e['memo']))}</td></tr>"
        for e in LEDGER
        if e["guard"] == guard
    )
    return rows or '<tr><td colspan="5" class="dim">No entries.</td></tr>'


@app.get("/")
def index():
    user = current_user()
    if user:
        return redirect("/console")
    return shell(
        "Clearing Corp",
        """<div class="panel"><h2>Treasury sign-in</h2>
        <form method="post" action="/login">
          <label>Username</label><input name="username" autocomplete="username">
          <label>Password</label><input name="password" type="password" autocomplete="current-password">
          <p><button type="submit">Sign in</button></p></form>
        <p class="note">Demo account: <code>devon</code> / <code>devon-treasury-2026</code>.</p></div>""",
    )


@app.post("/login")
def login():
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    user = USERS.get(username)
    if user and user["password"] == password:
        handle = secrets.token_urlsafe(18)
        SESSIONS[handle] = username
        resp = make_response(redirect("/console"))
        resp.set_cookie("cc_session", handle, httponly=True, samesite="Lax")
        return resp
    return shell("Sign-in failed", '<div class="flash err">Invalid credentials.</div>')


@app.get("/console")
def console():
    user = current_user()
    if not user:
        return redirect("/")
    data = USERS[user]
    role_line = ""
    if data["role"] == "admin":
        lab.objective_async("flag", "parameter pollution promoted the treasury account to admin")
        role_line = f'<div class="panel"><h2>Admin tools</h2><pre>{html.escape(lab.flag("flag"))}</pre></div>'
    return shell(
        "Treasury console",
        f"""<div class="panel"><h2>{html.escape(user)}</h2>
        <table><tr><th>Role</th><td>{html.escape(str(data["role"]))}</td></tr>
        <tr><th>Available balance</th><td class="mono">{float(data["balance"]):,.2f} USD</td></tr></table>{role_line}</div>
        <div class="grid">
          <div class="panel"><h2>Move funds</h2>
            <form method="post" action="/transfer">
              <label>Source account</label><input name="from" value="checking-4401">
              <label>Destination account</label><input name="to" value="savings-9902">
              <label>Amount</label><input name="amount" value="100.00">
              <input type="hidden" name="action" value="transfer">
              <p><button type="submit">Authorise transfer</button></p>
            </form></div>
          <div class="panel"><h2>Request role change</h2>
            <form method="post" action="/role">
              <label>Role</label><select name="role"><option>treasury</option><option>analyst</option></select>
              <p><button type="submit">Submit for approval</button></p>
            </form>
            <p class="note">Role changes are applied to your profile immediately once the compliance guard passes.</p></div>
        </div>""",
    )


@app.get("/ledger")
def ledger():
    user = current_user()
    if not user:
        return redirect("/")
    return shell(
        "Ledger",
        f"""<div class="panel"><h2>Your entries</h2>
        <table><tr><th>ID</th><th>Account</th><th>Type</th><th>Amount</th><th>Memo</th></tr>
        {ledger_rows(user)}</table></div>""",
    )


def _canonical_path(raw_url: str) -> str:
    """Normalise a raw query string (with or without a leading path) for comparison."""
    raw = raw_url[1:] if raw_url.startswith("?") else raw_url
    if raw.startswith("/"):
        raw = urlsplit(raw).query
    pairs = parse_qsl(raw, keep_blank_values=True)
    return "&".join(f"{k}={v}" for k, v in pairs)


def compliance_guard(raw_query: str, body: Any) -> str | None:
    """WAF-style check that mirrors the business logic. Returns a block reason."""
    canonical = _canonical_path(raw_query)
    seen: dict[str, int] = {}
    for key in parse_qs(canonical, keep_blank_values=True):
        seen[key] = seen.get(key, 0) + 1
    if hasattr(body, "getlist"):
        body_keys = {key: len(body.getlist(key)) for key in body.keys()}
    else:
        body_keys = {key: len(value) for key, value in body.items()}
    # VULNERABLE: the guard inspects the URL and the body separately. It never
    # considers the same name appearing once in the query and once in the body,
    # which is exactly how the business logic merges them.
    if canonical and (any(count > 1 for count in seen.values()) or len(seen) != len(parse_qsl(canonical, keep_blank_values=True))):
        return "duplicate parameter rejected: the query string repeats a parameter"
    if any(count > 1 for count in body_keys.values()):
        return "duplicate parameter rejected: the request body repeats a parameter"
    return None


def _last(values: dict[str, list[str]], name: str, default: str = "") -> str:
    got = values.get(name)
    return got[-1] if got else default


@app.route("/transfer", methods=["GET", "POST"])
def transfer():
    user = current_user()
    if not user:
        return redirect("/")

    raw_query = request.query_string.decode("latin-1")
    reason = compliance_guard(raw_query, request.form)
    if reason:
        return shell("Blocked by compliance guard", f'<div class="flash err">{html.escape(reason)}</div>')

    # VULNERABLE: the business logic folds query and body parameters together
    # and takes the last occurrence, while the guard only ever looked at the first.
    merged = {key: list(values) for key, values in request.args.to_dict(flat=False).items()}
    for key in request.form.keys():
        merged.setdefault(key, []).extend(request.form.getlist(key))

    action = _last(merged, "action", "role" if "role" in merged else "transfer")
    source = _last(merged, "from", "")
    target = _last(merged, "to", "")
    role = _last(merged, "role", "")
    account = _last(merged, "to", "") or _last(merged, "account", "")
    raw_amount = _last(merged, "amount", "0")
    try:
        amount = round(float(raw_amount), 2)
    except ValueError:
        return shell("Invalid amount", '<div class="flash err">The amount must be a number.</div>')

    if action == "role":
        # VULNERABLE: the guard only knows the first occurrence of `role`
        # ("treasury"), while the profile is written from the last one.
        USERS[user]["role"] = role or "treasury"
        return shell(
            "Role updated",
            f'<div class="flash ok">Profile updated: role is now <code>{html.escape(str(USERS[user]["role"]))}</code>.</div>'
            '<p><a class="btn" href="/console">Back to console</a></p>',
        )

    if action != "transfer":
        return shell("Rejected", '<div class="flash err">Unsupported action.</div>')
    if amount <= 0:
        return shell("Rejected", '<div class="flash err">The amount must be positive.</div>')
    if amount > float(USERS[user]["balance"]):
        return shell("Insufficient funds", '<div class="flash err">The transfer exceeds the available balance.</div>')
    destination = target or account
    if not destination:
        return shell("Rejected", '<div class="flash err">A destination account is required.</div>')

    USERS[user]["balance"] = float(USERS[user]["balance"]) - amount
    if destination in USERS:
        USERS[destination]["balance"] = float(USERS[destination]["balance"]) + amount
    LEDGER.insert(
        0,
        {
            "id": len(LEDGER) + 1,
            "guard": user,
            "role": USERS[user]["role"],
            "action": "OUTBOUND",
            "amount": amount,
            "memo": f"{source or 'checking'} → {destination}",
        },
    )
    return shell(
        "Transfer authorised",
        f'<div class="flash ok">Moved <span class="mono">{amount:,.2f}</span> from {html.escape(source or "checking")} '
        f'to {html.escape(destination)}.</div><p><a class="btn" href="/ledger">View ledger</a></p>',
    )


@app.route("/role", methods=["GET", "POST"])
def role_change():
    return transfer()


@app.get("/logout")
def logout():
    resp = make_response(redirect("/"))
    resp.delete_cookie("cc_session")
    return resp


if __name__ == "__main__":
    lab.run()