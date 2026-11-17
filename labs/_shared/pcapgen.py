"""Hand-built packet and pcap framing for network-simulation labs.

No live network exists inside the sandbox, so a lab that wants the player to
sniff traffic has to fabricate it: build real Ethernet/IPv4/UDP/TCP/DNS bytes
with correct checksums, then wrap them in the classic libpcap record format
tshark/tcpdump/Wireshark already know how to read. This module only provides
that framing. Traffic patterns (who talks to whom, how often, what the
payload says) stay in each lab, the same way vulnerability logic stays out of
``labkit``.
"""
from __future__ import annotations

import struct
import time

# -- Ethernet -----------------------------------------------------------

ETH_TYPE_IPV4 = 0x0800


def mac_for_ip(ip: str, prefix: bytes = b"\x02\x00") -> bytes:
    """Deterministic locally-administered MAC derived from an IPv4 address."""
    octets = bytes(int(part) for part in ip.split("."))
    return prefix + octets


def build_eth(dst_mac: bytes, src_mac: bytes, payload: bytes, ethertype: int = ETH_TYPE_IPV4) -> bytes:
    return dst_mac + src_mac + struct.pack("!H", ethertype) + payload


# -- Checksums ------------------------------------------------------------


def _checksum16(data: bytes) -> int:
    if len(data) % 2:
        data += b"\x00"
    total = sum(struct.unpack("!%dH" % (len(data) // 2), data))
    total = (total & 0xFFFF) + (total >> 16)
    total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


# -- IPv4 -------------------------------------------------------------------

PROTO_TCP = 6
PROTO_UDP = 17


def _ipv4_to_bytes(ip: str) -> bytes:
    return bytes(int(part) for part in ip.split("."))


def build_ipv4(src_ip: str, dst_ip: str, proto: int, payload: bytes, ident: int, ttl: int = 64, flags_offset: int = 0x4000) -> bytes:
    total_len = 20 + len(payload)
    header = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,  # version 4, header length 5 words
        0,  # DSCP/ECN
        total_len,
        ident & 0xFFFF,
        flags_offset,  # default: don't-fragment
        ttl,
        proto,
        0,  # checksum placeholder
        _ipv4_to_bytes(src_ip),
        _ipv4_to_bytes(dst_ip),
    )
    checksum = _checksum16(header)
    header = header[:10] + struct.pack("!H", checksum) + header[12:]
    return header + payload


def _pseudo_header(src_ip: str, dst_ip: str, proto: int, length: int) -> bytes:
    return _ipv4_to_bytes(src_ip) + _ipv4_to_bytes(dst_ip) + struct.pack("!BBH", 0, proto, length)


# -- UDP --------------------------------------------------------------------


def build_udp(src_ip: str, dst_ip: str, src_port: int, dst_port: int, payload: bytes) -> bytes:
    length = 8 + len(payload)
    header = struct.pack("!HHHH", src_port, dst_port, length, 0)
    checksum = _checksum16(_pseudo_header(src_ip, dst_ip, PROTO_UDP, length) + header + payload)
    header = header[:6] + struct.pack("!H", checksum or 0xFFFF) + header[8:]
    return header + payload


# -- TCP --------------------------------------------------------------------

TCP_FIN = 0x01
TCP_SYN = 0x02
TCP_RST = 0x04
TCP_PSH = 0x08
TCP_ACK = 0x10


def build_tcp(
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    seq: int,
    ack: int,
    flags: int,
    payload: bytes = b"",
    window: int = 64240,
) -> bytes:
    header = struct.pack(
        "!HHLLBBHHH",
        src_port,
        dst_port,
        seq & 0xFFFFFFFF,
        ack & 0xFFFFFFFF,
        0x50,  # data offset: 5 words, no options
        flags,
        window,
        0,  # checksum placeholder
        0,  # urgent pointer
    )
    length = len(header) + len(payload)
    checksum = _checksum16(_pseudo_header(src_ip, dst_ip, PROTO_TCP, length) + header + payload)
    header = header[:16] + struct.pack("!H", checksum) + header[18:]
    return header + payload


# -- DNS ----------------------------------------------------------------


def _encode_qname(name: str) -> bytes:
    out = b""
    for label in name.rstrip(".").split("."):
        out += bytes([len(label)]) + label.encode("ascii")
    return out + b"\x00"


def build_dns_query(txid: int, qname: str) -> bytes:
    header = struct.pack("!HHHHHH", txid, 0x0100, 1, 0, 0, 0)
    question = _encode_qname(qname) + struct.pack("!HH", 1, 1)  # A, IN
    return header + question


def build_dns_response(txid: int, qname: str, answer_ip: str) -> bytes:
    header = struct.pack("!HHHHHH", txid, 0x8180, 1, 1, 0, 0)
    question = _encode_qname(qname) + struct.pack("!HH", 1, 1)
    answer = (
        b"\xc0\x0c"  # name: pointer back to the question
        + struct.pack("!HHLH", 1, 1, 60, 4)
        + _ipv4_to_bytes(answer_ip)
    )
    return header + question + answer


# -- pcap framing -------------------------------------------------------

_PCAP_MAGIC = 0xA1B2C3D4
LINKTYPE_ETHERNET = 1


def pcap_global_header(linktype: int = LINKTYPE_ETHERNET) -> bytes:
    """Classic (non-pcapng) global header, little-endian, microsecond timestamps."""
    return struct.pack("<IHHiIII", _PCAP_MAGIC, 2, 4, 0, 0, 262144, linktype)


def pcap_record(frame: bytes, ts: float | None = None) -> bytes:
    """One libpcap packet record: per-packet header (little-endian) + the frame."""
    ts = time.time() if ts is None else ts
    seconds = int(ts)
    micros = int((ts - seconds) * 1_000_000)
    header = struct.pack("<IIII", seconds, micros, len(frame), len(frame))
    return header + frame
