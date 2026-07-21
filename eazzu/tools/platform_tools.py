"""Platform-aware utilities that adapt to Windows / macOS / Linux / Colab / iSH.

Where possible these are pure-stdlib. When a dependency is needed (Pillow for
QR codes, pyttsx3 for TTS, etc.) we attempt autoinstall through
``eazzu.autoinstall`` so users don't need to ``pip install`` anything.
"""
from __future__ import annotations

import base64
import ctypes
import hashlib
import json
import os
import platform as _platform
import re
import shutil
import socket
import subprocess
import sys
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from eazzu import autoinstall


# ------------------------------------------------------------- detection #
IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")
IS_IOS_ISH = IS_LINUX and Path("/etc/apk/world").exists() and "iSH" in (Path("/proc/version").read_text(errors="ignore"))
IS_COLAB = "google.colab" in sys.modules or os.environ.get("COLAB_RELEASE_TAG") or Path("/content").exists() and Path("/opt/conda").exists()
IS_WSL = IS_LINUX and "microsoft" in Path("/proc/version").read_text(errors="ignore").lower()


def detect_platform() -> dict:
    return {
        "ok": True,
        "platform": sys.platform,
        "os": _platform.system(),
        "release": _platform.release(),
        "python": sys.version.split()[0],
        "is_windows": IS_WIN,
        "is_mac": IS_MAC,
        "is_linux": IS_LINUX,
        "is_ish_ios": bool(IS_IOS_ISH),
        "is_colab": bool(IS_COLAB),
        "is_wsl": bool(IS_WSL),
        "is_tty": sys.stdin.isatty(),
        "cwd": os.getcwd(),
        "home": str(Path.home()),
    }


# ---------------------------------------------------------------- system #
def system_info() -> dict:
    info = detect_platform()
    info["hostname"] = socket.gethostname()
    info["user"] = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"
    info["cpu_count"] = os.cpu_count()
    try:
        info["uptime_s"] = int(time.time() - _boot_time())
    except Exception:
        info["uptime_s"] = None
    info["env_path_entries"] = len(os.environ.get("PATH", "").split(os.pathsep))
    try:
        import shutil as _s
        usage = _s.disk_usage(Path.home())
        info["disk_home_total_gb"] = round(usage.total / 1e9, 2)
        info["disk_home_free_gb"] = round(usage.free / 1e9, 2)
    except Exception:
        pass
    return info


def _boot_time() -> float:
    if IS_WIN:
        import ctypes.wintypes
        GetTickCount64 = ctypes.windll.kernel32.GetTickCount64
        GetTickCount64.restype = ctypes.c_ulonglong
        return time.time() - GetTickCount64() / 1000
    if IS_MAC or IS_LINUX:
        return float(Path("/proc/uptime").read_text().split()[0]) if IS_LINUX and Path("/proc/uptime").exists() else time.time()
    return time.time()


def battery() -> dict:
    if IS_WIN:
        try:
            class PowerStatus(ctypes.Structure):
                _fields_ = [("ACLineStatus", ctypes.c_byte),
                            ("BatteryFlag", ctypes.c_byte),
                            ("BatteryLifePercent", ctypes.c_byte),
                            ("Reserved1", ctypes.c_byte),
                            ("BatteryLifeTime", ctypes.c_ulong),
                            ("BatteryFullLifeTime", ctypes.c_ulong)]
            ps = PowerStatus()
            ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(ps))
            return {"ok": True, "ac_plugged": bool(ps.ACLineStatus == 1),
                    "percent": int(ps.BatteryLifePercent),
                    "charging": bool(ps.ACLineStatus == 1)}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    if IS_LINUX and Path("/sys/class/power_supply").exists():
        for bat in Path("/sys/class/power_supply").glob("BAT*"):
            try:
                cap = int((bat/"capacity").read_text().strip())
                status = (bat/"status").read_text().strip()
                return {"ok": True, "percent": cap, "status": status,
                        "device": bat.name}
            except Exception:
                continue
    if IS_MAC:
        try:
            out = subprocess.run(["pmset", "-g", "batt"], capture_output=True, text=True, timeout=5).stdout
            m = re.search(r"(\d+)%.*?(charging|discharging|charged|finishing charge)", out)
            if m:
                return {"ok": True, "percent": int(m.group(1)), "status": m.group(2)}
        except Exception:
            pass
    return {"ok": False, "error": "no battery interface found"}


