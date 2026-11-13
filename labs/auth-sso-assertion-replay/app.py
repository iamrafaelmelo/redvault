"""Helios SSO gateway — a deliberately vulnerable SAML-like assertion consumer.

This lab models the classic XML Signature Wrapping flaw with a dependency-free
profile: assertions are XML documents where the `<Signature>` element carries
`<SignedInfo>` (the canonical byte range of the `<Assertion>` element) and an
HMAC-SHA256 `<DigestValue>`. That is not real SAML (no XMLDSig, no canonicalised
C14N-Exclusive, no SHA-1/RSA), but the trust error is the same one that hits
real SAML SPs: the endpoint verifies a signature over one element and then reads
identity attributes from another element it never verified.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import html
import secrets
import xml.etree.ElementTree as ET

from flask import make_response, redirect, request

from labkit import Lab

lab = Lab("HELIOS SSO", accent="#a78bfa")
app = lab.app

# Key material for the internal IdP signing key (shared with the issuing IdP).
SIGNING_KEY = b"helios-idp-2026-assertion-signing-key"
SP_ENTITY = "https://helios-support.internal/sso/acs"


def signed_assertion_xml(username: str, role: str, email: str, name_id: str, assertion_id: str) -> str:
    return (
        '<Assertion xmlns="urn:helios:crm:assertion:1.0" ID="' + assertion_id + '">'
        f"<Subject><NameID>{name_id}</NameID></Subject>"
        f"<Attribute name=\"email\"><Value>{email}</Value></Attribute>"
        f"<Attribute name=\"role\"><Value>{role}</Value></Attribute>"
        f"<Attribute name=\"username\"><Value>{username}</Value></Attribute>"
        "</Assertion>"
    )


def canonical(element: ET.Element) -> str:
    """Text profile used as this lab's C14N stand-in: drop indentation and
    namespace declarations, serialise the element with ElementTree."""
    clone = ET.fromstring(ET.tostring(element, encoding="unicode"))
    for node in clone.iter():
        node.tail = None
    return ET.tostring(clone, encoding="unicode")


def digest_of(element: ET.Element) -> str:
    return hmac.new(SIGNING_KEY, canonical(element).encode(), hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# demo identity provider (browse to /idp/login to obtain a real signed response)
# ---------------------------------------------------------------------------
IDP_USERS = {
    "renner": {"password": "renner-demo-2026", "role": "user", "email": "renner@helios.local", "name_id": "renner@helios.local#2026"},
    "sp_admin": {"password": "not-for-humans", "role": "admin", "email": "sp_admin@helios.local", "name_id": "sp_admin@helios.local#svc"},
}


def build_response(username: str) -> str:
    user = IDP_USERS[username]
    assertion_id = "_" + secrets.token_hex(8)
    assertion = ET.fromstring(
        signed_assertion_xml(username, user["role"], user["email"], user["name_id"], assertion_id)
    )
    # The IdP signs the canonical form of exactly this assertion element.
    digest = digest_of(assertion)
    return (
        '<Response xmlns="urn:helios:crm:assertion:1.0" ID="_' + secrets.token_hex(6) + '">'
        '<Issuer>https://idp.helios.local/sso</Issuer>'
        f'<Destination>{SP_ENTITY}</Destination>'
        f'<Signature><SignedInfo><Reference URI="#{assertion_id}">'
        f"<DigestValue>{digest}</DigestValue></Reference></SignedInfo></Signature>"
        f"{ET.tostring(assertion, encoding='unicode')}"
        "</Response>"
    )


def b64(xml_text: str) -> str:
    return base64.b64encode(xml_text.encode()).decode()


def tag(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in list(element) if tag(child) == name]


def first_child(element: ET.Element, name: str) -> ET.Element | None:
    found = children(element, name)
    return found[0] if found else None


def text_of(element: ET.Element | None) -> str:
    return (element.text or "").strip() if element is not None else ""





def attributes_of(assertion: ET.Element) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for attribute in children(assertion, "Attribute"):
        attrs[attribute.get("name", "")] = text_of(first_child(attribute, "Value"))
    return attrs


def verify_envelope_signature(root: ET.Element) -> tuple[bool, str]:
    """Verify a detached HMAC signature over the assertion named by Reference URI."""
    signature = first_child(root, "Signature")
    if signature is None:
        return False, "envelope is not signed"
    signed_info = first_child(signature, "SignedInfo")
    reference = first_child(signed_info, "Reference") if signed_info is not None else None
    if reference is None:
        return False, "signature has no reference"
    digest_value = text_of(first_child(reference, "DigestValue"))
    uri = (reference.get("URI") or "").lstrip("#")
    for candidate in descendants(root, "Assertion"):
        if candidate.get("ID") == uri:
            expected = digest_of(candidate)
            if hmac.compare_digest(expected, digest_value):
                return True, uri
            return False, "digest mismatch"
    return False, "reference target missing"


def descendants(element: ET.Element, name: str) -> list[ET.Element]:
    return [node for node in element.iter() if tag(node) == name]


# ---------------------------------------------------------------------------
# relying party
# ---------------------------------------------------------------------------
SESSIONS: dict[str, dict[str, str]] = {}


def shell(title: str, body: str, nav: str | None = None) -> object:
    if nav is None:
        nav = '<a href="/">Support portal</a><a href="/idp/login">Demo IdP</a><a href="/debug/acs">ACS docs</a>'
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">HELIOS // FEDERATED SUPPORT</div><h1>{title}</h1></div>{body}',
        nav=nav,
    )


@app.get("/")
def index():
    return shell(
        "Helios Support",
        """<div class="panel"><h2>Partner SSO</h2>
        <p>Helios support staff sign in through the corporate identity provider. The gateway is at
        <code>/sso/acs</code>; the identity provider posts a base64 XML document in the <code>SAMLResponse</code>
        parameter, which may arrive in the query string or the body.</p>
        <p>The demo IdP at <code>/idp/login</code> issues a real signed response for the support account.</p></div>""",
    )


@app.route("/idp/login", methods=["GET", "POST"])
def idp_login():
    extra = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = IDP_USERS.get(username)
        if user and user["password"] == password:
            assertion = build_response(username)
            extra = (
                '<div class="flash ok">Authentication successful. Submit this assertion to the Helios ACS.</div>'
                f'<div class="panel"><h3>Raw XML</h3><pre>{html.escape(assertion)}</pre>'
                f'<h3>Base64 (SAMLResponse)</h3><pre>{html.escape(b64(assertion))}</pre></div>'
            )
        else:
            extra = '<div class="flash err">The identity provider rejected these credentials.</div>'
    return shell(
        "Demo identity provider",
        f"""<div class="panel"><h2>Corporate sign-in</h2>
        <form method="post"><label>UPN</label><input name="username"><label>Password</label><input name="password" type="password">
        <p><button type="submit">Authenticate</button></p></form>
        <p class="note">Training-only IdP credentials: <code>renner</code> / <code>renner-demo-2026</code>.</p></div>{extra}""",
    )


@app.route("/sso/acs", methods=["GET", "POST"])
def acs():
    raw = request.values.get("SAMLResponse", "")
    if not raw:
        return shell(
            "Assertion consumer",
            '<div class="flash err">No SAMLResponse parameter supplied.</div>'
            '<form method="post"><label>SAMLResponse (base64 XML)</label><textarea name="SAMLResponse" rows="6"></textarea>'
            '<p><button type="submit">Post to ACS</button></p></form>',
            ),
    try:
        xml_text = base64.b64decode(raw, validate=True).decode("utf-8")
        root = ET.fromstring(xml_text)
    except (ValueError, binascii.Error, ET.ParseError, UnicodeDecodeError) as exc:
        return shell("Broken assertion", f'<div class="flash err">The assertion could not be parsed: {html.escape(str(exc))}</div>')

    if tag(root) != "Response":
        return shell("Unexpected document", '<div class="flash err">The ACS expects a Response envelope.</div>')

    verified, detail = verify_envelope_signature(root)
    if not verified:
        return shell(
            "Untrusted assertion",
            f'<div class="flash err">The response did not validate: {html.escape(detail)}. Ask the IdP to re-issue it.</div>',
        )

    # VULNERABLE: the session identity comes from the first <Assertion> found in
    # the envelope — which need not be the element the signature covered.
    assertion = None
    for candidate in descendants(root, "Assertion"):
        assertion = candidate
        break
    if assertion is None:
        return shell("Empty assertion", '<div class="flash err">No assertion was carried in the response.</div>')

    attrs = attributes_of(assertion)
    session_id = secrets.token_urlsafe(18)
    SESSIONS[session_id] = {
        "username": attrs.get("username", "unknown"),
        "role": attrs.get("role", "user"),
        "email": attrs.get("email", ""),
        "name_id": text_of(first_child(first_child(assertion, "Subject"), "NameID")),
    }
    resp = make_response(redirect("/portal"))
    resp.set_cookie("helios_session", session_id, httponly=True, samesite="Lax")
    return resp


@app.get("/portal")
def portal():
    session_id = request.cookies.get("helios_session", "")
    user = SESSIONS.get(session_id)
    if not user:
        return shell("Not signed in", '<div class="flash">Open the ACS with a signed assertion first.</div>')
    flag = ""
    if user["role"] == "admin":
        lab.objective_async("flag", "forged admin assertion accepted through the wrapping window")
        flag = f'<div class="panel"><h2>Helios partner console</h2><pre>{html.escape(lab.flag("flag"))}</pre></div>'
    return shell(
        "Support portal",
        f"""<div class="panel"><h2>Federated session</h2>
        <table><tr><th>UPN</th><td>{html.escape(user["username"])}</td></tr>
        <tr><th>Role</th><td>{html.escape(user["role"])}</td></tr>
        <tr><th>Email</th><td>{html.escape(user["email"])}</td></tr>
        <tr><th>NameID</th><td>{html.escape(user["name_id"])}</td></tr></table></div>{flag}""",
        nav='<a href="/portal">Portal</a><a href="/logout">Sign out</a>',
    )


@app.get("/debug/acs")
def acs_docs():
    return shell(
        "ACS notes",
        """<div class="panel"><h2>Assertion profile</h2>
        <p>Helios uses a light XML profile for partner IdPs: the <code>Response</code> carries a
        <code>Signature</code> whose <code>SignedInfo/Reference URI</code> names an <code>Assertion</code> and whose
        <code>DigestValue</code> is an HMAC-SHA256 over that assertion's serialised bytes. This is not on-the-wire
        SAML; it is a dependency-free model of the same trust boundary.</p>
        <p>The gateway verifies the digest for the referenced assertion, then builds the local session from an
        assertion in the envelope. The relay accepts the value through <code>request.values</code>, so it can be sent
        in the query string or as a form field.</p></div>""",
    )


@app.get("/logout")
def logout():
    resp = make_response(redirect("/"))
    resp.delete_cookie("helios_session")
    return resp


if __name__ == "__main__":
    lab.run()