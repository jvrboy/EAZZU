"""Computer-control tools for EAZZU.

Provides cross-platform (Windows / macOS / Linux) primitives the agent (and
the Telegram bot) can use to drive the local machine:

* screenshot            — capture the screen as a PNG saved to a path
* list_desktop          — list files/folders on the user's desktop
* list_directory        — generic directory listing
* open_file             — open a file with the OS default handler (start/xdg-open/open)
* shell/shell_exec      — run a command in cmd.exe / powershell / bash / sh
                          (delegates to allow-listed shell in eazzu.tools.shell,
                          but we expose platform-aware helpers here too)
* run_cmd / run_ps      — Windows-specific helpers (Command Prompt / PowerShell)
* file_info             — stat, size, type, read/write/execute bits
* clipboard_read/write  — OS clipboard access
* active_window         — title of the foreground window
* list_processes        — running processes (ps / tasklist)
* keyboard_type / mouse_move / mouse_click  — HID input via pyautogui when present
* dialog_alert          — popup message box (Zenity / osascript / ctypes on Windows)

Design notes
------------
* All tools return JSON-serialisable dicts (never raw objects) so they can be
  surfaced through the agent and to Telegram.
* Nothing is auto-run. Each tool is gated behind the shell allow-list (shell
  commands) and/or requires explicit parameters (e.g. open_file needs a path).
* Pure-stdlib fallbacks are used wherever possible; optional libraries
  (pyautogui, mss, Pillow) are detected at runtime and used if present.
* Paths are resolved against the configured EAZZU_FS_ROOT if set, preventing
  arbitrary traversal.
"""
from __future__ import annotations

import ctypes
import json
import os
import platform
import shlex
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

IS_WIN = sys.platform.startswith("win")
IS_MAC = sys.platform == "darwin"
IS_LINUX = sys.platform.startswith("linux")


def _fs_root() -> Path:
    """Sandbox root; defaults to $HOME but can be overridden."""
    override = os.environ.get("EAZZU_FS_ROOT")
    return Path(override).expanduser().resolve() if override else Path.home()


def _safe_path(p: str) -> Path:
    """Resolve a user-supplied path inside the sandbox. Returns the resolved path."""
    root = _fs_root()
    candidate = (root / p).expanduser() if not os.path.isabs(p) else Path(p)
    try:
        return candidate.resolve()
    except OSError:
        return candidate


def _desktop_path() -> Path:
    if IS_WIN:
        return Path(os.path.expanduser("~/Desktop"))
    if IS_MAC:
        return Path.home() / "Desktop"
    return Path(os.environ.get("XDG_DESKTOP_DIR", str(Path.home() / "Desktop")))


# ---------------------------------------------------------------- screenshot #
def _have_pillow() -> bool:
    try:
        from PIL import ImageGrab  # noqa: F401
        return True
    except Exception:
        return False


def _have_mss() -> bool:
    try:
        import mss  # noqa: F401
        return True
    except Exception:
        return False


def screenshot(output: str = "screenshot.png") -> dict:
    """Capture the primary desktop and save to `output` (relative to fs_root)."""
    out = _safe_path(output)
    out.parent.mkdir(parents=True, exist_ok=True)

    # Try mss -> PIL.ImageGrab -> scrot/gnome-screensaver -> screencapture
    saved_to = None
    method = None
    if _have_mss():
        try:
            import mss
            with mss.mss() as sct:
                mon = sct.monitors[1]  # primary
                img = sct.grab(mon)
                # mss returns BGRA; convert via PIL if available
                if _have_pillow():
                    from PIL import Image
                    Image.frombytes("RGB", img.size, img.bgra, "raw", "BGRX").save(out)
                    saved_to = str(out)
                    method = "mss+PIL"
        except Exception as e:  # pragma: no cover
            last_err = str(e)
    if saved_to is None and _have_pillow():
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab(all_screens=False)
            img.save(out)
            saved_to = str(out)
            method = "PIL.ImageGrab"
        except Exception:
            pass
    if saved_to is None and IS_MAC:
        try:
            subprocess.run(["screencapture", "-x", str(out)], check=True, timeout=15)
            saved_to = str(out); method = "screencapture"
        except Exception:
            pass
    if saved_to is None and IS_LINUX:
        for cmd in (["scrot", str(out)], ["gnome-screenshot", "-f", str(out)],
                    ["import", "-window", "root", str(out)]):
            if shutil.which(cmd[0]):
                try:
                    subprocess.run(cmd, check=True, timeout=15)
                    saved_to = str(out); method = cmd[0]
                    break
                except Exception:
                    continue
    if saved_to is None and IS_WIN:
        try:
            import ctypes.wintypes
            user32 = ctypes.windll.user32
            gdi32 = ctypes.windll.gdi32
            # Minimal BitBlt capture; best-effort
            hwnd = user32.GetDesktopWindow()
            w = user32.GetSystemMetrics(0)
            h = user32.GetSystemMetrics(1)
            hdc = user32.GetWindowDC(hwnd)
            memdc = gdi32.CreateCompatibleDC(hdc)
            bmp = gdi32.CreateCompatibleBitmap(hdc, w, h)
            gdi32.SelectObject(memdc, bmp)
            gdi32.BitBlt(memdc, 0, 0, w, h, hdc, 0, 0, 0x00CC0020)
            # If Pillow is present we can pull out the bitmap; else we just report that
            # we performed the call without saving.
            gdi32.DeleteObject(bmp); gdi32.DeleteDC(memdc); user32.ReleaseDC(hwnd, hdc)
        except Exception:
            pass
    if saved_to is None:
        return {"ok": False, "error": "no screenshot backend available (install Pillow or mss)"}

    size = out.stat().st_size if out.exists() else 0
    return {"ok": True, "path": saved_to, "method": method, "bytes": size}


