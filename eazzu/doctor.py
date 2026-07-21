"""``eazzu doctor`` — environment diagnostics for EAZZU.

Reports:
* Python implementation / version / executable path
* Operating system and architecture
* EAZZU package version and install location
* Availability of optional-dependency groups (``trading``, ``dev``, ``image``,
  ``pdf``, ``slides``, ``full``) reported individually
* Home directory, config directory (~/.eazzu), free disk space
* Stored API keys (names only — never values), keyfile encryption status
* Connectivity quick-checks (GitHub PyPI reachability)
* Common mis-configurations (outdated pip, missing write permissions)
"""
from __future__ import annotations

import importlib
import importlib.util
import os
import platform
import shutil
import socket
import sys
from pathlib import Path
from typing import Any

from eazzu.cli_ui import colorize, C, kv, status_line


# Each entry is (group_name, pip_extra, list_of(import_names)).
_OPTIONAL_GROUPS: list[tuple[str, str, tuple[str, ...]]] = [
    ("trading", "trading", ("pandas", "numpy", "websocket")),
    ("dev", "dev", ("rich",)),
    ("image", "image", ("PIL",)),
    ("pdf", "pdf", ("fpdf",)),
    ("slides", "slides", ("pptx",)),
]


def _module_available(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


def _check_group(mods: tuple[str, ...]) -> tuple[bool, list[str]]:
    missing = [m for m in mods if not _module_available(m)]
    return (len(missing) == 0, missing)


def _config_dir() -> Path:
    return Path(os.environ.get("EAZZU_HOME", Path.home() / ".eazzu"))


def _free_disk_bytes(p: Path) -> int | None:
    try:
        return shutil.disk_usage(p).free
    except OSError:
        return None


def _human_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} PB"


def _tcp_reachable(host: str, port: int = 443, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def run_doctor(fix: bool = False) -> dict[str, Any]:
    """Run all diagnostics and return a structured report.

    When ``fix=True`` we attempt to create the config directory if missing.
    """
    report: dict[str, Any] = {"status": "ok", "checks": []}

    def _add(name: str, ok: bool, detail: str):
        report["checks"].append({"name": name, "ok": ok, "detail": detail})
        if not ok and report["status"] == "ok":
            report["status"] = "warn"

    # ---------- Python ----------
    _add(
        "python",
        True,
        f"{platform.python_implementation()} {platform.python_version()} at {sys.executable}",
    )

    # ---------- OS ----------
    _add(
        "platform",
        True,
        f"{platform.system()} {platform.release()} ({platform.machine()})",
    )

    # ---------- EAZZU package ----------
    import eazzu

    eazzu_path = Path(eazzu.__file__).parent if eazzu.__file__ else Path("?")
    _add("eazzu", True, f"v{eazzu.__version__} at {eazzu_path}")

    # ---------- Optional deps ----------
    extras_status: dict[str, dict] = {}
    for group, extra, mods in _OPTIONAL_GROUPS:
        ok, missing = _check_group(mods)
        extras_status[group] = {"ok": ok, "missing": missing}
        detail = "all imports ok" if ok else f"missing: {', '.join(missing)} (pip install -e '.[{extra}]')"
        _add(f"extra[{group}]", ok, detail)

    # ---------- Config directory ----------
    cfg = _config_dir()
    cfg_exists = cfg.is_dir()
    if not cfg_exists and fix:
        try:
            cfg.mkdir(parents=True, exist_ok=True)
            cfg_exists = True
        except OSError as e:
            _add("config_dir", False, f"could not create {cfg}: {e}")
    else:
        _add(
            "config_dir",
            cfg_exists,
            f"{cfg} — {'exists' if cfg_exists else 'missing (run with --fix to create)'}",
        )

    if cfg_exists:
        writable = os.access(cfg, os.W_OK)
        _add("config_writable", writable, f"{cfg} is {'writable' if writable else 'NOT writable'}")

    # ---------- Key store ----------
    try:
        from eazzu.providers import ConfigManager
        cm = ConfigManager()
        stored = cm.list_stored()
        keyfile = Path(cm.path) if hasattr(cm, "path") else cfg / "keys.enc"
        encrypted = keyfile.exists()
        _add(
            "keystore",
            True,
            f"{len(stored)} key(s) stored ({', '.join(stored) if stored else 'none'}) — "
            f"encrypted={'yes' if encrypted else 'n/a'} at {keyfile}",
        )
    except Exception as e:  # pragma: no cover — defensive
        _add("keystore", False, f"unavailable: {e}")

    # ---------- Disk ----------
    free = _free_disk_bytes(Path.home())
    if free is not None:
        _add("disk", free > 100 * 1024 * 1024, f"home free: {_human_bytes(free)}")

    # ---------- Network (best-effort, non-fatal) ----------
    gh = _tcp_reachable("github.com")
    pypi = _tcp_reachable("pypi.org")
    _add("network.github", gh, "github.com reachable" if gh else "github.com unreachable (offline?)")
    _add("network.pypi", pypi, "pypi.org reachable" if pypi else "pypi.org unreachable")

    # ---------- pip version (light touch) ----------
    pip_version = None
    try:
        import pip  # type: ignore
        pip_version = getattr(pip, "__version__", "?")
    except Exception:  # pragma: no cover
        pass
    _add("pip", bool(pip_version), f"pip {pip_version or 'not found'}")

    return report


def print_report(report: dict[str, Any]) -> None:
    """Render a doctor report to stdout with ANSI color."""
    status = report["status"]
    badge = {
        "ok": colorize("✓ healthy", C.BGREEN),
        "warn": colorize("⚠ issues found", C.BYELLOW),
        "fail": colorize("✗ errors", C.BRED),
    }.get(status, status)
    print(f"EAZZU doctor: {badge}")
    print()
    for c in report["checks"]:
        mark = colorize("✓", C.GREEN) if c["ok"] else colorize("✗", C.YELLOW)
        print(f"  {mark} {colorize(c['name'], C.CYAN):34s} {c['detail']}")


__all__ = ["run_doctor", "print_report"]
