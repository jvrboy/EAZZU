"""Deriv real-time forex client — public API, no auth required.

Connects to Deriv's public WebSocket endpoint (wss://ws.derivws.com/websockets/v3)
using the shared app_id 1089. Provides ticks, candles, active symbols, proposal
prices, and trading-times lookups. Falls back to the REST proxy at
https://api.deriv.com when the optional `websocket-client` package is absent.
"""
from __future__ import annotations

import json
import time
import uuid
from typing import Any, Dict, List, Optional

from urllib.parse import urlencode
from urllib.request import Request, urlopen

PUBLIC_WS_URL = "wss://ws.derivws.com/websockets/v3?app_id=1089"
PUBLIC_REST_URL = "https://api.deriv.com"
DEFAULT_APP_ID = "1089"


def _rest_request(payload: Dict[str, Any], timeout: int = 15) -> Dict[str, Any]:
    """Send a Deriv API call via the public REST proxy."""
    req_id = payload.get("req_id") or uuid.uuid4().hex[:8]
    payload = {**payload, "req_id": req_id}
    url = f"{PUBLIC_REST_URL}?{urlencode(payload)}"
    req = Request(url, headers={"User-Agent": "eazzu/1.0"})
    with urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def _ws_request(payload: Dict[str, Any], timeout: int = 20) -> Optional[Dict[str, Any]]:
    """Send a single Deriv API call over WebSocket and return the first matching reply."""
    try:
        import websocket  # type: ignore
    except ImportError:
        return None

    req_id = payload.get("req_id") or uuid.uuid4().hex[:8]
    payload = {**payload, "req_id": req_id}
    ws = websocket.create_connection(PUBLIC_WS_URL, timeout=timeout)
    try:
        ws.send(json.dumps(payload))
        deadline = time.time() + timeout
        while time.time() < deadline:
            raw = ws.recv()
            if not raw:
                continue
            data = json.loads(raw)
            if data.get("req_id") == req_id:
                return data
        return None
    finally:
        ws.close()


def _deriv_call(payload: Dict[str, Any], timeout: int = 15) -> Dict[str, Any]:
    """Prefer WebSocket; fall back to REST proxy."""
    result = _ws_request(payload, timeout=timeout)
    if result is not None:
        return result
    return _rest_request(payload, timeout=timeout)


# ─── Public market-data functions ───────────────────────────────────────


def ping() -> Dict[str, Any]:
    """Check Deriv API reachability and server time."""
    return _deriv_call({"ping": 1})


def server_time() -> Dict[str, Any]:
    """Fetch the current Deriv server time."""
    return _deriv_call({"time": 1})


def active_symbols() -> Dict[str, Any]:
    """List all currently active trading symbols."""
    return _deriv_call({"active_symbols": "brief", "product_type": "basic"})


def trading_times(date: Optional[str] = None) -> Dict[str, Any]:
    """Return market opening/closing times for a given date (YYYY-MM-DD)."""
    payload: Dict[str, Any] = {"trading_times": date or ""}
    return _deriv_call(payload)


def ticks_history(
    symbol: str = "R_100",
    count: int = 100,
    end: str = "latest",
    style: str = "ticks",
    granularity: int = 60,
    subscribe: int = 0,
) -> Dict[str, Any]:
    """Fetch historical tick or candle data for a symbol.

    style="ticks" returns individual ticks; style="candles" returns OHLC bars
    at the given granularity (in seconds).
    """
    payload = {
        "ticks_history": symbol,
        "count": count,
        "end": end,
        "style": style,
        "granularity": granularity,
        "subscribe": subscribe,
    }
    return _deriv_call(payload)


def candles(
    symbol: str = "R_100",
    count: int = 100,
    granularity: int = 60,
    end: str = "latest",
) -> Dict[str, Any]:
    """Convenience wrapper returning OHLC candles as a list of dicts."""
    raw = ticks_history(symbol, count=count, end=end, style="candles", granularity=granularity)
    if "error" in raw:
        return raw
    candles_list = raw.get("candles", [])
    return {
        "symbol": symbol,
        "granularity": granularity,
        "count": len(candles_list),
        "candles": [
            {
                "timestamp": c.get("epoch"),
                "open": float(c.get("open", 0)),
                "high": float(c.get("high", 0)),
                "low": float(c.get("low", 0)),
                "close": float(c.get("close", 0)),
                "volume": float(c.get("volume", 0)),
            }
            for c in candles_list
        ],
    }


def latest_tick(symbol: str = "R_100") -> Dict[str, Any]:
    """Return the most recent tick for a symbol."""
    raw = ticks_history(symbol, count=1, end="latest", style="ticks")
    if "error" in raw:
        return raw
    prices = raw.get("prices", [])
    times = raw.get("times", [])
    return {
        "symbol": symbol,
        "price": float(prices[-1]) if prices else None,
        "epoch": times[-1] if times else None,
        "pip_size": raw.get("pip_size"),
    }


def proposal(
    contract_type: str = "CALL",
    symbol: str = "R_100",
    amount: float = 1.0,
    currency: str = "USD",
    duration: int = 5,
    duration_unit: str = "m",
    basis: str = "stake",
    barrier: Optional[str] = None,
) -> Dict[str, Any]:
    """Get a price quote (proposal) for a hypothetical contract — no order placed."""
    payload: Dict[str, Any] = {
        "proposal": 1,
        "contract_type": contract_type,
        "symbol": symbol,
        "amount": amount,
        "currency": currency,
        "duration": duration,
        "duration_unit": duration_unit,
        "basis": basis,
    }
    if barrier:
        payload["barrier"] = barrier
    return _deriv_call(payload)


__all__ = [
    "ping", "server_time", "active_symbols", "trading_times",
    "ticks_history", "candles", "latest_tick", "proposal",
]
