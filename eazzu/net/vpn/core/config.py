"""
Configuration Manager for UltraVPN
Handles loading, saving, and validating VPN configurations
"""
import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict, Any


@dataclass
class VPNConfig:
    """Represents a single VPN configuration profile"""
    name: str
    protocol: str = "wireguard"  # wireguard, openvpn, ikev2, shadowsocks
    server_address: str = ""
    server_port: int = 51820
    username: str = ""
    password: str = ""
    private_key: str = ""
    public_key: str = ""
    preshared_key: str = ""
    dns_servers: List[str] = field(default_factory=lambda: ["1.1.1.1", "1.0.0.1"])
    kill_switch: bool = True
    dns_leak_protection: bool = True
    ipv6_leak_protection: bool = True
    split_tunneling: bool = False
    split_tunnel_apps: List[str] = field(default_factory=list)
    obfuscation: bool = False
    multi_hop: bool = False
    multi_hop_servers: List[str] = field(default_factory=list)
    auto_connect: bool = False
    encryption: str = "AES-256-GCM"  # AES-256-GCM, ChaCha20-Poly1305
    mtu: int = 1420
    keepalive: int = 25
    allowed_ips: str = "0.0.0.0/0, ::/0"
    endpoint_country: str = "US"
    endpoint_city: str = ""
    tags: List[str] = field(default_factory=list)
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "VPNConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


class ConfigManager:
    """Manages VPN configurations, presets, and user preferences"""

    def __init__(self, config_dir: Optional[str] = None):
        if config_dir is None:
            config_dir = os.path.join(str(Path.home()), ".ultravpn")
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.configs_file = self.config_dir / "configs.json"
        self.settings_file = self.config_dir / "settings.json"
        self.configs: Dict[str, VPNConfig] = {}
        self.settings: Dict[str, Any] = self._default_settings()
        self.load()

    def _default_settings(self) -> Dict[str, Any]:
        return {
            "auto_connect_on_startup": False,
            "connect_to_fastest": True,
            "block_ads": True,
            "block_trackers": True,
            "block_malware": True,
            "tor_over_vpn": False,
            "double_vpn": False,
            "notification_enabled": True,
            "theme": "dark",
            "language": "en",
            "log_level": "INFO",
            "reconnect_on_disconnect": True,
            "max_reconnect_attempts": 5,
            "connection_timeout": 30,
            "preferred_protocol": "wireguard",
            "startup_preset": None,
        }

    def load(self):
        """Load configurations and settings from disk"""
        if self.configs_file.exists():
            try:
                with open(self.configs_file, "r") as f:
                    data = json.load(f)
                    self.configs = {
                        name: VPNConfig.from_dict(cfg) for name, cfg in data.items()
                    }
            except (json.JSONDecodeError, KeyError):
                self.configs = {}

        if self.settings_file.exists():
            try:
                with open(self.settings_file, "r") as f:
                    loaded = json.load(f)
                    self.settings.update(loaded)
            except json.JSONDecodeError:
                pass

    def save(self):
        """Persist configurations and settings to disk"""
        with open(self.configs_file, "w") as f:
            json.dump(
                {name: cfg.to_dict() for name, cfg in self.configs.items()},
                f,
                indent=2,
            )
        with open(self.settings_file, "w") as f:
            json.dump(self.settings, f, indent=2)
        # Restrictive file permissions on POSIX
        try:
            os.chmod(self.configs_file, 0o600)
            os.chmod(self.settings_file, 0o600)
        except (OSError, NotImplementedError):
            pass

    def add_config(self, config: VPNConfig):
        self.configs[config.name] = config
        self.save()

    def remove_config(self, name: str) -> bool:
        if name in self.configs:
            del self.configs[name]
            self.save()
            return True
        return False

    def get_config(self, name: str) -> Optional[VPNConfig]:
        return self.configs.get(name)

    def list_configs(self) -> List[str]:
        return list(self.configs.keys())

    def update_setting(self, key: str, value: Any):
        self.settings[key] = value
        self.save()

    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)
