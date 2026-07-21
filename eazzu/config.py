"""``eazzu config`` — persistent CLI configuration.

Settings are stored as JSON under ``~/.eazzu/config.json`` (override via
``EAZZU_CONFIG`` env var). All settings are optional with sane defaults so
the file doesn't need to exist for EAZZU to operate.

Known settings:
    default_provider   str     default AI provider (fallback: EAZZU_PROVIDER, then 'openai')
    default_model      str|None default model name (fallback: EAZZU_MODEL, then None)
    color              str     'auto' | 'always' | 'never'  (controls ANSI output)
    shell_policy       str     'allowlist' (default) | 'deny' — restricts shell tool
    fs_root            str|None sandbox root for file tools (defaults to cwd)
    web_port           int     default port for 'eazzu web' (default 8787)
    editor             str|None preferred editor (used by dev tools)
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULTS: dict[str, Any] = {
    "default_provider": "auto",
    "default_model": None,
    "color": "auto",
    "shell_policy": "allowlist",
    "fs_root": None,
    "web_port": 8787,
    "editor": None,
    "router_strategy": "random",   # random | healthiest | fastest | cheapest
}

_VALIDATORS = {
    "color": {"auto", "always", "never"},
    "shell_policy": {"allowlist", "deny"},
}


class Config:
    """Simple JSON-backed config dict."""

    def __init__(self, path: Path | None = None) -> None:
        self.path = path or Path(
            os.environ.get("EAZZU_CONFIG") or Path.home() / ".eazzu" / "config.json"
        )
        self._data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        self._data = dict(DEFAULTS)
        if self.path.is_file():
            try:
                with self.path.open("r", encoding="utf-8") as f:
                    user = json.load(f)
                if isinstance(user, dict):
                    # Merge, but drop unknown keys silently so forward-compat is clean.
                    for k, v in user.items():
                        if k in DEFAULTS:
                            self._data[k] = v
            except (OSError, json.JSONDecodeError):
                # Corrupt config shouldn't crash the CLI; fall back to defaults.
                pass

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, sort_keys=True)
        tmp.replace(self.path)

    # --- dict-like access -------------------------------------------------
    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        if key not in DEFAULTS:
            raise KeyError(f"unknown config key: {key!r} (valid: {', '.join(sorted(DEFAULTS))})")
        if key in _VALIDATORS and value not in _VALIDATORS[key]:
            raise ValueError(f"invalid value {value!r} for {key!r} (allowed: {sorted(_VALIDATORS[key])})")
        # Coerce types for known keys.
        if key == "web_port":
            value = int(value)
        self._data[key] = value

    def all(self) -> dict[str, Any]:
        return dict(self._data)

    def reset(self) -> None:
        self._data = dict(DEFAULTS)


# A process-wide singleton so every command sees the same config without
# re-reading the file repeatedly.
_INSTANCE: Config | None = None


def get_config() -> Config:
    global _INSTANCE
    if _INSTANCE is None:
        _INSTANCE = Config()
    return _INSTANCE


def parse_value(raw: str) -> Any:
    """Parse a CLI string into a bool/None/int/float/str/JSON value."""
    low = raw.lower()
    if low in {"true", "yes", "on"}:
        return True
    if low in {"false", "no", "off"}:
        return False
    if low in {"null", "none", ""}:
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    if raw.startswith(("{", "[")):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass
    return raw


__all__ = ["Config", "get_config", "parse_value", "DEFAULTS"]
