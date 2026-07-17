"""
UltraVPN — integration & unit tests.
Run: python -m tests.test_all
"""
import sys
import time
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import ConfigManager, VPNConfig
from core.presets import PRESETS, get_preset, list_presets
from core.vpn_engine import VPNEngine, ConnectionState
from core.server_manager import ServerManager
from core.security import Blocklist


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cm = ConfigManager(config_dir=self.tmp)

    def test_add_and_load(self):
        cfg = VPNConfig(name="test1", server_address="1.2.3.4")
        self.cm.add_config(cfg)
        cm2 = ConfigManager(config_dir=self.tmp)
        self.assertIn("test1", cm2.list_configs())
        self.assertEqual(cm2.get_config("test1").server_address, "1.2.3.4")

    def test_remove(self):
        self.cm.add_config(VPNConfig(name="tmp"))
        self.assertTrue(self.cm.remove_config("tmp"))
        self.assertFalse(self.cm.remove_config("nope"))

    def test_settings_persistence(self):
        self.cm.update_setting("block_ads", False)
        cm2 = ConfigManager(config_dir=self.tmp)
        self.assertFalse(cm2.get_setting("block_ads"))


class TestPresets(unittest.TestCase):
    def test_all_presets_valid(self):
        self.assertTrue(len(PRESETS) >= 8)
        for name, cfg in PRESETS.items():
            self.assertEqual(cfg.name, name)
            self.assertTrue(cfg.protocol in ("wireguard", "openvpn", "ikev2", "shadowsocks"))
            self.assertTrue(cfg.server_port > 0)

    def test_get_preset_returns_copy(self):
        a = get_preset("balanced_default")
        a.server_address = "MODIFIED"
        b = get_preset("balanced_default")
        self.assertNotEqual(b.server_address, "MODIFIED")

    def test_missing_preset(self):
        with self.assertRaises(KeyError):
            get_preset("no_such_preset")


class TestEngine(unittest.TestCase):
    def test_connect_disconnect_cycle(self):
        eng = VPNEngine(simulate=True)
        cfg = get_preset("balanced_default")
        self.assertTrue(eng.connect(cfg))
        self.assertEqual(eng.state, ConnectionState.CONNECTED)
        self.assertIsNotNone(eng.stats["current_ip"])
        time.sleep(2.5)  # let monitor accumulate traffic
        self.assertTrue(eng.stats["bytes_sent"] > 0)
        self.assertTrue(eng.disconnect())
        self.assertEqual(eng.state, ConnectionState.DISCONNECTED)

    def test_multiple_protocols(self):
        for proto in ("wireguard", "openvpn", "ikev2", "shadowsocks"):
            eng = VPNEngine(simulate=True)
            cfg = VPNConfig(name=f"t_{proto}", protocol=proto,
                            server_address="test.example.com", server_port=443)
            self.assertTrue(eng.connect(cfg), f"{proto} should connect in sim mode")
            eng.disconnect()


class TestServers(unittest.TestCase):
    def test_list(self):
        sm = ServerManager()
        self.assertTrue(len(sm.servers) > 0)
        self.assertTrue(len(sm.list_countries()) > 0)

    def test_filter(self):
        sm = ServerManager()
        us = sm.filter_by_country("US")
        self.assertTrue(all(s.country == "US" for s in us))


class TestBlocklist(unittest.TestCase):
    def test_block(self):
        bl = Blocklist()
        self.assertTrue(bl.is_blocked("doubleclick.net"))
        self.assertTrue(bl.is_blocked("ads.doubleclick.net"))
        self.assertFalse(bl.is_blocked("example.com"))

    def test_stats(self):
        s = Blocklist().stats()
        self.assertTrue(s["total_domains"] > 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
