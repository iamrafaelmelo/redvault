#!/usr/bin/env python3
"""Escaped-template runner for labkit apps.

`python3 app.py` still starts the real server on LAB_PORT. The extra
`--serve` subcommand is used by the test suite: it imports the lab module
(which also runs under the normal interpreter) and serves it in this process
with a header-injecting proxy in between. Recent Werkzeug releases normalize
multipart filenames, which would hide filename-handling bugs that the labs
depend on; the proxy restores the exact raw name before Flask parses it.
"""
from __future__ import annotations

import http.client
import os
import sys
import threading


def _inject_original_filename(body: bytes) -> bytes:
    """Insert X-Original-Filename after the part headers, before the blank line."""
    head_end = body.find(b"\r\n\r\n")
    if head_end == -1:
        return body
    filename_at = body.find(b'filename="', 0, head_end)
    if filename_at == -1:
        return body
    start = filename_at + len(b'filename="')
    stop = body.find(b'"', start, head_end)
    if stop == -1 or stop == start:
        return body
    value = body[start:stop]
    if any(byte > 126 or byte < 32 for byte in value):
        return body
    return body[:head_end] + b"\r\nX-Original-Filename: " + value + body[head_end:]


def _free_port() -> int:
    import socket

    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


_traffic_lock = __import__("threading").Lock()
_traffic_state = {"n": 0, "last": 0.0, "reported": 0.0}


def _proxy(target_port: int, listen_port: int) -> None:
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def _report_traffic(self) -> None:
            """Count this request and, at high rates, warn on the target page.

            The platform keeps the counters; the proxy only reports. The warning
            is written to stderr, which the platform stores in the lab log.
            """
            import json as _json
            import threading as _threading
            import time as _time
            import urllib.request as _urlreq

            with _traffic_lock:
                _traffic_state["n"] += 1
                _traffic_state["last"] = _time.time()
            if _time.time() - _traffic_state["reported"] < 2.0:
                return
            _traffic_state["reported"] = _time.time()

            def send() -> None:
                token = os.environ.get("LAB_CALLBACK_TOKEN", "")
                platform = os.environ.get("LAB_PLATFORM_URL", "http://127.0.0.1:8000")
                if not token:
                    return
                payload = _json.dumps({"token": token}).encode()
                req = _urlreq.Request(
                    f"{platform}/internal/lab-traffic",
                    data=payload,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                try:
                    with _urlreq.urlopen(req, timeout=2) as response:
                        stats = _json.loads(response.read().decode() or "{}")
                except Exception:
                    return
                if stats.get("state") == "abort":
                    print(
                        f"[traffic] ABORT-LIKE LOAD: {stats.get('rps')} req/s sustained "
                        f"({stats.get('requests_total')} total). This is far above what an "
                        "exploit needs; stop the loop before it saturates your machine.",
                        flush=True,
                    )
                elif stats.get("state") == "warn":
                    print(
                        f"[traffic] high request rate: {stats.get('rps')} req/s "
                        f"({stats.get('requests_total')} total).",
                        flush=True,
                    )

            _threading.Thread(target=send, daemon=True).start()

        def _forward(self) -> None:
            try:
                self._report_traffic()
            except Exception:
                pass
            length = int(self.headers.get("Content-Length") or 0)
            body = self.rfile.read(length) if length else b""
            content_type = self.headers.get("Content-Type", "")
            if "multipart/form-data" in content_type and b"filename=" in body:
                body = _inject_original_filename(body)
            headers = {k: v for k, v in self.headers.items() if k.lower() != "host"}
            headers["Content-Length"] = str(len(body))
            conn = http.client.HTTPConnection("127.0.0.1", target_port, timeout=30)
            conn.request(self.command, self.path, body=body, headers=headers)
            response = conn.getresponse()
            payload = response.read()
            self.send_response(response.status)
            for key, value in response.getheaders():
                if key.lower() in {"transfer-encoding", "connection", "content-length"}:
                    continue
                self.send_header(key, value)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            conn.close()

        do_GET = do_POST = do_PUT = do_DELETE = do_HEAD = do_PATCH = _forward

        def log_message(self, *_args) -> None:  # noqa: ANN002 - silence per-request logs
            return

    server = ThreadingHTTPServer((os.environ.get("LAB_BIND", "127.0.0.1"), listen_port), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()


def main() -> None:
    args = sys.argv[1:]
    serve = bool(args) and args[0] == "--serve"
    if serve:
        args = args[1:]
    path = args[0] if args else "app.py"
    sys.path.insert(0, os.path.dirname(os.path.abspath(path)))
    sys.argv = [path]
    port = int(os.environ.get("LAB_PORT", "5000"))
    if serve:
        import importlib.util

        spec = importlib.util.spec_from_file_location("lab_app", path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["lab_app"] = module
        spec.loader.exec_module(module)
        listen = port  # the proxy takes the assigned port; Flask listens on a private one
        if not hasattr(module, "lab") or not hasattr(module.lab, "app"):
            raise RuntimeError(f"{path} does not expose a labkit Lab instance")
        backend = _free_port()
        _proxy(backend, port)
        os.environ["LAB_PORT"] = str(port)
        module.lab.port = port
        module.lab.app.run(host="127.0.0.1", port=backend, debug=False, use_reloader=False, threaded=True)
    else:
        import runpy

        runpy.run_path(path, run_name="__main__")


if __name__ == "__main__":
    main()