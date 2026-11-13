#!/usr/bin/env python3
"""REDVAULT development launcher.

Usage:
    python3 run.py                 # http://127.0.0.1:8000
    REDVAULT_PORT=9000 python3 run.py

The platform always binds to loopback. Set REDVAULT_HOST explicitly only when
you understand the isolation model; labs themselves are always loopback-only.
"""
from __future__ import annotations

import uvicorn

from app.config import HOST, PORT


def main() -> None:
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        proxy_headers=False,
        server_header=False,
        date_header=True,
    )


if __name__ == "__main__":
    main()
