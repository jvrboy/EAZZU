"""MetaTrader 5 (MT5) MCP adapter — account, orders, positions, history.

MetaTrader 5 provides a Python package (``MetaTrader5``) that connects to a
local MT5 terminal on Windows. On other platforms (iOS/iSH, Linux without
Wine), the native package is unavailable, so this adapter:

  1. Attempts to import ``MetaTrader5`` — if available, all live functions work.
  2. If unavailable, falls back to a REST bridge mode: set ``MT5_BRIDGE_URL``
     to point at a machine running the MT5 terminal + bridge server.
  3. If neither is available, returns informative errors so the agent can
     degrade gracefully.

No third-party dependencies are required for the REST bridge mode.
"""
from __future__ import annotations

import json
import os
import urllib.request
import urllib.error
from typing import Optional

_BRIDGE_URL = os.environ.get("MT5_BRIDGE_URL", "").rstrip("/")
_MT5_AVAILABLE = False

try:
    import MetaTrader5 as _mt5  # type: ignore
    _MT5_AVAILABLE = True
except ImportError:
    _mt5 = None  # type: ignore


def _available() -> bool:
    return _MT5_AVAILABLE or bool(_BRIDGE_URL)


def _bridge_get(path: str, timeout: float = 30) -> dict:
    if not _BRIDGE_URL:
        return {"error": "MT5 not available: install MetaTrader5 package or set MT5_BRIDGE_URL"}
    url = f"{_BRIDGE_URL}/{path.lstrip('/')}"
    token = os.environ.get("MT5_TOKEN", "")
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"error": f"HTTP {exc.code}", "detail": exc.read().decode("utf-8", errors="replace")[:500]}
    except urllib.error.URLError as exc:
        return {"error": str(exc)}


def _bridge_post(path: str, body: dict, timeout: float = 30) -> dict:
    if not _BRIDGE_URL:
        return {"error": "MT5 not available: install MetaTrader5 package or set MT5_BRIDGE_URL"}
    url = f"{_BRIDGE_URL}/{path.lstrip('/')}"
    token = os.environ.get("MT5_TOKEN", "")
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {token}"} if token else {"Content-Type": "application/json"}
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"error": f"HTTP {exc.code}", "detail": exc.read().decode("utf-8", errors="replace")[:500]}
    except urllib.error.URLError as exc:
        return {"error": str(exc)}


def initialize() -> dict:
    if _MT5_AVAILABLE:
        ok = _mt5.initialize()
        return {"initialized": ok, "mode": "native"}
    return _bridge_get("initialize")


def shutdown() -> dict:
    if _MT5_AVAILABLE:
        _mt5.shutdown()
        return {"shutdown": True, "mode": "native"}
    return _bridge_get("shutdown")


def account_info() -> dict:
    if _MT5_AVAILABLE:
        info = _mt5.account_info()
        if info is None:
            return {"error": "no account info — terminal not connected"}
        return info._asdict()
    return _bridge_get("account")


def terminal_info() -> dict:
    if _MT5_AVAILABLE:
        info = _mt5.terminal_info()
        if info is None:
            return {"error": "no terminal info"}
        return info._asdict()
    return _bridge_get("terminal")


def symbols_total() -> dict:
    if _MT5_AVAILABLE:
        return {"total": _mt5.symbols_total()}
    return _bridge_get("symbols/total")


def symbols_get(group: str = "*") -> dict:
    if _MT5_AVAILABLE:
        syms = _mt5.symbols_get(group)
        if syms is None:
            return {"error": "no symbols"}
        return {"symbols": [s._asdict() for s in syms[:100]], "count": len(syms)}
    return _bridge_get(f"symbols?group={group}")


def symbol_info_tick(symbol: str) -> dict:
    if _MT5_AVAILABLE:
        tick = _mt5.symbol_info_tick(symbol)
        if tick is None:
            return {"error": f"no tick for {symbol}"}
        return tick._asdict()
    return _bridge_get(f"tick?symbol={symbol}")


def symbol_info(symbol: str) -> dict:
    if _MT5_AVAILABLE:
        info = _mt5.symbol_info(symbol)
        if info is None:
            return {"error": f"unknown symbol {symbol}"}
        return info._asdict()
    return _bridge_get(f"symbol?name={symbol}")


def copy_rates(symbol: str, timeframe: str = "M1", count: int = 100) -> dict:
    """Get historical OHLCV bars. timeframe: M1,M5,M15,M30,H1,H4,D1,W1,MN1."""
    tf_map = {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60, "H4": 240, "D1": 1440, "W1": 10080, "MN1": 43200}
    tf = tf_map.get(timeframe.upper(), 1)
    if _MT5_AVAILABLE:
        rates = _mt5.copy_rates_from_pos(symbol, tf, 0, count)
        if rates is None:
            return {"error": f"no rates for {symbol}"}
        return {"symbol": symbol, "timeframe": timeframe, "candles": [dict(r) for r in rates], "count": len(rates)}
    return _bridge_get(f"rates?symbol={symbol}&timeframe={timeframe}&count={count}")


def positions_total() -> dict:
    if _MT5_AVAILABLE:
        return {"total": _mt5.positions_total()}
    return _bridge_get("positions/total")


def positions_get(symbol: str = "") -> dict:
    if _MT5_AVAILABLE:
        pos = _mt5.positions_get(symbol=symbol) if symbol else _mt5.positions_get()
        if pos is None:
            return {"positions": [], "count": 0}
        return {"positions": [p._asdict() for p in pos], "count": len(pos)}
    return _bridge_get(f"positions?symbol={symbol}")


def orders_total() -> dict:
    if _MT5_AVAILABLE:
        return {"total": _mt5.orders_total()}
    return _bridge_get("orders/total")


def orders_get(symbol: str = "") -> dict:
    if _MT5_AVAILABLE:
        orders = _mt5.orders_get(symbol=symbol) if symbol else _mt5.orders_get()
        if orders is None:
            return {"orders": [], "count": 0}
        return {"orders": [o._asdict() for o in orders], "count": len(orders)}
    return _bridge_get(f"orders?symbol={symbol}")


def history_orders(from_days: int = 7) -> dict:
    if _MT5_AVAILABLE:
        from datetime import datetime, timedelta
        start = datetime.now() - timedelta(days=from_days)
        orders = _mt5.history_orders_get(start, datetime.now())
        if orders is None:
            return {"orders": [], "count": 0}
        return {"orders": [o._asdict() for o in orders], "count": len(orders)}
    return _bridge_get(f"history/orders?days={from_days}")


def history_deals(from_days: int = 7) -> dict:
    if _MT5_AVAILABLE:
        from datetime import datetime, timedelta
        start = datetime.now() - timedelta(days=from_days)
        deals = _mt5.history_deals_get(start, datetime.now())
        if deals is None:
            return {"deals": [], "count": 0}
        return {"deals": [d._asdict() for d in deals], "count": len(deals)}
    return _bridge_get(f"history/deals?days={from_days}")


def order_send(request: dict) -> dict:
    """Send a trading order. request must contain action, symbol, volume, type, etc."""
    if _MT5_AVAILABLE:
        result = _mt5.order_send(request)
        if result is None:
            return {"error": "order_send failed"}
        return result._asdict()
    return _bridge_post("order", request)
