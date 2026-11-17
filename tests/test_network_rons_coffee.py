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

    # The anomalous host's connection pattern (fixed guards, no DNS,
    # always-on) is visible almost immediately; give the generator a couple
    # of ticks so the pattern is clearly established in the buffer.
    time.sleep(5)

    wrong = c.post("/relatorio", data={"ip": "10.20.0.99"})
    assert "flash err" in wrong.text
    assert flag_payload(lab) not in wrong.text

    right = c.post("/relatorio", data={"ip": RON_IP})
    assert "flash ok" in right.text
    assert flag_payload(lab) in right.text

    # Revisiting the report page keeps showing the flag once it's unlocked.
    again = c.get("/relatorio")
    assert flag_payload(lab) in again.text

    c.post("/disconnect")
    assert c.get("/capture/live").status_code == 409
