"""Tkinter desktop GUI for the AI Connector."""
from __future__ import annotations

import threading
import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox

from ai_connector import Connector
from eazzu.providers.providers import *  # noqa: F401,F403


class ConnectorGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AI API Connector")
        self.root.geometry("900x700")
        self.connector = Connector(enable_cache=True)

        self._build_layout()
        self._populate_providers()

    def _build_layout(self):
        top = ttk.Frame(self.root, padding=8)
        top.pack(fill="x")

        ttk.Label(top, text="Provider:").grid(row=0, column=0, sticky="w")
        self.provider_var = tk.StringVar()
        self.provider_cb = ttk.Combobox(
            top, textvariable=self.provider_var, width=25, state="readonly"
        )
        self.provider_cb.grid(row=0, column=1, padx=4)
        self.provider_cb.bind("<<ComboboxSelected>>", self._on_provider_change)

        ttk.Label(top, text="Model:").grid(row=0, column=2, sticky="w")
        self.model_var = tk.StringVar()
        self.model_entry = ttk.Entry(top, textvariable=self.model_var, width=30)
        self.model_entry.grid(row=0, column=3, padx=4)

        ttk.Label(top, text="Base URL (opt):").grid(row=1, column=0, sticky="w", pady=4)
        self.base_url_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.base_url_var, width=60).grid(
            row=1, column=1, columnspan=3, sticky="we", padx=4
        )

        ttk.Label(top, text="API Key (opt):").grid(row=2, column=0, sticky="w", pady=4)
        self.api_key_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.api_key_var, width=60, show="*").grid(
            row=2, column=1, columnspan=3, sticky="we", padx=4
        )
        ttk.Button(top, text="Save Encrypted", command=self._save_key).grid(row=2, column=4, padx=4)

        self.stream_var = tk.BooleanVar(value=True)
        self.cache_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(top, text="Stream", variable=self.stream_var).grid(row=3, column=1, sticky="w")
        ttk.Checkbutton(top, text="Cache", variable=self.cache_var).grid(row=3, column=2, sticky="w")

        # Input
        mid = ttk.Frame(self.root, padding=8)
        mid.pack(fill="both", expand=True)
        ttk.Label(mid, text="Prompt:").pack(anchor="w")
        self.prompt_box = scrolledtext.ScrolledText(mid, height=6, wrap="word")
        self.prompt_box.pack(fill="x")
        self.prompt_box.insert("1.0", "Hello! Introduce yourself in one sentence.")

        ttk.Label(mid, text="Response:").pack(anchor="w", pady=(8, 0))
        self.output_box = scrolledtext.ScrolledText(mid, height=20, wrap="word")
        self.output_box.pack(fill="both", expand=True)

        # Buttons
        bot = ttk.Frame(self.root, padding=8)
        bot.pack(fill="x")
        ttk.Button(bot, text="Send", command=self._send).pack(side="left", padx=4)
        ttk.Button(bot, text="Clear", command=lambda: self.output_box.delete("1.0", "end")).pack(side="left", padx=4)
        ttk.Button(bot, text="Usage Stats", command=self._show_usage).pack(side="left", padx=4)
        ttk.Button(bot, text="Refresh Providers", command=self._populate_providers).pack(side="left", padx=4)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(bot, textvariable=self.status_var, anchor="w").pack(side="right", padx=4)

    def _populate_providers(self):
        provs = self.connector.providers()
        self.provider_cb["values"] = provs
        if provs:
            self.provider_cb.current(provs.index("openai") if "openai" in provs else 0)
            self._on_provider_change()

    def _on_provider_change(self, *_):
        name = self.provider_var.get()
        if not name:
            return
        cls = self.connector.get_provider.__self__ and None
        from eazzu.providers.core.registry import PROVIDER_REGISTRY
        p_cls = PROVIDER_REGISTRY.get(name)
        if p_cls:
            self.model_var.set(getattr(p_cls, "default_model", ""))
            self.base_url_var.set(getattr(p_cls, "default_base_url", ""))

    def _save_key(self):
        prov = self.provider_var.get()
        val = self.api_key_var.get().strip()
        if prov and val:
            self.connector.config.set(prov, val)
            self.api_key_var.set("")
            messagebox.showinfo("Saved", f"Key stored (encrypted) for '{prov}'")

    def _send(self):
        provider = self.provider_var.get()
        prompt = self.prompt_box.get("1.0", "end").strip()
        if not provider or not prompt:
            messagebox.showwarning("Missing", "Provider and prompt are required")
            return
        self.output_box.delete("1.0", "end")
        self.status_var.set(f"Calling {provider}…")
        threading.Thread(target=self._do_send, args=(provider, prompt), daemon=True).start()

    def _do_send(self, provider, prompt):
        model = self.model_var.get() or None
        base_url = self.base_url_var.get() or None
        try:
            if self.stream_var.get():
                for chunk in self.connector.stream(provider, prompt, model=model, base_url=base_url):
                    self.output_box.insert("end", chunk)
                    self.output_box.see("end")
                    self.output_box.update_idletasks()
                self.status_var.set("Done (stream)")
            else:
                resp = self.connector.chat(
                    provider, prompt, model=model, base_url=base_url,
                    use_cache=self.cache_var.get(),
                )
                self.output_box.insert("end", resp.content)
                self.status_var.set(
                    f"{resp.total_tokens} tok · ${resp.cost_usd:.6f} · {resp.latency_ms:.0f}ms"
                )
        except Exception as e:
            self.output_box.insert("end", f"\n[ERROR] {e}")
            self.status_var.set("Error")

    def _show_usage(self):
        s = self.connector.tracker.summary()
        text = "\n".join(f"{k}: {v}" for k, v in s.items()) or "(no usage yet)"
        messagebox.showinfo("Usage Summary", text)


def main():
    root = tk.Tk()
    ConnectorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
