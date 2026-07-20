"""Deriv real-time forex tools — exposes the Deriv public API to the agent.

All tools are market-data only (analysis). No orders are placed and no
account token is required. Uses Deriv's default public app_id (1089).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from eazzu.trading.deriv_api import (
    collect_candles, collect_ticks, get_active_symbols, get_candles,
    get_candles_by_time, get_countries, get_exchange_rates,
    get_landing_company_details, get_payout_currencies, get_proposal,
    get_residence_list, get_tick, get_ticks_history, get_time,
    get_website_status, ping,
)


def _error(code: str, exc: Exception) -> Dict[str, Any]:
    return {"error": code, "message": str(exc)}


def deriv_ping() -> Dict[str, Any]:
    try:
        return ping()
    except Exception as exc:
        return _error("deriv_ping_failed", exc)


def deriv_active_symbols() -> Dict[str, Any]:
    try:
        return get_active_symbols()
    except Exception as exc:
        return _error("deriv_symbols_failed", exc)


def deriv_tick(symbol: str) -> Dict[str, Any]:
    try:
        return get_tick(symbol)
    except Exception as exc:
        return _error("deriv_tick_failed", exc)


def deriv_ticks_history(symbol: str, count: int = 100, style: str = "ticks") -> Dict[str, Any]:
    try:
        return get_ticks_history(symbol, count, style)
    except Exception as exc:
        return _error("deriv_history_failed", exc)


def deriv_candles(symbol: str, count: int = 100, granularity: int = 60) -> Dict[str, Any]:
    try:
        return get_candles(symbol, count, granularity)
    except Exception as exc:
        return _error("deriv_candles_failed", exc)


def deriv_candles_range(symbol: str, start: int, end: int, granularity: int = 60) -> Dict[str, Any]:
    try:
        return get_candles_by_time(symbol, start, end, granularity)
    except Exception as exc:
        return _error("deriv_range_failed", exc)


def deriv_proposal(contract_type: str = "CALL", symbol: str = "R_100",
                   amount: float = 10, basis: str = "stake", currency: str = "USD",
                   duration: int = 5, duration_unit: str = "m") -> Dict[str, Any]:
    try:
        return get_proposal(contract_type, symbol, amount, basis, currency, duration, duration_unit)
    except Exception as exc:
        return _error("deriv_proposal_failed", exc)


def deriv_website_status() -> Dict[str, Any]:
    try:
        return get_website_status()
    except Exception as exc:
        return _error("deriv_status_failed", exc)


def deriv_time() -> Dict[str, Any]:
    try:
        return get_time()
    except Exception as exc:
        return _error("deriv_time_failed", exc)


def deriv_exchange_rates(base: str = "USD") -> Dict[str, Any]:
    try:
        return get_exchange_rates(base)
    except Exception as exc:
        return _error("deriv_rates_failed", exc)


def deriv_residence_list() -> Dict[str, Any]:
    try:
        return get_residence_list()
    except Exception as exc:
        return _error("deriv_residence_failed", exc)


def deriv_payout_currencies() -> Dict[str, Any]:
    try:
        return get_payout_currencies()
    except Exception as exc:
        return _error("deriv_payout_failed", exc)


def deriv_countries() -> Dict[str, Any]:
    try:
        return get_countries()
    except Exception as exc:
        return _error("deriv_countries_failed", exc)


def deriv_landing_company(residence: str = "id") -> Dict[str, Any]:
    try:
        return get_landing_company_details(residence)
    except Exception as exc:
        return _error("deriv_landing_failed", exc)


def deriv_collect_ticks(symbol: str, count: int = 10, timeout: float = 30.0) -> Dict[str, Any]:
    try:
        return collect_ticks(symbol, count, timeout)
    except Exception as exc:
        return _error("deriv_collect_ticks_failed", exc)


def deriv_collect_candles(symbol: str, count: int = 10, granularity: int = 60,
                          timeout: float = 60.0) -> Dict[str, Any]:
    try:
        return collect_candles(symbol, count, granularity, timeout)
    except Exception as exc:
        return _error("deriv_collect_candles_failed", exc)


def deriv_price_snapshot(symbols: List[str]) -> Dict[str, Any]:
    out = {}
    for s in symbols:
        try:
            r = get_tick(s)
            if "tick" in r:
                out[s] = {"quote": r["tick"].get("quote"), "epoch": r["tick"].get("epoch")}
            else:
                out[s] = r
        except Exception as exc:
            out[s] = {"error": str(exc)}
    return {"symbols": out, "count": len(out)}


TOOLS = [
    {"name": "deriv_ping", "description": "Ping the Deriv public API to verify connectivity.",
     "params": {}, "run": deriv_ping},
    {"name": "deriv_active_symbols", "description": "List all tradeable Deriv symbols grouped by market (forex, synthetics, stocks).",
     "params": {}, "run": deriv_active_symbols},
    {"name": "deriv_tick", "description": "Get the latest real-time tick (price quote) for a Deriv symbol (e.g. R_100, frxEURUSD).",
     "params": {"symbol": "string"}, "run": deriv_tick},
    {"name": "deriv_ticks_history", "description": "Retrieve historical ticks or candles for a Deriv symbol.",
     "params": {"symbol": "string", "count": "int", "style": "string"}, "run": deriv_ticks_history},
    {"name": "deriv_candles", "description": "Retrieve real-time OHLC candles for a Deriv symbol. Granularity in seconds (60=1m, 3600=1h).",
     "params": {"symbol": "string", "count": "int", "granularity": "int"}, "run": deriv_candles},
    {"name": "deriv_candles_range", "description": "Retrieve OHLC candles between two epoch timestamps.",
     "params": {"symbol": "string", "start": "int", "end": "int", "granularity": "int"}, "run": deriv_candles_range},
    {"name": "deriv_proposal", "description": "Get a price proposal (analysis-only, does not buy a contract).",
     "params": {"contract_type": "string", "symbol": "string", "amount": "float", "basis": "string",
                "currency": "string", "duration": "int", "duration_unit": "string"}, "run": deriv_proposal},
    {"name": "deriv_website_status", "description": "Get Deriv website status (trading availability, currencies).",
     "params": {}, "run": deriv_website_status},
    {"name": "deriv_time", "description": "Get the current Deriv server time.",
     "params": {}, "run": deriv_time},
    {"name": "deriv_exchange_rates", "description": "Get real-time exchange rates relative to a base currency.",
     "params": {"base": "string"}, "run": deriv_exchange_rates},
    {"name": "deriv_residence_list", "description": "List supported residence countries.",
     "params": {}, "run": deriv_residence_list},
    {"name": "deriv_payout_currencies", "description": "List supported payout currencies.",
     "params": {}, "run": deriv_payout_currencies},
    {"name": "deriv_countries", "description": "List all supported countries.",
     "params": {}, "run": deriv_countries},
    {"name": "deriv_landing_company", "description": "Get landing company details for a residence code.",
     "params": {"residence": "string"}, "run": deriv_landing_company},
    {"name": "deriv_collect_ticks", "description": "Stream and collect N real-time ticks from a Deriv symbol, then stop.",
     "params": {"symbol": "string", "count": "int", "timeout": "float"}, "run": deriv_collect_ticks},
    {"name": "deriv_collect_candles", "description": "Stream and collect N real-time candles from a Deriv symbol, then stop.",
     "params": {"symbol": "string", "count": "int", "granularity": "int", "timeout": "float"},
     "run": deriv_collect_candles},
    {"name": "deriv_price_snapshot", "description": "Fetch the latest tick for multiple Deriv symbols at once.",
     "params": {"symbols": "array[string]"}, "run": deriv_price_snapshot},
]