def wifi_info() -> dict:
    """Return current SSID if detectable."""
    try:
        if IS_WIN:
            out = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True, timeout=5).stdout
            m = re.search(r"SSID\s*:\s*(.+)", out)
            return {"ok": True, "ssid": m.group(1).strip() if m else None}
        if IS_MAC:
            out = subprocess.run(["/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport", "-I"],
                                 capture_output=True, text=True, timeout=5).stdout
            m = re.search(r"^\s*SSID: (.+)$", out, re.MULTILINE)
            return {"ok": True, "ssid": m.group(1).strip() if m else None}
        if IS_LINUX:
            out = subprocess.run(["iwgetid", "-r"], capture_output=True, text=True, timeout=5).stdout.strip()
            return {"ok": True, "ssid": out or None}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "no wifi backend"}


def set_volume(percent: int) -> dict:
    percent = max(0, min(100, int(percent)))
    try:
        if IS_WIN:
            # NirCmd-free: use SendKeys via PowerShell
            subprocess.run(["powershell", "-NoProfile", "-Command",
                            f"(New-Object -ComObject WScript.Shell).SendKeys([char]174)" * (25)],  # mute first
                           capture_output=True, timeout=5)
            # Use nircmd-style via key volume up repeatedly isn't precise; we use a ctypes approach via SendMessageW
            import ctypes as _c
            VK_VOLUME_UP = 0xAF
            KEYEVENTF_KEYUP = 0x2
            # Reset: press mute then adjust
            for _ in range(50):
                _c.windll.user32.keybd_event(VK_VOLUME_UP, 0, KEYEVENTF_KEYUP, 0)
            for _ in range(int(50 * percent / 100)):
                _c.windll.user32.keybd_event(VK_VOLUME_UP, 0, 0, 0)
                _c.windll.user32.keybd_event(VK_VOLUME_UP, 0, KEYEVENTF_KEYUP, 0)
            return {"ok": True}
        if IS_MAC:
            subprocess.run(["osascript", "-e", f"set volume output volume {percent}"], check=True, timeout=5)
            return {"ok": True}
        if IS_LINUX and shutil.which("pactl"):
            subprocess.run(["pactl", "set-sink-volume", "@DEFAULT_SINK@", f"{percent}%"], check=True, timeout=5)
            return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "no volume backend"}


# ------------------------------------------------------------- launch app #
def launch_app(name_or_path: str) -> dict:
    """Launch an app / file by name or path."""
    try:
        if IS_WIN:
            os.startfile(name_or_path)  # type: ignore[attr-defined]
        elif IS_MAC:
            subprocess.Popen(["open", "-a", name_or_path] if not Path(name_or_path).exists() else ["open", name_or_path])
        else:
            subprocess.Popen(["xdg-open", name_or_path])
        return {"ok": True, "launched": name_or_path}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ------------------------------------------------------------- notifications #
def notify(title: str = "EAZZU", message: str = "") -> dict:
    try:
        if IS_WIN:
            try:
                from win10toast import ToastNotifier  # type: ignore
                ToastNotifier().show_toast(title, message, duration=5, threaded=True)
                return {"ok": True}
            except ImportError:
                # Fallback to MessageBox
                ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)
                return {"ok": True}
        if IS_MAC:
            subprocess.run(["osascript", "-e", f'display notification {json.dumps(message)} with title {json.dumps(title)}'],
                           check=True, timeout=5)
            return {"ok": True}
        for cmd in (["notify-send", title, message], ["zenity", "--info", f"--title={title}", f"--text={message}"]):
            if shutil.which(cmd[0]):
                subprocess.run(cmd, check=False, timeout=5)
                return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
    return {"ok": False, "error": "no notification backend"}


# ------------------------------------------------------------- timer #
def timer(seconds: int, message: str = "Timer done!") -> dict:
    try:
        time.sleep(max(0, int(seconds)))
        notify("EAZZU Timer", message)
        return {"ok": True, "elapsed_s": seconds}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ------------------------------------------------------------- crypto/encoding #
def hash_text(text: str, algo: str = "sha256") -> dict:
    a = algo.lower().replace("-", "")
    if a not in {"md5", "sha1", "sha224", "sha256", "sha384", "sha512", "blake2b"}:
        return {"ok": False, "error": f"unsupported algo: {algo}"}
    h = hashlib.new(a)
    h.update(text.encode())
    return {"ok": True, "algo": a, "digest": h.hexdigest()}


