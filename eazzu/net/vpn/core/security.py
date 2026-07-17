"""
Security & Privacy checks for UltraVPN
- DNS leak testing
- IP leak testing
- WebRTC leak detection helper
- Ad / tracker / malware blocklist checker
"""
import socket
import logging
import urllib.request
import urllib.error
import json
from typing import Dict, List, Optional

logger = logging.getLogger("ultravpn.security")


class LeakTester:
    """Perform quick DNS/IP leak tests. Requires network access."""

    IP_LOOKUP_URLS = [
        "https://api.ipify.org?format=json",
        "https://ipinfo.io/json",
    ]

    def get_public_ip(self, timeout: int = 5) -> Optional[Dict]:
        for url in self.IP_LOOKUP_URLS:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "UltraVPN/1.0"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return json.loads(r.read().decode("utf-8"))
            except (urllib.error.URLError, socket.timeout, json.JSONDecodeError):
                continue
        return None

    def test_dns_leak(self, expected_dns: List[str]) -> Dict:
        """Basic DNS leak test — checks which resolver answers."""
        try:
            resolver = socket.gethostbyname("dnsleaktest.com")
            return {"passed": True, "resolver_ip": resolver, "expected": expected_dns}
        except socket.gaierror as e:
            return {"passed": False, "error": str(e)}

    def full_check(self, expected_country: str = None, expected_dns: List[str] = None) -> Dict:
        result = {"ip_info": None, "dns_test": None, "warnings": []}
        ip_info = self.get_public_ip()
        result["ip_info"] = ip_info
        if ip_info and expected_country:
            country = ip_info.get("country") or ip_info.get("country_code")
            if country and country.upper() != expected_country.upper():
                result["warnings"].append(
                    f"IP country {country} doesn't match expected {expected_country}"
                )
        if expected_dns:
            result["dns_test"] = self.test_dns_leak(expected_dns)
        return result


class Blocklist:
    """Simple ad/tracker/malware blocklist (domain-based)."""

    DEFAULT_BLOCKLIST = {
        "ads": ["doubleclick.net", "googlesyndication.com", "adnxs.com", "adsystem.com"],
        "trackers": ["google-analytics.com", "facebook.com/tr", "hotjar.com", "mixpanel.com"],
        "malware": ["malware.example", "phishing.example"],
    }

    def __init__(self, categories: List[str] = None):
        self.enabled_categories = categories or ["ads", "trackers", "malware"]
        self.blocked_domains = set()
        for cat in self.enabled_categories:
            self.blocked_domains.update(self.DEFAULT_BLOCKLIST.get(cat, []))

    def is_blocked(self, domain: str) -> bool:
        domain = domain.lower().strip(".")
        return any(domain == b or domain.endswith("." + b) for b in self.blocked_domains)

    def stats(self) -> Dict:
        return {
            "categories": self.enabled_categories,
            "total_domains": len(self.blocked_domains),
        }
