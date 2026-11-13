from __future__ import annotations

import html
import os
from datetime import datetime, timezone

from flask import request
from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateNotFound, TemplateSyntaxError

from labkit import Lab

lab = Lab("PAPERTRAIL OPS", accent="#9f7aea")
app = lab.app

WORKSPACE = lab.state_dir / "workspace"
PAGES = WORKSPACE / "pages"
LOGS = WORKSPACE / "logs"
ACCESS_LOG = LOGS / "access.log"

# The edge node keeps the operations secret in a service file. Real process, real
# file, written at startup by the lab itself.
_FLAG_FILE = "/tmp/redvault-chain-lfi-to-rce.txt"
_FLAG_PAYLOAD = lab.flag("flag")
with open(_FLAG_FILE, "w") as _handle:
    _handle.write(_FLAG_PAYLOAD + "\n")
os.chmod(_FLAG_FILE, 0o644)


def _seed_files() -> None:
    PAGES.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    if not (PAGES / "about.html").exists():
        (PAGES / "about.html").write_text(
            "<h2>About Papertrail Ops</h2><p>Papertrail Ops renders operational documents "
            "on the edge node: runbooks, service pages and release notes.</p>"
        )
    (PAGES / "release-notes.html").write_text(
        "<h2>Release 4.12</h2><ul><li>Reader moved to <code>/docs?page=</code></li>"
        "<li>Access logs are rotated into <code>logs/access.log</code></li>"
        "<li>Preview compiler now accepts a template name, not only an id</li></ul>"
    )
    if not ACCESS_LOG.exists():
        ACCESS_LOG.write_text(
            '10.0.0.8 - - [01/Jan/2026:09:00:00 +0000] "GET /docs?page=about.html HTTP/1.1" 200 - "-" "curl"\n'
            '10.0.0.9 - - [01/Jan/2026:09:01:12 +0000] "GET /health HTTP/1.1" 200 - "-" "uptime"\n'
        )


_seed_files()

# VULNERABLE: the preview compiler resolves arbitrary names against the state
# workspace and the application directory — the directory that holds this file,
# its flags and its Python modules.
class LegacyLoader(FileSystemLoader):
    """Search-path loader that also accepts relative names.

    Jinja's stock loader rejects '..' segments and absolute names on purpose. The
    preview compiler was migrated from a bespoke loader and kept the old lookup:
    a name with separators is joined onto each search root as-is.
    """

    def get_source(self, environment, template):  # noqa: ANN001, ANN201
        if template.startswith("/"):
            candidates = [template]
        elif ".." in template:
            candidates = [os.path.join(root, template) for root in self.searchpath]
        else:
            return super().get_source(environment, template)
        for filename in candidates:
            try:
                mtime = os.path.getmtime(filename)
                with open(filename, encoding="utf-8", errors="replace") as handle:
                    source = handle.read()
            except OSError:
                continue
            return source, filename, lambda: os.path.getmtime(filename) == mtime
        raise TemplateNotFound(template)


compiler_env = Environment(
    loader=LegacyLoader([str(PAGES), str(WORKSPACE), os.path.dirname(os.path.abspath(__file__))]),
    autoescape=False,
    cache_size=0,
)


def shell(title: str, body: str, nav: str | None = None) -> object:
    if nav is None:
        nav = (
            '<a href="/">Overview</a><a href="/docs?page=about.html">Docs</a>'
            '<a href="/logs">Logs</a><a href="/preview">Preview compiler</a>'
        )
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">PAPERTRAIL // OPS CONSOLE</div><h1>{title}</h1></div>{body}',
        nav=nav,
    )


@app.get("/")
def index():
    return shell(
        "Papertrail Ops",
        """<div class="panel"><h2>Edge node pt-01.ops.internal</h2>
        <p>Reader, log tail and the template preview compiler for the operations runbooks.</p>
        <div class="grid3">
          <div><h3>Reader</h3><p><code>/docs?page=about.html</code></p></div>
          <div><h3>Logs</h3><p><code>/logs</code> tails <code>logs/access.log</code></p></div>
          <div><h3>Preview</h3><p><code>/preview?template=release-notes.html</code></p></div>
        </div></div>
        <div class="terminal"><span class="p">opsteam@pt-01:~$</span> ./pt run --role edge<br>
        <span class="ok">[edge] reader.open() uses os.path.join(pages_root, page)</span><br>
        <span class="ok">[edge] preview.compile() searches the state workspace, then the app folder</span></div>""",
    )


