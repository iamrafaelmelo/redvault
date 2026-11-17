"""Exploit-level test for the Ron's Coffee network-sniffing lab."""
from __future__ import annotations

import time

from conftest import flag_payload

RON_IP = "10.20.0.10"


def test_network_rons_coffee(lab):
    c = lab["client"]

    # Nothing to listen to before the player connects.
    r = c.get("/capture/live")
    assert r.status_code == 409

    c.post("/connect")

    marker = f"RV-CELL-EVIDENCE:{flag_payload(lab)}".encode()
    deadline = time.time() + 30
    found = False
    while time.time() < deadline:
        body = c.get("/capture/download").content
        if marker in body:
            found = True
            break
        time.sleep(1)
    assert found, "flag marker never showed up in the simulated capture"

    wrong = c.post("/relatorio", data={"ip": "10.20.0.99"})
    assert "flash err" in wrong.text

    right = c.post("/relatorio", data={"ip": RON_IP})
    assert "flash ok" in right.text

    c.post("/disconnect")
    assert c.get("/capture/live").status_code == 409
