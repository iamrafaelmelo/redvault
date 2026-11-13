from __future__ import annotations

import html
import secrets

from flask import request

from labkit import Lab

lab = Lab("PILOTLINE", accent="#67e8f9")
app = lab.app

TABS: dict[str, dict] = {}
EVENTS: list[dict] = []

COMMANDS = {"broadcast", "notify", "slow-mode", "ping", "profile", "twofa.disable", "vault.read"}


def shell(title: str, body: str, head: str = "") -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">PILOTLINE // OPS SOCKET</div><h1>{title}</h1></div>{body}',
        nav='<a href="/">Console</a><a href="/docs">API</a><a href="/captured">Events</a>',
        head=head,
    )


def tab_of():
    cookie = request.headers.get("Cookie", "")
    tid = ""
    for part in cookie.split(";"):
        name, _, value = part.strip().partition("=")
        if name == "pilot_tab":
            tid = value.strip()
    return tid, TABS.get(tid)


def tab_for_key(key: str):
    for tab in TABS.values():
        if tab["key"] == key:
            return tab
    return None


def resolve_tab():
    """Resolve the tab from the cookie, then from the integration key header."""
    _, tab = tab_of()
    if tab is not None:
        return tab
    key = request.headers.get("X-Pilot-Key", "")
    return tab_for_key(key) if key else None


def push(tab: dict, kind: str, message: str) -> None:
    EVENTS.append({"tab": tab["id"], "kind": kind, "message": message[:400]})


@app.get("/login")
def login_form():
    return shell(
        "Operator sign-in",
        """<div class="panel"><h2>Ops console</h2>
        <form method="post" action="/login">
          <label>Operator</label><input name="user" value="ops-lead">
          <label>Password</label><input name="password" type="password" value="console-2026">
          <p><button type="submit">Open console</button></p></form></div>""",
    )


@app.post("/login")
def login():
    user = request.form.get("user", "").strip()
    if user != "ops-lead" or request.form.get("password") != "console-2026":
        return shell("Operator sign-in", '<div class="flash err">Invalid operator credentials.</div>'), 401
    tab_id = secrets.token_urlsafe(16)
    TABS[tab_id] = {
        "id": tab_id,
        "key": secrets.token_urlsafe(18),
        "user": user,
        "twofa": True,
        "vault": lab.flag("flag"),
        "frames": 0,
    }
    response = lab.redirect("/")
    response.set_cookie("pilot_tab", tab_id, httponly=True, samesite="Lax", path="/")
    return response


@app.get("/")
def console():
    tab_id, tab = tab_of()
    if not tab:
        return lab.redirect("/login")
    frames = "".join(
        f'<li><span class="dim">[{html.escape(e["kind"])}]</span> {html.escape(e["message"])}</li>'
        for e in EVENTS
        if e["tab"] == tab_id
    ) or '<li class="dim">No frames yet.</li>'
    console_js = """<script>
const send = (body) => fetch("/ws/send", {method: "POST", headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)}).then(r => r.json());
async function tick() {
  const state = await (await fetch("/ws/state")).json();
  const panel = document.getElementById("panel");
  panel.textContent = "";
  const box = document.createElement("div"); box.className = "panel";
  const head = document.createElement("h2"); head.textContent = "Operator profile";
  const two = document.createElement("p"); two.textContent = "2FA: " + (state.twofa ? "enabled" : "disabled");
  box.appendChild(head); box.appendChild(two);
  for (const msg of state.messages) { const p = document.createElement("div"); p.className = "flash"; p.textContent = msg; box.appendChild(p); }
  panel.appendChild(box);
}
document.getElementById("send").addEventListener("submit", async (e) => {
  e.preventDefault();
  await send({action: document.getElementById("action").value, value: document.getElementById("arg").value});
  tick();
});
tick();
</script>"""
    return lab.page(
        "Operator console",
        f"""<div class="hero"><div class="kicker">PILOTLINE // OPS SOCKET</div><h1>Operator console</h1></div>
        <div class="panel"><h2>Session {tab_id[:8]}</h2>
        <p>Operator: <code>{html.escape(tab["user"])}</code> · 2FA: {'<span class="green">enabled</span>' if tab["twofa"] else '<span class="red">disabled</span>'}</p></div>
        <div id="panel"></div>
        <div class="split">
          <div style="flex:1"><h3>Send a command</h3>
          <form id="send"><input id="action" value="broadcast" style="margin-bottom:7px"><input id="arg" placeholder="message" style="margin-bottom:7px"><p><button type="submit">Send</button></p></form></div>
          <div style="flex:1"><h3>Socket transport</h3><p class="dim">The console keeps a socket open: it polls <code>/ws/state</code> for frames and pushes commands to <code>/ws/send</code>.</p></div>
        </div>
        <div class="panel"><h2>Recent frames</h2><ul class="list">{frames}</ul></div>
        <p class="note">The channel is modelled as HTTP polling so it can be driven with the JSON API at <a href="/docs">/docs</a>. It behaves like the production WebSocket upgrade: the cookie selects the socket, each frame body is JSON, and the server never looks at <code>Origin</code>.</p>""",
        nav='<a href="/">Console</a><a href="/docs">API</a><a href="/captured">Events</a>',
        head=console_js,
    )


