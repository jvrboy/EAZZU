"""Auto-install — install optional Python dependencies on demand.

On first use of a tool that requires an optional library (Pillow, pandas,
pyautogui, mss, playwright, rich, …) EAZZU can pip-install it into the
active environment. This keeps the base install iSH / Colab friendly — the
core package stays slim, but when a user runs `eazzu computer screenshot`
on a Windows box without Pillow, the tool pulls it in automatically.

Behavior
--------
* Disabled by default in CI / non-interactive (set EAZZU_AUTOINSTALL=1 to enable).
* Honors EAZZU_PIP_FLAGS for extra pip args (e.g. ``--user`` on iSH).
* Never auto-installs when sys.stdin is not a tty unless FORCE=1.
* Caches a "known-good" set so it doesn't retry failed installs repeatedly
  inside the same session.
"""
from __future__ import annotations

import importlib
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Optional libs grouped by feature. The key is the name passed to ensure().
_BUNDLES: dict[str, list[str]] = {
    "image":      ["pillow"],
    "screenshot": ["pillow", "mss"],
    "trading":    ["pandas", "numpy", "websocket-client"],
    "automation": ["pyautogui"],
    "web":        ["playwright"],
    "selenium":   ["selenium"],
    "rich":       ["rich"],
    "pdf":        ["fpdf"],
    "slides":     ["python-pptx"],
    "yaml":       ["pyyaml"],
    "tqdm":       ["tqdm"],
    "dotenv":     ["python-dotenv"],
    "fastapi":    ["fastapi", "uvicorn"],
    "httpx":      ["httpx"],
    "audio":      ["soundfile", "numpy"],
    "color":      ["colorama"],
}

_SESSION_INSTALLED: set[str] = set()
_SESSION_FAILED: set[str] = set()


def _autoinstall_enabled() -> bool:
    if os.environ.get("EAZZU_AUTOINSTALL", "").lower() in {"1", "true", "yes", "on"}:
        return True
    if os.environ.get("EAZZU_NO_AUTOINSTALL", "").lower() in {"1", "true", "yes", "on"}:
        return False
    # Default: OFF in CI / non-tty; ON in interactive shells.
    if os.environ.get("CI") or not sys.stdin.isatty():
        return False
    return True


def _pip_install(packages: list[str]) -> bool:
    flags = os.environ.get("EAZZU_PIP_FLAGS", "").split()
    cmd = [sys.executable, "-m", "pip", "install", "--quiet", *flags, *packages]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=300)
        return True
    except subprocess.CalledProcessError as e:
        sys.stderr.write(f"[eazzu] auto-install failed: {e.stderr.decode(errors='ignore')[:500]}\n")
        return False
    except subprocess.TimeoutExpired:
        sys.stderr.write("[eazzu] auto-install timed out\n")
        return False


def _import_name(pip_name: str) -> str:
    """Map pip package name to importable module name (handles hyphen/underscore)."""
    special = {
        "pillow": "PIL",
        "pyyaml": "yaml",
        "python-dotenv": "dotenv",
        "websocket-client": "websocket",
        "scikit-learn": "sklearn",
        "opencv-python": "cv2",
        "mss": "mss",
        "pyautogui": "pyautogui",
        "playwright": "playwright",
        "selenium": "selenium",
        "python-pptx": "pptx",
        "soundfile": "soundfile",
        "fpdf": "fpdf",
        "uvicorn": "uvicorn",
        "colorama": "colorama",
        "httpx": "httpx",
        "tqdm": "tqdm",
    }
    if pip_name in special:
        return special[pip_name]
    return pip_name.replace("-", "_").replace(".", "_")


def ensure(*features: str, packages: Optional[list[str]] = None,
           prompt: bool = True) -> dict:
    """Ensure libraries for the named features are importable; auto-install if needed.

    Returns a dict: {<import_name>: True/False, "_ok": bool, "_installed": list[str], "_missing": list[str]}
    """
    needed: list[str] = []
    for f in features:
        for pkg in _BUNDLES.get(f, [f]):
            if pkg not in needed:
                needed.append(pkg)
    if packages:
        for p in packages:
            if p not in needed:
                needed.append(p)

    result: dict[str, bool] = {}
    missing: list[str] = []
    installed_now: list[str] = []
    for pkg in needed:
        modname = _import_name(pkg)
        try:
            importlib.import_module(modname)
            result[modname] = True
            continue
        except ImportError:
            pass
        if pkg in _SESSION_FAILED:
            result[modname] = False
            missing.append(pkg)
            continue
        if not _autoinstall_enabled():
            result[modname] = False
            missing.append(pkg)
            continue
        # Attempt install
        if prompt and sys.stderr.isatty():
            sys.stderr.write(f"[eazzu] installing '{pkg}' (feature bundle: {list(features)})...\n")
        ok = _pip_install([pkg])
        if ok:
            try:
                importlib.invalidate_caches()
                importlib.import_module(modname)
                result[modname] = True
                _SESSION_INSTALLED.add(pkg)
                installed_now.append(pkg)
                continue
            except ImportError:
                pass
        _SESSION_FAILED.add(pkg)
        result[modname] = False
        missing.append(pkg)

    return {
        **result,
        "_ok": all(result.values()) if result else True,
        "_installed": installed_now,
        "_missing": missing,
    }


def ensure_silent(*features: str) -> bool:
    """ensure() but only return True/False overall, no output."""
    return ensure(*features, prompt=False)["_ok"]


# ---------------------------------------------------------------------- CLI #
_GROUP_MAP = {
    "trading": _BUNDLES["trading"],
    "dev": _BUNDLES["rich"],
    "image": _BUNDLES["image"] + _BUNDLES.get("screenshot", []),
    "pdf": _BUNDLES["pdf"],
    "slides": _BUNDLES["slides"],
    "automation": _BUNDLES["automation"],
    "web": _BUNDLES["web"],
    "audio": _BUNDLES["audio"],
    "yaml": _BUNDLES["yaml"],
    "http": _BUNDLES["httpx"],
    "server": _BUNDLES["fastapi"] + _BUNDLES.get("uvicorn", []),
}
_GROUP_MAP["full"] = list({p for plist in _BUNDLES.values() for p in plist})
_GROUP_MAP["all"] = _GROUP_MAP["full"]


def run_install(groups: list[str], packages: list[str], yes: bool = False) -> int:
    """Install dependency groups and/or extra pip packages."""
    targets: list[str] = []
    for g in groups:
        if g not in _GROUP_MAP:
            print(f"[eazzu] unknown group: {g} (try: {', '.join(_GROUP_MAP)})")
            return 2
        targets.extend(_GROUP_MAP[g])
    targets.extend(packages)
    # de-dup
    seen = set()
    final = []
    for t in targets:
        if t not in seen:
            final.append(t)
            seen.add(t)
    if not final:
        print("[eazzu] nothing to install. Use --list to see groups.")
        return 0
    if not yes and sys.stdin.isatty():
        ans = input(f"Install: {', '.join(final)}? [Y/n] ").strip().lower()
        if ans and ans[0] == "n":
            return 1
    print(f"[eazzu] pip install: {' '.join(final)}")
    ok = _pip_install(final)
    return 0 if ok else 1
