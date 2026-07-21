"""Advanced CLI UI — a pure-stdlib rich-like terminal renderer.

Provides colored output, panels, tables, progress bars, spinners, and
formatted key-value displays without any third-party dependencies.

Uses ANSI escape codes for colors and formatting. Degrades gracefully on
terminals that don't support ANSI (output remains readable, just uncolored).
"""
from __future__ import annotations

import os
import sys
import shutil
import time
import threading
from typing import Optional, Any


# ---- ANSI support detection ---- #
_FORCE_COLOR = os.environ.get("EAZZU_FORCE_COLOR", "")
_NO_COLOR = os.environ.get("EAZZU_NO_COLOR", "") or os.environ.get("NO_COLOR", "")
if _NO_COLOR:
    _ANSI = False
elif _FORCE_COLOR:
    _ANSI = _FORCE_COLOR == "1"
else:
    _ANSI = sys.stdout.isatty() and (shutil.which("tput") is not None or sys.stdout.isatty())


def set_color(enabled: bool | None) -> None:
    """Programmatic override (True=on, False=off, None=auto). Used by --no-color / config."""
    global _ANSI
    if enabled is None:
        if _NO_COLOR:
            _ANSI = False
        elif _FORCE_COLOR:
            _ANSI = _FORCE_COLOR == "1"
        else:
            _ANSI = sys.stdout.isatty() and (shutil.which("tput") is not None or sys.stdout.isatty())
        return
    _ANSI = bool(enabled)


# ---- Color codes ---- #
class C:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"
    BRED = "\033[91m"
    BGREEN = "\033[92m"
    BYELLOW = "\033[93m"
    BBLUE = "\033[94m"
    BMAGENTA = "\033[95m"
    BCYAN = "\033[96m"
    BWHITE = "\033[97m"
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_BLUE = "\033[44m"
    BG_CYAN = "\033[46m"


def _c(text: str, color: str) -> str:
    if not _ANSI:
        return text
    return f"{color}{text}{C.RESET}"


def colorize(text: str, color: str) -> str:
    return _c(text, color)


# ---- Panel ---- #
def panel(title: str, body: str, color: str = C.CYAN, width: int = 70) -> str:
    """Draw a titled panel with a border."""
    if not _ANSI:
        return f"[{title}]\n{body}\n"
    w = min(width, shutil.get_terminal_size((80, 24)).columns)
    top = f"╭{'─' * (w - 2)}╮"
    bottom = f"╰{'─' * (w - 2)}╯"
    title_line = f"│ {_c(title, color)}{' ' * (w - 4 - len(title))}│"
    sep = f"├{'─' * (w - 2)}┤"
    body_lines = []
    for line in body.split("\n"):
        while len(line) > w - 4:
            body_lines.append(f"│ {line[:w - 4]} │")
            line = line[w - 4:]
        body_lines.append(f"│ {line}{' ' * max(0, w - 4 - len(line))} │")
    return "\n".join([_c(top, color), title_line, _c(sep, color), *body_lines, _c(bottom, color)])


# ---- Table ---- #
def table(headers: list[str], rows: list[list[str]], color: str = C.CYAN) -> str:
    """Render a simple ASCII table."""
    if not _ANSI:
        lines = ["\t".join(headers)]
        for row in rows:
            lines.append("\t".join(row))
        return "\n".join(lines)
    col_widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))
    sep = "┼" + "┼".join("─" * (w + 2) for w in col_widths) + "┼"
    header_line = "│ " + " │ ".join(_c(h.ljust(col_widths[i]), C.BOLD) for i, h in enumerate(headers)) + " │"
    row_lines = []
    for row in rows:
        cells = [str(row[i]).ljust(col_widths[i]) if i < len(row) else "".ljust(col_widths[i]) for i in range(len(headers))]
        row_lines.append("│ " + " │ ".join(cells) + " │")
    return "\n".join([_c(sep, color), header_line, _c(sep, color), *row_lines, _c(sep, color)])


# ---- Key-value display ---- #
def kv(items: list[tuple[str, str]], color: str = C.CYAN) -> str:
    """Render a list of key-value pairs."""
    if not items:
        return ""
    max_key = max(len(k) for k, _ in items)
    lines = []
    for k, v in items:
        lines.append(f"  {_c(k.ljust(max_key), color)}  {_c('→', C.DIM)}  {v}")
    return "\n".join(lines)


