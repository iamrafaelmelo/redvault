"""Ron's Coffee: free Wi-Fi recon lab.

The player connects to a simulated open Wi-Fi and has to find the one host
that doesn't belong: a machine that keeps a handful of persistent, unchanging
connections to two fixed addresses instead of the normal browse-and-leave
pattern everyone else on the network shows. There is no captive portal and no
page that does the listening for the player -- they point their own tool
(tshark, tcpdump, Wireshark, scapy...) at the capture stream and read it
themselves.

Traffic is fabricated, not replayed or proxied: ``pcapgen`` builds real
Ethernet/IPv4/UDP/TCP/DNS bytes with correct checksums for every packet, and a
background thread keeps appending them to a ring buffer while the player is
"connected". ``/capture/live`` streams that buffer as a live pcap; the normal
flag form on the platform accepts the flag only after the player has also
named the anomalous IP correctly through this lab's own page, following the
same requires_objective pattern used across the platform's other labs.
"""
from __future__ import annotations

import html
import os
import random
import struct
import threading
import time
from collections import deque

from flask import Response, request, stream_with_context

import pcapgen as pg
from labkit import Lab

lab = Lab("RONSCOFFEE WIFI", accent="#39dca0")
app = lab.app

ROUTER_IP = "10.20.0.1"
USER_IP = "10.20.0.77"
RON_IP = "10.20.0.10"
RON_PORT = 9001
GUARD_IPS = ("203.0.113.201", "203.0.113.202")

# TEST-NET-3 (RFC 5737) stands in for "the internet" so nothing here looks
# like it resolves to a real company's infrastructure.
SITES = {
    "google.com": "203.0.113.11",
    "wikipedia.org": "203.0.113.12",
    "news.ycombinator.com": "203.0.113.13",
    "weather.example": "203.0.113.14",
}
CLIENT_IPS = ["10.20.0.21", "10.20.0.22", "10.20.0.23", "10.20.0.24"]

RETENTION_SECONDS = 90
TICK_SECONDS = 1.2

_lock = threading.Lock()
_state = {
    "connected": False,
    "connected_at": 0.0,
    "attempts": 0,
    "reported_ok": False,
}
_buffer: deque[tuple[int, float, bytes]] = deque()
_seq_counter = {"n": 0}
_seq_counters: dict[tuple[str, str, int, int], int] = {}


def _mac(ip: str) -> bytes:
    return pg.mac_for_ip(ip)


def _next_seq(src_ip: str, dst_ip: str, src_port: int, dst_port: int, step: int) -> int:
    key = (src_ip, dst_ip, src_port, dst_port)
    seq = _seq_counters.get(key, random.randint(1000, 90000))
    _seq_counters[key] = seq + step
    return seq


def _frame(src_ip: str, dst_ip: str, ip_payload: bytes, proto: int, ident: int) -> bytes:
    ip_pkt = pg.build_ipv4(src_ip, dst_ip, proto, ip_payload, ident=ident)
    return pg.build_eth(_mac(dst_ip), _mac(src_ip), ip_pkt)


def _emit(frame: bytes) -> None:
    """Append one frame to the ring buffer with a monotonic sequence number.

    The live stream below has to know which packets a given listener has
    already seen. Comparing by wall-clock timestamp looked natural, but
    time.time() isn't fine-grained enough: a cell's request and response are
    emitted microseconds apart and can land on the same float value, which
    made the strictly-greater-than check drop the second one forever. A
    sequence counter has no such ties.
    """
    now = time.time()
    with _lock:
        _seq_counter["n"] += 1
        _buffer.append((_seq_counter["n"], now, pg.pcap_record(frame, ts=now)))
        cutoff = now - RETENTION_SECONDS
        while _buffer and _buffer[0][1] < cutoff:
            _buffer.popleft()


_ident_counter = {"n": 1}


def _ident() -> int:
    _ident_counter["n"] += 1
    return _ident_counter["n"] & 0xFFFF


