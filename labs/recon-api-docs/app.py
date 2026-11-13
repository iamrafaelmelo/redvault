from __future__ import annotations

from flask import jsonify, request

from labkit import Lab

lab = Lab("SENTINEL API", accent="#8b7cf6")
app = lab.app

DEBUG_KEY = "rv-debug-2026"

OPENAPI = {
    "openapi": "3.0.3",
    "info": {
        "title": "Sentinel Fleet API",
        "version": "1.9.0",
        "description": "Public and internal fleet telemetry endpoints.",
    },
    "servers": [{"url": "/"}],
    "paths": {
        "/api/v1/status": {
            "get": {
                "summary": "Fleet status",
                "responses": {"200": {"description": "Current aggregate status"}},
            }
        },
        "/api/v1/admin/secret": {
            "get": {
                "summary": "Internal secret export",
                "description": (
                    "SRE-only export used during incident response. Authenticate with the "
                    "DebugKey security scheme. Current non-secret debug key: rv-debug-2026"
                ),
                "security": [{"DebugKey": []}],
                "parameters": [
                    {
                        "name": "X-Debug-Key",
                        "in": "header",
                        "required": True,
                        "description": "Debug key issued to the on-call SRE rotation.",
                        "schema": {"type": "string", "example": DEBUG_KEY},
                        "example": DEBUG_KEY,
                    }
                ],
                "responses": {
                    "200": {"description": "Internal export containing the release flag"},
                    "401": {"description": "Missing or invalid debug key"},
                },
            }
        },
    },
    "components": {
        "securitySchemes": {
            "DebugKey": {
                "type": "apiKey",
                "in": "header",
                "name": "X-Debug-Key",
                "description": f"Incident-response debug key. Current value: {DEBUG_KEY}",
            }
        }
    },
}


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">SENTINEL // FLEET API</div><h1>{title}</h1>'
        "<p>Telemetry and incident tooling for the Sentinel edge fleet.</p></div>"
        f"{body}",
        nav='<a href="/">Portal</a><a href="/docs">API docs</a><a href="/openapi.json">OpenAPI</a>',
    )


@app.get("/")
def index():
    return shell(
        "Sentinel developer portal",
        """<div class="grid">
        <div class="panel"><h2>Fleet API</h2>
        <p>Integrate with Sentinel telemetry. The interactive reference is generated from the live OpenAPI document.</p>
        <p><a class="btn" href="/docs">Read the API reference</a></p></div>
        <div class="panel"><h2>Service status</h2>
        <p>All public endpoints are operational. The incident-response surface is documented alongside the public API for on-call convenience.</p>
        <p class="dim mono">api v1.9.0 · docs generated 2026-11-09</p></div>
        </div>""",
    )


@app.get("/openapi.json")
def openapi():
    return jsonify(OPENAPI)


@app.get("/docs")
def docs():
    endpoint = """<div class="panel"><h2>GET /api/v1/admin/secret</h2>
    <p>Internal secret export used by the SRE rotation. This endpoint is intentionally omitted from the public navigation but remains in the generated reference.</p>
    <table>
      <tr><th>Header</th><th>Value</th></tr>
      <tr><td><code>X-Debug-Key</code></td><td><code>rv-debug-2026</code></td></tr>
    </table>
    <pre>curl -H 'X-Debug-Key: rv-debug-2026' http://127.0.0.1:PORT/api/v1/admin/secret</pre>
    <p class="note">The debug key is a shared, non-secret operational value. Access is still gated by the header check.</p></div>"""
    return shell(
        "API reference",
        """<div class="panel"><h2>Sentinel Fleet API · v1.9.0</h2>
        <p>Base URL: <code>/</code> · Auth: none for public endpoints, <code>X-Debug-Key</code> for incident tooling.</p></div>
        <div class="panel"><h2>GET /api/v1/status</h2><p>Public aggregate fleet status.</p></div>"""
        + endpoint.replace("PORT", str(lab.port)),
    )


@app.get("/api/v1/status")
def status():
    return jsonify({"service": "sentinel-fleet", "status": "operational", "nodes": 12})


@app.get("/api/v1/admin/secret")
def admin_secret():
    if request.headers.get("X-Debug-Key") != DEBUG_KEY:
        return jsonify({"error": "unauthorized", "detail": "X-Debug-Key required"}), 401
    return jsonify(
        {
            "service": "sentinel-incident-response",
            "operator": "sre-oncall",
            "flag": lab.flag("flag"),
            "note": "Rotate this debug key before the next release.",
        }
    )


if __name__ == "__main__":
    lab.run()