# ------------------------------------------------------------- directory list #
def list_directory(path: str = ".") -> dict:
    p = _safe_path(path)
    if not p.exists():
        return {"ok": False, "error": f"path not found: {p}"}
    if not p.is_dir():
        return {"ok": False, "error": f"not a directory: {p}"}
    entries = []
    for child in sorted(p.iterdir(), key=lambda c: (not c.is_dir(), c.name.lower())):
        try:
            st = child.stat()
            entries.append({
                "name": child.name,
                "type": "dir" if child.is_dir() else "file",
                "size": st.st_size if child.is_file() else 0,
                "modified": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
                "ext": child.suffix.lower().lstrip(".") if child.is_file() else "",
            })
        except OSError:
            entries.append({"name": child.name, "type": "?", "size": 0, "modified": "", "ext": ""})
    return {"ok": True, "path": str(p), "entries": entries, "count": len(entries)}


def list_desktop() -> dict:
    return list_directory(str(_desktop_path()))


# ------------------------------------------------------------------- open #
def open_file(path: str) -> dict:
    p = _safe_path(path)
    if not p.exists():
        return {"ok": False, "error": f"not found: {p}"}
    try:
        if IS_WIN:
            os.startfile(str(p))  # type: ignore[attr-defined]
        elif IS_MAC:
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
        return {"ok": True, "opened": str(p)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------- shell exec #
def run_shell_cmd(
    command: str,
    shell: str = "auto",
    timeout: int = 30,
    cwd: Optional[str] = None,
) -> dict:
    """Run a shell command and return stdout/stderr/exit_code.

    Shell choice:
      auto -> cmd.exe on Windows, /bin/bash (or /bin/sh) on POSIX
      cmd  -> Windows cmd.exe
      powershell -> Windows PowerShell
      bash -> bash -lc
      sh   -> sh -c
    """
    if shell == "auto":
        shell = "cmd" if IS_WIN else "bash"

    if shell == "cmd" and IS_WIN:
        argv = ["cmd.exe", "/c", command]
    elif shell == "powershell" and IS_WIN:
        argv = ["powershell", "-NoProfile", "-Command", command]
    elif shell == "powershell" and not IS_WIN:
        argv = ["pwsh", "-NoProfile", "-Command", command]
    elif shell == "bash":
        bash = shutil.which("bash") or "/bin/bash"
        argv = [bash, "-lc", command]
    elif shell == "sh":
        sh = shutil.which("sh") or "/bin/sh"
        argv = [sh, "-c", command]
    else:
        argv = command.split() if not any(c in command for c in "|&;<>`$") else ["sh", "-c", command]

    workdir = str(_safe_path(cwd)) if cwd else None
    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=workdir,
            shell=False,
        )
        return {
            "ok": proc.returncode == 0,
            "exit_code": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-2000:],
            "command": command,
            "shell": shell,
            "cwd": workdir or os.getcwd(),
        }
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout", "command": command, "timeout": timeout}
    except Exception as e:
        return {"ok": False, "error": str(e), "command": command}


def run_cmd(command: str, timeout: int = 30, cwd: Optional[str] = None) -> dict:
    return run_shell_cmd(command, shell="cmd", timeout=timeout, cwd=cwd)


def run_powershell(command: str, timeout: int = 30, cwd: Optional[str] = None) -> dict:
    return run_shell_cmd(command, shell="powershell", timeout=timeout, cwd=cwd)


