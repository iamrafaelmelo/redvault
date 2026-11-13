from __future__ import annotations

import secrets
from pathlib import Path

from flask import redirect, render_template_string, request, session

from labkit import Lab

lab = Lab("HARBOR CLAIMS", accent="#4fb3a5")
app = lab.app

Path("/tmp/insurance-root.txt").write_text(lab.flag("root") + "\n")

USERS = {
    "customer": {"password": "claim2026", "role": "customer", "display": "Elena Ruiz"},
    "adjuster": {"password": secrets.token_urlsafe(24), "role": "adjuster", "display": "Claims Desk"},
}
CLAIMS = [
    {"id": "CLM-8821", "type": "water damage", "amount": "$8,420", "status": "review"},
    {"id": "CLM-8822", "type": "storm damage", "amount": "$12,700", "status": "adjuster"},
]


def shell(title: str, body: str) -> object:
    nav = '<a href="/portal">Portal</a><a href="/logout">Logout</a>' if session.get("user") else '<a href="/">Sign in</a>'
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">HARBOR // CLAIMS OPERATIONS</div><h1>{title}</h1>'
        "<p>Property claims intake and adjustment for coastal policies.</p></div>" + body,
        nav=nav,
    )


@app.get("/")
def index():
    if session.get("user"):
        return redirect("/portal")
    return shell(
        "Claims sign-in",
        """<div class="panel"><h2>Policyholder access</h2>
        <form method="post" action="/login"><label>Username</label><input name="username">
        <label>Password</label><input name="password" type="password">
        <p><button type="submit">Sign in</button></p></form>
        <p class="note">Demo onboarding material is published for the claims migration.</p></div>""",
    )


@app.get("/static/onboarding.txt")
def onboarding():
    return lab.app.response_class(
        "Harbor claims migration\ncustomer= customer\npassword= claim2026\nrole= policyholder\n",
        mimetype="text/plain",
    )


@app.post("/login")
def login():
    username = request.form.get("username", "")
    record = USERS.get(username)
    if record and record["password"] == request.form.get("password", ""):
        session.clear()
        session["user"] = username
        session["role"] = record["role"]
        return redirect("/portal")
    return shell("Login failed", '<div class="flash err">Invalid policyholder credentials.</div><p><a href="/">Try again</a></p>')


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.get("/portal")
def portal():
    if not session.get("user"):
        return redirect("/")
    rows = "".join(
        f'<div class="panel"><h3>{claim["id"]} · {claim["type"]}</h3>'
        f'<p>Estimated loss: {claim["amount"]}</p><span class="tag">{claim["status"]}</span></div>'
        for claim in CLAIMS
    )
    role = session.get("role")
    extra = ""
    if role == "customer":
        extra = f'<div class="panel"><h2>Policyholder flag</h2><pre>{lab.flag("user")}</pre><p>Claims are visible to the policyholder who opened them.</p></div>'
    if role == "adjuster":
        extra = f'<div class="panel"><h2>Adjuster flag</h2><pre>{lab.flag("api")}</pre><p><a href="/adjuster">Open adjuster report desk</a></p></div>'
    return shell(
        f"Portal · {USERS[session['user']]['display']}",
        f'<div class="panel"><h2>Active claims</h2><p>Session role: <code>{role}</code></p></div>' + extra + rows,
    )


@app.post("/profile")
def profile():
    if not session.get("user"):
        return redirect("/")
    # VULNERABLE: mass assignment accepts a privileged role from the profile form.
    for field in ("display", "email", "role"):
        value = request.form.get(field)
        if value:
            if field == "role":
                session["role"] = value
            else:
                USERS[session["user"]][field] = value
    return redirect("/portal")


@app.get("/adjuster")
def adjuster():
    if session.get("role") != "adjuster":
        return shell("Forbidden", '<div class="flash err">Adjuster role required.</div>'), 403
    return shell(
        "Adjuster report desk",
        f"""<div class="panel"><h2>Adjuster console</h2>
        <p>Adjuster flag: <code>{lab.flag("api")}</code></p>
        <p>Generate a policyholder-facing report from an internal note. The report desk renders Jinja templates for legacy correspondence.</p>
        <form method="post" action="/adjuster/report"><label>Internal note</label>
        <textarea name="note" rows="4" placeholder="Claim review summary"></textarea>
        <p><button type="submit">Render report</button></p></form>
        <p class="note">The service account can read <code>/tmp/insurance-root.txt</code>.</p></div>""",
    )


@app.post("/adjuster/report")
def adjuster_report():
    if session.get("role") != "adjuster":
        return shell("Forbidden", '<div class="flash err">Adjuster role required.</div>'), 403
    note = request.form.get("note", "")
    error = ""
    rendered = ""
    try:
        # VULNERABLE: operator-supplied correspondence is compiled as a template.
        rendered = render_template_string(f'<div class="panel"><h2>Claim correspondence</h2><p>{note}</p></div>')
    except Exception as exc:  # noqa: BLE001 - surfaced as a template error
        error = f'<div class="flash err">Template error: {exc}</div>'
    if lab.flag("root") in rendered:
        lab.objective_async("root", "root flag read through adjuster template injection")
    return shell(
        "Rendered correspondence",
        error + (rendered or '<p class="dim">No report generated.</p>'),
    )


if __name__ == "__main__":
    lab.run()
