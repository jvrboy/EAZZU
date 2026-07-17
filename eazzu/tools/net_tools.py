"""Networking tools — IP intel, HTTP GET, DNS."""
from __future__ import annotations

import ipaddress
import json
import socket
from typing import Any
from urllib.request import Request, urlopen


def http_get(url: str, timeout: int = 15) -> dict[str, Any]:
    try:
        req = Request(url, headers={"User-Agent": "eazzu/1.0"})
        with urlopen(req, timeout=timeout) as r:
            body = r.read(200_000).decode("utf-8", errors="replace")
            return {"status": r.status, "url": r.geturl(), "body": body[:20_000]}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def dns_lookup(hostname: str) -> dict[str, Any]:
    try:
        infos = socket.getaddrinfo(hostname, None)
        addrs = sorted({i[4][0] for i in infos})
        return {"hostname": hostname, "addresses": addrs}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def ip_info(address: str) -> dict[str, Any]:
    try:
        ip = ipaddress.ip_address(address)
        return {
            "address": str(ip),
            "version": ip.version,
            "is_private": ip.is_private,
            "is_global": ip.is_global,
            "is_loopback": ip.is_loopback,
            "is_multicast": ip.is_multicast,
        }
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


TOOLS = [
    {"name": "http_get", "description": "Fetch a URL (GET) and return status + body (truncated).",
     "params": {"url": "string", "timeout": "int"}, "run": http_get},
    {"name": "dns_lookup", "description": "Resolve a hostname to its IPv4/IPv6 addresses.",
     "params": {"hostname": "string"}, "run": dns_lookup},
    {"name": "ip_info", "description": "Classify an IP address (private/global/loopback/etc).",
     "params": {"address": "string"}, "run": ip_info},
]
