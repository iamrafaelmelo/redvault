from __future__ import annotations

import html

from flask import request

from labkit import Lab

lab = Lab("HELPDESK NIGHTFALL", accent="#e6a04c")
app = lab.app

TICKETS: list[dict[str, str]] = [
    {"subject": "Welcome", "message": "The night desk reviews every support ticket before the morning shift."}
]
CAPTURED: list[str] = []


def shell(title: str, body: str, nav: str | None = None) -> object:
    if nav is None:
        nav = '<a href="/">Support</a><a href="/admin/tickets">Admin tickets</a><a href="/report">Bot preview</a><a href="/captured">Captured data</a>'
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">NIGHTFALL // SUPPORT DESK</div><h1>{title}</h1></div>{body}',
        nav=nav,
    )


@app.route("/", methods=["GET", "POST"])
@app.route("/tickets", methods=["GET", "POST"])
def tickets():
    notice = ""
    if request.method == "POST":
        subject = request.form.get("subject", "").strip()[:120] or "Support request"
        message = request.form.get("message", "").strip()[:4000]
        if message:
            # VULNERABLE: ticket content is stored exactly as submitted.
            TICKETS.append({"subject": subject, "message": message})
            notice = '<div class="flash ok">Ticket received. The night desk will review it shortly.</div>'
        else:
            notice = '<div class="flash err">A message is required.</div>'
    recent = "".join(f'<li>{html.escape(ticket["subject"])} <span class="dim">· queued</span></li>' for ticket in reversed(TICKETS[-5:]))
    return shell(
        "Night desk support",
        f"""<div class="panel"><h2>Open a ticket</h2>
        <form method="post" action="/">
          <label>Subject</label><input name="subject" placeholder="Checkout problem">
          <label>Message</label><textarea name="message" rows="4" placeholder="Describe the issue"></textarea>
          <p><button type="submit">Submit ticket</button></p>
        </form>{notice}
        <p class="note">The night desk bot reviews the admin queue with its readable session cookie.</p></div>
        <div class="panel"><h2>Recent queue</h2><ul class="list">{recent}</ul></div>""",
    )


@app.get("/admin/tickets")
def admin_tickets():
    # The internal queue is mounted on the same origin and does not repeat the
    # administrative check; the bot's cookie is what makes the review privileged.
    rendered = "".join(
        f'<div class="panel"><h3>{ticket["subject"]}</h3><p>{ticket["message"]}</p><span class="tag">TICKET</span></div>'
        for ticket in reversed(TICKETS)
    )
    return shell(
        "Night desk queue",
        f'<div class="flash ok">Internal review queue · newest first</div>{rendered}',
    )


@app.route("/report", methods=["GET", "POST"])
def report():
    message = ""
    if request.method == "POST":
        result = lab.bot(
            "/admin/tickets",
            cookies=[{"name": "admin_session", "value": lab.flag("flag")}],
            wait=2.0,
        )
        message = f'<div class="flash {"ok" if result.get("ok") else "err"}">Bot visit: {result.get("ok") and "completed" or result.get("error", "failed")}</div>'
    return shell(
        "Night desk bot",
        f"""<div class="panel"><h2>Trigger a review</h2>
        <p>The night desk bot opens <code>/admin/tickets</code> with a readable <code>admin_session</code> cookie. Any stored markup runs in that browser.</p>
        <form method="post"><button type="submit">Send night desk bot</button></form>{message}
        <p class="note">The collector records exfiltrated values at <code>/collect</code>.</p></div>""",
    )


@app.route("/collect", methods=["GET", "POST"])
def collect():
    value = request.args.get("c", "") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
        if lab.flag("flag") in value:
            lab.objective_async("flag", "admin cookie exfiltrated from the ticket queue")
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(f'<li><code>{html.escape(value)}</code></li>' for value in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'
    return shell("Captured data", f'<div class="panel"><h2>Exfiltration collector</h2><ul class="list">{rows}</ul></div>')


if __name__ == "__main__":
    lab.run()
