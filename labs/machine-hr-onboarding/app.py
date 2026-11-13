from __future__ import annotations

import html
import sqlite3
import subprocess
from pathlib import Path

from flask import redirect, request, session

from labkit import Lab

lab = Lab("ATLAS HR", accent="#e5a54b")
app = lab.app

ROOT_FILE = Path("/tmp/atlas-hr-root.txt")
ROOT_FILE.write_text(lab.flag("root") + "\n")
CONVERTED_DIR = lab.state_dir / "converted"
CONVERTED_DIR.mkdir(parents=True, exist_ok=True)

CANDIDATE_LOGIN = "nadia.okafor@atlas-people.example"
CANDIDATE_PASSWORD = "Atlas!Onboard26"

schema = """
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    public_id TEXT NOT NULL,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL,
    department TEXT NOT NULL,
    title TEXT NOT NULL,
    location TEXT NOT NULL,
    manager TEXT NOT NULL,
    start_date TEXT NOT NULL,
    salary INTEGER NOT NULL,
    contract TEXT NOT NULL
);
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password TEXT NOT NULL,
    role TEXT NOT NULL,
    employee_id INTEGER
);
CREATE TABLE documents (
    id INTEGER PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    classification TEXT NOT NULL
);
"""

employees = [
    (1, "emp-1041", "Priya Raman", "priya.raman@atlas-people.example", "Platform", "Staff Engineer",
     "Berlin", "Marcus Feld", "2021-03-15", 148000, "full-time"),
    (2, "emp-1088", "Marcus Feld", "marcus.feld@atlas-people.example", "Platform", "Engineering Manager",
     "Berlin", "Ana Duarte", "2019-08-01", 176000, "full-time"),
    (3, "emp-1123", "Elena Vargas", "elena.vargas@atlas-people.example", "Payroll", "Payroll Lead",
     "Lisbon", "Ana Duarte", "2020-01-20", 140400, "full-time"),
    (4, "emp-1177", "Tomo Ishida", "tomo.ishida@atlas-people.example", "Design", "Product Designer",
     "Kyoto", "Sofia Klein", "2022-06-06", 112000, "full-time"),
    (5, "emp-1204", "Sofia Klein", "sofia.klein@atlas-people.example", "Design", "Design Director",
     "Amsterdam", "Ana Duarte", "2018-11-12", 168500, "full-time"),
    (6, "emp-1260", "Owen Brady", "owen.brady@atlas-people.example", "Sales", "Account Executive",
     "Dublin", "Nadia Okafor", "2023-02-13", 96000, "full-time"),
    (7, "emp-1299", "Ana Duarte", "ana.duarte@atlas-people.example", "People", "Chief People Officer",
     "Lisbon", "Board", "2017-04-03", 210000, "full-time"),
    (8, "emp-1310", "Jules Moreau", "jules.moreau@atlas-people.example", "Finance", "Financial Controller",
     "Paris", "Ana Duarte", "2021-09-27", 132500, "contract"),
    (9, "emp-1355", "Hana Sato", "hana.sato@atlas-people.example", "Support", "Support Lead",
     "Osaka", "Priya Raman", "2022-10-17", 88500, "full-time"),
    (10, "emp-1402", "Nadia Okafor", "nadia.okafor@atlas-people.example", "Sales", "Sales Manager",
     "London", "Ana Duarte", "2026-11-02", 118000, "full-time"),
]

users = [
    (1, "nadia.okafor@atlas-people.example", CANDIDATE_PASSWORD, "candidate", 10),
    (2, "priya.raman@atlas-people.example", "pr-2026-rotate-me", "employee", 1),
    (3, "elena.vargas@atlas-people.example", "el-2026-rotate-me", "employee", 3),
    (4, "ana.duarte@atlas-people.example", "ad-2026-rotate-me", "hr_admin", 7),
    (5, "jules.moreau@atlas-people.example", "jm-2026-rotate-me", "employee", 8),
]

