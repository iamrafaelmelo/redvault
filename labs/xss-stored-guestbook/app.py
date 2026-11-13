from __future__ import annotations

from flask import request

from labkit import Lab

lab = Lab("FIELDBOOK", accent="#e6b450")
app = lab.app

ENTRIES: list[str] = ["The first rule of fieldwork is to write it down."]
CAPTURED: list[str] = []


def shell(title: str, body: str) -> object:
    return lab.page(title, f'<div class="hero"><div class="kicker">FIELDBOOK // SHARED NOTES</div><h1>{title}</h1></div>{body}', nav='<a href="/">Guestbook</a><a href="/report">Bot preview</a><a href="/captured">Captured data</a>')


@app.route("/", methods=["GET", "POST"])
def guestbook():
    notice = ""
    if request.method == "POST":
        message = request.form.get("message", "").strip()[:1000]
        if message:
            # VULNERABLE: stored without sanitization and rendered as raw HTML.
            ENTRIES.append(message)
            notice = '<div class="flash ok">Entry stored. It will be reviewed by the field editor.</div>'
    notes = "".join(f'<div class="panel"><p>{entry}</p><span class="tag">FIELD ENTRY</span></div>' for entry in reversed(ENTRIES))
    return shell(
        "Field guestbook",
        f"""<div class="panel"><h2>Leave an observation</h2><form method="post">
        <label>Entry</label><textarea name="message" rows="4" placeholder="A note for the field team"></textarea>
        <p><button type="submit">Store entry</button></p></form>{notice}</div>
        <h2>Recent entries</h2>{notes}
        <p class="note">The field editor bot reviews all entries with an administrative cookie.</p>""",
    )


@app.route("/report", methods=["GET", "POST"])
def report():
    notice = ""
    if request.method == "POST":
        result = lab.bot("/", cookies=[{"name": "editor_session", "value": lab.flag("flag")}], wait=2.0)
        notice = f'<div class="flash {"ok" if result.get("ok") else "err"}">Bot visit: {result.get("ok") and "completed" or result.get("error", "failed")}</div>'
    return shell(
        "Editor bot",
        f'<div class="panel"><h2>Review queue</h2><p>The editor visits the guestbook with a readable privileged cookie. Trigger a review after storing your payload.</p><form method="post"><button type="submit">Send editor bot</button></form>{notice}</div>',
    )


@app.route("/collect")
def collect():
    value = request.args.get("c", "") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
        if lab.flag("flag") in value:
            lab.objective_async("flag", "editor cookie exfiltrated through stored XSS")
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(f"<li><code>{value}</code></li>" for value in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'
    return shell("Captured data", f'<div class="panel"><h2>Exfiltration collector</h2><ul class="list">{rows}</ul></div>')


if __name__ == "__main__":
    lab.run()
