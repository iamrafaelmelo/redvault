"""Shared runtime for REDVAULT lab applications.

Labs are deliberately vulnerable Flask apps. This module only provides the
boring parts: flag access, objective callbacks, the victim-bot bridge and a
consistent shell. Vulnerability logic stays in each lab.
"""
from __future__ import annotations

import html
import json
import os
import secrets
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from flask import Flask, Response, redirect, request

LAB_CSS = r"""
:root{--bg:#08090a;--panel:#0f1012;--line:#26282d;--text:#eef0f3;--muted:#9297a1;--dim:#61666f;--red:#e02338;--red2:#ff4157;--green:#48d99b;--amber:#eeb64c;--mono:"Fira Code","DejaVu Sans Mono",monospace;--sans:"DejaVu Sans",system-ui,sans-serif}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);font-size:14px;line-height:1.6}
a{color:var(--red2);text-decoration:none}a:hover{text-decoration:underline}
.shell{max-width:980px;margin:0 auto;padding:0 22px 60px}
.top{border-bottom:1px solid var(--line);margin-bottom:28px;padding:16px 0;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.brand{font-family:var(--mono);font-size:12px;letter-spacing:.14em;font-weight:700;color:var(--text)}
.brand b{color:var(--red2)}
.top .tag{font-family:var(--mono);font-size:8px;letter-spacing:.12em;color:var(--dim);border:1px solid var(--line);padding:2px 6px}
.top nav{margin-left:auto;display:flex;gap:15px;font-family:var(--mono);font-size:10px}
.top nav a{color:var(--muted)}.top nav a:hover{color:var(--text);text-decoration:none}
h1{font-size:27px;letter-spacing:-.02em;margin:0 0 7px}h2{font-size:18px;margin:25px 0 10px}h3{font-size:14px;margin:18px 0 7px}
p{color:var(--muted)}.lead{font-size:14px;color:var(--muted);max-width:720px}
.panel{background:var(--panel);border:1px solid var(--line);padding:18px;margin:14px 0}
.grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
.grid3{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px}
label{display:block;font-family:var(--mono);font-size:9px;letter-spacing:.1em;color:var(--muted);margin:11px 0 5px;text-transform:uppercase}
input,textarea,select{width:100%;background:#09090b;border:1px solid #34363c;color:var(--text);padding:9px 10px;font-family:var(--sans);font-size:13px;border-radius:2px;outline:none}
input:focus,textarea:focus{border-color:#7a2934}
button,.btn{display:inline-flex;align-items:center;gap:7px;background:var(--red);border:1px solid var(--red);color:#fff;padding:8px 12px;font-family:var(--mono);font-size:10px;letter-spacing:.05em;text-transform:uppercase;cursor:pointer;border-radius:2px;text-decoration:none}
button:hover,.btn:hover{background:var(--red2);text-decoration:none}
.btn-ghost{background:transparent;color:var(--muted);border-color:var(--line)}
.btn-ghost:hover{background:#15161a;color:var(--text)}
.btn-sm{padding:6px 9px;font-size:9px}
table{width:100%;border-collapse:collapse;font-size:12px}th{text-align:left;font-family:var(--mono);font-size:8px;letter-spacing:.1em;color:var(--dim);border-bottom:1px solid #36383e;padding:8px}td{border-bottom:1px solid var(--line);padding:8px;color:var(--muted);vertical-align:top}
code,pre{font-family:var(--mono);font-size:11px}pre{background:#09090b;border:1px solid var(--line);padding:12px;overflow-x:auto;color:#d9dce2}
code{background:#111215;border:1px solid var(--line);padding:1px 4px;color:#ff8b9a}
.mono{font-family:var(--mono)}.muted{color:var(--muted)}.dim{color:var(--dim)}.green{color:var(--green)}.red{color:var(--red2)}.amber{color:var(--amber)}
.tag{display:inline-block;border:1px solid var(--line);font-family:var(--mono);font-size:8px;padding:1px 5px;color:var(--dim);letter-spacing:.07em}
.flash{padding:10px 12px;border:1px solid var(--line);background:#0e0f11;margin:12px 0;font-size:12px}.flash.err{border-color:#5e1721;color:#ff8b9a}.flash.ok{border-color:#1e4637;color:var(--green)}
.badge{display:inline-block;background:#2a0a0e;color:var(--red2);border:1px solid #5b141d;padding:2px 7px;font-family:var(--mono);font-size:8px}
.hero{border:1px solid var(--line);background:radial-gradient(circle at 85% 0%,rgba(224,35,56,.1),transparent 40%),var(--panel);padding:28px;margin-bottom:20px}
.hero .kicker{font-family:var(--mono);font-size:9px;letter-spacing:.13em;color:var(--red2);text-transform:uppercase}
.hero p{max-width:720px}
.terminal{background:#070708;border:1px solid #303239;padding:14px;font-family:var(--mono);font-size:11px;color:#c8ccd3;line-height:1.8}
.terminal .p{color:var(--red2)}.terminal .ok{color:var(--green)}
.note{border-left:2px solid #5b141d;padding:4px 0 4px 12px;color:var(--muted);font-size:11px;margin:14px 0}
.list{list-style:none;padding:0;margin:0}.list li{padding:9px 0;border-bottom:1px solid var(--line);font-size:12px}
.split{display:flex;gap:16px;align-items:flex-start}.split>*{min-width:0}
.mt{margin-top:20px}.center{text-align:center}
@media(max-width:720px){.grid,.grid3{grid-template-columns:1fr}.split{display:block}}
"""