documents = [
    (1, 10, "offer", "Offer letter — Sales Manager",
     "Base salary GBP 118,000, quarterly bonus 12% target. Reports to Ana Duarte. Start date 2026-11-02.", "confidential"),
    (2, 10, "payslip", "October 2026 payslip",
     "Gross 12,300.00 GBP · Net 9,910.42 GBP · Tax code 1257L · Pension 2%.", "confidential"),
    (3, 10, "onboarding", "Onboarding checklist — week 1",
     "Day 1: collect laptop at reception. Day 2: security training. Day 3: meet the sales pod. All steps signed off by People Ops.", "internal"),
    (4, 3, "payslip", "October 2026 payslip",
     "Gross 11,700.00 EUR · Net 8,411.33 EUR · Tax withholding automatic · Pension 3%.", "confidential"),
    (5, 1, "payslip", "October 2026 payslip",
     "Gross 12,333.00 EUR · Net 8,901.72 EUR · Pension 3% · ESPP 2%.", "confidential"),
    (6, 7, "payslip", "October 2026 payslip",
     "Gross 17,500.00 EUR · Net 12,180.55 EUR · Executive pension 5%.", "confidential"),
    (7, 7, "offer", "Offer letter — Chief People Officer",
     "Base salary EUR 210,000, LTI grant 0.4%. Start date 2017-04-03.", "confidential"),
    (8, 2, "payslip", "October 2026 payslip",
     "Gross 14,666.00 EUR · Net 10,204.88 EUR · Pension 3%.", "confidential"),
    (9, 5, "review", "2026 mid-year review",
     "Exceeds expectations. Promotion recommendation pending band review.", "confidential"),
    (10, 8, "payslip", "October 2026 payslip",
     "Gross 11,041.00 EUR · Net 7,822.10 EUR · Contractor status: no pension.", "confidential"),
    (11, 4, "offer", "Offer letter — Product Designer",
     "Base salary JPY 14,800,000, relocation budget JPY 1,200,000.", "confidential"),
    (12, 6, "review", "2026 mid-year review",
     "On track. Pipeline for Q4 covered; coaching set for discovery calls.", "confidential"),
    (13, 9, "payslip", "October 2026 payslip",
     "Gross JPY 1,180,000 · Net JPY 907,540 · Commuting allowance included.", "confidential"),
]

seed = [f"INSERT INTO employees VALUES {row};" for row in employees]
seed += [f"INSERT INTO users VALUES {row};" for row in users]
seed += [f"INSERT INTO documents VALUES {row};" for row in documents]
lab.init_db("atlas.db", schema, seed)


def b64_script(source: str) -> str:
    import base64

    return base64.b64encode(source.encode()).decode()


CONVERTER_SCRIPT = "import sys;print('atlas-hr converter 3.2');print('input:', sys.argv[1] if len(sys.argv) > 1 else '(none)');print('profile: pdf/lossless, no fonts embedded')"


def db():
    return lab.db("atlas.db")


def current_user():
    email = session.get("email")
    if not email:
        return None
    conn = db()
    try:
        row = conn.execute(
            "SELECT u.id, u.email, u.role, u.employee_id, e.full_name, e.department, e.title "
            "FROM users u LEFT JOIN employees e ON e.id = u.employee_id WHERE u.email = ?",
            (email,),
        ).fetchone()
    finally:
        conn.close()
    return dict(row) if row else None


def shell(title: str, body: str, status: int = 200) -> object:
    user = current_user()
    if user:
        nav = '<a href="/dashboard">Dashboard</a><a href="/profile">My profile</a>'
        if user["role"] == "hr_admin":
            nav += '<a href="/admin/employees">Employee export</a><a href="/admin/converter">Converter</a>'
        nav += '<a href="/logout">Log out</a>'
    else:
        nav = '<a href="/">Sign in</a><a href="/careers">Careers</a>'
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">ATLAS HR // PEOPLE OPERATIONS</div><h1>{title}</h1>'
        "<p>Onboarding, employee records and payroll for Atlas People GmbH.</p></div>" + body,
        nav=nav,
        status=status,
    )


