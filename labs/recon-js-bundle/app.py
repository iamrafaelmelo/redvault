from __future__ import annotations

from flask import jsonify, request

from labkit import Lab

lab = Lab("ORBITAL UI", accent="#ff5a36")
app = lab.app

api_key = "rv_live_7f3a91c2"  # deliberately disclosed by the front-end build


@app.get("/")
def index():
    return lab.page(
        "Orbital UI",
        """
        <div class="hero"><div class="kicker">ORBITAL // CUSTOMER CONSOLE</div><h1>Telemetry, without the noise.</h1>
        <p>A small single-page console for satellite operations teams. The bundle is loaded from `/static/app.js`.</p></div>
        <div class="panel">
          <h2>Status board</h2>
          <p id="status">Loading telemetry...</p>
          <button id="refresh">Refresh</button>
          <p class="dim mono" id="build">build 2.8.17 · edge-static</p>
        </div>
        <script src="/static/app.js"></script>
        """,
        nav='<a href="/">Console</a><a href="/static/app.js">app.js</a>',
    )


@app.get("/static/app.js")
def js():
    body = f"""// Orbital UI 2.8.17
const CONFIG = {{
  telemetryEndpoint: "/api/status",
  internalEndpoint: "/api/internal/config",
  apiKey: "{api_key}",
  build: "edge-static"
}};

async function refresh() {{
  const el = document.getElementById("status");
  try {{
    const response = await fetch(CONFIG.telemetryEndpoint);
    const data = await response.json();
    el.textContent = `${{data.satellites}} satellites nominal · uplink ${{data.uplink}}`;
  }} catch (error) {{
    el.textContent = "telemetry unavailable";
  }}
}}
document.getElementById("refresh")?.addEventListener("click", refresh);
refresh();
"""
    return lab.app.response_class(body, mimetype="application/javascript")


@app.get("/api/status")
def status():
    return jsonify({"satellites": 4, "uplink": "degraded", "last_contact": "2026-11-12T19:44:00Z"})


@app.get("/api/internal/config")
def internal_config():
    if request.headers.get("X-API-Key") != api_key:
        return jsonify({"error": "unauthorized", "detail": "service API key required"}), 401
    return jsonify(
        {
            "service": "orbital-internal",
            "environment": "edge-static",
            "flag": lab.flag("flag"),
            "warning": "Do not ship this key in browser bundles.",
        }
    )


if __name__ == "__main__":
    lab.run()
