"""MCP client — JSON-RPC 2.0 over stdio or HTTP, pure stdlib.

Speaks the Model Context Protocol (MCP) so EAZZU can connect to any
MCP-compatible server: HuggingFace Spaces, TradingView bridges, MT5 bridges,
local filesystem servers, remote fetch servers, and more.

Two transports are supported:
  * ``stdio`` — spawn a local process and talk over stdin/stdout
  * ``http``  — POST JSON-RPC envelopes to an HTTP endpoint

No third-party dependencies. ``websocket-client`` is used for streaming
notifications if available, but the client degrades gracefully without it.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.request
import urllib.error
from typing import Any, Optional


class MCPConnectionError(RuntimeError):
    """Raised when an MCP server cannot be reached or responds invalidly."""


class MCPClient:
    """A minimal MCP client supporting stdio and HTTP transports.

    Parameters
    ----------
    endpoint:
        * For HTTP: a full URL (``http://host:port`` or ``https://...``)
        * For stdio: a command string (``python -m my_mcp_server``)
    transport:
        ``"http"`` (default) or ``"stdio"``.
    headers:
        Optional dict of HTTP headers (e.g. auth tokens).
    timeout:
        Per-request timeout in seconds.
    """

    def __init__(
        self,
        endpoint: str,
        transport: str = "http",
        *,
        headers: Optional[dict] = None,
        timeout: float = 30.0,
        env: Optional[dict] = None,
    ) -> None:
        self.endpoint = endpoint
        self.transport = transport
        self.headers = headers or {}
        self.timeout = timeout
        self.env = env
        self._proc: Optional[subprocess.Popen] = None
        self._req_id = 0
        self._tools_cache: Optional[list[dict]] = None
        self._resources_cache: Optional[list[dict]] = None
        self._prompts_cache: Optional[list[dict]] = None
        self._server_info: Optional[dict] = None

    # -------------------------------------------------------------- helpers #
    def _next_id(self) -> int:
        self._req_id += 1
        return self._req_id

    def _envelope(self, method: str, params: Optional[dict] = None) -> dict:
        return {"jsonrpc": "2.0", "id": self._next_id(), "method": method, "params": params or {}}

    # ----------------------------------------------------------- transports #
    def _roundtrip_http(self, payload: dict) -> dict:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers={"Content-Type": "application/json", **self.headers},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
        except urllib.error.URLError as exc:
            raise MCPConnectionError(f"cannot reach MCP server at {self.endpoint}: {exc}") from exc
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise MCPConnectionError(f"invalid JSON response from MCP server: {exc}") from exc

    def _roundtrip_stdio(self, payload: dict) -> dict:
        if self._proc is None or self._proc.poll() is not None:
            cmd = self.endpoint.split()
            exe = shutil.which(cmd[0]) or cmd[0]
            try:
                self._proc = subprocess.Popen(
                    [exe, *cmd[1:]],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env={**os.environ, **(self.env or {})},
                    text=True,
                    bufsize=1,
                )
            except OSError as exc:
                raise MCPConnectionError(f"cannot spawn MCP server '{self.endpoint}': {exc}") from exc
        line = json.dumps(payload) + "\n"
        assert self._proc.stdin is not None
        self._proc.stdin.write(line)
        self._proc.stdin.flush()
        assert self._proc.stdout is not None
        raw = self._proc.stdout.readline()
        if not raw:
            err = ""
            if self._proc.stderr:
                err = self._proc.stderr.read()
            raise MCPConnectionError(f"MCP server closed stdout: {err}")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise MCPConnectionError(f"invalid JSON from MCP server: {exc}") from exc

    def _roundtrip(self, payload: dict) -> dict:
        if self.transport == "stdio":
            return self._roundtrip_stdio(payload)
        return self._roundtrip_http(payload)

    def _check(self, resp: dict) -> dict:
        if "error" in resp:
            err = resp["error"]
            raise MCPConnectionError(f"MCP error {err.get('code')}: {err.get('message')}")
        return resp.get("result", {})

    # ------------------------------------------------------- MCP methods #
    def initialize(self) -> dict:
        """Perform the MCP handshake. Returns server info."""
        result = self._check(self._roundtrip(self._envelope("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "eazzu", "version": "1.3.0"},
        })))
        self._server_info = result
        try:
            self._roundtrip({"jsonrpc": "2.0", "method": "notifications/initialized"})
        except MCPConnectionError:
            pass
        return result

    def list_tools(self, refresh: bool = False) -> list[dict]:
        """Return the server's tool catalogue. Cached after first call."""
        if self._tools_cache is not None and not refresh:
            return self._tools_cache
        result = self._check(self._roundtrip(self._envelope("tools/list")))
        self._tools_cache = result.get("tools", [])
        return self._tools_cache

    def call_tool(self, name: str, arguments: Optional[dict] = None) -> dict:
        """Invoke a tool on the MCP server and return its result."""
        result = self._check(self._roundtrip(self._envelope("tools/call", {
            "name": name,
            "arguments": arguments or {},
        })))
        return result

    def list_resources(self, refresh: bool = False) -> list[dict]:
        if self._resources_cache is not None and not refresh:
            return self._resources_cache
        result = self._check(self._roundtrip(self._envelope("resources/list")))
        self._resources_cache = result.get("resources", [])
        return self._resources_cache

    def read_resource(self, uri: str) -> dict:
        return self._check(self._roundtrip(self._envelope("resources/read", {"uri": uri})))

    def list_prompts(self, refresh: bool = False) -> list[dict]:
        if self._prompts_cache is not None and not refresh:
            return self._prompts_cache
        result = self._check(self._roundtrip(self._envelope("prompts/list")))
        self._prompts_cache = result.get("prompts", [])
        return self._prompts_cache

    def get_prompt(self, name: str, arguments: Optional[dict] = None) -> dict:
        return self._check(self._roundtrip(self._envelope("prompts/get", {
            "name": name,
            "arguments": arguments or {},
        })))

    def ping(self) -> bool:
        try:
            self._check(self._roundtrip(self._envelope("ping")))
            return True
        except MCPConnectionError:
            return False

    def close(self) -> None:
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None

    def __enter__(self):
        self.initialize()
        return self

    def __exit__(self, *exc):
        self.close()

    # ------------------------------------------------------ EAZZU adapter #
    def to_eazzu_tools(self) -> list[dict]:
        """Convert the server's tool catalogue into EAZZU agent tools."""
        tools = []
        for spec in self.list_tools():
            schema = spec.get("inputSchema", {})
            params = {}
            required = set(schema.get("required", []))
            for pname, pdef in schema.get("properties", {}).items():
                ptype = pdef.get("type", "string")
                if isinstance(ptype, list):
                    ptype = ptype[0] if ptype else "string"
                params[pname] = ptype
            name = spec.get("name", "unknown")
            tools.append({
                "name": f"mcp_{name}",
                "description": f"[MCP] {spec.get('description', '')}",
                "params": params,
                "run": lambda args, _name=name, _client=self: _client.call_tool(_name, args),
            })
        return tools