# ---- Progress bar ---- #
def progress_bar(current: int, total: int, width: int = 30, label: str = "", color: str = C.GREEN) -> str:
    """Render a progress bar."""
    if total == 0:
        pct = 100
    else:
        pct = int(current / total * 100)
    filled = int(width * pct / 100) if total > 0 else width
    bar = "█" * filled + "░" * (width - filled)
    if not _ANSI:
        return f"[{bar}] {pct}% {label}"
    return f"{_c('[', C.DIM)}{_c(bar[:filled], color)}{_c(bar[filled:], C.DIM)}{_c(']', C.DIM)} {pct}% {label}"


# ---- Spinner ---- #
class Spinner:
    """A simple async spinner that runs in a background thread."""

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message: str = "Working...", color: str = C.CYAN):
        self.message = message
        self.color = color
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if not _ANSI:
            print(self.message, end="", flush=True)
            return
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self) -> None:
        i = 0
        while self._running:
            frame = self.FRAMES[i % len(self.FRAMES)]
            sys.stdout.write(f"\r{_c(frame, self.color)} {self.message}")
            sys.stdout.flush()
            i += 1
            time.sleep(0.1)

    def stop(self, final_message: str = "") -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        if _ANSI:
            sys.stdout.write("\r" + " " * (len(self.message) + 4) + "\r")
            sys.stdout.flush()
        if final_message:
            print(final_message)


# ---- Status badge ---- #
def badge(text: str, color: str = C.GREEN) -> str:
    return _c(f" {text} ", f"\033[30m{color.replace('3', '4')}")


# ---- Banner ---- #
def banner() -> str:
    art = r"""
 ███████╗ █████╗ ███████╗███████╗██╗   ██╗
 ██╔════╝██╔══██╗╚══███╔╝╚══███╔╝██║   ██║
 █████╗  ███████║  ███╔╝   ███╔╝ ██║   ██║
 ██╔══╝  ██╔══██║ ███╔╝   ███╔╝  ██║   ██║
 ███████╗██║  ██║███████╗███████╗╚██████╔╝
 ╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝ ╚═════╝
"""
    tagline = "  agentic dev · trading · AI · MCP toolkit  v1.3.0"
    if not _ANSI:
        return art + tagline
    return _c(art, C.BCYAN) + _c(tagline, C.DIM)


# ---- Pretty JSON ---- #
def pretty_json(obj: Any, indent: int = 2) -> str:
    import json
    text = json.dumps(obj, indent=indent, default=str)
    if not _ANSI:
        return text
    text = text.replace('"([^"]+)":', lambda m: f'{_c(m.group(0)[:-1], C.CYAN)}:')
    return text


# ---- Tree ---- #
def tree(items: dict, indent: int = 0, color: str = C.CYAN) -> str:
    """Render a tree structure from a nested dict."""
    lines = []
    keys = list(items.keys())
    for i, key in enumerate(keys):
        is_last = i == len(keys) - 1
        prefix = "└── " if is_last else "├── "
        value = items[key]
        if isinstance(value, dict):
            lines.append(f"{' ' * indent}{_c(prefix, C.DIM)}{_c(key, color)}")
            lines.append(tree(value, indent + 4, color))
        else:
            lines.append(f"{' ' * indent}{_c(prefix, C.DIM)}{_c(key, color)}  {_c(str(value), C.DIM)}")
    return "\n".join(lines)


# ---- Status line ---- #
def status_line(text: str, status: str = "info") -> str:
    """A colored status line: [INFO] / [OK] / [WARN] / [ERROR]."""
    colors = {"info": C.CYAN, "ok": C.GREEN, "warn": C.YELLOW, "error": C.RED}
    icons = {"info": "ℹ", "ok": "✓", "warn": "⚠", "error": "✗"}
    color = colors.get(status, C.CYAN)
    icon = icons.get(status, "•")
    return f"{_c(icon, color)} {text}"


# ---- Rule ---- #
def rule(title: str = "", color: str = C.DIM, width: int = 70) -> str:
    """A horizontal rule with an optional title."""
    w = min(width, shutil.get_terminal_size((80, 24)).columns)
    if title:
        line = "─" * (w - len(title) - 3)
        return _c(f"── {title} {line}", color)
    return _c("─" * w, color)