class Lab:
    def __init__(self, name: str, accent: str = "#e02338") -> None:
        self.name = name
        self.port = int(os.environ.get("LAB_PORT", "5000"))
        self.flags: dict[str, str] = json.loads(os.environ.get("LAB_FLAGS", "{}") or "{}")
        self.token = os.environ.get("LAB_CALLBACK_TOKEN", "")
        self.callback_url = os.environ.get("LAB_CALLBACK_URL", "")
        self.platform_url = os.environ.get("LAB_PLATFORM_URL", "http://127.0.0.1:8000")
        self.state_dir = Path(os.environ.get("LAB_STATE_DIR", "/tmp/redvault-state"))
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.accent = accent
        self.app = Flask(name)
        self.app.secret_key = secrets.token_hex(32)
        self._init_common_routes()
        self._init_traffic_reporting()

    # -- flag / objective -------------------------------------------------
    def flag(self, key: str) -> str:
        return self.flags.get(key, "RV{missing_flag}")

    def objective(self, key: str, evidence: str = "") -> bool:
        if not self.callback_url or not self.token:
            return False
        payload = json.dumps({"token": self.token, "flag_key": key, "evidence": evidence[:280]}).encode()
        req = urllib.request.Request(
            self.callback_url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=3) as response:
                return response.status == 200
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError):
            return False

    def objective_async(self, key: str, evidence: str = "") -> None:
        threading.Thread(target=self.objective, args=(key, evidence), daemon=True).start()

    def bot(self, path_or_url: str, cookies: list[dict] | None = None, wait: float = 3.5) -> dict:
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            target = path_or_url
        else:
            target = f"http://127.0.0.1:{self.port}/{path_or_url.lstrip('/')}"
        payload = json.dumps({"token": self.token, "url": target, "cookies": cookies or []}).encode()
        req = urllib.request.Request(
            f"{self.platform_url}/internal/bot",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=25) as response:
                return json.loads(response.read().decode() or "{}")
        except urllib.error.HTTPError as exc:
            try:
                detail = json.loads(exc.read().decode()).get("detail", str(exc))
            except Exception:
                detail = str(exc)
            return {"ok": False, "error": detail}
        except Exception as exc:  # noqa: BLE001 - surfaced to lab page
            return {"ok": False, "error": str(exc)}

    # -- presentation -----------------------------------------------------
    def page(
        self,
        title: str,
        body: str,
        nav: str | None = None,
        status: int = 200,
        head: str = "",
        wide: bool = False,
    ) -> Response:
        nav_html = nav if nav is not None else '<a href="/">Home</a><a href="/health">Health</a>'
        mode = "LAN SHARED" if os.environ.get("LAB_BIND", "127.0.0.1") not in ("127.0.0.1", "::1") else "LOCAL ONLY"
        shell = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(title)} · {html.escape(self.name)}</title>
<style>{LAB_CSS}
:root{{--red:{self.accent};--red2:{self.accent}}}
.shell{{max-width:{'1180px' if wide else '980px'}}}
</style>{head}</head>
<body>
<div class="shell">
<header class="top">
  <span class="brand">RED<b>VAULT</b>//LAB</span>
  <span class="tag">SANDBOX · {mode} · {html.escape(self.name.upper())}</span>
  <nav>{nav_html}</nav>
