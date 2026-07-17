"""File-system tools — read / write / list, scoped to a safe root."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def _safe_path(path: str) -> Path:
    """Resolve *path* but refuse to leave $EAZZU_FS_ROOT (defaults to CWD)."""
    root = Path(os.environ.get("EAZZU_FS_ROOT", os.getcwd())).resolve()
    p = (root / path).resolve() if not os.path.isabs(path) else Path(path).resolve()
    if root not in p.parents and p != root:
        raise PermissionError(f"path escapes root: {p}")
    return p


def read_file(path: str, max_bytes: int = 200_000) -> dict[str, Any]:
    try:
        p = _safe_path(path)
        data = p.read_bytes()[:max_bytes]
        return {"path": str(p), "bytes": len(data), "content": data.decode("utf-8", errors="replace")}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def write_file(path: str, content: str, append: bool = False) -> dict[str, Any]:
    try:
        p = _safe_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with p.open(mode, encoding="utf-8") as f:
            f.write(content)
        return {"path": str(p), "written": len(content), "mode": mode}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


def list_dir(path: str = ".", pattern: str = "*") -> dict[str, Any]:
    try:
        p = _safe_path(path)
        entries = []
        for child in sorted(p.glob(pattern)):
            st = child.stat()
            entries.append({
                "name": child.name,
                "is_dir": child.is_dir(),
                "size": st.st_size,
            })
        return {"path": str(p), "entries": entries[:200]}
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}


TOOLS = [
    {
        "name": "read_file",
        "description": "Read a text file (utf-8, up to max_bytes).",
        "params": {"path": "string", "max_bytes": "int (default 200000)"},
        "run": read_file,
    },
    {
        "name": "write_file",
        "description": "Write / append text to a file (parents auto-created).",
        "params": {"path": "string", "content": "string", "append": "bool (default false)"},
        "run": write_file,
    },
    {
        "name": "list_dir",
        "description": "List entries in a directory (optional glob).",
        "params": {"path": "string (default '.')", "pattern": "glob string (default '*')"},
        "run": list_dir,
    },
]