@app.get("/docs")
def docs():
    page = request.args.get("page", "about.html")
    # VULNERABLE: request path traversal. os.path.join keeps absolute paths and
    # happily walks '..' segments out of the pages directory.
    target = page if page.startswith("/") else os.path.join(str(PAGES), page)
    content = ""
    error = ""
    try:
        with open(target, "r", errors="replace") as handle:
            content = handle.read(20000)
    except OSError as exc:
        error = f'<div class="flash err">Cannot read <code>{html.escape(page)}</code>: {html.escape(str(exc))}</div>'
    try:
        shown = os.path.relpath(target, str(WORKSPACE))
    except ValueError:
        shown = target
    return shell(
        "Document reader",
        f"""<div class="panel"><h2>Read a runbook</h2>
        <form method="get" action="/docs"><label>Page</label><input name="page" value="{html.escape(page)}">
        <p><button type="submit">Read</button></p></form>{error}
        <p class="note">Resolved: <code>workspace/{html.escape(shown)}</code></p>
        <pre>{html.escape(content) if content else "empty document"}</pre></div>""",
    )


@app.get("/logs")
def logs():
    try:
        body = "\n".join(ACCESS_LOG.read_text(errors="replace").splitlines()[-40:])
    except OSError:
        body = ""
    return shell(
        "Access log",
        f"""<div class="panel"><h2>logs/access.log</h2>
        <p>The edge webserver appends one line per request to the shared operations log.</p>
        <pre>{html.escape(body or "(empty)")}</pre></div>""",
    )


@app.get("/preview")
def preview():
    name = request.args.get("template", "release-notes.html")
    output = ""
    error = ""
    body = ""
    if name:
        try:
            # VULNERABLE: any file the compiler can resolve is treated as a Jinja
            # template and executed server-side.
            source, _, _uptodate = compiler_env.loader.get_source(compiler_env, name)
            # Non-page sources (logs, fragments) are rendered and shown verbatim so
            # their output can be inspected in the preview pane.
            output = str(compiler_env.from_string(source).render())
            output = output.encode("utf-8", "surrogatepass").decode("utf-8", "replace")
        except TemplateNotFound:
            error = f'<div class="flash err">Template not found: <code>{html.escape(name)}</code></div>'
        except TemplateSyntaxError as exc:
            error = f'<div class="flash err">Compile error: <code>{html.escape(str(exc))[:600]}</code></div>'
        except Exception as exc:  # noqa: BLE001 - compiler diagnostics in the UI
            error = f'<div class="flash err">Render error: <code>{html.escape(type(exc).__name__)}: {html.escape(str(exc))[:600]}</code></div>'
    if lab.flag("flag") in output:
        lab.objective_async("flag", "LFI -> log injection -> template compile -> shell read of the flag file")
    return shell(
        "Preview compiler",
        f"""<div class="panel"><h2>Compile a template</h2>
        <form method="get" action="/preview"><label>Template name</label>
        <input name="template" value="{html.escape(name)}" size="60">
        <p><button type="submit">Compile</button></p></form>{error}
        <p class="note">Names are resolved under the state workspace and the application folder.</p>
        <h3>Output</h3><pre>{output}</pre></div>""",
    )


@app.after_request
def access_log(response):  # noqa: ANN001, ANN201
    if request.path == "/health":
        return response
    stamp = datetime.now(timezone.utc).strftime("%d/%b/%Y:%H:%M:%S")
    agent = request.headers.get("User-Agent", "-")[:160] or "-"
    referer = request.headers.get("Referer", "-")[:160] or "-"
    # VULNERABLE: the user agent and referer are concatenated into the operations
    # log without escaping, and that log sits inside the template search path.
    line = (
        f'10.0.0.8 - - [{stamp} +0000] "{request.method} {request.path} HTTP/1.1" '
        f'{response.status_code} - "{referer}" "{agent}"\n'
    )
    try:
        with ACCESS_LOG.open("a") as handle:
            handle.write(line)
    except OSError:
        pass
    return response


if __name__ == "__main__":
    lab.run()