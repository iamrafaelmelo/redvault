from __future__ import annotations

import html
import secrets

from flask import request

from labkit import Lab

lab = Lab("NORTHBEAM API", accent="#a3e635")
app = lab.app

TOKENS: dict[str, dict] = {}
AUDIT: list[dict] = []

RECORDS = [
    {"id": "inv-1001", "customer": "Harbor Supply", "amount": 1420.50},
    {"id": "inv-1002", "customer": "Ostrander Marine", "amount": 980.00},
    {"id": "inv-1003", "customer": "Keel & Co", "amount": 2205.75},
]

# Permission required by each operation type.
PERMISSIONS = {
    "accounts.list": "accounts:read",
    "invoices.list": "invoices:read",
    "invoices.get": "invoices:read",
    "reports.summary": "reports:read",
    "tasks.create": "tasks:write",
    "admin.export": "admin:export",
}

MEMBER_PERMISSIONS = {"accounts:read", "invoices:read", "reports:read", "tasks:write"}


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">NORTHBEAM // REST API</div><h1>{title}</h1></div>{body}',
        nav='<a href="/">Overview</a><a href="/docs">Docs</a><a href="/console">API console</a>',
    )


@app.get("/")
def index():
    return shell(
        "Northbeam API",
        """<div class="panel"><h2>One request, many operations</h2>
        <p>Clients group reads and writes into a single <code>POST /api/batch</code> call. The gateway performs the authorization check once per batch and then executes each operation in order, returning partial results.</p>
        <p class="note">Get a demo token with <code>POST /api/token</code> (member scope). Full reference in <a href="/docs">/docs</a>.</p></div>""",
    )


@app.get("/docs")
def docs():
    rows = "".join(f"<tr><td><code>{html.escape(op)}</code></td><td><code>{html.escape(perm)}</code></td></tr>" for op, perm in PERMISSIONS.items())
    return shell(
        "API reference",
        f"""<div class="panel"><h2>Authentication</h2>
        <p>Send <code>Authorization: Bearer &lt;token&gt;</code>. Demo member token: <code>POST /api/token</code> with <code>{{"name": "demo"}}</code>.</p></div>
        <div class="panel"><h2>POST /api/batch</h2>
        <p>Body: <code>{{"operations": [{{"op": "invoices.list"}}, {{"op": "accounts.list"}}]}}</code></p>
        <p>Each operation may carry a <code>value</code> object. The gateway checks the batch <em>for the first operation</em>, then executes all of them. Individual operations that fail are reported inline.</p>
        <table><tr><th>Operation</th><th>Required permission</th></tr>{rows}</table>
        <p class="note">Our exporter calls <code>admin.export</code>, which is restricted to the integrations role.</p></div>""",
    )


@app.post("/api/token")
def issue_token():
    raw = request.get_json(silent=True) or {}
    role = "member"
    token = "nb_" + secrets.token_urlsafe(24)
    TOKENS[token] = {"role": role, "name": str(raw.get("name", "demo"))[:60], "permissions": set(MEMBER_PERMISSIONS)}
    return {"token": token, "role": role, "permissions": sorted(MEMBER_PERMISSIONS)}


def bearer():
    header = request.headers.get("Authorization", "")
    if header.lower().startswith("bearer "):
        return TOKENS.get(header[7:].strip())
    return None


@app.post("/api/batch")
def batch():
    caller = bearer()
    if caller is None:
        return {"error": "missing or invalid bearer token"}, 401
    raw = request.get_json(silent=True) or {}
    operations = raw.get("operations")
    if not isinstance(operations, list) or not operations:
        return {"error": "operations must be a non-empty list"}, 400
    if len(operations) > 25:
        return {"error": "at most 25 operations per batch"}, 400
    for op in operations:
        if not isinstance(op, dict) or not isinstance(op.get("op"), str):
            return {"error": "each operation needs a string `op`"}, 400

    # VULNERABLE: authorization is evaluated only from the first operation.
    # Every later operation runs with the first operation's permission check.
    first = operations[0]["op"]
    required = PERMISSIONS.get(first)
    if required is None:
        return {"error": f"unknown operation: {first}"}, 400
    if required not in caller["permissions"]:
        return {"error": "permission denied", "required": required, "op": first}, 403

    results = []
    for op in operations:
        results.append(execute(caller, op))
    failed = [r for r in results if r["status"] >= 400]
    ok = len(results) - len(failed)
    if ok == 0:
        return {"results": results, "partial": False, "count": len(results)}, (403 if all(r["status"] == 403 for r in failed) else 400)
    code = 207 if failed else 200
    return {"results": results, "partial": bool(failed), "count": len(results)}, code


def execute(caller: dict, operation: dict) -> dict:
    op = operation["op"]
    required = PERMISSIONS.get(op)
    if required is None:
        return {"op": op, "status": 400, "error": f"unknown operation: {op}"}
    if op == "admin.export":
        # The export handler checks the role and records the attempt. Once the
        # batch reached this point the check was already skipped upstream, so
        # the handler runs and returns the export manifest.
        exported = {
            "export": "northbeam-finance",
            "generated_by": caller["name"],
            "role": caller["role"],
            "records": len(RECORDS),
            "vault_flag": lab.flag("flag"),
        }
        AUDIT.append({"op": op, "caller": caller["name"], "role": caller["role"], "allowed": True})
        if caller["role"] == "member" and lab.flag("flag") in str(exported):
            lab.objective_async("flag", "admin.export executed inside a member batch after the first operation")
        return {"op": op, "status": 200, "data": exported}
    if op == "accounts.list":
        return {"op": op, "status": 200, "data": [{"id": "acct-77", "name": "Harbor Supply"}, {"id": "acct-78", "name": "Keel & Co"}]}
    if op == "invoices.list":
        return {"op": op, "status": 200, "data": RECORDS}
    if op == "invoices.get":
        wanted = str((operation.get("value") or {}).get("id", ""))
        hit = [r for r in RECORDS if r["id"] == wanted]
        if not hit:
            return {"op": op, "status": 404, "error": "invoice not found"}
        return {"op": op, "status": 200, "data": hit[0]}
    if op == "reports.summary":
        return {"op": op, "status": 200, "data": {"open_invoices": len(RECORDS), "currency": "USD"}}
    if op == "tasks.create":
        title = str((operation.get("value") or {}).get("title", "Untitled"))[:80]
        return {"op": op, "status": 201, "data": {"id": "task-" + secrets.token_hex(3), "title": title}}
    return {"op": op, "status": 500, "error": "operation not implemented"}


@app.get("/api/admin/export")
@app.post("/api/admin/export")
def admin_export_single():
    caller = bearer()
    if caller is None:
        return {"error": "missing or invalid bearer token"}, 401
    if "admin:export" not in caller["permissions"]:
        return {"error": "permission denied", "required": "admin:export"}, 403
    return {"export": "northbeam-finance", "records": len(RECORDS), "vault_flag": lab.flag("flag")}


@app.get("/console")
def console():
    return shell(
        "API console",
        """<div class="panel"><h2>Try a batch</h2>
        <p>1. Get a token: <code>curl -s -X POST /api/token -d '{"name":"demo"}' -H 'Content-Type: application/json'</code></p>
        <p>2. Send a batch:</p>
        <pre>curl -s -X POST /api/batch \\
  -H "Authorization: Bearer nb_..." -H 'Content-Type: application/json' \\
  -d '{"operations":[{"op":"invoices.list"}]}'</pre>
        <p class="note">A batch returns <code>207</code> with per-operation results when some operations fail.</p></div>""",
    )


if __name__ == "__main__":
    lab.run()