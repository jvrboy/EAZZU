# 🛡️ UltraVPN — Ultra Private, Configurable Python VPN Tool

A full-featured VPN client written in pure Python with **CLI + GUI dashboard**, multiple protocols, curated presets, and a strong focus on privacy.

> ⚠️ **Educational / self-hosted use.** Server addresses in the built-in presets are placeholders. Point them at your own WireGuard/OpenVPN server or a provider whose credentials you own.

---

## ✨ Features

### Core
- **4 protocols**: WireGuard, OpenVPN, IKEv2, Shadowsocks
- **9 ready-made presets**: Ultra-Privacy US/EU, Streaming US/UK, Gaming, P2P/Torrent, Bypass Censorship, Balanced Default, Mobile
- **Custom configs**: fully editable — server, port, DNS, encryption, MTU, keepalive, allowed IPs
- **Simulation mode**: automatically enabled when no VPN backend is installed, so the whole app is usable offline for testing

### Privacy & Security
- 🔒 **Kill switch** — blocks all traffic if VPN drops
- 🛡️ **DNS-leak protection** — DNS pinned to trusted resolvers (Cloudflare / Quad9)
- 🛡️ **IPv6-leak protection**
- 🌀 **Multi-hop** — chain your traffic through 2+ servers
- 🥷 **Obfuscation** — disguise VPN traffic as HTTPS
- ✂️ **Split tunneling** — route only chosen apps through the VPN
- 🚫 **Ad / tracker / malware blocklist**
- 🧅 **Tor-over-VPN** toggle
- 🔑 **On-device WireGuard keypair generation** (Curve25519) + PSK
- 🔍 **Built-in leak tester** (public IP + DNS)

### UX
- 🖥️ **Dark-themed Tkinter GUI dashboard** with live status, uptime, traffic stats
- ⌨️ **Full CLI** with 17 commands
- ⚡ **Auto-select fastest server** (TCP-handshake latency + load penalty)
- 💾 **Encrypted local storage** of configs
- 📤 **Import/export** configs as JSON
- 🔄 **Auto-reconnect** on drop

---

## 📦 Installation

```bash
# 1. Unzip and enter the folder
unzip UltraVPN-1.0.0.zip && cd vpn_tool

# 2. (optional) create a virtualenv
python3 -m venv venv && source venv/bin/activate

# 3. Install the one dependency
pip install -r requirements.txt
```

For real (non-simulated) connections on Linux you also need one of:
```bash
sudo apt install wireguard-tools openvpn
```

---

## 🚀 Quick Start

### GUI dashboard
```bash
python -m gui.dashboard
```

### CLI
```bash
# See all presets
python -m cli.main list-presets

# Load the ultra-privacy preset
python -m cli.main use-preset ultra_privacy_us

# Connect
python -m cli.main connect ultra_privacy_us

# Status / disconnect
python -m cli.main status
python -m cli.main disconnect

# Find fastest server
python -m cli.main fastest

# Run a leak test
python -m cli.main leak-test

# Generate a WireGuard keypair
python -m cli.main genkey
```

---

## 🧩 Preset Overview

| Preset | Focus | Highlights |
|---|---|---|
| `ultra_privacy_us` | Max privacy | Multi-hop US→CA, ChaCha20, Quad9 DNS |
| `ultra_privacy_eu` | Max privacy (EU) | Multi-hop CH→IS, privacy jurisdictions |
| `streaming_us` / `streaming_uk` | Streaming | High-speed, low overhead |
| `gaming_low_latency` | Gaming | Split tunnel, MTU 1500, keepalive 15 |
| `p2p_torrent` | P2P | Kill switch always on, NL server |
| `bypass_censorship` | Stealth | OpenVPN/443, obfuscated |
| `balanced_default` | Daily use | Speed + privacy balance |
| `mobile_data_saver` | Mobile | Low MTU, extended keepalive |

---

## 🏗️ Architecture

```
vpn_tool/
├── core/
│   ├── config.py          # config data-class + persistence
│   ├── presets.py         # 9 curated presets
│   ├── vpn_engine.py      # state machine, protocol dispatchers
│   ├── crypto.py          # WireGuard keypair, PSK, config encryption
│   ├── security.py        # leak tester, blocklists
│   └── server_manager.py  # latency probing, fastest server pick
├── cli/main.py            # argparse CLI
├── gui/dashboard.py       # Tkinter dashboard
├── tests/test_all.py      # unittest suite (17 tests)
├── requirements.txt
└── README.md
```

---

## ✅ Testing

```bash
python -m tests.test_all
```

All tests use simulation mode so they run anywhere without root or a real VPN backend.

---

## 🔐 Security notes

- Configs are stored under `~/.ultravpn/` with `0600` permissions.
- WireGuard keys are generated with `cryptography`'s X25519 primitives (no home-rolled crypto).
- Kill switch uses `iptables` on Linux (real mode). Simulation mode logs the action but doesn't touch firewall rules.
- The tool never uploads any config off-device.

---

## 📝 License

MIT — see LICENSE.
