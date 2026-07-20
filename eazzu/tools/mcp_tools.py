"""MCP agent tools — expose MCP servers as EAZZU agent tools.

Connects to configured MCP servers (HuggingFace, TradingView, MT5, filesystem,
fetch, GitHub) and wraps their tools in the EAZZU tool registry format.
"""
from __future__ import annotations

import os
from typing import Optional

from eazzu.mcp import MCPRegistry, list_default_servers, get_server
from eazzu.mcp.servers import huggingface, tradingview, mt5

TOOLS: list[dict] = [
    {
        "name": "mcp_list_servers",
        "description": "List all configured MCP servers and their connection details",
        "params": {},
        "run": lambda args: {"servers": list_default_servers()},
    },
    {
        "name": "mcp_server_status",
        "description": "Ping all configured MCP servers and report which are reachable",
        "params": {},
        "run": lambda args: MCPRegistry().server_status(),
    },
    {
        "name": "mcp_connect",
        "description": "Connect to a named MCP server and list its available tools",
        "params": {"server": "string"},
        "run": lambda args: _connect_server(args.get("server", "")),
    },
    {
        "name": "mcp_call_tool",
        "description": "Call a tool on a named MCP server with arguments",
        "params": {"server": "string", "tool": "string", "arguments": "object"},
        "run": lambda args: _call_mcp_tool(args.get("server", ""), args.get("tool", ""), args.get("arguments", {})),
    },
    # ---- HuggingFace ---- #
    {
        "name": "hf_search_models",
        "description": "Search HuggingFace Hub for AI models by query",
        "params": {"query": "string", "limit": "int"},
        "run": lambda args: huggingface.search_models(args.get("query", ""), int(args.get("limit", 10)), os.environ.get("HF_TOKEN")),
    },
    {
        "name": "hf_search_datasets",
        "description": "Search HuggingFace Hub for datasets",
        "params": {"query": "string", "limit": "int"},
        "run": lambda args: huggingface.search_datasets(args.get("query", ""), int(args.get("limit", 10)), os.environ.get("HF_TOKEN")),
    },
    {
        "name": "hf_search_spaces",
        "description": "Search HuggingFace Hub for Spaces (live AI demos)",
        "params": {"query": "string", "limit": "int"},
        "run": lambda args: huggingface.search_spaces(args.get("query", ""), int(args.get("limit", 10)), os.environ.get("HF_TOKEN")),
    },
    {
        "name": "hf_search_papers",
        "description": "Search HuggingFace for research papers",
        "params": {"query": "string", "limit": "int"},
        "run": lambda args: huggingface.search_papers(args.get("query", ""), int(args.get("limit", 10)), os.environ.get("HF_TOKEN")),
    },
    {
        "name": "hf_model_info",
        "description": "Get detailed info about a HuggingFace model (e.g. 'bert-base-uncased')",
        "params": {"model_id": "string"},
        "run": lambda args: huggingface.get_model_info(args.get("model_id", ""), os.environ.get("HF_TOKEN")),
    },
    {
        "name": "hf_model_files",
        "description": "List files in a HuggingFace model repository",
        "params": {"model_id": "string"},
        "run": lambda args: huggingface.get_model_files(args.get("model_id", ""), os.environ.get("HF_TOKEN")),
    },
    {
        "name": "hf_whoami",
        "description": "Check which HuggingFace account the current token belongs to",
        "params": {},
        "run": lambda args: huggingface.whoami(os.environ.get("HF_TOKEN", "")) if os.environ.get("HF_TOKEN") else {"error": "HF_TOKEN not set"},
    },
    # ---- TradingView ---- #
    {
        "name": "tv_list_indicators",
        "description": "List all available TradingView technical indicators with their Pine Script references",
        "params": {},
        "run": lambda args: tradingview.list_indicators(),
    },
    {
        "name": "tv_get_indicator",
        "description": "Get details for a specific TradingView indicator (rsi, macd, ema, bollinger, etc.)",
        "params": {"name": "string"},
        "run": lambda args: tradingview.get_indicator(args.get("name", "")),
    },
    {
        "name": "tv_list_strategies",
        "description": "List available Pine Script trading strategies",
        "params": {},
        "run": lambda args: tradingview.list_strategies(),
    },
    {
        "name": "tv_get_strategy",
        "description": "Get full Pine Script code for a named strategy (ema_cross, rsi_reversal, etc.)",
        "params": {"name": "string"},
        "run": lambda args: tradingview.get_strategy(args.get("name", "")),
    },
    {
        "name": "tv_chart_url",
        "description": "Build a TradingView chart widget URL for a symbol",
        "params": {"symbol": "string", "interval": "string", "theme": "string"},
        "run": lambda args: tradingview.chart_url(args.get("symbol", ""), args.get("interval", "60"), args.get("theme", "dark")),
    },
    {
        "name": "tv_screener_url",
        "description": "Build a TradingView screener URL for a market (crypto, forex, stocks)",
        "params": {"market": "string"},
        "run": lambda args: tradingview.screener_url(args.get("market", "crypto")),
    },
    {
        "name": "tv_webhook",
        "description": "Process a TradingView webhook alert payload",
        "params": {"payload": "object"},
        "run": lambda args: tradingview.webhook_receiver(args.get("payload", {})),
    },
    # ---- MT5 ---- #
    {
        "name": "mt5_status",
        "description": "Check if MetaTrader 5 is available (native or bridge mode)",
        "params": {},
        "run": lambda args: {"available": mt5._available(), "mode": "native" if mt5._MT5_AVAILABLE else ("bridge" if mt5._BRIDGE_URL else "unavailable"), "bridge_url": mt5._BRIDGE_URL or None},
    },
    {
        "name": "mt5_initialize",
        "description": "Initialize MT5 connection (native or bridge)",
        "params": {},
        "run": lambda args: mt5.initialize(),
    },
    {
        "name": "mt5_account",
        "description": "Get MT5 account info (balance, equity, margin, leverage)",
        "params": {},
        "run": lambda args: mt5.account_info(),
    },
    {
        "name": "mt5_terminal",
        "description": "Get MT5 terminal info",
        "params": {},
        "run": lambda args: mt5.terminal_info(),
    },
    {
        "name": "mt5_symbols",
        "description": "List available MT5 symbols (optionally filtered by group pattern)",
        "params": {"group": "string"},
        "run": lambda args: mt5.symbols_get(args.get("group", "*")),
    },
    {
        "name": "mt5_tick",
        "description": "Get latest tick (bid/ask) for an MT5 symbol",
        "params": {"symbol": "string"},
        "run": lambda args: mt5.symbol_info_tick(args.get("symbol", "")),
    },
    {
        "name": "mt5_rates",
        "description": "Get historical OHLCV bars from MT5 (timeframe: M1,M5,M15,M30,H1,H4,D1,W1,MN1)",
        "params": {"symbol": "string", "timeframe": "string", "count": "int"},
        "run": lambda args: mt5.copy_rates(args.get("symbol", ""), args.get("timeframe", "M1"), int(args.get("count", 100))),
    },
    {
        "name": "mt5_positions",
        "description": "List open MT5 positions (optionally filtered by symbol)",
        "params": {"symbol": "string"},
        "run": lambda args: mt5.positions_get(args.get("symbol", "")),
    },
    {
        "name": "mt5_orders",
        "description": "List pending MT5 orders",
        "params": {"symbol": "string"},
        "run": lambda args: mt5.orders_get(args.get("symbol", "")),
    },
    {
        "name": "mt5_history_orders",
        "description": "Get MT5 order history for the past N days",
        "params": {"days": "int"},
        "run": lambda args: mt5.history_orders(int(args.get("days", 7))),
    },
    {
        "name": "mt5_history_deals",
        "description": "Get MT5 deal history for the past N days",
        "params": {"days": "int"},
        "run": lambda args: mt5.history_deals(int(args.get("days", 7))),
    },
    {
        "name": "mt5_order_send",
        "description": "Send a trading order to MT5 (requires native or bridge connection)",
        "params": {"request": "object"},
        "run": lambda args: mt5.order_send(args.get("request", {})),
    },
]


def _connect_server(name: str) -> dict:
    try:
        spec = get_server(name)
        from eazzu.mcp.client import MCPClient
        client = MCPClient(endpoint=spec["endpoint"], transport=spec["transport"])
        info = client.initialize()
        tools = client.list_tools()
        client.close()
        return {"server": name, "info": info, "tools": tools, "count": len(tools)}
    except Exception as exc:  # noqa: BLE001
        return {"server": name, "error": str(exc)}


def _call_mcp_tool(server: str, tool: str, arguments: dict) -> dict:
    try:
        spec = get_server(server)
        from eazzu.mcp.client import MCPClient
        client = MCPClient(endpoint=spec["endpoint"], transport=spec["transport"])
        client.initialize()
        result = client.call_tool(tool, arguments)
        client.close()
        return result
    except Exception as exc:  # noqa: BLE001
        return {"server": server, "tool": tool, "error": str(exc)}
