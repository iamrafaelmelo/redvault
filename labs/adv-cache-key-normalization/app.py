from __future__ import annotations

import html
import time

from flask import request

from labkit import Lab

lab = Lab("SAILMAKER", accent="#f2b36b")
app = lab.app

# Edge cache: one entry per path. Query strings are normalised away because the
# product team "knows" the marketing page has no meaningful parameters.
CACHE: dict[str, tuple[str, float]] = {}
CAPTURED: list[str] = []
TTL = 600.0

LANGUAGES = {
    "en": {"name": "English", "greeting": "Welcome to Sailmaker", "tagline": "Plans that move at the speed of your fleet."},
    "pt": {"name": "Português", "greeting": "Bem-vindo à Sailmaker", "tagline": "Planos na velocidade da sua frota."},
    "es": {"name": "Español", "greeting": "Bienvenido a Sailmaker", "tagline": "Planes a la velocidad de tu flota."},
    "fr": {"name": "Français", "greeting": "Bienvenue chez Sailmaker", "tagline": "Des offres à la vitesse de votre flotte."},
}

def shell(title: str, body: str, head: str = "") -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">SAILMAKER // PRICING EDGE</div><h1>{title}</h1></div>{body}',
        nav='<a href="/">Home</a><a href="/page">Pricing</a><a href="/cache">Cache</a><a href="/captured">Captured</a>',
        head=head,
    )


def cache_key() -> str:
    # VULNERABLE: the key drops the query string. `/page?lang=x` and `/page`
    # share one entry while the body is still rendered from `lang`.
    return request.path


@app.get("/")
def index():
    return shell(
        "Localized pricing",
        """<div class="panel"><h2>One page, every market</h2>
        <p>The pricing page is translated at the edge from a <code>lang</code> query parameter. Marketing asked that the page stay fast, so the edge stores it for ten minutes.</p>
        <ul class="list"><li><a href="/page">Default pricing page</a></li><li><a href="/page?lang=pt">Portuguese</a></li><li><a href="/page?lang=es">Spanish</a></li></ul></div>""",
    )


@app.get("/page")
def page():
    lang = (request.args.get("lang") or "en")[:200]
    selected = LANGUAGES.get(lang)

    def render() -> str:
        leak = ""
        if selected is None:
            greeting = lang
            tagline = "Translation not published yet."
            # VULNERABLE: the requested language is interpolated into the
            # banner without encoding.
            banner = f'<div class="flash">Requested language: <b>{lang}</b> is not in the catalogue.</div>'
            # The fallback branch appends a release tag with the pricing vault
            # identifier, so the flag travels inside the cached body.
            head = ""
            leak = f'<!-- release-tag vault:{lab.flag("flag")} -->'
        else:
            greeting = html.escape(selected["greeting"])
            tagline = html.escape(selected["tagline"])
            banner = f'<div class="flash">Language: {html.escape(selected["name"])}</div>'
            head = '<meta name="robots" content="index,follow">'
        # The requested code is echoed into the banner as submitted and the
        # document is stored whole by the edge.
        body = f"""<div class="panel">{banner}<h2>{greeting}</h2><p>{tagline}</p></div>
        <div class="grid3">
          <div class="panel"><h3>Shore</h3><p>3 vessels · $49 / month</p></div>
          <div class="panel"><h3>Fleet</h3><p>25 vessels · $189 / month</p></div>
          <div class="panel"><h3>Armada</h3><p>Unlimited · talk to sales</p></div>
        </div>
        <p class="note">Rendered by the edge. Compare <code>X-Cache</code> and <code>X-Cache-Key</code>.</p>"""
        return shell("Pricing", body + leak, head=head).get_data(as_text=True)

    now = time.monotonic()
    key = cache_key()
    entry = CACHE.get(key)
    state = "HIT" if entry and entry[1] > now else "MISS"
    if state == "HIT":
        response = lab.app.response_class(entry[0], mimetype="text/html")
        ttl_left = entry[1] - now
    else:
        document_html = render()
        CACHE[key] = (document_html, now + TTL)
        response = lab.app.response_class(document_html, mimetype="text/html")
        ttl_left = TTL
    response.headers["X-Cache"] = state
    response.headers["X-Cache-Key"] = key
    response.headers["X-Cache-TTL"] = str(max(0, int(ttl_left)))
    response.headers["Cache-Control"] = f"public, max-age={int(TTL)}"
    return response


@app.get("/cache")
def cache_view():
    now = time.monotonic()
    rows = "".join(
        f'<li><code>{html.escape(key)}</code> · <span class="dim">ttl {max(0, int(expires - now))}s</span></li>'
        for key, (_, expires) in CACHE.items()
    ) or '<li class="dim">Cache is empty.</li>'
    stored = CACHE.get("/page")
    preview = f'<h3>Stored /page document</h3><pre>{html.escape(stored[0])}</pre>' if stored else ""
    return shell(
        "Edge cache state",
        f'<div class="panel"><h2>Path-keyed cache</h2><ul class="list">{rows}</ul>{preview}</div><p><a href="/cache/reset">Purge cache</a></p>',
    )


@app.get("/cache/reset")
def cache_reset():
    CACHE.clear()
    return lab.redirect("/cache")


@app.get("/collect")
def collect():
    value = request.args.get("c", "") or request.get_data(as_text=True)
    if value:
        CAPTURED.append(value[:2000])
        if lab.flag("flag") in value:
            lab.objective_async("flag", "cached payload reached the collector")
    return ("", 204)


@app.get("/captured")
def captured():
    rows = "".join(f'<li><code>{html.escape(v)}</code></li>' for v in CAPTURED) or '<li class="dim">Nothing captured yet.</li>'
    return shell("Captured data", f'<div class="panel"><h2>Collector</h2><ul class="list">{rows}</ul></div>')


if __name__ == "__main__":
    lab.run()