"""
UltraVPN — Command-Line Interface
Usage:
    python -m cli.main <command> [options]

Commands:
    list-presets                    Show all built-in presets
    list-configs                    Show saved configs
    use-preset <name>               Load a preset into your configs
    add                             Interactively add a custom config
    remove <name>                   Delete a saved config
    show <name>                     Show details of a config
    connect <name>                  Connect using a saved config
    disconnect                      Disconnect current session
    status                          Show current connection status
    servers                         List servers with latency
    fastest                         Auto-select fastest server
    leak-test                       Run DNS/IP leak test
    genkey                          Generate WireGuard keypair
    export <name> <file>            Export config to file
    import <file>                   Import config from file
    set <key> <value>               Update a global setting
    settings                        Show global settings
"""
import sys
import json
import logging
import argparse
from pathlib import Path

# Allow running as module or script
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.config import ConfigManager, VPNConfig
from core.presets import PRESETS, get_preset, list_presets
from core.vpn_engine import VPNEngine, ConnectionState
from core.security import LeakTester
from core.server_manager import ServerManager
from core.crypto import generate_wireguard_keypair, generate_preshared_key


# ANSI colors
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BLUE = "\033[94m"
    GRAY = "\033[90m"


def banner():
    print(f"""{C.CYAN}{C.BOLD}
╔══════════════════════════════════════════════╗
║       🛡️  UltraVPN — Private & Secure  🛡️      ║
║              v1.0.0 — CLI                    ║
╚══════════════════════════════════════════════╝{C.RESET}""")


# ============ commands ============

def cmd_list_presets(cm, args):
    print(f"{C.BOLD}Available presets:{C.RESET}")
    for name, desc in list_presets().items():
        preset = PRESETS[name]
        tags = " ".join(f"{C.GRAY}[{t}]{C.RESET}" for t in preset.tags)
        print(f"  {C.GREEN}{name:<25}{C.RESET} {tags}")
        print(f"    {C.GRAY}{desc}{C.RESET}")


def cmd_list_configs(cm, args):
    configs = cm.list_configs()
    if not configs:
        print(f"{C.YELLOW}No saved configs. Add one with 'use-preset' or 'add'.{C.RESET}")
        return
    print(f"{C.BOLD}Saved configs:{C.RESET}")
    for name in configs:
        c = cm.get_config(name)
        print(f"  {C.CYAN}{name:<25}{C.RESET} {c.protocol:<10} {c.server_address}:{c.server_port}")


def cmd_use_preset(cm, args):
    try:
        cfg = get_preset(args.name)
    except KeyError as e:
        print(f"{C.RED}{e}{C.RESET}"); return
    cm.add_config(cfg)
    print(f"{C.GREEN}✅ Preset '{args.name}' loaded into your configs.{C.RESET}")
    print(f"   Edit server/keys with: {C.CYAN}ultravpn show {args.name}{C.RESET}")


def cmd_add(cm, args):
    print(f"{C.BOLD}Add custom VPN config{C.RESET} (Ctrl+C to cancel)\n")
    name = input("Name: ").strip()
    if not name:
        print(f"{C.RED}Name required.{C.RESET}"); return
    protocol = input("Protocol [wireguard/openvpn/ikev2/shadowsocks] (wireguard): ").strip() or "wireguard"
    server = input("Server address: ").strip()
    port = int(input("Port (51820): ").strip() or "51820")
    country = input("Country code (US): ").strip().upper() or "US"

    cfg = VPNConfig(name=name, protocol=protocol, server_address=server,
                    server_port=port, endpoint_country=country)

    if protocol == "wireguard":
        gen = input("Generate WireGuard keypair? [Y/n]: ").strip().lower()
        if gen != "n":
            priv, pub = generate_wireguard_keypair()
            cfg.private_key = priv
            print(f"  Public key: {C.CYAN}{pub}{C.RESET}")
            cfg.public_key = input("Peer public key: ").strip()
            psk = input("Generate preshared key? [y/N]: ").strip().lower()
            if psk == "y":
                cfg.preshared_key = generate_preshared_key()
    else:
        cfg.username = input("Username: ").strip()
        cfg.password = input("Password: ").strip()

    ks = input("Kill switch? [Y/n]: ").strip().lower()
    cfg.kill_switch = ks != "n"

    cm.add_config(cfg)
    print(f"{C.GREEN}✅ Config '{name}' saved.{C.RESET}")


