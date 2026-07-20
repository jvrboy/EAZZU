"""Fetch MCP server — HTTP GET/POST any URL, return body + headers.

Run with: ``python -m eazzu.mcp.servers.fetch``
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error

from eazzu.mcp.servers._protocol import serve


def _fetch(args: dict) -> dict:
    url = args.get("url", "")
    method = (args.get("method") or "GET").upper()
    headers = args.get("headers") or {}
    body = args.get("body")
    timeout = float(args.get("timeout", 30))
    if not url:
        return {"error": "url is required"}
    data = None
    if body is not None:
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode("utf-8")
            headers = {"Content-Type": "application/json", **headers}
        else:
            data = str(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            text = raw.decode("utf-8", errors="replace")
            return {
                "status": resp.status,
                "headers": dict(resp.headers),
                "body": text[:50000],
                "truncated": len(text) > 50000,
                "size": len(raw),
            }
    except urllib.error.HTTPError as exc:
        return {"error": str(exc), "status": exc.code, "url": url}
    except urllib.error.URLError as exc:
        return {"error": str(exc), "url": url}


def _get(args: dict) -> dict:
    args = {**args, "method": "GET"}
    return _fetch(args)


def _post(args: dict) -> dict:
    args = {**args, "method": "POST"}
    return _fetch(args)


TOOL_SPECS = [
    {"name": "fetch", "description": "HTTP request to any URL", "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}, "method": {"type": "string"}, "headers": {"type": "object"}, "body": {}, "timeout": {"type": "number"}}, "required": ["url"]}},
    {"name": "get", "description": "HTTP GET request", "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}, "headers": {"type": "object"}, "timeout": {"type": "number"}}, "required": ["url"]}},
    {"name": "post", "description": "HTTP POST request", "inputSchema": {"type": "object", "properties": {"url": {"type": "string"}, "body": {}, "headers": {"type": "object"}, "timeout": {"type": "number"}}, "required": ["url"]}},
]

HANDLERS = {"fetch": _fetch, "get": _get, "post": _post}


def main() -> None:
    serve(HANDLERS, TOOL_SPECS, server_name="eazzu-fetch")


if __name__ == "__main__":
    main()
