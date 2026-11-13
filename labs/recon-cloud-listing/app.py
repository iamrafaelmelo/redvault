from __future__ import annotations

from flask import Response

from labkit import Lab

lab = Lab("VAULTLINE STORAGE", accent="#5aa9e6")
app = lab.app


def shell(title: str, body: str) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">VAULTLINE // OBJECT STORAGE</div><h1>{title}</h1>'
        "<p>A small S3-compatible console for the Vaultline research buckets.</p></div>"
        f"{body}",
        nav='<a href="/">Overview</a><a href="/storage/">Object browser</a>',
    )


@app.get("/")
def index():
    return shell(
        "Vaultline object storage",
        """<div class="grid">
        <div class="panel"><h2>Object browser</h2>
        <p>Browse the buckets that the research team keeps on the shared storage node. Listing is enabled while the migration audit is in progress.</p>
        <p><a class="btn" href="/storage/">Open storage browser</a></p></div>
        <div class="panel"><h2>Migration note</h2>
        <p>The `backups` bucket is retained for a final restore test. Archive it only after the audit sign-off.</p>
        <p class="note">Bucket ACLs were relaxed for the audit window. The storage console shows every object the node can list.</p></div>
        </div>""",
    )


@app.get("/storage/")
def storage_root():
    return shell(
        "Index of /storage",
        """<div class="panel"><h2>Buckets</h2>
        <table><tr><th>Name</th><th>Objects</th><th>Last modified</th></tr>
        <tr><td><a href="/storage/backups/">backups/</a></td><td>1</td><td>2026-11-02 03:14 UTC</td></tr>
        <tr><td><a href="/storage/public-assets/">public-assets/</a></td><td>3</td><td>2026-10-28 17:02 UTC</td></tr>
        </table>
        <p class="note">Object listing was enabled for the storage migration. Keys beginning with `prod.` are operational exports.</p></div>""",
    )


@app.get("/storage/backups/")
def backups():
    return shell(
        "Index of /storage/backups",
        """<div class="panel"><h2>Prefix: backups/</h2>
        <table><tr><th>Key</th><th>Size</th><th>Last modified</th></tr>
        <tr><td><a href="/storage/backups/prod.env">prod.env</a></td><td>418 B</td><td>2026-11-02 03:14 UTC</td></tr>
        </table>
        <p class="dim mono">bucket: backups · region: local · listing: public-read</p></div>""",
    )


@app.get("/storage/backups/prod.env")
def prod_env():
    content = f"""# Vaultline production environment (restore copy)
APP_ENV=production
S3_BUCKET=vaultline-prod
DATABASE_URL=postgresql://vaultline:__redacted__@db.internal:5432/vaultline
RELEASE_FLAG={lab.flag("flag")}
# Remove this object after the restore audit.
"""
    return Response(content, mimetype="text/plain")


@app.get("/storage/public-assets/")
def public_assets():
    return shell(
        "Index of /storage/public-assets",
        """<div class="panel"><h2>Prefix: public-assets/</h2>
        <table><tr><th>Key</th><th>Size</th></tr>
        <tr><td>logo.svg</td><td>1.8 KB</td></tr>
        <tr><td>status.json</td><td>96 B</td></tr>
        <tr><td>index.html</td><td>742 B</td></tr>
        </table></div>""",
    )


if __name__ == "__main__":
    lab.run()
