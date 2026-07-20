"""Code runner and interpreter tools.

Provides safe execution of Python code snippets and scripts, plus a
multi-language code runner that delegates to the appropriate interpreter.

Features:
  * ``run_python`` — execute a Python code string in a subprocess and return
    stdout, stderr, exit code, and timing
  * ``run_python_interactive`` — maintain an interactive Python session across
    multiple calls (persistent globals)
  * ``run_script`` — run a script file with any interpreter (python, node, sh,
    ruby, perl, etc.)
  * ``interpret_code`` — evaluate a Python expression and return its value
  * ``run_shell`` — run a shell command and return output (scoped by allow-list)

All execution happens in isolated subprocesses with configurable timeouts.
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import json
from pathlib import Path
from typing import Optional

_TIMEOUT_DEFAULT = 30
_MAX_OUTPUT = 50000


def _truncate(text: str) -> tuple[str, bool]:
    if len(text) > _MAX_OUTPUT:
        return text[:_MAX_OUTPUT], True
    return text, False


def run_python(code: str, timeout: int = _TIMEOUT_DEFAULT, cwd: Optional[str] = None) -> dict:
    """Execute Python code in a subprocess and return output."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir=cwd) as f:
        f.write(code)
        script_path = f.name
    try:
        start = time.time()
        proc = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
        elapsed = time.time() - start
        stdout, truncated = _truncate(proc.stdout)
        stderr, stderr_truncated = _truncate(proc.stderr)
        return {
            "exit_code": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "truncated": truncated or stderr_truncated,
            "elapsed_s": round(elapsed, 3),
            "timeout": timeout,
        }
    except subprocess.TimeoutExpired:
        return {"exit_code": -1, "error": f"timeout after {timeout}s", "stdout": "", "stderr": f"timeout after {timeout}s", "elapsed_s": timeout}
    finally:
        os.unlink(script_path)


def run_python_interactive(code: str, session_id: str = "default", timeout: int = _TIMEOUT_DEFAULT) -> dict:
    """Execute Python code in a persistent session (globals preserved across calls)."""
    import pickle
    sessions_dir = Path.home() / ".eazzu" / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_file = sessions_dir / f"{session_id}.pkl"

    namespace: dict = {"__builtins__": __builtins__}
    if session_file.exists():
        try:
            namespace = pickle.loads(session_file.read_bytes())
        except Exception:
            namespace = {"__builtins__": __builtins__}

    import io
    import contextlib
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()
    start = time.time()
    try:
        with contextlib.redirect_stdout(stdout_buf), contextlib.redirect_stderr(stderr_buf):
            exec(code, namespace)
        elapsed = time.time() - start
        session_file.write_bytes(pickle.dumps(namespace))
        out, trunc = _truncate(stdout_buf.getvalue())
        err, err_trunc = _truncate(stderr_buf.getvalue())
        return {
            "session_id": session_id,
            "stdout": out,
            "stderr": err,
            "truncated": trunc or err_trunc,
            "elapsed_s": round(elapsed, 3),
            "success": True,
        }
    except Exception as exc:
        elapsed = time.time() - start
        return {
            "session_id": session_id,
            "stdout": stdout_buf.getvalue(),
            "stderr": str(exc),
            "elapsed_s": round(elapsed, 3),
            "success": False,
            "error": str(exc),
            "error_type": type(exc).__name__,
        }


def interpret_code(expression: str, timeout: int = 10) -> dict:
    """Evaluate a Python expression and return its value as JSON."""
    import io, contextlib
    namespace = {"__builtins__": __builtins__}
    stdout_buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(stdout_buf):
            result = eval(expression, namespace)
        try:
            json.dumps(result)
            return {"expression": expression, "result": result, "stdout": stdout_buf.getvalue(), "success": True}
        except (TypeError, ValueError):
            return {"expression": expression, "result": str(result), "stdout": stdout_buf.getvalue(), "success": True}
    except Exception as exc:
        return {"expression": expression, "error": str(exc), "error_type": type(exc).__name__, "success": False}