def hash_file(path: str, algo: str = "sha256") -> dict:
    try:
        p = Path(path).expanduser()
        if not p.exists():
            return {"ok": False, "error": "not found"}
        a = algo.lower().replace("-", "")
        h = hashlib.new(a)
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return {"ok": True, "algo": a, "file": str(p), "digest": h.hexdigest(), "size": p.stat().st_size}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def b64_encode(text: str) -> dict:
    return {"ok": True, "encoded": base64.b64encode(text.encode()).decode()}


def b64_decode(text: str) -> dict:
    try:
        return {"ok": True, "decoded": base64.b64decode(text).decode(errors="replace")}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def make_uuid() -> dict:
    return {"ok": True, "uuid": str(uuid.uuid4())}


def qr_code(data: str, output: str = "qr.png") -> dict:
    if not autoinstall.ensure_silent("image"):
        # Try installing qrcode[pil]
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "qrcode[pil]"], check=True, timeout=60)
        except Exception as e:
            return {"ok": False, "error": f"need Pillow/qrcode; install failed: {e}"}
    try:
        import qrcode  # type: ignore
        img = qrcode.make(data)
        out = Path(output).expanduser()
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out)
        return {"ok": True, "path": str(out), "data": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ------------------------------------------------------------- short funcs #
def uuid4() -> dict:
    return make_uuid()


def now() -> dict:
    from datetime import timezone
    n = datetime.now(timezone.utc).astimezone()
    return {"ok": True, "iso": n.isoformat(timespec="seconds"), "unix": int(time.time()), "tz": str(n.tzinfo)}


def calc(expr: str) -> dict:
    """Safe arithmetic eval — only numbers and basic operators."""
    if not re.fullmatch(r"[\d\s\+\-\*\/\(\)\.\%\,\<\>\=\!\&\|]+", expr):
        return {"ok": False, "error": "only math/expressions allowed"}
    try:
        # Whitelist builtins to just numeric ops
        result = eval(expr, {"__builtins__": {}}, {})  # noqa: S307
        return {"ok": True, "expression": expr, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def say(text: str) -> dict:
    """Text-to-speech via platform native engine."""
    try:
        if IS_WIN:
            import pyttsx3  # type: ignore
            eng = pyttsx3.init(); eng.say(text); eng.runAndWait()
            return {"ok": True}
        if IS_MAC:
            subprocess.run(["say", text], check=True, timeout=max(5, len(text)/5))
            return {"ok": True}
        for exe in ("spd-say", "espeak", "espeak-ng"):
            if shutil.which(exe):
                subprocess.run([exe, text], check=False, timeout=max(5, len(text)/5))
                return {"ok": True}
        return {"ok": False, "error": "no TTS backend (install espeak/spd-say)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def ip_external() -> dict:
    import urllib.request
    try:
        with urllib.request.urlopen("https://api.ipify.org?format=json", timeout=8) as r:
            return {"ok": True, **json.loads(r.read().decode())}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def whoami() -> dict:
    return {"ok": True,
            "user": os.environ.get("USER") or os.environ.get("USERNAME"),
            "home": str(Path.home()), "cwd": os.getcwd(),
            "hostname": socket.gethostname()}


# ------------------------------------------------------------- Colab/iSH extras #
def colab_mount() -> dict:
    if not IS_COLAB:
        return {"ok": False, "error": "not running in Google Colab"}
    try:
        from google.colab import drive  # type: ignore
        drive.mount("/content/drive")
        return {"ok": True, "mount": "/content/drive"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def ish_info() -> dict:
    if not IS_IOS_ISH:
        return {"ok": False, "error": "not running in iSH (iOS)"}
    return {
        "ok": True,
        "apk_world": Path("/etc/apk/world").read_text(errors="ignore"),
        "hint": "use `apk add --no-cache <pkg>` to install Alpine packages. "
                "Base EAZZU install works; `pip install -e '.[full]'` for extras.",
    }


def pip_install(*packages: str) -> dict:
    """Programmatic pip install (used by /install command)."""
    if not packages:
        return {"ok": False, "error": "no packages specified"}
    try:
        import subprocess as _sp
        proc = _sp.run([sys.executable, "-m", "pip", "install", *packages],
                       capture_output=True, text=True, timeout=600)
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout_tail": proc.stdout[-2000:],
            "stderr_tail": proc.stderr[-2000:],
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ------------------------------------------------------------- tool registry #
def _wrap(fn):
    def r(**kw): return fn(**kw)
    r.__name__ = fn.__name__
    return r


TOOLS: list[dict] = [
    {"name": "detect_platform", "description": "Detect platform (Windows/macOS/Linux/Colab/iSH/WSL) and environment details.",
     "params": {}, "run": _wrap(detect_platform)},
    {"name": "system_info", "description": "Get system info: OS, CPU count, disk, uptime, user, hostname.",
     "params": {}, "run": _wrap(system_info)},
    {"name": "battery", "description": "Battery status (percent, charging) — Windows/macOS/Linux.",
     "params": {}, "run": _wrap(battery)},
    {"name": "wifi_info", "description": "Current Wi-Fi SSID.",
     "params": {}, "run": _wrap(wifi_info)},
    {"name": "set_volume", "description": "Set system volume 0-100 (Windows/macOS/Linux/pulseaudio).",
     "params": {"percent": {"type": "integer", "required": True}}, "run": _wrap(set_volume)},
    {"name": "launch_app", "description": "Launch an application by name or file path (OS-default).",
     "params": {"name_or_path": {"type": "string", "required": True}}, "run": _wrap(launch_app)},
    {"name": "notify", "description": "Show a desktop notification (Windows toast / macOS notification-center / notify-send).",
     "params": {"title": {"type": "string", "default": "EAZZU"}, "message": {"type": "string", "required": True}},
     "run": _wrap(notify)},
    {"name": "timer", "description": "Sleep for N seconds then notify.",
     "params": {"seconds": {"type": "integer", "required": True},
                "message": {"type": "string", "default": "Timer done!"}}, "run": _wrap(timer)},
    {"name": "hash_text", "description": "Hash a string (md5/sha1/sha256/sha512/blake2b).",
     "params": {"text": {"type": "string", "required": True}, "algo": {"type": "string", "default": "sha256"}},
     "run": _wrap(hash_text)},
    {"name": "hash_file", "description": "Hash a file on disk.",
     "params": {"path": {"type": "string", "required": True}, "algo": {"type": "string", "default": "sha256"}},
     "run": _wrap(hash_file)},
    {"name": "b64_encode", "description": "Base64-encode a string.",
     "params": {"text": {"type": "string", "required": True}}, "run": _wrap(b64_encode)},
    {"name": "b64_decode", "description": "Base64-decode a string.",
     "params": {"text": {"type": "string", "required": True}}, "run": _wrap(b64_decode)},
    {"name": "make_uuid", "description": "Generate a random UUIDv4.",
     "params": {}, "run": _wrap(make_uuid)},
    {"name": "qr_code", "description": "Generate a QR code PNG from text/url.",
     "params": {"data": {"type": "string", "required": True},
                "output": {"type": "string", "default": "qr.png"}}, "run": _wrap(qr_code)},
    {"name": "now", "description": "Current time (ISO, unix epoch, timezone).",
     "params": {}, "run": _wrap(now)},
    {"name": "calc", "description": "Safely evaluate a math expression (+,-,*,/,()).",
     "params": {"expr": {"type": "string", "required": True}}, "run": _wrap(calc)},
    {"name": "say", "description": "Text-to-speech (Windows SAPI, macOS 'say', espeak/spd-say).",
     "params": {"text": {"type": "string", "required": True}}, "run": _wrap(say)},
    {"name": "ip_external", "description": "Get external/public IP via ipify.org.",
     "params": {}, "run": _wrap(ip_external)},
    {"name": "whoami", "description": "Current user, home, cwd, hostname.",
     "params": {}, "run": _wrap(whoami)},
    {"name": "colab_mount", "description": "Mount Google Drive when running in Colab.",
     "params": {}, "run": _wrap(colab_mount)},
    {"name": "ish_info", "description": "Info about the iSH (iOS) Alpine environment (apk packages).",
     "params": {}, "run": _wrap(ish_info)},
    {"name": "pip_install", "description": "pip-install one or more packages programmatically.",
     "params": {"packages": {"type": "string", "required": True,
                              "description": "space-separated package names"}},
     "run": lambda **kw: pip_install(*kw["packages"].split())},
]