</header>
{body}
<footer style="border-top:1px solid var(--line);margin-top:36px;padding-top:13px;font-family:var(--mono);font-size:8px;color:var(--dim);display:flex;justify-content:space-between">
  <span>INTENTIONALLY VULNERABLE · LOCAL ONLY</span><span>PORT {self.port}</span>
</footer>
</div>
</body></html>"""
        return Response(shell, status=status, mimetype="text/html")

    def flash_page(self, title: str, message: str, kind: str = "err", links: str = "") -> Response:
        cls = "ok" if kind == "ok" else "err"
        body = f'<div class="flash {cls}">{message}</div>{links}'
        return self.page(title, f"<h1>{html.escape(title)}</h1>{body}", status=200)

    def redirect(self, path: str) -> Response:
        return redirect(path)

    def write_state(self, name: str, content: str) -> Path:
        path = self.state_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def read_state(self, name: str) -> str:
        path = self.state_dir / name
        try:
            return path.read_text()
        except OSError:
            return ""

    def init_db(self, name: str, schema: str, seed: list[str] | None = None) -> None:
        import sqlite3

        path = self.state_dir / name
        fresh = not path.exists()
        conn = sqlite3.connect(path)
        try:
            conn.executescript(schema)
            if fresh and seed:
                conn.executescript("\n".join(seed))
            conn.commit()
        finally:
            conn.close()

    def db(self, name: str):
        import sqlite3

        conn = sqlite3.connect(self.state_dir / name)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_traffic_reporting(self) -> None:
        """Count every request so the platform can spot runaway brute force.

        The lab cannot see its own traffic rate (the platform owns the reaper),
        so a single background reporter sends the local count to
        /internal/lab-traffic every couple of seconds. Two side effects that
        matter for a LAN-widened lab: traffic from another machine counts as
        activity (the lab is not reaped mid-exercise), and an absurd rate is
        both logged and surfaced as a header on the lab's own response.

        The request hook only increments an integer; it never spawns a thread,
        because under a brute force the Flask worker pool is saturated and a
        per-request thread would be lost before it could report.
        """
        if not self.callback_url or not self.token:
            return
        endpoint = f"{self.callback_url.rsplit('/', 1)[0]}/lab-traffic"
        state = {"pending": 0, "state": "normal"}
        lock = threading.Lock()

        @self.app.after_request
        def _count(response):  # noqa: ANN001 - Flask hook signature
            with lock:
                state["pending"] += 1
                current = state["state"]
            response.headers["X-Redvault-Traffic"] = current
            return response

        def reporter() -> None:
            while True:
                time.sleep(2.0)
                with lock:
                    count = state["pending"]
                    state["pending"] = 0
                if not count:
                    continue
                payload = json.dumps({"token": self.token, "count": count}).encode()
                req = urllib.request.Request(
                    endpoint,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    with urllib.request.urlopen(req, timeout=3) as response:
                        data = json.loads(response.read().decode() or "{}")
                except Exception:  # noqa: BLE001 - never break the lab over telemetry
                    with lock:
                        state["pending"] += count
                    continue
                previous = state["state"]
                with lock:
                    state["state"] = data.get("state", "normal")
                if data.get("state") != previous and data.get("state") in {"warn", "abort"}:
                    print(
                        f"[traffic] {data.get('state').upper()}: {data.get('rps')} req/s "
                        f"({data.get('requests_total')} total). Far above what an exploit "
                        "needs; stop the loop before it saturates your machine.",
                        flush=True,
                    )

        threading.Thread(target=reporter, name="lab-traffic", daemon=True).start()

    def _init_common_routes(self) -> None:
        @self.app.get("/health")
        def health():  # noqa: ANN202
            return {"ok": True, "lab": self.name, "port": self.port}

        @self.app.get("/favicon.ico")
        def favicon():  # noqa: ANN202
            svg = (
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">'
                '<rect width="32" height="32" fill="#09090b"/>'
                f'<path d="M16 3 27 9.5v13L16 29 5 22.5v-13L16 3Z" fill="none" stroke="{self.accent}" stroke-width="1.5"/>'
                f'<circle cx="16" cy="16" r="4" fill="{self.accent}"/></svg>'
            )
            return Response(svg, mimetype="image/svg+xml")

    def run(self) -> None:
        bind = os.environ.get("LAB_BIND", "127.0.0.1")
        self.app.run(host=bind, port=self.port, debug=False, use_reloader=False, threaded=True)
