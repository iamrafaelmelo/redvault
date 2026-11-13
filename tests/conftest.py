"""Test fixtures for standalone vulnerable labs.

Each test receives a fresh Flask process on an ephemeral loopback port. The
tests use the same LAB_FLAGS contract as the platform, but never the platform's
real derived flag values.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REAL_DATA = (ROOT / "data").resolve()
# Standalone lab tests never import ``app``; they still get a throwaway data
# directory so the application is never configured against the real database.
if "REDVAULT_DATA" not in os.environ:
    os.environ["REDVAULT_DATA"] = tempfile.mkdtemp(prefix="redvault-tests-")


def pytest_configure(config) -> None:
    configured = os.environ.get("REDVAULT_DATA")
    if configured is None:
        raise SystemExit(
            "Refusing to run tests: REDVAULT_DATA is not set, so the suite would "
            f"write into the real database at {REAL_DATA}. Import the app only "
            "after pointing REDVAULT_DATA at a temporary directory."
        )
    resolved = Path(configured).resolve()
    if resolved == REAL_DATA or REAL_DATA in resolved.parents:
        raise SystemExit(
            f"Refusing to run tests against the operator database ({resolved}). "
            "Point REDVAULT_DATA at a temporary directory instead."
        )


import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]
LABS = ROOT / "labs"
SHARED = LABS / "_shared"

SLUG_BY_TEST = {
    "test_access_bfla_admin": "access-bfla-admin",
    "test_access_bola_accounts": "access-bola-accounts",
    "test_access_idor_invoices": "access-idor-invoices",
    "test_access_mass_assignment": "access-mass-assignment",
    "test_access_method_override": "access-method-override",
    "test_access_tenant_header": "access-tenant-header",
    "test_adv_cache_deception": "adv-cache-deception",
    "test_adv_cache_poison_header": "adv-cache-poison-header",
    "test_api_excessive_data": "api-excessive-data",
    "test_api_pagination_leak": "api-pagination-leak",
    "test_api_version_downgrade": "api-version-downgrade",
    "test_auth_jwt_alg_confusion": "auth-jwt-alg-confusion",
    "test_auth_jwt_kid_traversal": "auth-jwt-kid-traversal",
    "test_auth_jwt_weak_key": "auth-jwt-weak-key",
    "test_auth_otp_bruteforce": "auth-otp-bruteforce",
    "test_auth_reset_host": "auth-reset-host",
    "test_auth_session_fixation": "auth-session-fixation",
    "test_auth_username_enum": "auth-username-enum",
    "test_chain_idor_to_admin": "chain-idor-to-admin",
    "test_chain_sqli_to_admin": "chain-sqli-to-admin",
    "test_chain_ssrf_internal": "chain-ssrf-internal",
    "test_chain_upload_to_rce": "chain-upload-to-rce",
    "test_client_cors_reflect": "client-cors-reflect",
    "test_client_postmessage": "client-postmessage",
    "test_command_ping": "command-ping",
    "test_lfi_document_reader": "lfi-document-reader",
    "test_logic_coupon_stack": "logic-coupon-stack",
    "test_logic_negative_cart": "logic-negative-cart",
    "test_logic_race_withdraw": "logic-race-withdraw",
    "test_logic_refund_abuse": "logic-refund-abuse",
    "test_logic_workflow_skip": "logic-workflow-skip",
    "test_machine_fintech_support": "machine-fintech-support",
    "test_machine_insurance_claims": "machine-insurance-claims",
    "test_machine_logistics_api": "machine-logistics-api",
    "test_machine_meridian_bank": "machine-meridian-bank",
    "test_machine_nexus_commerce": "machine-nexus-commerce",
    "test_realistic_horizon_health": "realistic-horizon-health",
    "test_recon_api_docs": "recon-api-docs",
    "test_recon_backup_vault": "recon-backup-vault",
    "test_recon_cloud_listing": "recon-cloud-listing",
    "test_recon_js_bundle": "recon-js-bundle",
    "test_recon_source_map": "recon-source-map",
    "test_server_blind_cmdi": "server-blind-cmdi",
    "test_server_nosql_auth": "server-nosql-auth",
    "test_server_ssrf_webhook": "server-ssrf-webhook",
    "test_server_xxe_reader": "server-xxe-reader",
    "test_sqli_blind_boolean": "sqli-blind-boolean",
    "test_sqli_login_bypass": "sqli-login-bypass",
    "test_sqli_second_order": "sqli-second-order",
    "test_sqli_union_catalog": "sqli-union-catalog",
    "test_sqli_waf_bypass": "sqli-waf-bypass",
    "test_ssrf_image_fetcher": "ssrf-image-fetcher",
    "test_ssti_card": "ssti-card",
    "test_upload_filename_xss": "upload-filename-xss",
    "test_upload_svg_avatar": "upload-svg-avatar",
    "test_upload_zip_slip": "upload-zip-slip",
    "test_xss_attribute_injection": "xss-attribute-injection",
    "test_xss_blind_support": "xss-blind-support",
    "test_xss_dom_hash": "xss-dom-hash",
    "test_xss_reflected_search": "xss-reflected-search",
    "test_xss_stored_guestbook": "xss-stored-guestbook",
    "test_xss_csp_nonce_bypass": "xss-csp-nonce-bypass",
    "test_xss_dom_clobber": "xss-dom-clobber",
    "test_client_prototype_pollution": "client-prototype-pollution",
    "test_client_clickjacking_frame": "client-clickjacking-frame",
    "test_api_graphql_field_auth": "api-graphql-field-auth",
    "test_upload_archive_traversal": "upload-archive-traversal",
    "test_upload_content_type_confusion": "upload-content-type-confusion",
    "test_upload_polyglot_image": "upload-polyglot-image",
    "test_xss_csp_jsonp": "xss-csp-jsonp",
    "test_auth_jwt_jku_injection": "auth-jwt-jku-injection",
    "test_machine_saas_admin_console": "machine-saas-admin-console",
    "test_machine_hr_onboarding": "machine-hr-onboarding",
    "test_logic_coupon_race": "logic-coupon-race",
    "test_logic_signup_bonus_loop": "logic-signup-bonus-loop",
    "test_logic_approval_self": "logic-approval-self",
    "test_logic_cart_quantity_rounding": "logic-cart-quantity-rounding",
    "test_logic_invite_reuse": "logic-invite-reuse",
    "test_auth_password_reset_poison": "auth-password-reset-poison",
    "test_auth_mfa_bypass_response": "auth-mfa-bypass-response",
    "test_auth_sso_assertion_replay": "auth-sso-assertion-replay",
    "test_access_http_parameter_pollution": "access-http-parameter-pollution",
    "test_access_trust_proxy_header": "access-trust-proxy-header",
    "test_chain_open_redirect_to_token_theft": "chain-open-redirect-to-token-theft",
    "test_chain_lfi_to_rce": "chain-lfi-to-rce",
    "test_chain_xss_to_csrf_admin": "chain-xss-to-csrf-admin",
    "test_chain_jwt_to_sqli": "chain-jwt-to-sqli",
    "test_chain_ssti_to_flask_config": "chain-ssti-to-flask-config",
    "test_adv_http_host_header_reset": "adv-http-host-header-reset",
    "test_adv_csrf_token_reuse": "adv-csrf-token-reuse",
    "test_adv_cache_key_normalization": "adv-cache-key-normalization",
    "test_client_websocket_csrf": "client-websocket-csrf",
    "test_api_batch_endpoint_auth": "api-batch-endpoint-auth",
    "test_server_ssti_jinja_sandbox": "server-ssti-jinja-sandbox",
    "test_server_deserialization_pickle": "server-deserialization-pickle",
}


def pytest_generate_tests(metafunc):
    if "lab" not in metafunc.fixturenames:
        return
    name = metafunc.function.__name__
    if name not in SLUG_BY_TEST:
        raise pytest.UsageError(f"no lab slug mapped for {name}")
    metafunc.parametrize("lab", [SLUG_BY_TEST[name]], indirect=True)



def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest.fixture()
def lab(request):
    slug = request.param
    lab_dir = LABS / slug
    port = free_port()
    state = Path(os.environ.get("PYTEST_TMPDIR", "/tmp")) / f"rv-test-{slug}-{port}"
    state.mkdir(parents=True, exist_ok=True)
    flags = {key: f"RV{{test_{slug}_{key}}}" for key in ("flag", "user", "api", "root", "bonus", "hidden")}
    env = os.environ.copy()
    env.update(
        {
            "LAB_PORT": str(port),
            "LAB_STATE_DIR": str(state),
            "LAB_FLAGS": json.dumps(flags),
            "LAB_CALLBACK_TOKEN": "",
            "LAB_CALLBACK_URL": "",
            "PYTHONPATH": str(SHARED),
            "PYTHONUNBUFFERED": "1",
        }
    )
    log = state / "app.log"
    handle = log.open("ab")
    process = subprocess.Popen(
        [sys.executable, str(SHARED / "serve_lab.py"), "--serve", str(lab_dir / "app.py")],
        cwd=str(lab_dir),
        env=env,
        stdout=handle,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )
    base = f"http://127.0.0.1:{port}"
    deadline = time.time() + 12
    ready = False
    while time.time() < deadline:
        if process.poll() is not None:
            break
        try:
            if httpx.get(f"{base}/health", timeout=0.4).status_code == 200:
                ready = True
                break
        except httpx.HTTPError:
            pass
        time.sleep(0.15)
    if not ready:
        handle.close()
        process.terminate()
        output = log.read_text(errors="replace")[-3000:] if log.exists() else ""
        pytest.fail(f"lab {slug} failed to start\n{output}")
    yield {"base": base, "port": port, "slug": slug, "flags": flags, "state": state, "client": httpx.Client(base_url=base, follow_redirects=True, timeout=10)}
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass
    handle.close()
    import shutil

    shutil.rmtree(state, ignore_errors=True)


def flag_payload(lab, key: str = "flag") -> str:
    return lab["flags"][key]