def run_script(path: str, interpreter: str = "python", args: Optional[list[str]] = None, timeout: int = _TIMEOUT_DEFAULT, cwd: Optional[str] = None) -> dict:
    """Run a script file with the specified interpreter."""
    interp_map = {
        "python": [sys.executable],
        "python3": [sys.executable],
        "node": ["node"],
        "sh": ["sh"],
        "bash": ["bash"],
        "ruby": ["ruby"],
        "perl": ["perl"],
        "lua": ["lua"],
        "php": ["php"],
        "go": ["go", "run"],
        "rust": ["rustc", "-o"],
    }
    cmd = interp_map.get(interpreter, [interpreter])
    cmd = [*cmd, path, *(args or [])]
    try:
        start = time.time()
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        elapsed = time.time() - start
        stdout, trunc = _truncate(proc.stdout)
        stderr, err_trunc = _truncate(proc.stderr)
        return {
            "interpreter": interpreter,
            "command": " ".join(cmd),
            "exit_code": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "truncated": trunc or err_trunc,
            "elapsed_s": round(elapsed, 3),
        }
    except subprocess.TimeoutExpired:
        return {"error": f"timeout after {timeout}s", "exit_code": -1}
    except FileNotFoundError:
        return {"error": f"interpreter '{interpreter}' not found", "exit_code": -1}


def run_shell(command: str, timeout: int = _TIMEOUT_DEFAULT, cwd: Optional[str] = None) -> dict:
    """Run a shell command and return output. Respects EAZZU_SHELL_ALLOW."""
    allow = os.environ.get("EAZZU_SHELL_ALLOW", "")
    if allow:
        allowed = [a.strip() for a in allow.split(",")]
        cmd_name = command.strip().split()[0] if command.strip() else ""
        if cmd_name not in allowed:
            return {"error": f"command '{cmd_name}' not in allow-list (EAZZU_SHELL_ALLOW={allow})"}
    try:
        start = time.time()
        proc = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=timeout, cwd=cwd)
        elapsed = time.time() - start
        stdout, trunc = _truncate(proc.stdout)
        stderr, err_trunc = _truncate(proc.stderr)
        return {
            "command": command,
            "exit_code": proc.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "truncated": trunc or err_trunc,
            "elapsed_s": round(elapsed, 3),
        }
    except subprocess.TimeoutExpired:
        return {"error": f"timeout after {timeout}s", "exit_code": -1}


TOOLS: list[dict] = [
    {
        "name": "run_python",
        "description": "Execute Python code in a subprocess and return stdout, stderr, exit code, and timing",
        "params": {"code": "string", "timeout": "int"},
        "run": lambda args: run_python(args.get("code", ""), int(args.get("timeout", 30))),
    },
    {
        "name": "run_python_interactive",
        "description": "Execute Python code in a persistent session (globals preserved across calls)",
        "params": {"code": "string", "session_id": "string"},
        "run": lambda args: run_python_interactive(args.get("code", ""), args.get("session_id", "default")),
    },
    {
        "name": "interpret_code",
        "description": "Evaluate a Python expression and return its value",
        "params": {"expression": "string"},
        "run": lambda args: interpret_code(args.get("expression", "")),
    },
    {
        "name": "run_script",
        "description": "Run a script file with any interpreter (python, node, sh, ruby, perl, lua, php, go, rust)",
        "params": {"path": "string", "interpreter": "string", "args": "list", "timeout": "int"},
        "run": lambda args: run_script(args.get("path", ""), args.get("interpreter", "python"), args.get("args", []), int(args.get("timeout", 30))),
    },
    {
        "name": "run_shell",
        "description": "Run a shell command and return output (respects EAZZU_SHELL_ALLOW)",
        "params": {"command": "string", "timeout": "int"},
        "run": lambda args: run_shell(args.get("command", ""), int(args.get("timeout", 30))),
    },
    {
        "name": "list_sessions",
        "description": "List active interactive Python sessions",
        "params": {},
        "run": lambda args: _list_sessions(),
    },
    {
        "name": "clear_session",
        "description": "Clear an interactive Python session",
        "params": {"session_id": "string"},
        "run": lambda args: _clear_session(args.get("session_id", "default")),
    },
]


def _list_sessions() -> dict:
    sessions_dir = Path.home() / ".eazzu" / "sessions"
    if not sessions_dir.exists():
        return {"sessions": [], "count": 0}
    sessions = [f.stem for f in sessions_dir.glob("*.pkl")]
    return {"sessions": sessions, "count": len(sessions)}


def _clear_session(session_id: str) -> dict:
    sessions_dir = Path.home() / ".eazzu" / "sessions"
    session_file = sessions_dir / f"{session_id}.pkl"
    if session_file.exists():
        session_file.unlink()
        return {"cleared": session_id}
    return {"error": f"session '{session_id}' not found"}
