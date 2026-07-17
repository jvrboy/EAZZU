"""Sandboxed shell tool. Only whitelisted commands can run by default."""
from __future__ import annotations

import os
import shlex
import subprocess
from typing import Any

# Users can widen this via env var, but default is safe-ish read-only utilities.
_DEFAULT_ALLOWED = {
    "ls", "pwd", "cat", "head", "tail", "wc", "grep", "find",
    "echo", "date", "whoami", "uname", "which", "df", "du", "ps",
    "python", "python3", "pip", "pip3", "git", "curl", "wget",
    "node", "npm", "npx", "ping", "nslookup", "dig", "traceroute",
}


def _allowed() -> set[str]:
    extra = os.environ.get("EAZZU_SHELL_ALLOW", "")
    return _DEFAULT_ALLOWED | {c.strip() for c in extra.split(",") if c.strip()}


def run_shell(command: str, timeout: int = 30) -> dict[str, Any]:
    """Run a shell command, capped by an allow-list + timeout."""
    if not command or not command.strip():
        return {"error": "empty_command"}
    try:
        tokens = shlex.split(command)
    except ValueError as e:
        return {"error": f"parse_error: {e}"}
    exe = os.path.basename(tokens[0])
    if exe not in _allowed():
        return {
            "error": "command_not_allowed",
            "hint": f"'{exe}' is not in the allow-list. Set EAZZU_SHELL_ALLOW=extra,commands to widen.",
            "allowed": sorted(_allowed()),
        }
    try:
        r = subprocess.run(
            tokens, capture_output=True, text=True, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return {"error": "timeout", "command": command}
    return {
        "exit_code": r.returncode,
        "stdout": (r.stdout or "")[-4000:],
        "stderr": (r.stderr or "")[-2000:],
    }


TOOLS = [
    {
        "name": "shell",
        "description": "Run a whitelisted shell command and return stdout/stderr/exit_code.",
        "params": {"command": "string", "timeout": "int (seconds, default 30)"},
        "run": run_shell,
    }
]