def _tcp_frame(src_ip: str, dst_ip: str, sport: int, dport: int, seq: int, ack: int, flags: int, payload: bytes = b"") -> bytes:
    tcp = pg.build_tcp(src_ip, dst_ip, sport, dport, seq, ack, flags, payload)
    return _frame(src_ip, dst_ip, tcp, pg.PROTO_TCP, _ident())


def _dns_lookup(client_ip: str, site: str, answer_ip: str) -> None:
    txid = random.randint(0, 0xFFFF)
    port = random.randint(49152, 65535)
    query = pg.build_dns_query(txid, site)
    _emit(_frame(client_ip, ROUTER_IP, pg.build_udp(client_ip, ROUTER_IP, port, 53, query), pg.PROTO_UDP, _ident()))
    response = pg.build_dns_response(txid, site, answer_ip)
    _emit(_frame(ROUTER_IP, client_ip, pg.build_udp(ROUTER_IP, client_ip, 53, port, response), pg.PROTO_UDP, _ident()))


def _normal_client_flow() -> None:
    client_ip = random.choice(CLIENT_IPS)
    site, site_ip = random.choice(list(SITES.items()))
    _dns_lookup(client_ip, site, site_ip)

    sport = random.randint(49152, 65535)
    seq_c = _next_seq(client_ip, site_ip, sport, 80, 1)
    seq_s = _next_seq(site_ip, client_ip, 80, sport, 1)

    _emit(_tcp_frame(client_ip, site_ip, sport, 80, seq_c, 0, pg.TCP_SYN))
    _emit(_tcp_frame(site_ip, client_ip, 80, sport, seq_s, seq_c + 1, pg.TCP_SYN | pg.TCP_ACK))
    _emit(_tcp_frame(client_ip, site_ip, sport, 80, seq_c + 1, seq_s + 1, pg.TCP_ACK))

    request_bytes = f"GET / HTTP/1.1\r\nHost: {site}\r\nConnection: close\r\n\r\n".encode()
    _emit(_tcp_frame(client_ip, site_ip, sport, 80, seq_c + 1, seq_s + 1, pg.TCP_PSH | pg.TCP_ACK, request_bytes))
    body = f"<html><body>Welcome to {site}</body></html>".encode()
    response_bytes = f"HTTP/1.1 200 OK\r\nContent-Length: {len(body)}\r\n\r\n".encode() + body
    seq_s2 = seq_s + 1
    _emit(_tcp_frame(site_ip, client_ip, 80, sport, seq_s2, seq_c + 1 + len(request_bytes), pg.TCP_PSH | pg.TCP_ACK, response_bytes))

    seq_c2 = seq_c + 1 + len(request_bytes)
    seq_s3 = seq_s2 + len(response_bytes)
    _emit(_tcp_frame(client_ip, site_ip, sport, 80, seq_c2, seq_s3, pg.TCP_FIN | pg.TCP_ACK))
    _emit(_tcp_frame(site_ip, client_ip, 80, sport, seq_s3, seq_c2 + 1, pg.TCP_FIN | pg.TCP_ACK))


_ron_session: dict[str, int] = {}


