from __future__ import annotations

import html
from pathlib import Path

from flask import request
from jinja2.exceptions import SecurityError
from jinja2.sandbox import SandboxedEnvironment

from labkit import Lab

lab = Lab("PAPERFORM", accent="#8b9df7")
app = lab.app

_FLAG_FILE = Path("/tmp/redvault-ssti-jinja-sandbox.txt")
_FLAG_FILE.write_text(lab.flag("flag") + "\n")


def money(value: object) -> str:
    try:
        return f"${float(value):,.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def slugline(value: object) -> str:
    return "-".join(str(value).lower().split())


def branding_prefix() -> str:
    """Branding prefix rendered next to every invoice."""
    return "PAPERFORM · invoice rendering"


# VULNERABLE: the billing team patched the sandbox in place so its preview
# snippets could introspect helpers. Letting underscores through except for a
# short deny-list re-opens the generic escape the sandbox exists to prevent:
# ``__globals__`` exposes module globals and ``__subclasses__`` exposes every
# loaded class.
class PermissiveSandbox(SandboxedEnvironment):
    DENIED = {"__mro__", "__bases__", "__code__", "__reduce__", "__reduce_ex__"}

    def is_safe_attribute(self, obj, attr: str, value) -> bool:
        if getattr(attr, "startswith", lambda _prefix: False)("_"):
            return attr not in self.DENIED
        return True


env = PermissiveSandbox(autoescape=True)
env.filters.update(money=money, slugline=slugline)

TEMPLATES: dict[str, str] = {
    "invoice": "Invoice {{ invoice_id }} for {{ customer }} — total {{ total | money }}. — {{ branding() }}",
    "reminder": "Hi {{ customer }}, invoice {{ invoice_id }} is due in {{ days }} days ({{ total | money }}).",
    "receipt": "Payment received from {{ customer }}. Thank you. — {{ branding() }}",
}

STATE = {"invoice_id": "INV-2026-0431", "customer": "Kestrel Logistics", "total": 1420.5, "days": 7}


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">PAPERFORM // BILLING TEMPLATES</div><h1>{title}</h1></div>{body}',
        nav='<a href="/">Preview</a><a href="/sandbox">Sandbox notes</a>',
    )


@app.get("/")
def index():
    return shell(
        "Template preview",
        """<div class="panel"><h2>Preview a billing template</h2>
        <p>Billing operators maintain the customer-facing templates. Previews render through a Jinja
        <code>SandboxedEnvironment</code>, so anything the sandbox does not allow is rejected.</p>
        <form method="get" action="/preview">
          <label>Template</label><input name="template" value="invoice">
          <label>Template body (optional override)</label><textarea name="body" rows="4" placeholder="Leave empty to use the stored template"></textarea>
          <p><button type="submit">Render preview</button></p>
        </form></div>
        <div class="panel"><h2>Stored templates</h2><ul class="list">
        <li><code>invoice</code> · Invoice, customer total and branding</li>
        <li><code>reminder</code> · Payment reminder with the due date</li>
        <li><code>receipt</code> · Payment received acknowledgement</li>
        </ul></div>""",
    )


@app.get("/preview")
def preview():
    name = request.args.get("template", "invoice")
    override = request.args.get("body", "")
    # VULNERABLE: an operator-supplied body is compiled as a template inside the
    # "sandbox".
    source = override.strip() if isinstance(override, str) and override.strip() else TEMPLATES.get(name, "")
    rendered = ""
    error = ""
    if source:
        try:
            template = env.from_string(source)
            template.globals.setdefault("branding", branding_prefix)
            rendered = template.render(**STATE)
        except SecurityError as exc:
            error = f'<div class="flash err">Sandbox blocked this template: <code>{html.escape(str(exc))}</code></div>'
        except Exception as exc:  # noqa: BLE001 - preview errors shown to the operator
            error = (
                f'<div class="flash err">Render error: '
                f'<code>{html.escape(type(exc).__name__)}</code></div>'
            )
        if lab.flag("flag") in rendered:
            lab.objective_async("flag", "the Jinja sandbox was escaped through an exposed helper's globals")
    return shell(
        "Rendered preview",
        f'<div class="panel"><h2>Preview output</h2><pre>{html.escape(rendered) or "(empty)"}</pre></div>{error}',
    )


@app.get("/sandbox")
def sandbox_notes():
    return shell(
        "Sandbox notes",
        """<div class="panel"><h2>How templates run</h2>
        <p>Templates render in <code>jinja2.sandbox.SandboxedEnvironment</code> with autoescaping enabled.
        Helpers available to templates:</p>
        <ul class="list">
          <li><code>branding()</code> — tenant branding prefix</li>
          <li><code>money</code> / <code>slugline</code> — formatting filters</li>
        </ul>
        <p class="note">The sandbox allow-list was customised so billing previews can introspect
        helpers. The templates come from trusted operators, so the risk was accepted.</p></div>""",
    )


if __name__ == "__main__":
    lab.run()