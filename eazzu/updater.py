"""``eazzu update`` — upgrade helper.

Performs an in-place upgrade when EAZZU was installed from a git clone:

    1. ``git pull --ff-only`` inside the package directory
    2. ``pip install -e .`` (or ``.[full]`` with ``--full`` flag)
    3. ``eazzu --version`` to confirm

If the package wasn't installed from git (e.g. PyPI), prints a helpful
message instructing the user how to upgrade.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Iterable


def _run(cmd: list[str], cwd: Path) -> tuple[int, str]:
    """Run a command, capturing output (no streaming for cleanliness)."""
    proc = subprocess.run(
        cmd,
        cwd=str(cwd),
        capture_output=True,
        text=True,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def _package_root() -> Path | None:
    """Return the git-working-tree root if eazzu is installed from one."""
    try:
        import eazzu
        p = Path(eazzu.__file__).resolve().parent  # eazzu/pkg
        # Walk up looking for .git
        for candidate in (p, *p.parents):
            if (candidate / ".git").exists():
                return candidate
    except Exception:
        return None
    return None


def update(full: bool = False, yes: bool = False) -> int:
    root = _package_root()
    if root is None:
        print("eazzu doesn't appear to be installed from a git clone.")
        print("Upgrade via pip:  pip install -U eazzu")
        return 1

    print(f"EAZZU git root: {root}")
    if not yes:
        try:
            resp = input("Proceed with `git pull --ff-only` and `pip install -e .`? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            return 1
        if resp not in {"y", "yes"}:
            print("aborted.")
            return 0

    # 1. git pull
    print("→ git pull --ff-only")
    rc, out = _run(["git", "pull", "--ff-only"], root)
    print(out.rstrip())
    if rc != 0:
        print("git pull failed — resolve conflicts/dirty tree and retry.", file=sys.stderr)
        return rc

    # 2. pip install -e
    target = ".[full]" if full else "."
    print(f"→ pip install -e {target}")
    rc, out = _run([sys.executable, "-m", "pip", "install", "-e", target], root)
    # Only print tail to keep output tight
    tail = "\n".join(out.splitlines()[-8:])
    print(tail)
    if rc != 0:
        print("pip install failed.", file=sys.stderr)
        return rc

    # 3. Verify
    print("→ eazzu --version")
    rc, out = _run([sys.executable, "-m", "eazzu", "--version"], root)
    print(out.strip() or "(no output)")
    return rc


__all__ = ["update"]