def _ron_flow() -> None:
    """Persistent, DNS-less connections from the hidden-service host to fixed guards.

    Established once per lab run, then kept alive with fixed-size cells on a
    schedule that does not slow down outside business hours -- the pattern
    the player is meant to notice, not the cell's (simulated) content.
    """
    guard_ip = _ron_session.setdefault("guard", random.choice(GUARD_IPS))
    sport = _ron_session.setdefault("sport", random.randint(49152, 65535))

    if "seq" not in _ron_session:
        seq_c = _next_seq(RON_IP, guard_ip, sport, RON_PORT, 1)
        seq_s = _next_seq(guard_ip, RON_IP, RON_PORT, sport, 1)
        _emit(_tcp_frame(RON_IP, guard_ip, sport, RON_PORT, seq_c, 0, pg.TCP_SYN))
        _emit(_tcp_frame(guard_ip, RON_IP, RON_PORT, sport, seq_s, seq_c + 1, pg.TCP_SYN | pg.TCP_ACK))
        _emit(_tcp_frame(RON_IP, guard_ip, sport, RON_PORT, seq_c + 1, seq_s + 1, pg.TCP_ACK))
        _ron_session["seq"] = 1
        _ron_session["cells_sent"] = 0

    # Cells are opaque padding, same as real Tor traffic: the flag is never
    # inside the payload. What identifies this host is the connection
    # pattern itself (fixed guards, no prior DNS, always-on) -- that pattern
    # is the evidence, and it's what /relatorio checks.
    cell_size = 512
    cells_sent = _ron_session["cells_sent"]
    payload = os.urandom(cell_size)

    seq_c = _next_seq(RON_IP, guard_ip, sport, RON_PORT, cell_size)
    seq_s = _next_seq(guard_ip, RON_IP, RON_PORT, sport, 4)
    _emit(_tcp_frame(RON_IP, guard_ip, sport, RON_PORT, seq_c, seq_s, pg.TCP_PSH | pg.TCP_ACK, payload))
    _emit(_tcp_frame(guard_ip, RON_IP, RON_PORT, sport, seq_s, seq_c + cell_size, pg.TCP_PSH | pg.TCP_ACK, os.urandom(4)))
    _ron_session["cells_sent"] = cells_sent + 1


def _generator_loop() -> None:
    tick = 0
    while True:
        time.sleep(TICK_SECONDS)
        with _lock:
            connected = _state["connected"]
        if not connected:
            tick = 0
            _ron_session.clear()
            continue
        tick += 1
        if random.random() < 0.6:
            _normal_client_flow()
        if tick % 3 == 0:
            _ron_flow()


threading.Thread(target=_generator_loop, name="rons-coffee-traffic", daemon=True).start()


# -- presentation -----------------------------------------------------------


def shell(title: str, body: str) -> Response:
    return lab.page(
        title,
        f'<div class="hero"><div class="kicker">RONSCOFFEE // FREE WI-FI</div><h1>{html.escape(title)}</h1>'
        "<p>Rede aberta de um café. Conecte-se e escute o tráfego com suas próprias ferramentas.</p></div>"
        f"{body}",
        nav='<a href="/">Redes</a><a href="/relatorio">Relatório</a>',
    )


@app.get("/")
def index():
    with _lock:
        connected = _state["connected"]
        connected_at = _state["connected_at"]

    if connected:
        uptime = int(time.time() - connected_at)
        capture_url = request.host_url.rstrip("/") + "/capture/live"
        banner = f"""<div class="panel">
          <h2>Conectado</h2>
          <table>
            <tr><td>IP</td><td class="mono">{USER_IP}/24</td></tr>
            <tr><td>Gateway</td><td class="mono">{ROUTER_IP}</td></tr>
            <tr><td>DNS</td><td class="mono">{ROUTER_IP}</td></tr>
            <tr><td>Conectado há</td><td class="mono">{uptime}s</td></tr>
          </table>
          <p class="note">O tráfego já está fluindo. Use sua ferramenta de escuta apontando para este host na porta do lab.</p>
          <p class="mono dim">Captura: <code>{capture_url}</code></p>
          <p class="note">Esse endpoint entrega um stream pcap fabricado por este processo, não tráfego de uma placa de rede real. Por isso ele não aparece na lista de interfaces do Wireshark/tshark: a captura é feita lendo esse stream (ex. <code>curl -sN {capture_url} | tshark -i -</code>), nunca escolhendo sua Wi-Fi física.</p>
          <form method="post" action="/disconnect"><button class="btn btn-ghost" type="submit">Desconectar</button></form>
        </div>"""
    else:
        banner = """<div class="panel">
          <h2>Redes disponíveis</h2>
          <table><tr><th>SSID</th><th>Segurança</th><th></th></tr>
          <tr><td>RonsCoffee_FreeWiFi</td><td class="green">Aberta</td>
            <td><form method="post" action="/connect"><button class="btn" type="submit">Conectar</button></form></td></tr>
          <tr><td class="dim">Vizinho_5G</td><td class="dim">WPA2</td><td class="dim">bloqueada</td></tr>
          <tr><td class="dim">ESCRITORIO-RH</td><td class="dim">WPA2-Enterprise</td><td class="dim">bloqueada</td></tr>
          </table>
        </div>"""

    return shell("Ron's Coffee Wi-Fi", banner)


