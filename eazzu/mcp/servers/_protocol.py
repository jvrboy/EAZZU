"""Minimal MCP stdio server protocol helpers.

Reads JSON-RPC requests line-by-line from stdin, dispatches to handler
methods, and writes responses line-by-line to stdout. Notifications (no
``id``) are acknowledged silently.
"""
from __future__ import annotations

import json
import sys
from typing import Any, Callable


def serve(tool_handlers: dict[str, Callable[[dict], Any]], tool_specs: list[dict], server_name: str = "eazzu-mcp") -> None:
    """Run a stdio MCP server.

    Parameters
    ----------
    tool_handlers:
        Maps tool name -> callable(args_dict) -> result dict.
    tool_specs:
        List of tool spec dicts with keys: name, description, inputSchema.
    server_name:
        Reported in the initialize response.
    """
    for raw_line in sys.stdin:
        line = raw_line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            sys.stderr.write(f"invalid JSON: {line}\n")
            continue
        method = req.get("method", "")
        req_id = req.get("id")
        params = req.get("params", {}) or {}
        result: Any = None
        error: dict | None = None
        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": server_name, "version": "1.0.0"},
                }
            elif method == "notifications/initialized":
                continue  # notification — no response
            elif method == "tools/list":
                result = {"tools": tool_specs}
            elif method == "tools/call":
                tname = params.get("name", "")
                args = params.get("arguments", {}) or {}
                handler = tool_handlers.get(tname)
                if handler is None:
                    error = {"code": -32601, "message": f"unknown tool '{tname}'"}
                else:
                    result = handler(args)
            elif method == "ping":
                result = {}
            else:
                error = {"code": -32601, "message": f"method '{method}' not found"}
        except Exception as exc:  # noqa: BLE001
            error = {"code": -32000, "message": str(exc)}
        if req_id is None:
            continue
        resp = {"jsonrpc": "2.0", "id": req_id}
        if error:
            resp["error"] = error
        else:
            resp["result"] = result
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()
