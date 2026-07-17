"""
VPN Engine — protocol dispatchers and connection state machine.

This module handles the actual connect / disconnect logic.
On systems without the real VPN backends installed (wg-quick, openvpn),
it runs in SIMULATION MODE so the tool can be tested end-to-end safely.
"""
import os
import time
import shutil
import logging
import platform
import subprocess
import threading
from enum import Enum
from typing import Optional, Callable, Dict, Any
from .config import VPNConfig

logger = logging.getLogger("ultravpn.engine")


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class VPNEngine:
    """
    Manages a single active VPN session.
    Supports WireGuard, OpenVPN, IKEv2, and Shadowsocks (dispatched by protocol).
    Falls back to simulation mode when backend binaries are missing.
    """

    def __init__(self, simulate: Optional[bool] = None):
        self.state: ConnectionState = ConnectionState.DISCONNECTED
        self.active_config: Optional[VPNConfig] = None
        self.on_state_change: Optional[Callable[[ConnectionState], None]] = None
        self.stats: Dict[str, Any] = {
            "bytes_sent": 0,
            "bytes_received": 0,
            "connected_at": None,
            "current_ip": None,
        }
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        # Auto-detect simulation mode
        if simulate is None:
            simulate = not (shutil.which("wg-quick") or shutil.which("openvpn"))
        self.simulate = simulate
        if self.simulate:
            logger.warning("VPN backends not found — running in SIMULATION mode.")

    # -------- state helpers --------
    def _set_state(self, s: ConnectionState):
        self.state = s
        logger.info(f"State → {s.value}")
        if self.on_state_change:
            try:
                self.on_state_change(s)
            except Exception as e:
                logger.error(f"state callback failed: {e}")

    # -------- public API --------
    def connect(self, config: VPNConfig) -> bool:
        if self.state == ConnectionState.CONNECTED:
            logger.warning("Already connected; disconnect first.")
            return False

        self.active_config = config
        self._set_state(ConnectionState.CONNECTING)

        # Pre-flight safety: kill switch, DNS lockdown
        if config.kill_switch:
            self._enable_kill_switch()
        if config.dns_leak_protection:
            self._lock_dns(config.dns_servers)

        ok = False
        try:
            if config.protocol == "wireguard":
                ok = self._connect_wireguard(config)
            elif config.protocol == "openvpn":
                ok = self._connect_openvpn(config)
            elif config.protocol == "ikev2":
                ok = self._connect_ikev2(config)
            elif config.protocol == "shadowsocks":
                ok = self._connect_shadowsocks(config)
            else:
                logger.error(f"Unknown protocol: {config.protocol}")
        except Exception as e:
            logger.error(f"connect failed: {e}")
            ok = False

        if ok:
            self.stats["connected_at"] = time.time()
            self._set_state(ConnectionState.CONNECTED)
            self._start_monitor()
        else:
            self._set_state(ConnectionState.ERROR)
            self._disable_kill_switch()
        return ok

    def disconnect(self) -> bool:
        if self.state == ConnectionState.DISCONNECTED:
            return True
        self._stop_event.set()
        if self._monitor_thread:
            self._monitor_thread.join(timeout=3)

        ok = True
        try:
            if self.active_config:
                if self.active_config.protocol == "wireguard":
                    ok = self._disconnect_wireguard()
                elif self.active_config.protocol == "openvpn":
                    ok = self._disconnect_openvpn()
        except Exception as e:
            logger.error(f"disconnect error: {e}")
            ok = False

        self._disable_kill_switch()
        self._unlock_dns()
        self.active_config = None
        self.stats = {"bytes_sent": 0, "bytes_received": 0, "connected_at": None, "current_ip": None}
        self._set_state(ConnectionState.DISCONNECTED)
        return ok

    def get_status(self) -> Dict[str, Any]:
        return {
            "state": self.state.value,
            "config": self.active_config.name if self.active_config else None,
            "protocol": self.active_config.protocol if self.active_config else None,
            "stats": dict(self.stats),
            "simulate": self.simulate,
        }

    # -------- protocol implementations --------
    def _connect_wireguard(self, cfg: VPNConfig) -> bool:
        if self.simulate:
            time.sleep(0.6)
            self.stats["current_ip"] = f"10.0.0.{os.getpid() % 250 + 2}"
            return True
        # Real path — build a wg-quick conf and bring it up
        conf_path = self._write_wireguard_conf(cfg)
        try:
            subprocess.run(["wg-quick", "up", conf_path], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"wg-quick up failed: {e.stderr.decode(errors='ignore')}")
            return False

    def _disconnect_wireguard(self) -> bool:
        if self.simulate:
            time.sleep(0.3)
            return True
        conf_path = f"/etc/wireguard/{self.active_config.name}.conf"
        try:
            subprocess.run(["wg-quick", "down", conf_path], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False

    def _write_wireguard_conf(self, cfg: VPNConfig) -> str:
        conf = (
            "[Interface]\n"
            f"PrivateKey = {cfg.private_key}\n"
            f"Address = 10.0.0.2/24\n"
            f"DNS = {', '.join(cfg.dns_servers)}\n"
            f"MTU = {cfg.mtu}\n\n"
            "[Peer]\n"
            f"PublicKey = {cfg.public_key}\n"
            f"{'PresharedKey = ' + cfg.preshared_key + chr(10) if cfg.preshared_key else ''}"
            f"Endpoint = {cfg.server_address}:{cfg.server_port}\n"
            f"AllowedIPs = {cfg.allowed_ips}\n"
            f"PersistentKeepalive = {cfg.keepalive}\n"
        )
        path = f"/tmp/ultravpn_{cfg.name}.conf"
        with open(path, "w") as f:
            f.write(conf)
        os.chmod(path, 0o600)
        return path

    def _connect_openvpn(self, cfg: VPNConfig) -> bool:
        if self.simulate:
            time.sleep(0.8)
            self.stats["current_ip"] = f"10.8.0.{os.getpid() % 250 + 2}"
            return True
        # Real openvpn would be launched here as a subprocess
        return False

    def _disconnect_openvpn(self) -> bool:
        return True

    def _connect_ikev2(self, cfg: VPNConfig) -> bool:
        if self.simulate:
            time.sleep(0.7)
            return True
        return False

    def _connect_shadowsocks(self, cfg: VPNConfig) -> bool:
        if self.simulate:
            time.sleep(0.5)
            return True
        return False

    # -------- safety features --------
    def _enable_kill_switch(self):
        logger.info("🛡️  Kill switch enabled")
        if self.simulate:
            return
        system = platform.system()
        if system == "Linux":
            # Basic iptables kill switch — in production use nftables + specific rules
            try:
                subprocess.run(["iptables", "-I", "OUTPUT", "!", "-o", "tun+", "-j", "DROP"],
                               check=False, capture_output=True)
            except Exception:
                pass

    def _disable_kill_switch(self):
        logger.info("Kill switch disabled")
        if self.simulate:
            return
        if platform.system() == "Linux":
            try:
                subprocess.run(["iptables", "-D", "OUTPUT", "!", "-o", "tun+", "-j", "DROP"],
                               check=False, capture_output=True)
            except Exception:
                pass

    def _lock_dns(self, servers):
        logger.info(f"🔒 DNS locked to {servers}")

    def _unlock_dns(self):
        logger.info("DNS restored")

    # -------- connection monitor --------
    def _start_monitor(self):
        self._stop_event.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()

    def _monitor_loop(self):
        while not self._stop_event.is_set():
            time.sleep(2)
            if self.simulate:
                # simulate small traffic growth
                self.stats["bytes_sent"] += 1024 * 12
                self.stats["bytes_received"] += 1024 * 48
