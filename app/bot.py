"""Headless Chromium worker used by XSS labs.

The bot only accepts loopback URLs on the port of the lab session that requested
it. It sets an intentionally-readable victim cookie, visits the target and lets
the lab collect the exfiltrated data itself. It never returns page contents.
"""
from __future__ import annotations

import ipaddress
import threading
import time
from urllib.parse import urlparse

from .config import BOT_ENABLED, BOT_TIMEOUT, CHROMEDRIVER

_lock = threading.Lock()
_last_error = ""


class BotError(RuntimeError):
    pass


def _driver():
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service

    options = Options()
    for arg in (
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-extensions",
        "--disable-background-networking",
        "--disable-sync",
        "--no-first-run",
        "--window-size=1280,900",
        "--user-agent=REDVAULT-AdminBot/1.0",
    ):
        options.add_argument(arg)
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return webdriver.Chrome(service=Service(CHROMEDRIVER), options=options)


def validate_target(url: str, expected_port: int) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise BotError("only http(s) targets are allowed")
    if not parsed.hostname:
        raise BotError("missing host")
    try:
        address = ipaddress.ip_address(parsed.hostname)
    except ValueError as exc:
        raise BotError("target must use a loopback IP literal") from exc
    if not address.is_loopback:
        raise BotError("target must be loopback")
    if parsed.port != expected_port:
        raise BotError("target port does not belong to the requesting lab")
    if parsed.username or parsed.password:
        raise BotError("userinfo is not allowed")
    return url


def run_bot(url: str, expected_port: int, cookies: list[dict] | None = None, wait_seconds: float = 3.5) -> dict:
    """Visit a lab URL as the simulated victim. Blocking; caller uses a thread."""
    global _last_error
    if not BOT_ENABLED:
        raise BotError("bot is disabled")
    url = validate_target(url, expected_port)
    if not _lock.acquire(timeout=1):
        raise BotError("bot busy, retry in a moment")
    driver = None
    started = time.time()
    try:
        driver = _driver()
        driver.set_page_load_timeout(max(10, BOT_TIMEOUT))
        base = f"http://127.0.0.1:{expected_port}/"
        driver.get(base)
        for cookie in cookies or []:
            name = str(cookie.get("name", ""))
            if not name or name.lower() in {"rv_session", "__host-rv_session"}:
                continue
            value = str(cookie.get("value", ""))
            item = {"name": name, "value": value, "path": "/", "domain": "127.0.0.1"}
            if cookie.get("httpOnly") is not None:
                item["httpOnly"] = bool(cookie["httpOnly"])
            driver.add_cookie(item)
        driver.get(url)
        time.sleep(max(0.5, min(wait_seconds, BOT_TIMEOUT)))
        return {
            "ok": True,
            "elapsed": round(time.time() - started, 2),
            "final_url": driver.current_url.split("?")[0][:200],
        }
    except Exception as exc:  # noqa: BLE001 - reported to the lab
        _last_error = f"{type(exc).__name__}: {exc}"[:300]
        raise BotError(f"bot execution failed: {_last_error}") from exc
    finally:
        if driver is not None:
            try:
                driver.quit()
            except Exception:
                pass
        _lock.release()


def bot_status() -> dict:
    return {"enabled": BOT_ENABLED, "busy": _lock.locked(), "last_error": _last_error}
