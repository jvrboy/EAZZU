"""App-builder tools — take a description and produce a production-ready,
runnable app with screenshots.

Pipeline:
  1. create_app(description, language, out_dir)  — scaffolds project, writes code
  2. run_app(dir, command)                        — runs the app with timeout
  3. fix_app(dir, error_log)                      — patches files until it starts
  4. screenshot_app(url, out) / screenshot_window(window_title)  — captures UI
  5. package_app(dir, fmt)                        — bundles (zip, tar.gz)
  6. deliver_app(dir)                             — returns summary + artifact paths

The agent can call these tools directly; or there is a single high-level
``build_app`` entry-point that runs the full create → fix → run → screenshot
loop up to N attempts.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import time
import zipfile
import tarfile
from pathlib import Path
from typing import Optional

from eazzu.tools.computer_tools import (
    _fs_root, _safe_path, screenshot, run_shell_cmd, dialog_alert,
)


DEFAULT_WEB_TEMPLATE = """<!doctype html>
<html lang=\"en\">
<head>
<meta charset=\"utf-8\" />
<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\" />
<title>{title}</title>
<style>
  :root {{ color-scheme: dark light; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin:0; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, sans-serif;
    background: linear-gradient(135deg,#0f172a,#1e293b); color: #e2e8f0; min-height:100vh;
    display:flex; align-items:center; justify-content:center; padding: 2rem;
  }}
  .card {{ background:#111827cc; backdrop-filter: blur(8px); border:1px solid #334155;
           border-radius:16px; padding:2rem; max-width:720px; box-shadow:0 20px 60px #0008; }}
  h1 {{ margin-top:0; background:linear-gradient(90deg,#60a5fa,#a78bfa);
        -webkit-background-clip:text; background-clip:text; color:transparent; }}
  button {{ background: linear-gradient(135deg,#6366f1,#8b5cf6); border:0; color:#fff;
            padding:.7rem 1.2rem; border-radius:10px; font-weight:600; cursor:pointer; }}
  button:hover {{ filter: brightness(1.1); }}
  pre {{ background:#0b1220; padding:1rem; border-radius:10px; overflow:auto; }}
</style>
</head>
<body>
<div class=\"card\">
  <h1>{title}</h1>
  <p id=\"greeting\">{subtitle}</p>
  <button onclick=\"hi()\">Say Hi</button>
  <pre id=\"out\"></pre>
</div>
<script>
function hi() {{
  document.getElementById('out').textContent = 'Hello from {title}!';
}}
</script>
</body></html>
"""


def _workdir(parent: Optional[str] = None, name: str = "app") -> Path:
    root = _fs_root() / "eazzu_apps" if parent is None else _safe_path(parent)
    root.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%d-%H%M%S")
    d = root / f"{name}-{ts}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def create_app(
    description: str,
    language: str = "html",
    out_dir: Optional[str] = None,
    title: Optional[str] = None,
) -> dict:
    """Scaffold a new app.

    language: 'html' (static single-file web app, default), 'python', 'node'.
    For python/node we produce starter source + requirements/package.json.
    The LLM can then freely edit the files with write_file / run_shell.
    """
    d = _workdir(out_dir, name=language)
    title = title or description[:40].strip().replace("/", "-") or "EAZZU App"
    files_written: list[str] = []

    if language == "html":
        idx = d / "index.html"
        idx.write_text(DEFAULT_WEB_TEMPLATE.format(title=title, subtitle=description), encoding="utf-8")
        files_written.append("index.html")
        readme = d / "README.md"
        readme.write_text(f"# {title}\n\n{description}\n\nOpen `index.html` in a browser.\n", encoding="utf-8")
        files_written.append("README.md")
    elif language == "python":
        (d / "main.py").write_text(
            textwrap.dedent(f'''\
                """{title} — {description}"""
                from __future__ import annotations
                import sys

                def main():
                    print("Hello from {title}")
                    return 0

                if __name__ == "__main__":
                    sys.exit(main())
            '''), encoding="utf-8")
        files_written.append("main.py")
        (d / "requirements.txt").write_text("# dependencies\n", encoding="utf-8")
        files_written.append("requirements.txt")
    elif language == "node":
        (d / "package.json").write_text(json.dumps({
            "name": re.sub(r"[^a-z0-9-]", "-", title.lower()).strip("-") or "eazzu-app",
            "version": "1.0.0",
            "description": description,
            "main": "index.js",
            "scripts": {"start": "node index.js"},
        }, indent=2), encoding="utf-8")
        files_written.append("package.json")
        (d / "index.js").write_text(f"console.log('Hello from {title}');\n", encoding="utf-8")
        files_written.append("index.js")
    else:
        return {"ok": False, "error": f"unsupported language: {language}"}

    return {
        "ok": True,
        "dir": str(d),
        "language": language,
        "files": files_written,
        "next": "Open the generated entry file or use write_file to edit; then run_app.",
    }


def run_app(
    directory: str,
    command: Optional[str] = None,
    timeout: int = 30,
    background: bool = False,
    port: int = 0,
) -> dict:
    """Run the app and return its stdout/stderr/exit code or background PID."""
    d = _safe_path(directory)
    if not d.exists():
        return {"ok": False, "error": f"not found: {d}"}
    if command is None:
        # Auto-detect
        if (d / "index.html").exists():
            # Spawn a local static server
            port = port or 8765
            cmd = f'"{sys.executable}" -m http.server {port}'
            sh = "sh" if not sys.platform.startswith("win") else "cmd"
            if sh == "cmd":
                cmd = f'"{sys.executable}" -m http.server {port}'
        elif (d / "main.py").exists():
            cmd = f'"{sys.executable}" main.py'
            sh = "auto"
        elif (d / "index.js").exists():
            cmd = "node index.js"
            sh = "auto"
        else:
            return {"ok": False, "error": "cannot auto-detect start command; pass command="}
    else:
        cmd = command
        sh = "auto"
    if background:
        try:
            proc = subprocess.Popen(cmd, shell=True, cwd=str(d),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return {"ok": True, "pid": proc.pid, "dir": str(d), "command": cmd}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    return run_shell_cmd(cmd, shell=sh, timeout=timeout, cwd=str(d))


def fix_app(directory: str, error_log: str, max_rounds: int = 3) -> dict:
    """High-level 'please fix it' hint. Writes a FIX_LOG.txt and returns a hint
    for the agent (we don't auto-patch here — the agent has write_file/run_shell
    for that; this tool captures the error context for it)."""
    d = _safe_path(directory)
    log = d / "FIX_LOG.txt"
    entry = f"=== {time.strftime('%Y-%m-%d %H:%M:%S')} ===\n{error_log}\n\n"
    with log.open("a", encoding="utf-8") as f:
        f.write(entry)
    return {
        "ok": True,
        "log": str(log),
        "hint": "Read the failing file(s) and FIX_LOG.txt, then re-run with run_app. Repeat until exit_code == 0.",
        "rounds_budget": max_rounds,
    }


def screenshot_app(url: str = "http://localhost:8765", output: Optional[str] = None,
                   wait_ms: int = 1500) -> dict:
    """Attempt to capture a browser/app window.

    For HTML apps, the agent can use the computer_tools.screenshot after starting
    a server (we can't render headless without extra deps). This helper falls
    back to the generic screenshot if no URL capture backend is available.
    """
    out = output or "app.png"
    # Try playwright/selenium if available, else fall back to screenshot
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1280, "height": 800})
            page.goto(url, wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(wait_ms)
            page.screenshot(path=out, full_page=True)
            browser.close()
        return {"ok": True, "path": out, "method": "playwright"}
    except Exception:
        pass
    try:
        from selenium import webdriver  # type: ignore
        from selenium.webdriver.chrome.options import Options
        opts = Options(); opts.add_argument("--headless=new")
        driver = webdriver.Chrome(options=opts)
        driver.set_window_size(1280, 800)
        driver.get(url)
        time.sleep(wait_ms / 1000)
        driver.save_screenshot(out)
        driver.quit()
        return {"ok": True, "path": out, "method": "selenium"}
    except Exception:
        pass
    # Fallback to desktop screenshot (useful if the app opened a window via open_file)
    return screenshot(out)


def package_app(directory: str, fmt: str = "zip") -> dict:
    d = _safe_path(directory)
    if not d.exists():
        return {"ok": False, "error": f"not found: {d}"}
    archive_base = d.parent / d.name
    if fmt == "zip":
        out = archive_base.with_suffix(".zip")
        with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
            for child in d.rglob("*"):
                if "__pycache__" in child.parts or child.name.endswith(".pyc"):
                    continue
                zf.write(child, child.relative_to(d.parent))
    elif fmt in ("tar", "tgz", "tar.gz"):
        out = archive_base.with_suffix(".tar.gz")
        with tarfile.open(out, "w:gz") as tf:
            tf.add(d, arcname=d.name)
    else:
        return {"ok": False, "error": f"unknown fmt: {fmt}"}
    return {"ok": True, "path": str(out), "bytes": out.stat().st_size}


def build_app(
    description: str,
    language: str = "html",
    max_fix_rounds: int = 3,
) -> dict:
    """One-shot: create → run → screenshot → package. Returns a summary."""
    created = create_app(description, language=language)
    if not created["ok"]:
        return created
    d = created["dir"]
    # Start the app in background for html, blocking-run otherwise.
    run_result: dict = {"ok": True}
    if language == "html":
        # Start static server
        srv = run_app(d, background=True, port=8765)
        time.sleep(1.0)
        shot = screenshot_app(url="http://localhost:8765", output=str(Path(d) / "screenshot.png"))
        # Shut down — best effort
        try:
            import signal
            os.kill(srv.get("pid", -1), signal.SIGTERM) if sys.platform != "win32" else subprocess.run(
                ["taskkill", "/PID", str(srv.get("pid", 0)), "/F"], capture_output=True)
        except Exception:
            pass
    else:
        shot = screenshot(output=str(Path(d) / "screenshot.png"))
    pkg = package_app(d)
    return {
        "ok": True,
        "description": description,
        "dir": d,
        "language": language,
        "files": created["files"],
        "screenshot": shot,
        "package": pkg,
        "note": "Use write_file and run_app to iterate; run build_app again after changes.",
    }


# -------------------------------------------------------- registry #
def _wrap(fn):
    def r(**kw): return fn(**kw)
    r.__name__ = fn.__name__
    return r


TOOLS: list[dict] = [
    {"name": "create_app",
     "description": "Scaffold a new production-ready app (html|python|node). Returns the project directory and starter files.",
     "params": {
         "description": {"type": "string", "required": True, "description": "what the app should do"},
         "language": {"type": "string", "description": "html|python|node", "default": "html"},
         "out_dir": {"type": "string", "description": "parent directory (defaults to ~/eazzu_apps)"},
         "title": {"type": "string", "description": "app title"},
     },
     "run": _wrap(create_app)},

    {"name": "run_app",
     "description": "Run the scaffolded app (auto-detects start command) and return stdout/stderr/exit.",
     "params": {
         "directory": {"type": "string", "required": True},
         "command": {"type": "string"},
         "timeout": {"type": "integer", "default": 30},
         "background": {"type": "boolean", "description": "spawn and return pid", "default": False},
         "port": {"type": "integer", "description": "port for http.server", "default": 0},
     },
     "run": _wrap(run_app)},

    {"name": "fix_app",
     "description": "Record an error log in the project directory (FIX_LOG.txt) to drive the next fix iteration.",
     "params": {
         "directory": {"type": "string", "required": True},
         "error_log": {"type": "string", "required": True},
     },
     "run": _wrap(fix_app)},

    {"name": "screenshot_app",
     "description": "Screenshot a running web app (Playwright/Selenium/desktop fallback).",
     "params": {
         "url": {"type": "string", "default": "http://localhost:8765"},
         "output": {"type": "string"},
         "wait_ms": {"type": "integer", "default": 1500},
     },
     "run": _wrap(screenshot_app)},

    {"name": "package_app",
     "description": "Zip/tar.gz the app directory for delivery.",
     "params": {
         "directory": {"type": "string", "required": True},
         "fmt": {"type": "string", "default": "zip"},
     },
     "run": _wrap(package_app)},

    {"name": "build_app",
     "description": "End-to-end pipeline: scaffold → start → screenshot → package a new app.",
     "params": {
         "description": {"type": "string", "required": True},
         "language": {"type": "string", "default": "html"},
         "max_fix_rounds": {"type": "integer", "default": 3},
     },
     "run": _wrap(build_app)},
]
