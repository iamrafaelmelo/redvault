#!/usr/bin/env python3
"""Brute-force load check for one lab, measured the way the router sees it.

This starts the OTP lab through a plain Flask process, hammers it with a
realistic brute force, and reports:
  * requests per second the lab actually sustains
  * bytes on the wire (approximate, from the response sizes)
  * what that means as a share of a normal LAN interface

It talks to the lab on loopback, which is exactly the traffic path of a
bruteforce: the router is not involved, because source and destination are the
same host. Run it when you want to see the numbers for your own machine.

    python3 scripts/bruteforce_load.py            # 10 seconds
    python3 scripts/bruteforce_load.py --seconds 3
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LABS = ROOT / "labs"


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def wait_ready(port: int, proc: subprocess.Popen, timeout: float = 15.0) -> bool:
    import httpx

    deadline = time.time() + timeout
    while time.time() < deadline:
        if proc.poll() is not None:
            return False
        try:
            if httpx.get(f"http://127.0.0.1:{port}/health", timeout=0.5).status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(0.1)
    return False


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--lab", default="auth-otp-bruteforce")
    args = parser.parse_args(argv)

    lab_dir = LABS / args.lab
    if not (lab_dir / "app.py").exists():
        print(f"lab não encontrado: {args.lab}", file=sys.stderr)
        return 2

    port = free_port()
    state = Path(tempfile.mkdtemp(prefix="redvault-load-"))
    env = {
        "PATH": "/usr/local/bin:/usr/bin:/bin",
        "HOME": "/tmp",
        "PYTHONPATH": str(LABS / "_shared"),
        "LAB_PORT": str(port),
        "LAB_STATE_DIR": str(state),
        "LAB_BIND": "127.0.0.1",
        "LAB_FLAGS": json.dumps({"flag": "RV{load_test}"}),
        "PYTHONUNBUFFERED": "1",
    }
    proc = subprocess.Popen(
        [sys.executable, str(lab_dir / "app.py")],
        env=env, cwd=str(lab_dir),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        start_new_session=True,
    )

    try:
        if not wait_ready(port, proc):
            print("lab não iniciou", file=sys.stderr)
            return 1

        import httpx

        base = f"http://127.0.0.1:{port}"
        counters = {"n": 0, "bytes": 0, "errors": 0}
        lock = threading.Lock()
        stop = threading.Event()

        def worker() -> None:
            client = httpx.Client(base_url=base, timeout=10)
            try:
                client.post("/login", data={"username": "operator", "password": "operator123"})
            except httpx.HTTPError:
                with lock:
                    counters["errors"] += 1
                return
            i = 0
            while not stop.is_set():
                i += 1
                try:
                    response = client.post("/verify", data={"code": f"{i % 1_000_000:06d}"})
                    with lock:
                        counters["n"] += 1
                        counters["bytes"] += len(response.content) + 500  # ~HTTP overhead
                except httpx.HTTPError:
                    with lock:
                        counters["errors"] += 1
            client.close()

        threads = [threading.Thread(target=worker, daemon=True) for _ in range(args.workers)]
        start = time.time()
        for thread in threads:
            thread.start()
        time.sleep(args.seconds)
        stop.set()
        for thread in threads:
            thread.join(timeout=5)
        elapsed = time.time() - start

        rps = counters["n"] / elapsed
        mbps = counters["bytes"] * 8 / elapsed / 1_000_000
        print(f"\nLab: {args.lab}  ({args.workers} workers, {elapsed:.1f}s)")
        print(f"Requisições:   {counters['n']}  ({counters['errors']} erros)")
        print(f"Taxa:          {rps:,.0f} req/s")
        print(f"Tráfego:       {mbps:,.2f} Mbps  (~{counters['bytes'] / elapsed / 1024:,.0f} KB/s)")
        print("\nContexto:")
        print("  - origem e destino são o MESMO host (127.0.0.1): o roteador não vê esse tráfego.")
        print("  - seu Wi-Fi doméstico costuma aguentar 100+ Mbps; vídeo 4K usa ~25 Mbps.")
        print(f"  - esta carga é ~{mbps / 1000 * 100:.2f}% de 1 Gbps.")
        return 0
    finally:
        import signal

        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except OSError:
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
        import shutil

        shutil.rmtree(state, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))