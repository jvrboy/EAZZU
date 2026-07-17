"""Developer tools — thin wrappers over the vendored ``devtoolkit``."""
from __future__ import annotations

import importlib
import os
from typing import Any


def _lazy(module: str, attr: str):
    try:
        mod = importlib.import_module(module)
        return getattr(mod, attr, None)
    except Exception as e:  # pragma: no cover
        return {"error": f"import_failed:{module}:{e}"}


def analyze_code(path: str) -> dict[str, Any]:
    """Static/AI analysis pass on a directory or file."""
    fn = _lazy("eazzu.dev.toolkit.ai_analyzer", "analyze")
    if callable(fn):
        try:
            return {"path": path, "report": fn(path)}
        except Exception as e:  # pragma: no cover
            return {"error": f"analyze_failed: {e}"}
    # Fallback: quick file summary.
    summary = {"files": [], "total_lines": 0}
    for root, _, files in os.walk(path):
        for fname in files:
            if fname.endswith((".py", ".js", ".ts", ".go", ".rs")):
                fp = os.path.join(root, fname)
                try:
                    with open(fp, encoding="utf-8", errors="ignore") as f:
                        lines = sum(1 for _ in f)
                    summary["files"].append({"path": fp, "lines": lines})
                    summary["total_lines"] += lines
                except OSError:
                    continue
    return summary


def run_file(path: str, args: str = "") -> dict[str, Any]:
    fn = _lazy("eazzu.dev.toolkit.runner", "run")
    if callable(fn):
        try:
            return {"path": path, "output": fn(path, args)}
        except Exception as e:  # pragma: no cover
            return {"error": f"run_failed: {e}"}
    return {"error": "runner_unavailable"}


TOOLS = [
    {"name": "analyze_code",
     "description": "Analyze a code file or directory (falls back to a file/line summary).",
     "params": {"path": "string"}, "run": analyze_code},
    {"name": "run_file",
     "description": "Execute a script file through the vendored devtoolkit runner.",
     "params": {"path": "string", "args": "string"}, "run": run_file},
]
