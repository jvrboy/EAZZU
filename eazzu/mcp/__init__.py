"""MCP (Model Context Protocol) client framework for EAZZU.

A lightweight, pure-stdlib MCP client that speaks JSON-RPC 2.0 over stdio or
HTTP. Connects to any MCP-compatible server (HuggingFace, TradingView, MT5,
filesystem, fetch, custom) and exposes its tools as EAZZU agent tools.

Usage:
    from eazzu.mcp import MCPClient, MCPRegistry
    client = MCPClient("http://localhost:8080")
    tools = client.list_tools()
    result = client.call_tool("search", {"query": "AI"})
"""
from eazzu.mcp.client import MCPClient, MCPConnectionError
from eazzu.mcp.registry import MCPRegistry, list_default_servers, get_server

__all__ = [
    "MCPClient",
    "MCPConnectionError",
    "MCPRegistry",
    "list_default_servers",
    "get_server",
]
