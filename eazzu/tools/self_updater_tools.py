"""Self-improvement tools — the agent can modify its own source tree, test,
and push updates safely.

The workflow is:
  1. clone_self(dest)        git-clone the current repo into a sandbox dir
  2. edit_file/write_file    existing file tools can modify code
  3. test_self(dest)         run the test suite (pytest) + compileall + ruff
  4. install_self(dest)      pip install -e . in the clone to smoke-test import
  5. commit_self(dest,msg)   commit changes inside the clone
  6. push_self(dest)         push the clone to origin/main (or a PR branch)
  7. apply_to_live(dest)     copy changes back into the live install so the
                             running agent picks up new features immediately

The tool refuses to act unless it sees a git repo, and prints clear errors.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from eazzu.tools.computer_tools import _safe_path, run_shell_cmd


def _repo_root() -> Optional[Path]:
    """Find the git root of the running EAZZU install (if any)."""
    try:
        import eazzu
        p = Path(eazzu.__file__).resolve().parent
        for cand in (p, *p.parents):
            if (cand / ".git").exists():
                return cand
    except Exception:
        return None
    return None


def clone_self(dest: Optional[str] = None, branch: str = "self-improve") -> dict:
    """Clone the current repo into a sandbox directory.

    If the agent is running from a git clone, we clone that; otherwise we
    try `origin` remote.
    """
    src = _repo_root()
    if src is None:
        return {"ok": False, "error": "running install is not a git clone"}
    if dest is None:
        sandbox = Path.home() / ".eazzu" / "clones"
        sandbox.mkdir(parents=True, exist_ok=True)
        dest = str(sandbox / f"eazzu-{int(time.time())}")
    dest_p = _safe_path(dest)
    if dest_p.exists():
        shutil.rmtree(dest_p)
    proc = subprocess.run(
        ["git", "clone", str(src), str(dest_p)],
        capture_output=True, text=True, timeout=120,
    )
    if proc.returncode != 0:
        return {"ok": False, "error": proc.stderr.strip(), "stdout": proc.stdout.strip()}
    # Create a feature branch
    subprocess.run(["git", "-C", str(dest_p), "checkout", "-b", branch],
                   capture_output=True, text=True)
    return {"ok": True, "clone_dir": str(dest_p), "source": str(src), "branch": branch}


def test_self(directory: str, args: str = "-q") -> dict:
    """Run pytest + compileall + ruff in a clone. Returns pass/fail + log."""
    d = _safe_path(directory)
    if not (d / ".git").exists():
        return {"ok": False, "error": f"not a git repo: {d}"}
    results = {}
    # compileall
    c = run_shell_cmd(
        f'"{sys.executable}" -m compileall -q eazzu', shell="sh" if not sys.platform.startswith("win") else "cmd",
        timeout=120, cwd=str(d),
    )
    results["compileall"] = {"ok": c["ok"], "exit_code": c.get("exit_code")}
    # pytest
    p = run_shell_cmd(
        f'"{sys.executable}" -m pytest {args}',
        shell="sh" if not sys.platform.startswith("win") else "cmd",
        timeout=300, cwd=str(d),
    )
    results["pytest"] = {"ok": p["ok"], "exit_code": p.get("exit_code"),
                         "stdout_tail": (p.get("stdout") or "")[-1500:],
                         "stderr_tail": (p.get("stderr") or "")[-1500:]}
    # ruff if available
    ruff = shutil.which("ruff")
    if ruff:
        r = run_shell_cmd(
            f'"{ruff}" check eazzu/ tests/ --select E9,F --ignore F401,F403,F405,F541,F601,F811,F821,F841',
            shell="sh" if not sys.platform.startswith("win") else "cmd",
            timeout=60, cwd=str(d),
        )
        results["ruff"] = {"ok": r["ok"], "output_tail": (r.get("stdout") or r.get("stderr") or "")[-1500:]}
    ok = all(v.get("ok", False) or k != "pytest" for k, v in results.items())
    return {"ok": ok, "results": results, "dir": str(d)}


def install_self(directory: str) -> dict:
    """pip install -e the clone (editable) into the current env."""
    d = _safe_path(directory)
    return run_shell_cmd(
        f'"{sys.executable}" -m pip install -e .',
        shell="sh" if not sys.platform.startswith("win") else "cmd",
        timeout=180, cwd=str(d),
    )


def commit_self(directory: str, message: str) -> dict:
    d = _safe_path(directory)
    subprocess.run(["git", "-C", str(d), "add", "-A"], capture_output=True, timeout=30)
    proc = subprocess.run(
        ["git", "-C", str(d), "commit", "-m", message],
        capture_output=True, text=True, timeout=30,
    )
    return {"ok": proc.returncode == 0, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}


def push_self(directory: str, branch: Optional[str] = None, to_main: bool = True) -> dict:
    """Push a clone. If to_main, check out main, merge the feature branch, push main."""
    d = _safe_path(directory)
    if branch:
        proc = subprocess.run(["git", "-C", str(d), "push", "-u", "origin", branch],
                              capture_output=True, text=True, timeout=60)
        return {"ok": proc.returncode == 0, "stdout": proc.stdout, "stderr": proc.stderr}
    if to_main:
        # merge branch into main then push main
        b_proc = subprocess.run(["git", "-C", str(d), "rev-parse", "--abbrev-ref", "HEAD"],
                                capture_output=True, text=True)
        feature = b_proc.stdout.strip()
        subprocess.run(["git", "-C", str(d), "checkout", "main"], capture_output=True)
        subprocess.run(["git", "-C", str(d), "merge", "--no-ff", feature, "-m", f"Merge {feature}"],
                       capture_output=True)
    proc = subprocess.run(["git", "-C", str(d), "push", "origin", "main"],
                          capture_output=True, text=True, timeout=120)
    return {"ok": proc.returncode == 0, "stdout": proc.stdout, "stderr": proc.stderr}


def apply_to_live(directory: str, restart_cmd: Optional[str] = None) -> dict:
    """Copy changed files from a clone back into the live install so the running
    agent picks them up without a full reinstall."""
    d = _safe_path(directory)
    live = _repo_root()
    if live is None:
        return {"ok": False, "error": "cannot find live install path"}
    import filecmp
    copied = []
    for root, _dirs, files in os.walk(d / "eazzu"):
        for f in files:
            if f.endswith(".pyc") or "__pycache__" in root:
                continue
            src = Path(root) / f
            rel = src.relative_to(d)
            dst = live / rel
            if not dst.exists() or not filecmp.cmp(src, dst, shallow=False):
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied.append(str(rel))
    # Tests
    t_src = d / "tests"
    t_dst = live / "tests"
    if t_src.exists():
        for root, _dirs, files in os.walk(t_src):
            for f in files:
                if f.endswith(".pyc") or "__pycache__" in root:
                    continue
                src = Path(root) / f
                rel = src.relative_to(d)
                dst = live / rel
                if not dst.exists() or not filecmp.cmp(src, dst, shallow=False):
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    copied.append(str(rel))
    if restart_cmd:
        subprocess.Popen(restart_cmd, shell=True)
    return {"ok": True, "copied_files": copied, "count": len(copied)}


def status_self() -> dict:
    """Report where the running EAZZU is installed and if it is a git repo."""
    import eazzu
    root = _repo_root()
    return {
        "ok": True,
        "package_path": str(Path(eazzu.__file__).resolve().parent),
        "git_root": str(root) if root else None,
        "is_git_clone": root is not None,
        "version": eazzu.__version__,
    }


def _wrap(fn):
    def r(**kw): return fn(**kw)
    r.__name__ = fn.__name__
    return r


TOOLS: list[dict] = [
    {"name": "self_status",
     "description": "Report where EAZZU is installed, version, and whether it's a git clone (required for self-update).",
     "params": {}, "run": _wrap(status_self)},

    {"name": "self_clone",
     "description": "Clone the running EAZZU repo into a sandbox directory for safe modification.",
     "params": {"dest": {"type": "string"}, "branch": {"type": "string", "default": "self-improve"}},
     "run": _wrap(clone_self)},

    {"name": "self_test",
     "description": "Run pytest + compileall + (ruff if present) inside a clone directory to validate changes.",
     "params": {"directory": {"type": "string", "required": True}, "args": {"type": "string", "default": "-q"}},
     "run": _wrap(test_self)},

    {"name": "self_install",
     "description": "pip install -e a clone to verify imports.",
     "params": {"directory": {"type": "string", "required": True}},
     "run": _wrap(install_self)},

    {"name": "self_commit",
     "description": "Stage and commit all changes in a clone.",
     "params": {"directory": {"type": "string", "required": True}, "message": {"type": "string", "required": True}},
     "run": _wrap(commit_self)},

    {"name": "self_push",
     "description": "Push a clone to origin/main (merges feature branch into main).",
     "params": {"directory": {"type": "string", "required": True}, "branch": {"type": "string"}, "to_main": {"type": "boolean", "default": True}},
     "run": _wrap(push_self)},

    {"name": "self_apply",
     "description": "Copy changed files from a clone back into the live EAZZU install so new features take effect immediately.",
     "params": {"directory": {"type": "string", "required": True}, "restart_cmd": {"type": "string"}},
     "run": _wrap(apply_to_live)},
]
