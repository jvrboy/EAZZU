"""
Server Manager — measure latency, pick fastest, list servers.
"""
import time
import socket
import logging
import concurrent.futures
from typing import List, Dict, Optional

logger = logging.getLogger("ultravpn.servers")


class Server:
    def __init__(self, name: str, address: str, port: int,
                 country: str = "", city: str = "", load: float = 0.0):
        self.name = name
        self.address = address
        self.port = port
        self.country = country
        self.city = city
        self.load = load  # 0.0 - 1.0
        self.latency_ms: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "name": self.name, "address": self.address, "port": self.port,
            "country": self.country, "city": self.city,
            "load": self.load, "latency_ms": self.latency_ms,
        }


# Demo server list (replace with real provider list / API in production)
DEFAULT_SERVERS = [
    Server("us-nyc-1", "us1.example-vpn.net", 51820, "US", "New York", 0.35),
    Server("us-lax-1", "us2.example-vpn.net", 51820, "US", "Los Angeles", 0.50),
    Server("uk-lon-1", "uk1.example-vpn.net", 51820, "GB", "London", 0.40),
    Server("de-fra-1", "de1.example-vpn.net", 51820, "DE", "Frankfurt", 0.25),
    Server("nl-ams-1", "nl1.example-vpn.net", 51820, "NL", "Amsterdam", 0.30),
    Server("ch-zur-1", "ch1.example-vpn.net", 51820, "CH", "Zurich", 0.20),
    Server("is-rey-1", "is1.example-vpn.net", 51820, "IS", "Reykjavik", 0.15),
    Server("jp-tok-1", "jp1.example-vpn.net", 51820, "JP", "Tokyo", 0.45),
    Server("sg-sin-1", "sg1.example-vpn.net", 51820, "SG", "Singapore", 0.55),
    Server("ca-tor-1", "ca1.example-vpn.net", 51820, "CA", "Toronto", 0.30),
]


class ServerManager:
    def __init__(self, servers: List[Server] = None):
        self.servers = servers or DEFAULT_SERVERS

    def measure_latency(self, server: Server, timeout: float = 2.0) -> Optional[float]:
        """TCP handshake latency (ms). Returns None on failure."""
        try:
            start = time.perf_counter()
            with socket.create_connection((server.address, server.port), timeout=timeout):
                pass
            latency = (time.perf_counter() - start) * 1000
            server.latency_ms = latency
            return latency
        except (socket.timeout, OSError):
            server.latency_ms = None
            return None

    def measure_all(self, max_workers: int = 8) -> List[Server]:
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            list(ex.map(self.measure_latency, self.servers))
        return self.servers

    def fastest(self) -> Optional[Server]:
        self.measure_all()
        reachable = [s for s in self.servers if s.latency_ms is not None]
        if not reachable:
            return None
        # score = latency * (1 + load)  → penalize high load
        return min(reachable, key=lambda s: s.latency_ms * (1 + s.load))

    def filter_by_country(self, country_code: str) -> List[Server]:
        return [s for s in self.servers if s.country.upper() == country_code.upper()]

    def list_countries(self) -> List[str]:
        return sorted(set(s.country for s in self.servers))
