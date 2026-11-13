from __future__ import annotations

import json

from flask import Response, jsonify, request

from labkit import Lab

lab = Lab("NORTHWIND RELEASE", accent="#4fd1c5")
app = lab.app

INTERNAL_TOKEN = "rv-map-7d41c9"
RELEASE_PATH = "/api/internal/release"

APP_JS = """// Northwind release console 4.2.0
const CONFIG = {
  statusEndpoint: "/api/status",
  releaseEndpoint: "/api/internal/release",
  internalToken: "rv-map-7d41c9",
  build: "prod-4.2.0"
};

async function refresh() {
  const el = document.getElementById("status");
  try {
    const response = await fetch(CONFIG.statusEndpoint);
    const data = await response.json();
    el.textContent = `${data.service} · ${data.state} · build ${CONFIG.build}`;
  } catch (error) {
    el.textContent = "status unavailable";
  }
}

document.getElementById("refresh")?.addEventListener("click", refresh);
refresh();
//# sourceMappingURL=app.js.map"""

SOURCE_CONTENT = """// app.ts - internal release publisher
const INTERNAL_TOKEN = "rv-map-7d41c9";
const RELEASE_ENDPOINT = "/api/internal/release";

export async function publishRelease(): Promise<Response> {
  return fetch(RELEASE_ENDPOINT, {
    method: "GET",
    headers: {
      "X-Internal-Token": INTERNAL_TOKEN,
    },
  });
}
"""

SOURCE_MAP = {
    "version": 3,
    "file": "app.js",
    "sourceRoot": "",
    "sources": ["app.ts"],
    "sourcesContent": [SOURCE_CONTENT],
    "names": [],
    "mappings": "",
}


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">NORTHWIND // RELEASE CONSOLE</div><h1>{title}</h1>'
        "<p>Builds, rollout state and release metadata for the Northwind edge fleet.</p></div>"
        f"{body}",
        nav='<a href="/">Console</a><a href="/static/app.js">Bundle</a><a href="/api/status">API status</a>',
    )


@app.get("/")
def index():
    return shell(
        "Release console",
        """<div class="grid">
        <div class="panel"><h2>Production rollout</h2>
        <p id="status">Loading telemetry...</p>
        <p><button id="refresh">Refresh</button></p>
        <p class="dim mono">build prod-4.2.0 · edge-static</p></div>
        <div class="panel"><h2>Release notes</h2>
        <p>The customer console is a static bundle. The build pipeline publishes it with debugging metadata so rollout issues can be traced in production.</p>
        <p class="note">Engineering asked for the internal release trigger to stay available during the migration window.</p></div>
        </div>
        <script src="/static/app.js"></script>""",
    )


@app.get("/static/app.js")
def app_js():
    return Response(APP_JS, mimetype="application/javascript")


@app.get("/static/app.js.map")
def app_map():
    return Response(json.dumps(SOURCE_MAP, indent=2), mimetype="application/json")


@app.get("/api/status")
def status():
    return jsonify({"service": "northwind-edge", "state": "operational", "build": "prod-4.2.0"})


@app.get(RELEASE_PATH)
def release():
    if request.headers.get("X-Internal-Token") != INTERNAL_TOKEN:
        return jsonify({"error": "unauthorized", "detail": "internal release token required"}), 401
    return jsonify(
        {
            "service": "northwind-release-control",
            "release": "prod-4.2.0",
            "flag": lab.flag("flag"),
            "warning": "Source maps must not ship with production bundles.",
        }
    )


if __name__ == "__main__":
    lab.run()
