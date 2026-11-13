from __future__ import annotations

from pathlib import Path

from flask import render_template_string, request

from labkit import Lab

lab = Lab("GREETING CARD", accent="#f28f3b")
app = lab.app

Path("/tmp/redvault-ssti-flag.txt").write_text(lab.flag("flag") + "\n")


def shell(title: str, body: str) -> object:
    return lab.page(title, f'<div class="hero"><div class="kicker">GREETING CARD // CARD STUDIO</div><h1>{title}</h1></div>{body}', nav='<a href="/">Card studio</a>')


@app.route("/", methods=["GET", "POST"])
def index():
    name = request.form.get("name", "") if request.method == "POST" else "Operator"
    error = ""
    rendered = ""
    if request.method == "POST":
        try:
            # VULNERABLE: user input is compiled as a Jinja template.
            rendered = render_template_string(f'<div class="panel"><h2>Hello, {name}!</h2><p>Your field card is ready.</p></div>')
        except Exception as exc:
            error = f'<div class="flash err">Template error: {exc}</div>'
        if lab.flag("flag") in rendered:
            lab.objective_async("flag", "server-side template injection executed a shell command")
    return shell(
        "Card studio",
        f"""<div class="panel"><h2>Create a greeting</h2><p>The studio renders your name into a Jinja template.</p>
        <form method="post"><label>Recipient name</label><input name="name" value="{name}" size="60">
        <p><button type="submit">Render card</button></p></form>{error}</div>{rendered}
        <p class="note">The card is generated server-side. A normal name should not need template syntax.</p>""",
    )


if __name__ == "__main__":
    lab.run()
