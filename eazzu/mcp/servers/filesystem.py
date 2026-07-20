"""Filesystem MCP server — read, write, list, search local files.

Run with: ``python -m eazzu.mcp.servers.filesystem``

Scoped to the current working directory by default. Set ``EAZZU_FS_ROOT`` to
restrict to a specific directory.
"""
from __future__ import annotations

import os
import fnmatch
import sys
from pathlib import Path

from eazzu.mcp.servers._protocol import serve

_ROOT = Path(os.environ.get("EAZZU_FS_ROOT", os.getcwd())).resolve()


def _safe(path: str) -> Path:
    p = (_ROOT / path).resolve()
    if _ROOT not in p.parents and p != _ROOT:
        raise PermissionError(f"path '{path}' escapes root {_ROOT}")
    return p


def _read(args: dict) -> dict:
    p = _safe(args.get("path", "."))
    if not p.exists():
        return {"error": f"not found: {p}"}
    if p.is_dir():
        return {"error": f"is a directory: {p}"}
    return {"path": str(p), "content": p.read_text(encoding="utf-8", errors="replace"), "size": p.stat().st_size}


def _write(args: dict) -> dict:
    p = _safe(args.get("path", ""))
    p.parent.mkdir(parents=True, exist_ok=True)
    content = args.get("content", "")
    p.write_text(content, encoding="utf-8")
    return {"path": str(p), "written": len(content)}


def _list(args: dict) -> dict:
    p = _safe(args.get("path", "."))
    if not p.exists():
        return {"error": f"not found: {p}"}
    if p.is_file():
        return {"error": f"is a file: {p}"}
    entries = []
    for child in sorted(p.iterdir()):
        entries.append({"name": child.name, "type": "dir" if child.is_dir() else "file", "size": child.stat().st_size if child.is_file() else 0})
    return {"path": str(p), "entries": entries}


def _search(args: dict) -> dict:
    pattern = args.get("pattern", "*")
    p = _safe(args.get("path", "."))
    matches = []
    for root, dirs, files in os.walk(p):
        for name in dirs + files:
            if fnmatch.fnmatch(name, pattern):
                matches.append(str(Path(root) / name))
        if len(matches) >= 500:
            break
    return {"pattern": pattern, "root": str(p), "matches": matches[:500], "truncated": len(matches) >= 500}


def _delete(args: dict) -> dict:
    p = _safe(args.get("path", ""))
    if not p.exists():
        return {"error": f"not found: {p}"}
    if p.is_dir():
        import shutil
        shutil.rmtree(p)
    else:
        p.unlink()
    return {"path": str(p), "deleted": True}


def _mkdir(args: dict) -> dict:
    p = _safe(args.get("path", ""))
    p.mkdir(parents=True, exist_ok=True)
    return {"path": str(p), "created": True}


TOOL_SPECS = [
    {"name": "read", "description": "Read a text file", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "write", "description": "Write a text file", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "content": {"type": "string"}}, "required": ["path", "content"]}},
    {"name": "list", "description": "List directory entries", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}}},
    {"name": "search", "description": "Search for files by glob pattern", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}, "pattern": {"type": "string"}}}},
    {"name": "delete", "description": "Delete a file or directory", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
    {"name": "mkdir", "description": "Create a directory", "inputSchema": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]}},
]

HANDLERS = {"read": _read, "write": _write, "list": _list, "search": _search, "delete": _delete, "mkdir": _mkdir}


def main() -> None:
    serve(HANDLERS, TOOL_SPECS, server_name="eazzu-filesystem")


if __name__ == "__main__":
    main()
