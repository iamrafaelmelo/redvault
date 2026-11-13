from __future__ import annotations

import base64
import hashlib
import hmac
import json
from pathlib import Path

from flask import Response, request, session

from labkit import Lab

lab = Lab("CIPHERLINE", accent="#8ec5ff")
app = lab.app

KEY_DIR = lab.state_dir / "keys"
KEY_DIR.mkdir(parents=True, exist_ok=True)
PRIVATE_PEM = KEY_DIR / "signing-private.pem"
PUBLIC_PEM = KEY_DIR / "signing-public.pem"

# Per-process RSA key pair. Cryptography is not a lab dependency, so use the
# openssl CLI to generate the pair once and never expose the private key.
if not PRIVATE_PEM.exists():
    import subprocess

    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(PRIVATE_PEM)],
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["openssl", "rsa", "-in", str(PRIVATE_PEM), "-pubout", "-out", str(PUBLIC_PEM)],
        check=True,
        capture_output=True,
    )
PUBLIC_KEY = PUBLIC_PEM.read_text().strip() + "\n"


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def sign_rs256(header: dict, payload: dict) -> str:
    header_segment = b64url(json.dumps(header, separators=(",", ":")).encode())
    payload_segment = b64url(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{header_segment}.{payload_segment}".encode()
    import subprocess

    raw = subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", str(PRIVATE_PEM)],
        input=signing_input,
        capture_output=True,
        check=True,
    ).stdout
    return f"{header_segment}.{payload_segment}.{b64url(raw)}"


def verify_token(token: str) -> dict | None:
    if not isinstance(token, str) or token.count(".") != 2:
        return None
    header_segment, payload_segment, signature = token.split(".")
    try:
        header = json.loads(b64url_decode(header_segment))
        claims = json.loads(b64url_decode(payload_segment))
        signature_raw = b64url_decode(signature)
    except (ValueError, json.JSONDecodeError):
        return None
    signing_input = f"{header_segment}.{payload_segment}".encode()
    alg = header.get("alg")
    if alg == "RS256":
        import subprocess
        import tempfile

        with tempfile.NamedTemporaryFile() as sig_file:
            sig_file.write(signature_raw)
            sig_file.flush()
            result = subprocess.run(
                ["openssl", "dgst", "-sha256", "-verify", str(PUBLIC_PEM), "-signature", sig_file.name],
                input=signing_input,
                capture_output=True,
            )
        if result.returncode == 0:
            return claims
        return None
    if alg == "HS256":
        # VULNERABLE: algorithm confusion. The verifier lets the token choose the
        # algorithm and then reuses the RSA public key bytes as an HMAC secret.
        expected = b64url(hmac.new(PUBLIC_KEY.encode(), signing_input, hashlib.sha256).digest())
        if hmac.compare_digest(expected, signature):
            return claims
    return None


def shell(title: str, body: str, status: int = 200) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">CIPHERLINE // TOKEN GATEWAY</div><h1>{title}</h1></div>{body}',
        nav='<a href="/">Status</a><a href="/login?username=guest">Guest token</a><a href="/jwks">Public key</a><a href="/admin">Admin</a>',
        status=status,
    )


@app.get("/")
def index():
    token = request.cookies.get("jwt_session", "")
    claims = verify_token(token) if token else None
    role = claims.get("role", "anonymous") if claims else "anonymous"
    return shell(
        "Gateway status",
        f"""<div class="panel"><h2>Session role: {role}</h2>
        <p>Cipherline issues RS256 tokens and publishes the verification key. A legacy provider integrates with HS256 on the same verifier.</p>
        <p class="note">Guest tokens are self-service. Admin tokens are issued by the identity team.</p></div>""",
    )


@app.get("/login")
def login():
    username = request.args.get("username", "")
    if username != "guest":
        return shell(
            "Guest access",
            '<div class="flash err">Only the demo guest account is self-service.</div>',
            status=401,
        )
    token = sign_rs256({"alg": "RS256", "typ": "JWT"}, {"sub": "guest", "role": "guest"})
    response = shell(
        "Guest token",
        f"""<div class="panel"><h2>Signed in as guest</h2>
        <p>Token set as the <code>jwt_session</code> cookie.</p><pre>{token}</pre>
        <p class="note">Header: <code>{{"alg":"RS256","typ":"JWT"}}</code>. The public key is at <a href="/jwks">/jwks</a>.</p></div>""",
    )
    response.set_cookie("jwt_session", token, httponly=True, samesite="Lax")
    return response


@app.get("/jwks")
def jwks():
    return Response(PUBLIC_KEY, mimetype="text/plain")


@app.get("/admin")
def admin():
    # VULNERABLE: the signature is never checked here; this console trusts the
    # identity that the gateway would have verified. Lab-only scaffold so the
    # exploit can be validated without a second process.
    token = request.cookies.get("jwt_session", "")
    claims = None
    if token.count(".") == 2:
        try:
            header_segment, payload_segment, _ = token.split(".")
            claims = json.loads(b64url_decode(payload_segment))
        except Exception:  # noqa: BLE001 - malformed tokens are simply rejected
            claims = None
    if not claims or claims.get("role") != "admin":
        return shell("Access denied", '<div class="flash err">An administrator token is required.</div>', status=403)
    return shell(
        "Administrator console",
        f'<div class="panel"><h2>Cipherline administration</h2><pre>{lab.flag("flag")}</pre></div>',
    )


if __name__ == "__main__":
    lab.run()