@app.get("/ws/state")
def ws_state():
    tab = resolve_tab()
    if not tab:
        return {"error": "socket not authenticated"}, 401
    return {
        "ok": True,
        "socket": "pilot-ops",
        "operator": tab["user"],
        "twofa": tab["twofa"],
        "messages": [e["message"] for e in EVENTS if e["tab"] == tab["id"]],
        "permissions": sorted(COMMANDS),
        "frames": tab["frames"],
    }


@app.post("/ws/poll")
def ws_poll():
    # VULNERABLE: the "socket" authenticates from the cookie and never checks
    # the Origin of the upgrade. Any page on the internet can poll it.
    tab = resolve_tab()
    if not tab:
        return {"error": "socket not authenticated"}, 401
    tab["frames"] += 1
    return {
        "ok": True,
        "socket": "pilot-ops",
        "operator": tab["user"],
        "twofa": tab["twofa"],
        "messages": [e["message"] for e in EVENTS if e["tab"] == tab["id"]],
        "frames": tab["frames"],
    }


@app.post("/ws/send")
def ws_send():
    # VULNERABLE: a cross-origin frame carrying the victim's cookie is accepted.
    # The only authorization is "is this tab's cookie present", and privileged
    # commands run without a fresh challenge.
    raw = request.get_json(silent=True) or {}
    action = str(raw.get("action", ""))
    value = str(raw.get("value", ""))[:200]
    tab = resolve_tab()
    if tab is None:
        return {"error": "socket not authenticated"}, 401
    if not action:
        return {"error": "action required"}, 400
    if action == "twofa.disable":
        tab["twofa"] = False
        push(tab, "state", "2FA disabled by operator")
        if lab.flag("flag") in tab["vault"]:
            lab.objective_async("flag", "cross-origin socket frame disabled 2FA on the operator tab")
        return {"ok": True, "action": action, "twofa": False, "note": "Two-factor authentication disabled."}
    if action == "vault.read":
        push(tab, "vault", "vault.read executed")
        if lab.flag("flag") in tab["vault"]:
            lab.objective_async("flag", "cross-origin socket frame read the operator vault")
        return {"ok": True, "action": action, "vault": tab["vault"]}
    if action == "profile":
        return {"ok": True, "action": action, "twofa": tab["twofa"], "user": tab["user"]}
    if action in {"broadcast", "notify", "slow-mode"}:
        push(tab, "streams", f"{action}: {value}")
        return {"ok": True, "action": action, "delivered": len([e for e in EVENTS if e["tab"] == tab["id"]])}
    if action == "ping":
        return {"ok": True, "action": action, "pong": True}
    return {"error": f"unknown action: {action}", "known": sorted(COMMANDS)}, 400


@app.get("/docs")
def docs():
    return shell(
        "Ops socket API",
        """<div class="panel"><h2>Pilotline socket (HTTP transport)</h2>
        <p>The console keeps a single socket open. For testing the same frames are exposed over JSON: the cookie selects the socket and every frame body is a JSON object.</p>
        <table><tr><th>Frame</th><th>Direction</th><th>Body</th></tr>
        <tr><td><code>GET /ws/state</code></td><td>server → client</td><td>state, queue and permissions</td></tr>
        <tr><td><code>POST /ws/poll</code></td><td>server → client</td><td><code>{}</code> — current state and queued frames</td></tr>
        <tr><td><code>POST /ws/send</code></td><td>client → server</td><td><code>{"action": "...", "value": "..."}</code></td></tr></table>
        <p class="note">Actions: broadcast, notify, slow-mode, ping, profile, twofa.disable, vault.read. In production this is a WebSocket upgrade on the same origin; the server trusts the cookie alone on that upgrade too.</p></div>""",
    )


@app.get("/captured")
def captured():
    rows = "".join(
        f'<li><span class="dim">[{html.escape(e["kind"])}]</span> {html.escape(e["message"])}</li>' for e in reversed(EVENTS[-50:])
    ) or '<li class="dim">No frames yet.</li>'
    return shell("Socket events", f'<div class="panel"><h2>Recent frames</h2><ul class="list">{rows}</ul></div>')


if __name__ == "__main__":
    lab.run()