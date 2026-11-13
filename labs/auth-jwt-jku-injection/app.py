from __future__ import annotations

import base64
import hashlib
import json
import re
import subprocess
import tempfile
import urllib.request
from pathlib import Path

from flask import Response, request

from labkit import Lab

lab = Lab("HARBORLINE", accent="#c3a6ff")
app = lab.app

KEY_DIR = lab.state_dir / "keys"
KEY_DIR.mkdir(parents=True, exist_ok=True)
PRIVATE_PEM = KEY_DIR / "signing-private.pem"
PUBLIC_PEM = KEY_DIR / "signing-public.pem"
TRUSTED_JWKS = KEY_DIR / "trusted-jwks.json"
KID = "harborline-2026"

if not PRIVATE_PEM.exists():
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


def b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def key_material(pem: str, kid: str) -> dict[str, str]:
    """Build a JWK (kid, kty, n, e) from an RSA public PEM using openssl output."""
    text = subprocess.run(
        ["openssl", "rsa", "-pubin", "-in", "/dev/stdin", "-noout", "-modulus", "-text"],
        input=pem.encode(),
        capture_output=True,
        check=True,
    ).stdout.decode("utf-8", "replace")
    modulus_hex = text.split("Modulus=", 1)[1].split("\n", 1)[0].strip()
    exponent = 65537
    for line in text.splitlines():
        if line.startswith("publicExponent:"):
            exponent = int(line.split(":", 1)[1].strip())
            break
    modulus = int(modulus_hex, 16)
    octets = modulus.to_bytes((modulus.bit_length() + 7) // 8, "big")
    exponent_octets = exponent.to_bytes((exponent.bit_length() + 7) // 8, "big")
    return {"kty": "RSA", "kid": kid, "alg": "RS256", "use": "sig", "n": b64url(octets), "e": b64url(exponent_octets)}


def issue_token(claims: dict) -> str:
    header_segment = b64url(json.dumps({"alg": "RS256", "typ": "JWT", "kid": KID}, separators=(",", ":")).encode())
    payload_segment = b64url(json.dumps(claims, separators=(",", ":")).encode())
    signing_input = f"{header_segment}.{payload_segment}".encode()
    signature = subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", str(PRIVATE_PEM)],
        input=signing_input,
        capture_output=True,
        check=True,
    ).stdout
    return f"{header_segment}.{payload_segment}.{b64url(signature)}"


def fetch_jwks(location: str) -> dict | None:
    """Fetch a key set. The lab runs on loopback only, so this is bounded to it."""
    if not re.fullmatch(r"http://127\.0\.0\.1:\d{1,5}/[A-Za-z0-9_./?=&%-]*", location):
        return None
    try:
        with urllib.request.urlopen(location, timeout=3) as response:
            if response.status != 200:
                return None
            return json.loads(response.read().decode() or "{}")
    except Exception:  # noqa: BLE001 - unreachable key sets invalidate the token
        return None


def verify_rs256(signing_input: bytes, signature: bytes, public_pem: str) -> bool:
    with tempfile.TemporaryDirectory() as workdir:
        key_path = Path(workdir) / "pub.pem"
        sig_path = Path(workdir) / "sig.bin"
        data_path = Path(workdir) / "data.bin"
        key_path.write_text(public_pem)
        sig_path.write_bytes(signature)
        data_path.write_bytes(signing_input)
        result = subprocess.run(
            ["openssl", "dgst", "-sha256", "-verify", str(key_path), "-signature", str(sig_path), str(data_path)],
            capture_output=True,
        )
    return result.returncode == 0


def jwk_to_pem(jwk: dict) -> str | None:
    try:
        n = int.from_bytes(b64url_decode(jwk["n"]), "big")
        e = int.from_bytes(b64url_decode(jwk["e"]), "big")
    except (KeyError, ValueError):
        return None
    # Minimal DER for SubjectPublicKeyInfo wrapping RSAPublicKey, then PEM.
    def der_len(length: int) -> bytes:
        if length < 0x80:
            return bytes([length])
        raw = length.to_bytes((length.bit_length() + 7) // 8, "big")
        return bytes([0x80 | len(raw)]) + raw

    def der_int(value: int) -> bytes:
        raw = value.to_bytes((value.bit_length() + 7) // 8 or 1, "big")
        if raw[0] & 0x80:
            raw = b"\x00" + raw
        return b"\x02" + der_len(len(raw)) + raw

    rsapublickey = der_int(n) + der_int(e)
    rsapublickey = b"\x30" + der_len(len(rsapublickey)) + rsapublickey
    algorithm = bytes.fromhex("300d06092a864886f70d0101010500")
    bitstring = b"\x03" + der_len(1 + len(rsapublickey)) + b"\x00" + rsapublickey
    spki = algorithm + bitstring
    spki = b"\x30" + der_len(len(spki)) + spki
    encoded = base64.encodebytes(spki).decode("ascii")
    return "-----BEGIN PUBLIC KEY-----\n" + encoded + "-----END PUBLIC KEY-----\n"


def verify_token(token: str) -> dict | None:
    if not token or token.count(".") != 2:
        return None
    header_segment, payload_segment, signature_segment = token.split(".")
    try:
        header = json.loads(b64url_decode(header_segment))
        claims = json.loads(b64url_decode(payload_segment))
        signature = b64url_decode(signature_segment)
    except (ValueError, json.JSONDecodeError):
        return None
    if header.get("alg") != "RS256":
        return None
    key_set = None
    if "jku" in header:
        # VULNERABLE: the key set location is taken from the token header and not
        # checked against the pinned identity provider origin.
        key_set = fetch_jwks(str(header["jku"]))
    if key_set is None:
        key_set = json.loads(TRUSTED_JWKS.read_text())
    kid = header.get("kid", "")
    for jwk in key_set.get("keys", []):
        if jwk.get("kid") != kid or jwk.get("kty") != "RSA":
            continue
        pem = jwk_to_pem(jwk)
        if not pem:
            continue
        if verify_rs256(f"{header_segment}.{payload_segment}".encode(), signature, pem):
            return claims
    return None


TRUSTED_JWKS.write_text(json.dumps({"keys": [key_material(PUBLIC_PEM.read_text(), KID)]}))


def shell(title: str, body: str, status: int = 200) -> object:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">HARBORLINE // IDENTITY GATEWAY</div><h1>{title}</h1></div>{body}',
        nav='<a href="/">Status</a><a href="/login?username=guest">Guest token</a><a href="/.well-known/jwks.json">JWKS</a><a href="/admin">Fleet console</a>',
        status=status,
    )


@app.get("/")
def index():
    token = request.cookies.get("hl_token", "")
    claims = verify_token(token) if token else None
    role = claims.get("role", "anonymous") if claims else "anonymous"
    return shell(
        "Gateway status",
        f"""<div class="panel"><h2>Session role: {role}</h2>
        <p>Harborline issues RS256 access tokens. The gateway signs with <code>kid={KID}</code> and
        verifies using the key set named by the token's <code>jku</code> header so rotating identity
        providers stay self-describing.</p></div>""",
    )


@app.get("/login")
def login():
    if request.args.get("username", "") != "guest":
        return shell("Guest access", '<div class="flash err">Only the demo guest account is self-service.</div>', status=401)
    token = issue_token({"sub": "guest", "role": "guest", "iss": "harborline"})
    response = shell(
        "Guest token",
        f"""<div class="panel"><h2>Signed in as guest</h2>
        <p>Token stored in the <code>hl_token</code> cookie.</p><pre>{token}</pre></div>""",
    )
    response.set_cookie("hl_token", token, httponly=True, samesite="Lax")
    return response


@app.get("/.well-known/jwks.json")
def jwks():
    return Response(TRUSTED_JWKS.read_text(), mimetype="application/json")


@app.get("/admin")
def admin():
    token = request.cookies.get("hl_token", "")
    claims = verify_token(token) if token else None
    if not claims or claims.get("role") != "admin":
        return shell("Access denied", '<div class="flash err">An administrator access token is required.</div>', status=403)
    return shell(
        "Fleet console",
        f'<div class="panel"><h2>Harborline fleet</h2><p>Signed in as <code>{claims.get("sub")}</code>.</p><pre>{lab.flag("flag")}</pre></div>',
    )


@app.get("/attacker/jwks")
def attacker_jwks():
    # A key set published by an external tenant (written to the shared state
    # directory by the attacker tooling). The gateway fetches it whenever a token
    # names this URL in its jku header, which is exactly what pinning should stop.
    keyset = lab.read_state("attacker-keyset.json")
    if not keyset:
        return Response('{"keys": []}', mimetype="application/json")
    return Response(keyset, mimetype="application/json")


if __name__ == "__main__":
    lab.run()