def cmd_remove(cm, args):
    if cm.remove_config(args.name):
        print(f"{C.GREEN}✅ Removed '{args.name}'.{C.RESET}")
    else:
        print(f"{C.RED}Not found: {args.name}{C.RESET}")


def cmd_show(cm, args):
    cfg = cm.get_config(args.name)
    if not cfg:
        print(f"{C.RED}Not found: {args.name}{C.RESET}"); return
    d = cfg.to_dict()
    # Redact secrets
    for k in ("private_key", "password", "preshared_key"):
        if d.get(k):
            d[k] = d[k][:6] + "…(hidden)"
    print(json.dumps(d, indent=2))


def cmd_connect(cm, args):
    cfg = cm.get_config(args.name)
    if not cfg:
        print(f"{C.RED}Config '{args.name}' not found.{C.RESET}"); return
    engine = VPNEngine()
    print(f"{C.YELLOW}⚡ Connecting to {cfg.name} ({cfg.server_address})...{C.RESET}")
    if engine.connect(cfg):
        print(f"{C.GREEN}✅ Connected. State: {engine.state.value}{C.RESET}")
        s = engine.get_status()
        print(f"   Protocol: {s['protocol']}   Simulated: {s['simulate']}")
        _save_active(args.name)
    else:
        print(f"{C.RED}❌ Connection failed.{C.RESET}")


def cmd_disconnect(cm, args):
    engine = VPNEngine()
    engine.disconnect()
    _save_active(None)
    print(f"{C.GREEN}✅ Disconnected.{C.RESET}")


def cmd_status(cm, args):
    active = _load_active()
    if active:
        print(f"{C.GREEN}● Active preset: {active}{C.RESET}")
    else:
        print(f"{C.GRAY}○ Not connected{C.RESET}")


def cmd_servers(cm, args):
    sm = ServerManager()
    print(f"{C.YELLOW}Pinging servers...{C.RESET}")
    sm.measure_all()
    print(f"{C.BOLD}{'Server':<15}{'Country':<10}{'City':<15}{'Load':<8}{'Latency':<10}{C.RESET}")
    for s in sorted(sm.servers, key=lambda x: x.latency_ms or 9999):
        lat = f"{s.latency_ms:.0f} ms" if s.latency_ms is not None else f"{C.RED}timeout{C.RESET}"
        load_bar = "█" * int(s.load * 10)
        print(f"  {s.name:<13}{s.country:<10}{s.city:<15}{load_bar:<8}{lat}")


def cmd_fastest(cm, args):
    sm = ServerManager()
    print(f"{C.YELLOW}Finding fastest server...{C.RESET}")
    s = sm.fastest()
    if s:
        print(f"{C.GREEN}⚡ Fastest: {s.name} ({s.city}, {s.country}) — {s.latency_ms:.0f} ms{C.RESET}")
    else:
        print(f"{C.RED}No reachable servers.{C.RESET}")


def cmd_leak_test(cm, args):
    tester = LeakTester()
    print(f"{C.YELLOW}Running leak tests...{C.RESET}")
    result = tester.full_check()
    ip_info = result.get("ip_info")
    if ip_info:
        print(f"  Public IP: {C.CYAN}{ip_info.get('ip')}{C.RESET}")
        print(f"  Country:   {ip_info.get('country', 'n/a')}")
    else:
        print(f"  {C.RED}Could not determine public IP.{C.RESET}")
    for w in result.get("warnings", []):
        print(f"  {C.YELLOW}⚠️  {w}{C.RESET}")
    if not result.get("warnings"):
        print(f"  {C.GREEN}✅ No obvious leaks detected.{C.RESET}")