@app.get("/")
def index():
    if current_user():
        return redirect("/dashboard")
    return shell(
        "Welcome to Atlas People",
        f"""<div class="panel"><h2>New hire sign-in</h2>
        <p>Your onboarding pack contains a temporary account. Use the email in your welcome
        message with the password issued by People Operations.</p>
        <form method="post" action="/login">
          <label>Work email</label><input name="username" autocomplete="username">
          <label>Password</label><input name="password" type="password" autocomplete="current-password">
          <p><button type="submit">Sign in</button></p>
        </form>
        <p class="note">Onboarding files shared by People Ops: <a href="/share/">onshape share</a>.
        Welcome messages are sent from <code>onboarding@atlas-people.example</code>.</p></div>""",
    )


@app.get("/robots.txt")
def robots():
    return lab.app.response_class(
        "# atlas-people employee portal\nUser-agent: *\nDisallow: /admin/\nDisallow: /share/\nDisallow: /documents/\n",
        mimetype="text/plain",
    )


@app.post("/login")
def login():
    username = request.form.get("username", "").strip().lower()
    password = request.form.get("password", "")
    conn = db()
    try:
        row = conn.execute("SELECT email, password FROM users WHERE email = ?", (username,)).fetchone()
    finally:
        conn.close()
    if row and row["password"] == password:
        session.clear()
        session["email"] = row["email"]
        return redirect("/dashboard")
    return shell("Sign-in failed", '<div class="flash err">Invalid email or password.</div><p><a href="/">Try again</a></p>')