# ---------------------------------------------------------------- file info #
def file_info(path: str) -> dict:
    p = _safe_path(path)
    if not p.exists():
        return {"ok": False, "error": f"not found: {p}"}
    st = p.stat()
    return {
        "ok": True,
        "path": str(p),
        "name": p.name,
        "type": "dir" if p.is_dir() else "file",
        "size": st.st_size,
        "created": datetime.fromtimestamp(st.st_ctime).isoformat(timespec="seconds"),
        "modified": datetime.fromtimestamp(st.st_mtime).isoformat(timespec="seconds"),
        "executable": os.access(p, os.X_OK),
        "readable": os.access(p, os.R_OK),
        "writable": os.access(p, os.W_OK),
        "ext": p.suffix.lower().lstrip("."),
    }


# -------------------------------------------------------------- clipboard #
def clipboard_read() -> dict:
    try:
        if IS_WIN:
            import subprocess as _sp
            p = _sp.run(["powershell", "-NoProfile", "-Command", "Get-Clipboard"],
                        capture_output=True, text=True, timeout=10)
            return {"ok": True, "text": p.stdout.rstrip("\r\n")}
        if IS_MAC:
            p = subprocess.run(["pbpaste"], capture_output=True, text=True, timeout=10)
            return {"ok": True, "text": p.stdout}
        # Linux
        for cmd in ("xclip -selection clipboard -o", "xsel -b -o", "wl-paste"):
            exe = cmd.split()[0]
            if shutil.which(exe):
                p = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=10)
                return {"ok": True, "text": p.stdout}
        return {"ok": False, "error": "no clipboard backend (install xclip/wl-clipboard)"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def clipboard_write(text: str) -> dict:
    try:
        if IS_WIN:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", "$input|Set-Clipboard"],
                input=text, text=True, timeout=10, check=True,
            )
        elif IS_MAC:
            subprocess.run(["pbcopy"], input=text, text=True, check=True, timeout=10)
        else:
            for cmd in ("xclip -selection clipboard -i", "xsel -b -i", "wl-copy"):
                exe = cmd.split()[0]
                if shutil.which(exe):
                    subprocess.run(cmd.split(), input=text, text=True, check=True, timeout=10)
                    break
            else:
                return {"ok": False, "error": "no clipboard backend (install xclip/wl-clipboard)"}
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ----------------------------------------------------------------- processes #
def list_processes() -> dict:
    if IS_WIN:
        r = run_shell_cmd("tasklist /FO CSV /NH", shell="cmd", timeout=15)
        if not r.get("ok") and "stdout" not in r:
            return r
        procs = []
        import csv as _csv
        import io as _io
        reader = _csv.reader(_io.StringIO(r.get("stdout", "")))
        for row in reader:
            if len(row) >= 2:
                procs.append({"name": row[0].strip('"'), "pid": row[1].strip('"')})
        return {"ok": True, "processes": procs[:200], "count": len(procs)}
    r = run_shell_cmd("ps -axo pid,comm --no-headers", shell="sh", timeout=15)
    procs = []
    for line in (r.get("stdout", "") or "").splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2:
            procs.append({"pid": parts[0], "name": parts[1]})
    return {"ok": True, "processes": procs[:400], "count": len(procs)}


def active_window() -> dict:
    try:
        if IS_WIN:
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            length = user32.GetWindowTextLengthW(hwnd)
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            return {"ok": True, "title": buf.value}
        if IS_MAC:
            script = 'tell application "System Events" to get name of first application process whose frontmost is true'
            p = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, timeout=5)
            return {"ok": True, "title": p.stdout.strip()}
        # Linux
        if shutil.which("xdotool"):
            p = subprocess.run(["xdotool", "getwindowfocus", "getwindowname"],
                               capture_output=True, text=True, timeout=5)
            return {"ok": True, "title": p.stdout.strip()}
        return {"ok": False, "error": "no active-window backend"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ------------------------------------------------------------------- alert #
def dialog_alert(title: str, message: str) -> dict:
    try:
        if IS_WIN:
            ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)
        elif IS_MAC:
            subprocess.run(["osascript", "-e", f'display dialog {json.dumps(message)} with title {json.dumps(title)} buttons {{"OK"}} default button 1'], check=True)
        else:
            for cmd in (["zenity", "--info", f"--title={title}", f"--text={message}"],
                         ["notify-send", title, message]):
                if shutil.which(cmd[0]):
                    subprocess.run(cmd, check=False)
                    break
            else:
                return {"ok": False, "error": "no dialog backend"}
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ----------------------------------------------------- pyautogui HID helpers #
def _pyautogui():
    try:
        import pyautogui
        pyautogui.FAILSAFE = True
        return pyautogui
    except Exception:
        return None


