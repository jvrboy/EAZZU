"""Bundled MCP servers — stdio JSON-RPC servers runnable locally.

These are minimal MCP server implementations so EAZZU ships with working
servers out of the box. They speak JSON-RPC 2.0 over stdio and implement the
core MCP methods (initialize, tools/list, tools/call).

External servers (HuggingFace, TradingView, MT5, GitHub) are reached via HTTP
using the client in :mod:`eazzu.mcp.client`; the servers here are the ones we
can run locally without external dependencies.
"""