@app.get("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.get("/share/")
def share_index():
    # Public share for onboarding packs. The listing is meant to be link-only, but
    # nothing stops a search engine or a new hire from listing it.
    return shell(
        "People Ops · shared files",
        """<div class="panel"><h2>Onshape share · onboarding 2026</h2>
        <p>Shared with new hires during their first week. Files are read-only and expire at the end of the quarter.</p>
        <ul class="list">
          <li><a href="/share/atlas-onboarding-retail-2026.txt">atlas-onboarding-retail-2026.txt</a> <span class="dim">· welcome pack</span></li>
          <li><a href="/share/atlas-benefits-overview-2026.pdf">atlas-benefits-overview-2026.pdf</a> <span class="dim">· benefits</span></li>
          <li><a href="/share/it-equipment-policy.txt">it-equipment-policy.txt</a> <span class="dim">· IT</span></li>
        </ul>
        <p class="note">Uploaded by onboarding@atlas-people.example. Do not forward outside the company.</p></div>""",
    )


@app.get("/share/atlas-onboarding-retail-2026.txt")
def share_onboarding():
    body = (
        "Atlas People — new hire onboarding pack (retail cohort, Nov 2026)\n"
        "===============================================================\n\n"
        "Welcome aboard! This pack is pre-configured for the London sales team.\n\n"
        "1. Activate your account on the employee portal.\n"
        "   <b>login:</b> " + CANDIDATE_LOGIN + "\n"
        "   <b>password:</b> " + CANDIDATE_PASSWORD + "\n"
        "2. Complete the security awareness module in week 1.\n"
        "3. Your buddy is Owen Brady (owen.brady@atlas-people.example).\n\n"
        "Questions? onboarding@atlas-people.example\n"
    )
    return lab.app.response_class(body, mimetype="text/plain")


@app.get("/share/atlas-benefits-overview-2026.pdf")
def share_benefits():
    return "Benefits overview 2026. This is now managed in the employee portal.", 404


@app.get("/share/it-equipment-policy.txt")
def share_it_policy():
    return lab.app.response_class(
        "IT equipment policy\nLaptop refresh every 3 years. Report loss to it@atlas-people.example.\n",
        mimetype="text/plain",
    )


@app.get("/careers")
def careers():
    return shell(
        "Careers at Atlas",
        """<div class="panel"><h2>Open roles</h2>
        <ul class="list"><li>Staff Engineer · Platform · Berlin</li><li>Account Executive · Sales · Dublin</li>
        <li>Support Lead · Osaka</li></ul>
        <p class="note">Internal transfers use the employee portal.</p></div>""",
    )


@app.get("/dashboard")
def dashboard():
    user = current_user()
    if not user:
        return redirect("/")
    conn = db()
    try:
        docs = conn.execute(
            "SELECT id, kind, title, classification FROM documents WHERE employee_id = ? ORDER BY id",
            (user["employee_id"],),
        ).fetchall()
    finally:
        conn.close()
    doc_html = "".join(
        f'<li><a href="/documents/{row["kind"]}/{row["id"]}">{html.escape(row["title"])}</a> '
        f'<span class="tag">{html.escape(row["classification"])}</span></li>'
        for row in docs
    )
    user_flag = ""
    if user["role"] == "candidate":
        user_flag = (
            f'<div class="panel"><h2>Onboarding access confirmed</h2><pre>{lab.flag("user")}</pre>'
            "<p>Your personal documents are visible below. Payroll continues after your first month.</p></div>"
        )
    api_flag = ""
    if user["role"] == "hr_admin":
        api_flag = (
            f'<div class="panel"><h2>HR administration unlocked</h2><pre>{lab.flag("api")}</pre>'
            '<p>Employee records export: <a href="/admin/employees">/admin/employees</a> · '
            'Document converter: <a href="/admin/converter">/admin/converter</a></p></div>'
        )
    return shell(
        f"Dashboard · {user['full_name']}",
        f'<div class="panel"><h2>Welcome, {html.escape((user["full_name"] or "").split(" ")[0])}</h2>'
        f'<p>{html.escape(user["title"] or "")} · {html.escape(user["department"] or "")} · '
        f'role <code>{html.escape(user["role"])}</code></p>'
        '<p><a href="/profile">Update your details</a></p></div>'
        + user_flag
        + api_flag
        + f'<div class="panel"><h2>My documents</h2><ul class="list">{doc_html or "<li class=\'dim\'>No documents yet.</li>"}</ul></div>',
    )


@app.route("/profile", methods=["GET", "POST"])
def profile():
    user = current_user()
    if not user:
        return redirect("/")
    message = ""
    if request.method == "POST":
        conn = db()
        try:
            # VULNERABLE: the update binds every profile field, including role,
            # from the request body without an allow-list.
            for field in ("full_name", "department", "title", "role"):
                value = request.form.get(field)
                if value is None:
                    continue
                if field == "role":
                    conn.execute("UPDATE users SET role = ? WHERE email = ?", (value, user["email"]))
                    session["role"] = value
                else:
                    conn.execute(f"UPDATE employees SET {field} = ? WHERE id = ?", (value, user["employee_id"]))
            conn.commit()
        finally:
            conn.close()
        message = '<div class="flash ok">Profile updated.</div>'
    return shell(
        "My profile",
        f"""<div class="panel"><h2>Profile</h2>{message}
        <form method="post">
          <label>Full name</label><input name="full_name" value="{html.escape(user['full_name'] or '')}">
          <label>Department</label><input name="department" value="{html.escape(user['department'] or '')}">
          <label>Title</label><input name="title" value="{html.escape(user['title'] or '')}">
          <p><button type="submit">Save profile</button></p>
        </form>
        <p class="note">Directory sync copies these fields into the intranet every night. Role is managed by People Ops.</p></div>""",
    )


@app.get("/documents/<kind>/<int:doc_id>")
def document(kind: str, doc_id: int):
    user = current_user()
    if not user:
        return redirect("/")
    conn = db()
    try:
        row = conn.execute(
            "SELECT d.*, e.full_name, e.title FROM documents d JOIN employees e ON e.id = d.employee_id WHERE d.id = ?",
            (doc_id,),
        ).fetchone()
    finally:
        conn.close()
    if not row:
        return shell("Document not found", '<div class="flash err">No such document.</div>', status=404)
    # VULNERABLE: no ownership check. Any authenticated user can enumerate
    # documents by sequential id (IDOR).
    return shell(
        row["title"],
        f"""<div class="panel"><h2>{html.escape(row['title'])}</h2>
        <p class="dim mono">document {row['id']} · kind {html.escape(row['kind'])} · employee record {html.escape(row['full_name'])}</p>
        <pre>{html.escape(row['body'])}</pre></div>""",
        status=200,
    )


@app.get("/admin/employees")
def admin_employees():
    user = current_user()
    if not user:
        return redirect("/")
    if user["role"] != "hr_admin":
        return shell("Forbidden", '<div class="flash err">HR administrator role required.</div>', status=403)
    conn = db()
    try:
        rows = conn.execute("SELECT * FROM employees ORDER BY id").fetchall()
    finally:
        conn.close()
    table = "".join(
        f"<tr><td class='mono'>{html.escape(r['public_id'])}</td><td>{html.escape(r['full_name'])}</td>"
        f"<td>{html.escape(r['department'])}</td><td>{html.escape(r['location'])}</td>"
        f"<td>${r['salary']:,}</td><td>{html.escape(r['contract'])}</td></tr>"
        for r in rows
    )
    return shell(
        "Employee export",
        f"""<div class="panel"><h2>Roster · {len(rows)} employees</h2>
        <table><tr><th>ID</th><th>Name</th><th>Dept</th><th>Location</th><th>Salary</th><th>Contract</th></tr>{table}</table></div>
        <div class="panel"><h2>CSV export</h2><p><code>GET /admin/employees.csv</code></p></div>""",
    )


@app.get("/admin/employees.csv")
def admin_employees_csv():
    user = current_user()
    if not user or user["role"] != "hr_admin":
        return lab.app.response_class("forbidden\n", status=403, mimetype="text/plain")
    conn = db()
    try:
        rows = conn.execute("SELECT * FROM employees ORDER BY id").fetchall()
    finally:
        conn.close()
    lines = ["public_id,name,email,department,title,location,salary"]
    lines += [f"{r['public_id']},{r['full_name']},{r['email']},{r['department']},{r['title']},{r['location']},{r['salary']}" for r in rows]
    return lab.app.response_class("\n".join(lines) + "\n", mimetype="text/csv")


@app.route("/admin/converter", methods=["GET", "POST"])
def admin_converter():
    user = current_user()
    if not user:
        return redirect("/")
    if user["role"] != "hr_admin":
        return shell("Forbidden", '<div class="flash err">HR administrator role required.</div>', status=403)
    output = ""
    if request.method == "POST":
        # Documented as `soffice --headless --convert-to pdf <file>`; the service
        # image pins the converter to this helper until the LibreOffice upgrade.
        file_arg = request.form.get("file", "")
        # VULNERABLE: the submitted filename is interpolated into a shell command.
        command = f"python3 -c 'import base64;exec(base64.b64decode(\"{b64_script(CONVERTER_SCRIPT)}\"))' {file_arg}"
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
            output = (result.stdout or "") + (result.stderr or "")
        except subprocess.TimeoutExpired:
            output = "conversion timed out"
        if lab.flag("root") in output:
            lab.objective_async("root", "converter command injection read the HR root file")
    listing = "".join(f"<li>{html.escape(p.name)}</li>" for p in sorted(CONVERTED_DIR.iterdir())) or '<li class="dim">No conversions yet.</li>'
    return shell(
        "Document converter",
        f"""<div class="panel"><h2>Convert an attachment</h2>
        <p>Uploaded onboarding attachments are stored in <code>attachments/</code>. Submit the stored
        filename to convert it to PDF.</p>
        <form method="post">
          <label>Stored filename</label><input name="file" value="onboarding.pdf">
          <p><button type="submit">Convert to PDF</button></p>
        </form>
        <p class="note">The converter runs <code>soffice --headless --convert-to pdf</code> as the
        <code>atlas-hr</code> service account.</p>
        {f'<div class="panel"><h2>Converter output</h2><pre>{output}</pre></div>' if output else ''}</div>
        <div class="panel"><h2>Converted files</h2><ul class="list">{listing}</ul></div>""",
    )


if __name__ == "__main__":
    lab.run()