@app.post("/connect")
def connect():
    with _lock:
        _state["connected"] = True
        _state["connected_at"] = time.time()
        _buffer.clear()
    return lab.redirect("/")


@app.post("/disconnect")
def disconnect():
    with _lock:
        _state["connected"] = False
    return lab.redirect("/")


def _flag_reveal_html() -> str:
    return f"""<div class="flash ok">
      IP confirmado. A flag deste alvo é:
      <pre>{html.escape(lab.flag("flag"))}</pre>
      Copie o valor acima no formulário de flag do desafio, na plataforma.
    </div>"""


@app.get("/relatorio")
def relatorio_form():
    with _lock:
        ok = _state["reported_ok"]
        attempts = _state["attempts"]
    status = _flag_reveal_html() if ok else ""
    body = f"""<div class="panel">
      <h2>Relatar IP suspeito</h2>
      <p>Identifique, pela captura, o host com padrão de tráfego anômalo e informe o IP de origem dele aqui. Se o IP estiver correto, a flag deste alvo é revelada abaixo.</p>
      {status}
      <form method="post" action="/relatorio">
        <label>IP suspeito</label>
        <input type="text" name="ip" placeholder="10.20.0.x" autocomplete="off">
        <p class="mt"><button class="btn" type="submit">Enviar</button></p>
      </form>
      <p class="dim mono">tentativas: {attempts}</p>
    </div>"""
    return shell("Relatório de IP suspeito", body)


@app.post("/relatorio")
def relatorio_submit():
    ip = request.form.get("ip", "").strip()
    with _lock:
        _state["attempts"] += 1
    if ip == RON_IP:
        with _lock:
            _state["reported_ok"] = True
        lab.objective_async("flag", evidence=f"reported suspect ip {ip}")
        body = _flag_reveal_html()
    else:
        body = '<div class="flash err">Esse IP não bate com o padrão descrito no objetivo. Reveja a captura.</div>'
    return shell("Relatório de IP suspeito", f'<div class="panel">{body}</div><p><a href="/relatorio">Tentar novamente</a></p>')


@app.get("/capture/live")
def capture_live():
    with _lock:
        connected = _state["connected"]
    if not connected:
        return Response(
            "not connected: join RonsCoffee_FreeWiFi from the lab page before listening\n",
            status=409,
            mimetype="text/plain",
        )

    def generate():
        yield pg.pcap_global_header()
        last_seq = 0
        with _lock:
            snapshot = list(_buffer)
        for seq, _ts, record in snapshot:
            last_seq = seq
            yield record
        try:
            while True:
                time.sleep(0.5)
                with _lock:
                    if not _state["connected"]:
                        return
                    pending = [(seq, rec) for seq, _ts, rec in _buffer if seq > last_seq]
                for seq, record in pending:
                    last_seq = seq
                    yield record
        except GeneratorExit:
            return

    return Response(stream_with_context(generate()), mimetype="application/vnd.tcpdump.pcap")


@app.get("/capture/download")
def capture_download():
    with _lock:
        snapshot = list(_buffer)
    body = pg.pcap_global_header() + b"".join(record for _, _ts, record in snapshot)
    return Response(
        body,
        mimetype="application/vnd.tcpdump.pcap",
        headers={"Content-Disposition": "attachment; filename=rons-coffee-capture.pcap"},
    )


if __name__ == "__main__":
    lab.run()
