from __future__ import annotations

import html
import json

from flask import Response, jsonify, request

from labkit import Lab

lab = Lab("PREFTOWN", accent="#6fd08c")
app = lab.app

CAPTURED: list[str] = []

BASE_PREFS: dict[str, object] = {"theme": "dark", "locale": "en-US", "currency": "USD"}

# Per-session store mirrors the browser model:
#   "prefs"    -> the user profile object (own properties only at first)
#   "prototype"-> the shared defaults object that JSON merges walk into
STORE: dict[str, object] = {}


def merge(target: dict[str, object], source: object) -> None:
    # VULNERABLE: recursive merge with no key denylist. `__proto__` and
    # `constructor` / `prototype` chains are followed exactly like in a
    # JavaScript `Object.assign`-style deep merge.
    if not isinstance(source, dict):
        return
    for key, value in source.items():
        if isinstance(value, dict):
            child = target.get(key)
            if not isinstance(child, dict):
                child = {}
                target[key] = child
            merge(child, value)
        else:
            target[key] = value


def ensure_store() -> None:
    STORE.setdefault("prefs", {})
    STORE.setdefault("prototype", {})


def target_for(profile: dict[str, object], key: str) -> dict[str, object]:
    """Resolve a merge key the way a naive deep-merge does: follow the
    prototype chain instead of creating an own property."""
    if key == "__proto__":
        return STORE["prototype"]  # VULNERABLE: prototype object writable by clients
    if key == "constructor":
        child = profile.get("constructor")
        if not isinstance(child, dict):
            child = {}
            profile["constructor"] = child
        return child
    if key == "prototype":
        # `X.prototype`: find the constructor object that owns this key.
        for candidate in _containers(profile):
            child = candidate.get(key)
            if isinstance(child, dict):
                return child
        # Fall back to the profile itself (fragment local, not pollution).
        child = profile.get(key)
        if not isinstance(child, dict):
            child = {}
            profile[key] = child
        return child
    child = profile.get(key)
    if not isinstance(child, dict):
        child = {}
        profile[key] = child
    return child


def _containers(profile: dict[str, object]) -> list[dict[str, object]]:
    found = [profile]
    ctor = profile.get("constructor")
    if isinstance(ctor, dict):
        found.append(ctor)
    found.append(STORE["prototype"])
    return found


def lookup(profile: dict[str, object], key: str) -> object:
    """Property lookup with prototype fallback (`obj[key] ?? proto[key]`)."""
    if key in profile:
        return profile[key]
    proto = STORE["prototype"]
    if key in proto:
        return proto[key]
    ctor = profile.get("constructor")
    if isinstance(ctor, dict):
        inherited = ctor.get("prototype")
        if isinstance(inherited, dict) and key in inherited:
            return inherited[key]
    return None


def merge(target: dict[str, object], source: object) -> None:
    # VULNERABLE: recursive merge with no key denylist. `__proto__` and
    # `constructor` / `prototype` chains are followed exactly like in a
    # JavaScript `Object.assign`-style deep merge.
    if not isinstance(source, dict):
        return
    for key, value in source.items():
        if isinstance(value, dict):
            merge(target_for(target, key), value)
        else:
            target[key] = value


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">PREFTOWN // PREFERENCES</div><h1>{title}</h1></div>{body}',
        nav='<a href="/">Studio</a><a href="/api/prefs">API</a><a href="/api/render">Render</a><a href="/captured">Captured</a>',
    )


@app.get("/")
def index():
    ensure_store()
    profile = STORE["prefs"]
    return shell(
        "Preference studio",
        f"""<div class="panel"><h2>Session profile</h2>
        <pre>{html.escape(json.dumps(profile, indent=2))}</pre>
        <p class="note">POST a JSON object to <code>/api/prefs</code>. It is deep-merged into the session profile,
        with the shared defaults object as the prototype chain. Render a licence quote at <code>/api/render</code>.</p>
        <form id="f"><label>JSON body</label><textarea name="body" rows="6" style="width:100%">{{"theme":"light"}}</textarea>
        <p><button type="button" onclick="fetch('/api/prefs',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:document.getElementById('f').body.value}}).then(r=>r.text()).then(t=>alert(t))">Save preferences</button></p></form></div>""",
    )


@app.route("/api/prefs", methods=["GET", "POST"])
def prefs():
    ensure_store()
    if request.method == "GET":
        return jsonify({"prefs": STORE["prefs"], "prototype": STORE["prototype"]})
    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify({"error": "JSON object required"}), 400
    merge(STORE["prefs"], payload)
    return jsonify({"ok": True, "merged": payload})


@app.get("/api/render")
def render():
    ensure_store()
    profile = STORE["prefs"]
    multiplier_raw = lookup(profile, "priceMultiplier")
    try:
        multiplier = float(multiplier_raw) if multiplier_raw is not None else 1.0
    except (TypeError, ValueError):
        multiplier = 1.0
    worker = lookup(profile, "worker") or "none"
    tier = lookup(profile, "tier") or "standard"
    base = 249.0
    total = round(base * multiplier, 2)
    privileged = multiplier < 0.01 or str(tier).lower() == "internal"
    flag_block = ""
    note = "Standard licence tier."
    if privileged:
        # VULNERABLE: a privileged branch is unlocked by polluted prototype state.
        flag_block = f'<pre class="green" id="flag">{html.escape(lab.flag("flag"))}</pre>'
        note = "Internal zero-cost tier granted by inherited configuration."
        lab.objective_async("flag", "prototype polluted priceMultiplier/tier unlocked the internal tier")
    return Response(
        f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Quote</title>
        <style>body{{background:#08090a;color:#eef0f3;font-family:system-ui;padding:30px}}code{{color:#ff9aa6}}.green{{color:#48d99b}}</style>
        </head><body><h1>Licence quote</h1>
        <p>Product: Preftown Pro · base <code>249.00</code> USD</p>
        <p>Effective multiplier: <code>{html.escape(str(multiplier))}</code> · tier <code>{html.escape(str(tier))}</code> · worker <code>{html.escape(str(worker))}</code></p>
        <h2>Total: {total:.2f} USD</h2>
        <p>{note}</p>
        {flag_block}</body></html>""",
        mimetype="text/html",
    )


@app.get("/collect")
def collect():
    value = request.args.get("c", "") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
        if lab.flag("flag") in value:
            lab.objective_async("flag", "polluted value exfiltrated to the collector")
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(f"<li><code>{html.escape(v)}</code></li>" for v in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'
    return shell("Captured data", f'<div class="panel"><h2>Collector</h2><ul class="list">{rows}</ul></div>')


if __name__ == "__main__":
    lab.run()