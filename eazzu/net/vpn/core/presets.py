"""
Preset VPN Configurations
Ready-to-use VPN profiles for popular servers/regions.
NOTE: Server addresses and keys are placeholders — users must replace them
with real credentials from their VPN provider before connecting.
"""
from typing import Dict
from .config import VPNConfig


PRESETS: Dict[str, VPNConfig] = {
    # ---------- Ultra Privacy Presets ----------
    "ultra_privacy_us": VPNConfig(
        name="ultra_privacy_us",
        protocol="wireguard",
        server_address="us1.example-vpn.net",
        server_port=51820,
        dns_servers=["9.9.9.9", "149.112.112.112"],  # Quad9 (blocks malicious)
        kill_switch=True,
        dns_leak_protection=True,
        ipv6_leak_protection=True,
        obfuscation=True,
        multi_hop=True,
        multi_hop_servers=["us1.example-vpn.net", "ca1.example-vpn.net"],
        encryption="ChaCha20-Poly1305",
        endpoint_country="US",
        endpoint_city="New York",
        tags=["ultra-privacy", "multi-hop", "recommended"],
        description="Maximum privacy: multi-hop US→CA, ChaCha20, Quad9 DNS, full leak protection.",
    ),
    "ultra_privacy_eu": VPNConfig(
        name="ultra_privacy_eu",
        protocol="wireguard",
        server_address="ch1.example-vpn.net",
        server_port=51820,
        dns_servers=["9.9.9.9", "149.112.112.112"],
        kill_switch=True,
        dns_leak_protection=True,
        ipv6_leak_protection=True,
        obfuscation=True,
        multi_hop=True,
        multi_hop_servers=["ch1.example-vpn.net", "is1.example-vpn.net"],
        encryption="ChaCha20-Poly1305",
        endpoint_country="CH",
        endpoint_city="Zurich",
        tags=["ultra-privacy", "multi-hop", "eu-jurisdiction"],
        description="Multi-hop through privacy-friendly jurisdictions (Switzerland → Iceland).",
    ),

    # ---------- Streaming Presets ----------
    "streaming_us": VPNConfig(
        name="streaming_us",
        protocol="wireguard",
        server_address="stream-us.example-vpn.net",
        server_port=51820,
        dns_servers=["1.1.1.1", "1.0.0.1"],
        kill_switch=False,
        dns_leak_protection=True,
        obfuscation=False,
        encryption="AES-256-GCM",
        endpoint_country="US",
        endpoint_city="Los Angeles",
        tags=["streaming", "high-speed"],
        description="Optimized for streaming US content — high-speed, low overhead.",
    ),
    "streaming_uk": VPNConfig(
        name="streaming_uk",
        protocol="wireguard",
        server_address="stream-uk.example-vpn.net",
        server_port=51820,
        dns_servers=["1.1.1.1", "1.0.0.1"],
        endpoint_country="GB",
        endpoint_city="London",
        tags=["streaming", "high-speed"],
        description="Optimized for streaming UK content.",
    ),

    # ---------- Gaming Preset ----------
    "gaming_low_latency": VPNConfig(
        name="gaming_low_latency",
        protocol="wireguard",
        server_address="game.example-vpn.net",
        server_port=51820,
        dns_servers=["1.1.1.1"],
        kill_switch=False,
        dns_leak_protection=True,
        split_tunneling=True,
        split_tunnel_apps=["steam.exe", "battle.net.exe"],
        encryption="ChaCha20-Poly1305",
        mtu=1500,
        keepalive=15,
        tags=["gaming", "low-latency"],
        description="Low-latency preset with split tunneling for game clients.",
    ),

    # ---------- P2P / Torrenting ----------
    "p2p_torrent": VPNConfig(
        name="p2p_torrent",
        protocol="wireguard",
        server_address="p2p.example-vpn.net",
        server_port=51820,
        dns_servers=["9.9.9.9"],
        kill_switch=True,
        dns_leak_protection=True,
        ipv6_leak_protection=True,
        encryption="ChaCha20-Poly1305",
        endpoint_country="NL",
        endpoint_city="Amsterdam",
        tags=["p2p", "torrent", "privacy"],
        description="P2P-friendly server with kill switch always on.",
    ),

    # ---------- Bypass Censorship ----------
    "bypass_censorship": VPNConfig(
        name="bypass_censorship",
        protocol="openvpn",  # OpenVPN is easier to obfuscate
        server_address="obf.example-vpn.net",
        server_port=443,  # HTTPS port to blend in
        dns_servers=["1.1.1.1", "8.8.8.8"],
        kill_switch=True,
        dns_leak_protection=True,
        obfuscation=True,
        encryption="AES-256-GCM",
        allowed_ips="0.0.0.0/0, ::/0",
        tags=["stealth", "obfuscation", "censorship-bypass"],
        description="Obfuscated OpenVPN on port 443, disguised as HTTPS traffic.",
    ),

    # ---------- Balanced Default ----------
    "balanced_default": VPNConfig(
        name="balanced_default",
        protocol="wireguard",
        server_address="auto.example-vpn.net",
        server_port=51820,
        dns_servers=["1.1.1.1", "1.0.0.1"],
        kill_switch=True,
        dns_leak_protection=True,
        ipv6_leak_protection=True,
        encryption="ChaCha20-Poly1305",
        tags=["balanced", "default", "recommended"],
        description="Good balance between speed and privacy — recommended for daily use.",
    ),

    # ---------- Mobile / Data Saver ----------
    "mobile_data_saver": VPNConfig(
        name="mobile_data_saver",
        protocol="wireguard",
        server_address="mobile.example-vpn.net",
        server_port=51820,
        dns_servers=["1.1.1.1"],
        kill_switch=True,
        mtu=1280,  # Lower MTU for mobile networks
        keepalive=60,
        encryption="ChaCha20-Poly1305",
        tags=["mobile", "data-saver"],
        description="Optimized for mobile networks: low MTU, extended keepalive.",
    ),
}


def get_preset(name: str) -> VPNConfig:
    """Return a *copy* of a preset so mutations don't affect the template."""
    if name not in PRESETS:
        raise KeyError(f"Preset '{name}' not found. Available: {list(PRESETS)}")
    from copy import deepcopy
    return deepcopy(PRESETS[name])


def list_presets() -> Dict[str, str]:
    """Return dict of {preset_name: description}"""
    return {name: cfg.description for name, cfg in PRESETS.items()}
