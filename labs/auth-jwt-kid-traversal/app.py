from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json

from flask import Response, redirect, request

from labkit import Lab

lab = Lab("GLACIER ID", accent="#63b3ed")
app = lab.app

PUBLIC_VALUE = "rv-public-kid-2026"
GUEST_KEY = "rv-guest-signing-key-2026"

lab.write_state("keys/guest.key", GUEST_KEY)
lab.write_state("public.txt", PUBLIC_VALUE)


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def sign_token(header: dict, payload: dict, key: bytes) -> str:
    header_segment = b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_segment = b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_segment}.{payload_segment}".encode()
    signature = b64url(hmac.new(key, signing_input, hashlib.sha256).digest())
    return f"{header_segment}.{payload_segment}.{signature}"


def verify_token(token: str) -> dict | None:
    try:
        header_segment, payload_segment, signature = token.split(".")
        header = json.loads(b64url_decode(header_segment))
        claims = json.loads(b64url_decode(payload_segment))
    except (ValueError, binascii.Error, json.JSONDecodeError):
        return None
    if header.get("alg") != "HS256":
        return None
    kid = str(header.get("kid", ""))
    # VULNERABLE: kid is used as a filesystem path without allowlisting.
    key_path = lab.state_dir / "keys" / kid
    try:
        key = key_path.read_bytes()
    except OSError:
        return None
    expected = b64url(hmac.new(key, f"{header_segment}.{payload_segment}".encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, signature):
        return None
    return claims


def shell(title: str, body: str, status: int = 200) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">GLACIER // IDENTITY GATEWAY</div><h1>{title}</h1>'
        "<p>Federated access for the Glacier internal console.</p></div>"
        f"{body}",
        nav='<a href="/">Status</a><a href="/login">Guest login</a><a href="/admin">Admin</a><a href="/static/public.txt">Public key file</a>',
        status=status,
    )


@app.get("/")
def index():
    token = request.cookies.get("kid_token", "")
    claims = verify_token(token) if token else None
    role = claims.get("role", "anonymous") if claims else "anonymous"
    return shell(
        "Gateway status",
        f"""<div class="panel"><h2>Session role: {role}</h2>
        <p>Glacier issues short-lived HS256 tokens for guest access. Administrative tokens are signed with a key selected by the token's `kid` header.</p>
        <p class="note">The public key material at <a href="/static/public.txt">/static/public.txt</a> is published for integration testing.</p></div>""",
    )


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST" or request.args.get("username"):
        username = request.form.get("username", "") or request.args.get("username", "")
        if username == "guest":
            token = sign_token(
                {"alg": "HS256", "kid": "guest.key"},
                {"sub": "guest", "role": "guest"},
                GUEST_KEY.encode(),
            )
            response = shell(
                "Guest session",
                f"""<div class="panel"><h2>Signed in as guest</h2>
                <p>Your identity token is set as the <code>kid_token</code> cookie.</p>
                <pre>{token}</pre>
                <p class="dim mono">header: {{"alg":"HS256","kid":"guest.key"}} · role: guest</p></div>""",
            )
            response.set_cookie("kid_token", token, httponly=True, samesite="Lax")
            return response
        return shell(
            "Guest access",
            '<div class="flash err">Only the demo guest account is self-service.</div>' + login_form(),
            status=401,
        )
    return shell("Guest access", login_form())


def login_form() -> str:
    return """<div class="panel"><h2>Request a guest token</h2>
    <form method="post" action="/login">
      <label>Username</label><input name="username" value="guest">
      <p><button type="submit">Issue guest token</button></p>
    </form>
    <p class="note">Admin accounts are provisioned internally and are not available through this form.</p></div>"""


@app.get("/admin")
def admin():
    token = request.cookies.get("kid_token", "")
    claims = verify_token(token) if token else None
    if not claims or claims.get("role") != "admin":
        return shell(
            "Access denied",
            '<div class="flash err">An administrator token is required.</div>',
            status=403,
        )
    return shell(
        "Administrator console",
        f"""<div class="panel"><h2>Glacier administration</h2>
        <p>Role claim: <code>admin</code> · signature verified.</p>
        <pre>{lab.flag("flag")}</pre></div>""",
    )


@app.get("/static/public.txt")
def public_key_file():
    return Response(lab.read_state("public.txt"), mimetype="text/plain")


if __name__ == "__main__":
    lab.run()
