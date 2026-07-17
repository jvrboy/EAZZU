"""Performance benchmark for UltraVPN core components."""
import sys, time, tempfile, statistics
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.config import ConfigManager, VPNConfig
from core.presets import PRESETS, get_preset
from core.vpn_engine import VPNEngine
from core.crypto import generate_wireguard_keypair, encrypt_data, decrypt_data
from core.server_manager import ServerManager


def bench(name, fn, n=100):
    times = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        times.append((time.perf_counter() - t) * 1000)
    print(f"  {name:<40} avg={statistics.mean(times):7.3f} ms  "
          f"p95={sorted(times)[int(0.95*n)]:7.3f} ms  min={min(times):6.3f} ms")


def main():
    print("=" * 72)
    print("UltraVPN v1.0.0 — Performance Benchmark")
    print("=" * 72)

    # 1. keypair generation
    print("\n[1] Cryptography")
    bench("WireGuard keypair generation", lambda: generate_wireguard_keypair(), 50)
    payload = "x" * 1024
    bench("Encrypt 1 KB data", lambda: encrypt_data(payload, "password"), 20)
    tok = encrypt_data(payload, "password")
    bench("Decrypt 1 KB data", lambda: decrypt_data(tok, "password"), 20)

    # 2. config persistence
    print("\n[2] Config persistence")
    tmp = tempfile.mkdtemp()
    cm = ConfigManager(config_dir=tmp)
    bench("Add config + save", lambda: cm.add_config(VPNConfig(name=f"c{time.time_ns()}")), 100)
    bench("List configs", lambda: cm.list_configs(), 1000)

    # 3. VPN engine
    print("\n[3] VPN engine (simulation mode)")
    eng = VPNEngine(simulate=True)
    cfg = get_preset("balanced_default")
    times = []
    for _ in range(20):
        t = time.perf_counter()
        eng.connect(cfg)
        eng.disconnect()
        times.append((time.perf_counter() - t) * 1000)
    print(f"  {'connect + disconnect cycle':<40} avg={statistics.mean(times):7.1f} ms  "
          f"min={min(times):7.1f} ms  max={max(times):7.1f} ms")

    # 4. server manager (measures real TCP handshakes; will be timeouts to placeholder hosts)
    print("\n[4] Server manager")
    sm = ServerManager()
    t = time.perf_counter()
    sm.measure_all()
    reachable = sum(1 for s in sm.servers if s.latency_ms is not None)
    print(f"  Pinged {len(sm.servers)} servers in {(time.perf_counter()-t)*1000:.0f} ms  "
          f"({reachable} reachable)")

    # 5. preset library
    print("\n[5] Preset library")
    print(f"  Presets available:                       {len(PRESETS)}")
    print(f"  Categories covered:                      privacy, streaming, gaming, P2P, stealth, mobile")

    print("\n" + "=" * 72)
    print("Benchmark complete.")
    print("=" * 72)


if __name__ == "__main__":
    main()
