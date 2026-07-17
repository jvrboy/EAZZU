"""
UltraVPN — Tkinter GUI Dashboard
Provides a modern dark-themed interface for the VPN engine.
"""
import sys
import time
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import tkinter as tk
from tkinter import ttk, messagebox, filedialog

from core.config import ConfigManager, VPNConfig
from core.presets import PRESETS, get_preset
from core.vpn_engine import VPNEngine, ConnectionState
from core.security import LeakTester
from core.server_manager import ServerManager


# --- theme ---
BG = "#0f1220"
BG2 = "#1a1e33"
FG = "#e6e9ef"
ACCENT = "#4ade80"
WARN = "#f59e0b"
ERR = "#ef4444"
MUTED = "#7c8399"


class UltraVPNApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("UltraVPN — Ultra Private VPN")
        self.geometry("900x620")
        self.configure(bg=BG)
        self.minsize(800, 560)

        self.cm = ConfigManager()
        self.engine = VPNEngine()
        self.engine.on_state_change = self._on_state_change
        self.selected_config_name = None
        self._connect_start = None

        self._setup_style()
        self._build_ui()
        self._refresh_configs()
        self._tick()

    # ---------- styles ----------
    def _setup_style(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", background=BG, foreground=FG, fieldbackground=BG2,
                        bordercolor=BG2, lightcolor=BG2, darkcolor=BG2)
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=BG2)
        style.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=BG, foreground=FG,
                        font=("Segoe UI", 20, "bold"))
        style.configure("Muted.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Big.TLabel", background=BG2, foreground=FG,
                        font=("Segoe UI", 14, "bold"))
        style.configure("Status.TLabel", background=BG2, foreground=ACCENT,
                        font=("Segoe UI", 26, "bold"))
        style.configure("TButton", background=BG2, foreground=FG,
                        font=("Segoe UI", 10, "bold"), borderwidth=0, padding=8)
        style.map("TButton", background=[("active", "#2a2f4a")])
        style.configure("Accent.TButton", background=ACCENT, foreground="#0b0e1a",
                        font=("Segoe UI", 11, "bold"), padding=10)
        style.map("Accent.TButton", background=[("active", "#22c55e")])
        style.configure("Danger.TButton", background=ERR, foreground="white",
                        font=("Segoe UI", 11, "bold"), padding=10)
        style.configure("TCombobox", fieldbackground=BG2, background=BG2, foreground=FG)
        style.configure("Treeview", background=BG2, fieldbackground=BG2, foreground=FG,
                        rowheight=26, borderwidth=0)
        style.configure("Treeview.Heading", background=BG, foreground=MUTED,
                        font=("Segoe UI", 9, "bold"))
        style.map("Treeview", background=[("selected", "#2a2f4a")])
        style.configure("TCheckbutton", background=BG2, foreground=FG)
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG, foreground=MUTED,
                        padding=[16, 8], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", BG2)],
                  foreground=[("selected", FG)])

    # ---------- layout ----------
    def _build_ui(self):
        header = ttk.Frame(self); header.pack(fill="x", padx=20, pady=(16, 8))
        ttk.Label(header, text="🛡️  UltraVPN", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text=" Ultra Private • Configurable • Powerful",
                  style="Muted.TLabel").pack(side="left", padx=8)

        nb = ttk.Notebook(self); nb.pack(fill="both", expand=True, padx=20, pady=8)
        self._tab_dashboard(nb)
        self._tab_configs(nb)
        self._tab_servers(nb)
        self._tab_settings(nb)

        # footer
        self.footer = ttk.Label(self, text="Ready.", style="Muted.TLabel")
        self.footer.pack(fill="x", padx=20, pady=(0, 10))

    def _tab_dashboard(self, nb):
        f = ttk.Frame(nb); nb.add(f, text="Dashboard")

        card = ttk.Frame(f, style="Card.TFrame"); card.pack(fill="x", padx=10, pady=10, ipady=20)
        self.status_lbl = ttk.Label(card, text="○ DISCONNECTED", style="Status.TLabel")
        self.status_lbl.pack(pady=(20, 4))
        self.status_sub = ttk.Label(card, text="Not connected", background=BG2, foreground=MUTED)
        self.status_sub.pack()

        row = ttk.Frame(card, style="Card.TFrame"); row.pack(pady=12)
        ttk.Label(row, text="Config:", background=BG2, foreground=MUTED).pack(side="left", padx=6)
        self.config_combo = ttk.Combobox(row, width=32, state="readonly")
        self.config_combo.pack(side="left", padx=6)
        self.config_combo.bind("<<ComboboxSelected>>", self._on_config_selected)

        btns = ttk.Frame(card, style="Card.TFrame"); btns.pack(pady=10)
        self.connect_btn = ttk.Button(btns, text="⚡ CONNECT", style="Accent.TButton",
                                      command=self._on_connect)
        self.connect_btn.pack(side="left", padx=6)
        self.disc_btn = ttk.Button(btns, text="Disconnect", style="Danger.TButton",
                                   command=self._on_disconnect, state="disabled")
        self.disc_btn.pack(side="left", padx=6)

        # stats card
        stats = ttk.Frame(f, style="Card.TFrame"); stats.pack(fill="x", padx=10, pady=(0, 10), ipady=10)
        grid = ttk.Frame(stats, style="Card.TFrame"); grid.pack(pady=8)
        self.stat_ip = self._stat_cell(grid, "IP", "—", 0)
        self.stat_proto = self._stat_cell(grid, "Protocol", "—", 1)
        self.stat_up = self._stat_cell(grid, "Uptime", "00:00:00", 2)
        self.stat_sent = self._stat_cell(grid, "↑ Sent", "0 B", 3)
        self.stat_recv = self._stat_cell(grid, "↓ Recv", "0 B", 4)

        # quick actions
        qa = ttk.Frame(f); qa.pack(fill="x", padx=10, pady=6)
        ttk.Button(qa, text="🔍 Leak Test", command=self._run_leak_test).pack(side="left", padx=4)
        ttk.Button(qa, text="⚡ Auto-select fastest", command=self._auto_fastest).pack(side="left", padx=4)
        ttk.Button(qa, text="🧭 Refresh", command=self._refresh_configs).pack(side="left", padx=4)

    def _stat_cell(self, parent, label, value, col):
        cell = ttk.Frame(parent, style="Card.TFrame")
        cell.grid(row=0, column=col, padx=16)
        ttk.Label(cell, text=label, background=BG2, foreground=MUTED,
                  font=("Segoe UI", 9)).pack()
        val = ttk.Label(cell, text=value, background=BG2, foreground=FG,
                        font=("Segoe UI", 13, "bold"))
        val.pack()
        return val

    def _tab_configs(self, nb):
        f = ttk.Frame(nb); nb.add(f, text="Configs & Presets")

        top = ttk.Frame(f); top.pack(fill="x", padx=10, pady=8)
        ttk.Label(top, text="Presets:", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.preset_combo = ttk.Combobox(top, values=list(PRESETS.keys()), width=32, state="readonly")
        self.preset_combo.pack(side="left", padx=6)
        ttk.Button(top, text="+ Load preset", command=self._load_preset).pack(side="left", padx=4)
        ttk.Button(top, text="+ New custom", command=self._new_custom).pack(side="left", padx=4)
        ttk.Button(top, text="Import…", command=self._import_config).pack(side="left", padx=4)

        # tree
        cols = ("name", "protocol", "server", "country", "kill_switch")
        self.tree = ttk.Treeview(f, columns=cols, show="headings", height=12)
        for c, w in zip(cols, (180, 100, 260, 90, 100)):
            self.tree.heading(c, text=c.replace("_", " ").title())
            self.tree.column(c, width=w, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=10, pady=6)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        actions = ttk.Frame(f); actions.pack(fill="x", padx=10, pady=6)
        ttk.Button(actions, text="✏️  Edit", command=self._edit_config).pack(side="left", padx=4)
        ttk.Button(actions, text="🗑️  Delete", command=self._delete_config).pack(side="left", padx=4)
        ttk.Button(actions, text="⬇  Export", command=self._export_config).pack(side="left", padx=4)
        ttk.Button(actions, text="🔑 Generate keys", command=self._gen_keys_dialog).pack(side="left", padx=4)

    def _tab_servers(self, nb):
        f = ttk.Frame(nb); nb.add(f, text="Servers")
        top = ttk.Frame(f); top.pack(fill="x", padx=10, pady=8)
        ttk.Button(top, text="🔄 Ping all servers", command=self._ping_servers).pack(side="left")
        ttk.Label(top, text="   Tip: green = fast, yellow = ok, red = timeout",
                  style="Muted.TLabel").pack(side="left")

        cols = ("name", "country", "city", "load", "latency")
        self.server_tree = ttk.Treeview(f, columns=cols, show="headings", height=14)
        for c, w in zip(cols, (140, 80, 160, 100, 120)):
            self.server_tree.heading(c, text=c.title())
            self.server_tree.column(c, width=w, anchor="w")
        self.server_tree.pack(fill="both", expand=True, padx=10, pady=6)
        self.server_tree.tag_configure("fast", foreground=ACCENT)
        self.server_tree.tag_configure("mid", foreground=WARN)
        self.server_tree.tag_configure("slow", foreground=ERR)

        self._populate_servers([])

    def _tab_settings(self, nb):
        f = ttk.Frame(nb); nb.add(f, text="Settings")
        box = ttk.Frame(f, style="Card.TFrame"); box.pack(fill="both", expand=True, padx=10, pady=10, ipady=10)
        ttk.Label(box, text="Global Settings", background=BG2, foreground=FG,
                  font=("Segoe UI", 13, "bold")).pack(anchor="w", padx=12, pady=(10, 6))

        self.setting_vars = {}
        opts = [
            ("auto_connect_on_startup", "Auto-connect on startup"),
            ("connect_to_fastest", "Auto-select fastest server"),
            ("block_ads", "Block advertisements"),
            ("block_trackers", "Block trackers"),
            ("block_malware", "Block malware domains"),
            ("tor_over_vpn", "Tor over VPN"),
            ("double_vpn", "Double VPN (multi-hop)"),
            ("reconnect_on_disconnect", "Auto-reconnect on drop"),
            ("notification_enabled", "Desktop notifications"),
        ]
        for key, label in opts:
            v = tk.BooleanVar(value=bool(self.cm.get_setting(key, False)))
            ttk.Checkbutton(box, text=label, variable=v,
                            command=lambda k=key, var=v: self.cm.update_setting(k, var.get())
                            ).pack(anchor="w", padx=20, pady=2)
            self.setting_vars[key] = v

        # info
        info = ttk.Frame(f); info.pack(fill="x", padx=10, pady=8)
        ttk.Label(info, text=f"Config directory: {self.cm.config_dir}", style="Muted.TLabel").pack(anchor="w")
        ttk.Label(info, text="Simulation mode: " + ("ON (no VPN backend detected)" if self.engine.simulate else "OFF"),
                  style="Muted.TLabel").pack(anchor="w")

    # ---------- data refresh ----------
    def _refresh_configs(self):
        names = self.cm.list_configs()
        self.config_combo["values"] = names
        if names and not self.config_combo.get():
            self.config_combo.set(names[0])
            self.selected_config_name = names[0]
        # tree
        for i in self.tree.get_children():
            self.tree.delete(i)
        for n in names:
            c = self.cm.get_config(n)
            self.tree.insert("", "end", values=(
                c.name, c.protocol, f"{c.server_address}:{c.server_port}",
                c.endpoint_country, "ON" if c.kill_switch else "OFF"))

    # ---------- events ----------
    def _on_config_selected(self, _):
        self.selected_config_name = self.config_combo.get()

    def _on_tree_select(self, _):
        sel = self.tree.selection()
        if sel:
            self.selected_config_name = self.tree.item(sel[0])["values"][0]
            self.config_combo.set(self.selected_config_name)

    def _on_connect(self):
        name = self.config_combo.get() or self.selected_config_name
        if not name:
            messagebox.showwarning("No config", "Please select or add a config first."); return
        cfg = self.cm.get_config(name)
        if not cfg: return
        self._connect_start = time.time()
        self.footer.config(text=f"Connecting to {cfg.name}…")
        threading.Thread(target=self.engine.connect, args=(cfg,), daemon=True).start()

    def _on_disconnect(self):
        threading.Thread(target=self.engine.disconnect, daemon=True).start()
        self.footer.config(text="Disconnecting…")

    def _on_state_change(self, state: ConnectionState):
        self.after(0, self._render_state, state)

    def _render_state(self, state):
        color_map = {
            ConnectionState.DISCONNECTED: ("○ DISCONNECTED", MUTED),
            ConnectionState.CONNECTING: ("⋯ CONNECTING", WARN),
            ConnectionState.CONNECTED: ("● CONNECTED", ACCENT),
            ConnectionState.RECONNECTING: ("⟳ RECONNECTING", WARN),
            ConnectionState.ERROR: ("✕ ERROR", ERR),
        }
        text, color = color_map.get(state, ("?", MUTED))
        self.status_lbl.config(text=text, foreground=color)
        is_conn = state == ConnectionState.CONNECTED
        self.connect_btn.config(state="disabled" if is_conn or state == ConnectionState.CONNECTING else "normal")
        self.disc_btn.config(state="normal" if is_conn else "disabled")
        if is_conn and self.engine.active_config:
            c = self.engine.active_config
            self.status_sub.config(text=f"{c.name} • {c.endpoint_city or c.endpoint_country}")
            self.stat_proto.config(text=c.protocol.upper())
            self.stat_ip.config(text=self.engine.stats.get("current_ip") or "—")
            self.footer.config(text=f"Connected to {c.name}")
        else:
            self.status_sub.config(text="Not connected")
            self.stat_proto.config(text="—")
            self.stat_ip.config(text="—")
            if state == ConnectionState.DISCONNECTED:
                self.footer.config(text="Ready.")

    # periodic UI refresh
    def _tick(self):
        if self.engine.state == ConnectionState.CONNECTED and self.engine.stats.get("connected_at"):
            up = int(time.time() - self.engine.stats["connected_at"])
            h, r = divmod(up, 3600); m, s = divmod(r, 60)
            self.stat_up.config(text=f"{h:02d}:{m:02d}:{s:02d}")
            self.stat_sent.config(text=self._fmt_bytes(self.engine.stats["bytes_sent"]))
            self.stat_recv.config(text=self._fmt_bytes(self.engine.stats["bytes_received"]))
        else:
            self.stat_up.config(text="00:00:00")
            self.stat_sent.config(text="0 B")
            self.stat_recv.config(text="0 B")
        self.after(1000, self._tick)

    @staticmethod
    def _fmt_bytes(n):
        for u in ("B", "KB", "MB", "GB", "TB"):
            if n < 1024: return f"{n:.1f} {u}"
            n /= 1024
        return f"{n:.1f} PB"

    # ---------- actions ----------
    def _load_preset(self):
        name = self.preset_combo.get()
        if not name: return
        cfg = get_preset(name)
        self.cm.add_config(cfg)
        self._refresh_configs()
        self.footer.config(text=f"Loaded preset '{name}'")

    def _new_custom(self):
        ConfigDialog(self, self.cm, on_save=self._refresh_configs)

    def _edit_config(self):
        if not self.selected_config_name: return
        cfg = self.cm.get_config(self.selected_config_name)
        if cfg:
            ConfigDialog(self, self.cm, existing=cfg, on_save=self._refresh_configs)

    def _delete_config(self):
        if not self.selected_config_name: return
        if messagebox.askyesno("Delete", f"Delete '{self.selected_config_name}'?"):
            self.cm.remove_config(self.selected_config_name)
            self._refresh_configs()

    def _export_config(self):
        if not self.selected_config_name: return
        cfg = self.cm.get_config(self.selected_config_name)
        if not cfg: return
        path = filedialog.asksaveasfilename(defaultextension=".json",
                                            initialfile=f"{cfg.name}.json",
                                            filetypes=[("JSON", "*.json")])
        if path:
            import json
            with open(path, "w") as f:
                json.dump(cfg.to_dict(), f, indent=2)
            messagebox.showinfo("Exported", f"Config exported to {path}")

    def _import_config(self):
        import json
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json")])
        if not path: return
        try:
            with open(path, "r") as f:
                data = json.load(f)
            self.cm.add_config(VPNConfig.from_dict(data))
            self._refresh_configs()
        except Exception as e:
            messagebox.showerror("Import error", str(e))

    def _gen_keys_dialog(self):
        from core.crypto import generate_wireguard_keypair, generate_preshared_key
        try:
            priv, pub = generate_wireguard_keypair()
            psk = generate_preshared_key()
        except Exception as e:
            messagebox.showerror("Error", str(e)); return
        top = tk.Toplevel(self); top.title("Generated Keys"); top.configure(bg=BG)
        top.geometry("560x260")
        for label, val in [("Private key", priv), ("Public key", pub), ("PSK", psk)]:
            ttk.Label(top, text=label + ":", background=BG, foreground=MUTED).pack(anchor="w", padx=12, pady=(10, 0))
            e = tk.Entry(top, width=76, bg=BG2, fg=FG, insertbackground=FG); e.pack(padx=12, fill="x")
            e.insert(0, val)

    def _run_leak_test(self):
        self.footer.config(text="Running leak test…")
        def go():
            r = LeakTester().full_check()
            ip = (r.get("ip_info") or {}).get("ip", "?")
            warns = r.get("warnings") or ["No leaks detected"]
            self.after(0, lambda: messagebox.showinfo("Leak Test", f"Public IP: {ip}\n\n" + "\n".join(warns)))
            self.after(0, lambda: self.footer.config(text="Leak test complete."))
        threading.Thread(target=go, daemon=True).start()

    def _auto_fastest(self):
        self.footer.config(text="Pinging servers…")
        def go():
            sm = ServerManager()
            s = sm.fastest()
            if s:
                msg = f"Fastest: {s.name} ({s.city}, {s.country}) — {s.latency_ms:.0f} ms"
            else:
                msg = "No reachable servers."
            self.after(0, lambda: self.footer.config(text=msg))
        threading.Thread(target=go, daemon=True).start()

    def _ping_servers(self):
        self.footer.config(text="Pinging servers…")
        def go():
            sm = ServerManager(); sm.measure_all()
            self.after(0, lambda: self._populate_servers(sm.servers))
            self.after(0, lambda: self.footer.config(text="Server ping complete."))
        threading.Thread(target=go, daemon=True).start()

    def _populate_servers(self, servers):
        for i in self.server_tree.get_children():
            self.server_tree.delete(i)
        for s in sorted(servers, key=lambda x: x.latency_ms or 9999):
            lat = f"{s.latency_ms:.0f} ms" if s.latency_ms is not None else "timeout"
            tag = "slow" if s.latency_ms is None else ("fast" if s.latency_ms < 80 else "mid" if s.latency_ms < 200 else "slow")
            load = "█" * int(s.load * 10) + "·" * (10 - int(s.load * 10))
            self.server_tree.insert("", "end",
                                    values=(s.name, s.country, s.city, load, lat), tags=(tag,))


class ConfigDialog(tk.Toplevel):
    """Add / edit a VPN configuration."""
    def __init__(self, parent, cm: ConfigManager, existing: VPNConfig = None, on_save=None):
        super().__init__(parent)
        self.title("Edit Config" if existing else "New Custom Config")
        self.configure(bg=BG); self.geometry("520x560")
        self.cm = cm; self.on_save = on_save; self.existing = existing
        cfg = existing or VPNConfig(name="")
        self._vars = {}
        fields = [
            ("name", "Name"), ("protocol", "Protocol"), ("server_address", "Server address"),
            ("server_port", "Port"), ("endpoint_country", "Country code"),
            ("private_key", "Private key"), ("public_key", "Public key"),
            ("preshared_key", "Preshared key"), ("username", "Username"), ("password", "Password"),
            ("mtu", "MTU"), ("keepalive", "Keepalive"),
        ]
        for k, label in fields:
            row = ttk.Frame(self, style="Card.TFrame"); row.pack(fill="x", padx=12, pady=3)
            ttk.Label(row, text=label, background=BG, foreground=MUTED, width=18).pack(side="left")
            v = tk.StringVar(value=str(getattr(cfg, k, "")))
            e = tk.Entry(row, textvariable=v, bg=BG2, fg=FG, insertbackground=FG, relief="flat")
            e.pack(side="left", fill="x", expand=True, padx=6, ipady=4)
            self._vars[k] = v
        # checkboxes
        self._bool_vars = {}
        for k, label in [("kill_switch", "Kill switch"),
                         ("dns_leak_protection", "DNS leak protection"),
                         ("ipv6_leak_protection", "IPv6 leak protection"),
                         ("obfuscation", "Obfuscation"),
                         ("multi_hop", "Multi-hop")]:
            v = tk.BooleanVar(value=bool(getattr(cfg, k, False)))
            ttk.Checkbutton(self, text=label, variable=v).pack(anchor="w", padx=16)
            self._bool_vars[k] = v

        btns = ttk.Frame(self); btns.pack(fill="x", pady=12)
        ttk.Button(btns, text="Cancel", command=self.destroy).pack(side="right", padx=6)
        ttk.Button(btns, text="Save", style="Accent.TButton", command=self._save).pack(side="right")

    def _save(self):
        name = self._vars["name"].get().strip()
        if not name:
            messagebox.showwarning("Missing", "Name required"); return
        data = {}
        for k, v in self._vars.items():
            val = v.get()
            if k in ("server_port", "mtu", "keepalive"):
                try: val = int(val)
                except ValueError: val = 0
            data[k] = val
        for k, v in self._bool_vars.items():
            data[k] = v.get()
        cfg = VPNConfig(**{k: v for k, v in data.items() if k in VPNConfig.__annotations__})
        self.cm.add_config(cfg)
        if self.on_save: self.on_save()
        self.destroy()


def main():
    app = UltraVPNApp()
    app.mainloop()


if __name__ == "__main__":
    main()
