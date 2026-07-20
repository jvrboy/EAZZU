"""MCP server registry — catalog of known MCP servers and connection helpers.

Each entry describes how to reach an MCP server (endpoint, transport, auth).
Keys are looked up by name via :func:`get_server` and iterated via
:func:`list_default_servers`.
"""
from __future__ import annotations

import os
from typing import Optional

# Default MCP servers. Users can override endpoints via environment variables
# (e.g. ``EAZZU_MCP_HUGGINGFACE_URL``) or by editing this dict at runtime.
DEFAULT_SERVERS: dict[str, dict] = {
    "huggingface": {
        "endpoint": os.environ.get(
            "EAZZU_MCP_HUGGINGFACE_URL",
            "https://huggingface.co/api/mcp",
        ),
        "transport": "http",
        "description": "HuggingFace Hub — models, datasets, spaces, papers search",
        "auth_env": "HF_TOKEN",
    },
    "tradingview": {
        "endpoint": os.environ.get(
            "EAZZU_MCP_TRADINGVIEW_URL",
            "http://localhost:9800",
        ),
        "transport": "http",
        "description": "TradingView bridge — charts, indicators, screeners, alerts",
        "auth_env": "TRADINGVIEW_TOKEN",
    },
    "mt5": {
        "endpoint": os.environ.get(
            "EAZZU_MCP_MT5_URL",
            "http://localhost:9801",
        ),
        "transport": "http",
        "description": "MetaTrader 5 bridge — account, orders, positions, history",
        "auth_env": "MT5_TOKEN",
    },
    "filesystem": {
        "endpoint": os.environ.get(
            "EAZZU_MCP_FS_CMD",
            "python -m eazzu.mcp.servers.filesystem",
        ),
        "transport": "stdio",
        "description": "Local filesystem — read, write, list, search files",
        "auth_env": None,
    },
    "fetch": {
        "endpoint": os.environ.get(
            "EAZZU_MCP_FETCH_CMD",
            "python -m eazzu.mcp.servers.fetch",
        ),
        "transport": "stdio",
        "description": "HTTP fetch — GET/POST any URL, return body + headers",
        "auth_env": None,
    },
    "github": {
        "endpoint": os.environ.get(
            "EAZZU_MCP_GITHUB_URL",
            "https://api.githubcopilot.com/mcp/",
        ),
        "transport": "http",
        "description": "GitHub — repos, issues, PRs, code search",
        "auth_env": "GITHUB_TOKEN",
    },
}


def list_default_servers() -> list[dict]:
    """Return a list of ``{name, endpoint, transport, description, auth_env}``."""
    out = []
    for name, spec in DEFAULT_SERVERS.items():
        out.append({"name": name, **spec})
    return out


def get_server(name: str) -> dict:
    """Return the connection spec for a named server."""
    name = name.lower().strip()
    if name not in DEFAULT_SERVERS:
        raise KeyError(f"unknown MCP server '{name}'. Known: {sorted(DEFAULT_SERVERS)}")
    return DEFAULT_SERVERS[name]


def _auth_headers(spec: dict) -> dict:
    """Build auth headers from the server spec's ``auth_env`` var, if set."""
    env_var = spec.get("auth_env")
    if not env_var:
        return {}
    token = os.environ.get(env_var, "")
    if not token:
        return {}
    return {"Authorization": f"Bearer {token}"}


class MCPRegistry:
    """A live registry of connected MCP clients.

    Lazily connects to servers on first use and caches the client instance.
    Each connected server's tools are exposed via :meth:`all_tools`.
    """

    def __init__(self, servers: Optional[list[str]] = None) -> None:
        self._servers = servers or list(DEFAULT_SERVERS.keys())
        self._clients: dict[str, "MCPClient"] = {}

    def connect(self, name: str) -> "MCPClient":
        """Lazily connect to a named server, caching the client."""
        if name in self._clients:
            return self._clients[name]
        from eazzu.mcp.client import MCPClient
        spec = get_server(name)
        client = MCPClient(
            endpoint=spec["endpoint"],
            transport=spec["transport"],
            headers=_auth_headers(spec),
        )
        client.initialize()
        self._clients[name] = client
        return client

    def disconnect(self, name: str) -> None:
        client = self._clients.pop(name, None)
        if client:
            client.close()

    def disconnect_all(self) -> None:
        for name in list(self._clients):
            self.disconnect(name)

    def all_tools(self) -> list[dict]:
        """Collect tools from all connected servers."""
        tools = []
        for name in self._servers:
            try:
                client = self.connect(name)
                tools.extend(client.to_eazzu_tools())
            except Exception as exc:  # noqa: BLE001
                tools.append({
                    "name": f"mcp_{name}_status",
                    "description": f"[MCP] {name} server unavailable: {exc}",
                    "params": {},
                    "run": lambda *a, _n=name, _e=exc: {"server": _n, "error": str(_e)},
                })
        return tools

    def server_status(self) -> list[dict]:
        """Ping every configured server and report reachability."""
        out = []
        for name in self._servers:
            spec = get_server(name)
            try:
                client = self.connect(name)
                ok = client.ping()
                out.append({"name": name, "reachable": ok, "endpoint": spec["endpoint"]})
            except Exception as exc:  # noqa: BLE001
                out.append({"name": name, "reachable": False, "error": str(exc), "endpoint": spec["endpoint"]})
        return out

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.disconnect_all()