def cmd_genkey(cm, args):
    priv, pub = generate_wireguard_keypair()
    print(f"Private key: {C.CYAN}{priv}{C.RESET}")
    print(f"Public key:  {C.CYAN}{pub}{C.RESET}")
    print(f"PSK:         {C.CYAN}{generate_preshared_key()}{C.RESET}")


def cmd_export(cm, args):
    cfg = cm.get_config(args.name)
    if not cfg:
        print(f"{C.RED}Not found: {args.name}{C.RESET}"); return
    with open(args.file, "w") as f:
        json.dump(cfg.to_dict(), f, indent=2)
    print(f"{C.GREEN}✅ Exported to {args.file}{C.RESET}")


def cmd_import(cm, args):
    with open(args.file, "r") as f:
        data = json.load(f)
    cfg = VPNConfig.from_dict(data)
    cm.add_config(cfg)
    print(f"{C.GREEN}✅ Imported '{cfg.name}'{C.RESET}")


def cmd_set(cm, args):
    # Try to coerce booleans/ints
    v = args.value
    if v.lower() in ("true", "false"):
        v = v.lower() == "true"
    else:
        try: v = int(v)
        except ValueError: pass
    cm.update_setting(args.key, v)
    print(f"{C.GREEN}✅ {args.key} = {v}{C.RESET}")


def cmd_settings(cm, args):
    print(json.dumps(cm.settings, indent=2))


# ============ helpers ============

def _active_file():
    from pathlib import Path
    p = Path.home() / ".ultravpn" / "active.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _save_active(name):
    with open(_active_file(), "w") as f:
        json.dump({"active": name}, f)


def _load_active():
    try:
        with open(_active_file(), "r") as f:
            return json.load(f).get("active")
    except Exception:
        return None


# ============ dispatcher ============

def build_parser():
    p = argparse.ArgumentParser(prog="ultravpn", description="UltraVPN CLI")
    sub = p.add_subparsers(dest="command", required=False)
    sub.add_parser("list-presets")
    sub.add_parser("list-configs")
    u = sub.add_parser("use-preset"); u.add_argument("name")
    sub.add_parser("add")
    r = sub.add_parser("remove"); r.add_argument("name")
    s = sub.add_parser("show"); s.add_argument("name")
    c = sub.add_parser("connect"); c.add_argument("name")
    sub.add_parser("disconnect")
    sub.add_parser("status")
    sub.add_parser("servers")
    sub.add_parser("fastest")
    sub.add_parser("leak-test")
    sub.add_parser("genkey")
    e = sub.add_parser("export"); e.add_argument("name"); e.add_argument("file")
    i = sub.add_parser("import"); i.add_argument("file")
    st = sub.add_parser("set"); st.add_argument("key"); st.add_argument("value")
    sub.add_parser("settings")
    return p


COMMANDS = {
    "list-presets": cmd_list_presets,
    "list-configs": cmd_list_configs,
    "use-preset": cmd_use_preset,
    "add": cmd_add,
    "remove": cmd_remove,
    "show": cmd_show,
    "connect": cmd_connect,
    "disconnect": cmd_disconnect,
    "status": cmd_status,
    "servers": cmd_servers,
    "fastest": cmd_fastest,
    "leak-test": cmd_leak_test,
    "genkey": cmd_genkey,
    "export": cmd_export,
    "import": cmd_import,
    "set": cmd_set,
    "settings": cmd_settings,
}


def main():
    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(levelname)s %(message)s")
    parser = build_parser()
    args = parser.parse_args()
    banner()
    if not args.command:
        parser.print_help(); return
    cm = ConfigManager()
    fn = COMMANDS.get(args.command)
    if fn:
        try:
            fn(cm, args)
        except KeyboardInterrupt:
            print(f"\n{C.YELLOW}Cancelled.{C.RESET}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