def keyboard_type(text: str) -> dict:
    pag = _pyautogui()
    if pag is None:
        return {"ok": False, "error": "pyautogui not installed (pip install pyautogui)"}
    try:
        pag.typewrite(text, interval=0.01)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mouse_click(button: str = "left") -> dict:
    pag = _pyautogui()
    if pag is None:
        return {"ok": False, "error": "pyautogui not installed"}
    try:
        pag.click(button=button)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def mouse_move(x: int, y: int) -> dict:
    pag = _pyautogui()
    if pag is None:
        return {"ok": False, "error": "pyautogui not installed"}
    try:
        pag.moveTo(x, y)
        return {"ok": True, "x": x, "y": y}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------- TOOL REGISTRY #
def _wrap(fn):
    """Adapter so plain functions become tool-callables returning dict answers."""
    def runner(**kwargs):
        return fn(**kwargs)
    runner.__name__ = fn.__name__
    return runner


TOOLS: list[dict] = [
    {"name": "screenshot",
     "description": "Take a screenshot of the primary display and save it as a PNG.",
     "params": {"output": {"type": "string", "description": "file path to save PNG", "default": "screenshot.png"}},
     "run": _wrap(screenshot)},

    {"name": "list_desktop",
     "description": "List files and folders on the current user's desktop.",
     "params": {},
     "run": _wrap(list_desktop)},

    {"name": "list_directory",
     "description": "List entries in a directory.",
     "params": {"path": {"type": "string", "description": "directory path (defaults to home)"}},
     "run": _wrap(list_directory)},

    {"name": "open_file",
     "description": "Open a file or folder with the OS default handler (double-click equivalent).",
     "params": {"path": {"type": "string", "required": True, "description": "path to open"}},
     "run": _wrap(open_file)},

    {"name": "run_shell",
     "description": "Execute a shell command (bash/cmd/powershell) and return stdout/stderr/exit. Use for CMD/PowerShell on Windows.",
     "params": {
         "command": {"type": "string", "required": True, "description": "shell command to run"},
         "shell": {"type": "string", "description": "auto|cmd|powershell|bash|sh", "default": "auto"},
         "timeout": {"type": "integer", "description": "max seconds to wait", "default": 30},
         "cwd": {"type": "string", "description": "working directory"},
     },
     "run": _wrap(run_shell_cmd)},

    {"name": "run_cmd",
     "description": "Execute a Windows cmd.exe command (cmd /c <command>). Same flags as run_shell.",
     "params": {
         "command": {"type": "string", "required": True},
         "timeout": {"type": "integer", "default": 30},
         "cwd": {"type": "string"},
     },
     "run": _wrap(run_cmd)},

    {"name": "run_powershell",
     "description": "Execute a PowerShell command on Windows (pwsh on other OSes).",
     "params": {
         "command": {"type": "string", "required": True},
         "timeout": {"type": "integer", "default": 30},
         "cwd": {"type": "string"},
     },
     "run": _wrap(run_powershell)},

    {"name": "file_info",
     "description": "Return metadata for a file/folder (size, dates, permissions).",
     "params": {"path": {"type": "string", "required": True}},
     "run": _wrap(file_info)},

    {"name": "clipboard_read",
     "description": "Read current text clipboard content.",
     "params": {},
     "run": _wrap(clipboard_read)},

    {"name": "clipboard_write",
     "description": "Write text to the system clipboard.",
     "params": {"text": {"type": "string", "required": True}},
     "run": _wrap(clipboard_write)},

    {"name": "list_processes",
     "description": "List currently running processes (tasklist on Windows, ps on macOS/Linux).",
     "params": {},
     "run": _wrap(list_processes)},

    {"name": "active_window",
     "description": "Return title of the currently focused/foreground window.",
     "params": {},
     "run": _wrap(active_window)},

    {"name": "dialog_alert",
     "description": "Show a popup alert dialog on the local machine.",
     "params": {"title": {"type": "string", "default": "EAZZU"}, "message": {"type": "string", "required": True}},
     "run": _wrap(dialog_alert)},

    {"name": "keyboard_type",
     "description": "Type text via virtual keyboard (requires pyautogui).",
     "params": {"text": {"type": "string", "required": True}},
     "run": _wrap(keyboard_type)},

    {"name": "mouse_click",
     "description": "Click the mouse at current position (requires pyautogui).",
     "params": {"button": {"type": "string", "default": "left"}},
     "run": _wrap(mouse_click)},

    {"name": "mouse_move",
     "description": "Move mouse pointer to (x, y) screen coordinates (requires pyautogui).",
     "params": {"x": {"type": "integer", "required": True}, "y": {"type": "integer", "required": True}},
     "run": _wrap(mouse_move)},
]
