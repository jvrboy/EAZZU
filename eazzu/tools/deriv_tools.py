"""Deriv trading tools — real-time forex data via Deriv's public API.

All tools are read-only / analysis-only. No orders are submitted; the
`proposal` tool returns a price quote for a hypothetical contract without
placing it. Requires no authentication (public app_id 1089).
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def _error(code: str, exc: Exception) -> Dict[str, Any]:
    return {"error": code, "message": str(exc)}


def deriv_ping() -> Dict[str, Any]:
    """Check Deriv API reachability and server time."""
    try:
        from eazzu.trading.deriv_client import ping
        return ping()
    except Exception as exc:
        return _error("deriv_ping_failed", exc)


def deriv_server_time() -> Dict[str, Any]:
    """Fetch the current Deriv server time."""
    try:
        from eazzu.trading.deriv_client import server_time
        return server_time()
    except Exception as exc:
        return _error("deriv_time_failed", exc)


def deriv_active_symbols() -> Dict[str, Any]:
    """List all currently active Deriv trading symbols (volatility indices, forex, etc.)."""
    try:
        from eazzu.trading.deriv_client import active_symbols
        return active_symbols()
    except Exception as exc:
        return _error("deriv_symbols_failed", exc)


def deriv_trading_times(date: Optional[str] = None) -> Dict[str, Any]:
    """Return market opening/closing times for a given date (YYYY-MM-DD), or today if omitted."""
    try:
        from eazzu.trading.deriv_client import trading_times
        return trading_times(date)
    except Exception as exc:
        return _error("deriv_trading_times_failed", exc)


def deriv_candles(
    symbol: str = "R_100",
    count: int = 100,
    granularity: int = 60,
) -> Dict[str, Any]:
    """Fetch real-time OHLC candles for a Deriv symbol (e.g. R_100, frxEURUSD).

    granularity is in seconds (60 = 1m, 300 = 5m, 900 = 15m, 3600 = 1h).
    """
    try:
        from eazzu.trading.deriv_client import candles
        return candles(symbol=symbol, count=count, granularity=granularity)
    except Exception as exc:
        return _error("deriv_candles_failed", exc)


def deriv_latest_tick(symbol: str = "R_100") -> Dict[str, Any]:
    """Return the most recent live tick price for a Deriv symbol."""
    try:
        from eazzu.trading.deriv_client import latest_tick
        return latest_tick(symbol)
    except Exception as exc:
        return _error("deriv_tick_failed", exc)


def deriv_proposal(
    contract_type: str = "CALL",
    symbol: str = "R_100",
    amount: float = 1.0,
    currency: str = "USD",
    duration: int = 5,
    duration_unit: str = "m",
    basis: str = "stake",
    barrier: Optional[str] = None,
) -> Dict[str, Any]:
    """Get a price quote (proposal) for a hypothetical contract — no order is placed.

    contract_type: CALL (rise), PUT (fall), DIGITOVER, DIGITUNDER, etc.
    duration_unit: m (minutes), h (hours), d (days), t (ticks).
    basis: 'stake' (amount = stake) or 'payout' (amount = desired payout).
    """
    try:
        from eazzu.trading.deriv_client import proposal
        return proposal(
            contract_type=contract_type,
            symbol=symbol,
            amount=amount,
            currency=currency,
            duration=duration,
            duration_unit=duration_unit,
            basis=basis,
            barrier=barrier,
        )
    except Exception as exc:
        return _error("deriv_proposal_failed", exc)


def deriv_live_analysis(
    symbol: str = "R_100",
    count: int = 200,
    granularity: int = 60,
    min_confidence: float = 0.56,
) -> Dict[str, Any]:
    """Fetch live candles from Deriv and run EAZZU's transparent technical analysis on them."""
    try:
        from eazzu.trading.deriv_client import candles
        from eazzu.trading.intelligence import TechnicalAnalysisEngine, SignalGenerator, AdaptiveSignalTracker

        candle_data = candles(symbol=symbol, count=count, granularity=granularity)
        if "error" in candle_data:
            return candle_data

        bars = candle_data["candles"]
        analysis = TechnicalAnalysisEngine().analyze(bars, symbol=symbol).to_dict()
        tracker = AdaptiveSignalTracker()
        signal = SignalGenerator(tracker=tracker).generate(
            bars, symbol=symbol, min_confidence=min_confidence
        )
        return {
            "symbol": symbol,
            "granularity": granularity,
            "candle_count": len(bars),
            "analysis": analysis,
            "signal": signal,
        }
    except Exception as exc:
        return _error("deriv_live_analysis_failed", exc)


TOOLS = [
    {
        "name": "deriv_ping",
        "description": "Check Deriv API reachability and server time (public, no auth).",
        "params": {},
        "run": deriv_ping,
    },
    {
        "name": "deriv_server_time",
        "description": "Fetch the current Deriv server time.",
        "params": {},
        "run": deriv_server_time,
    },
    {
        "name": "deriv_active_symbols",
        "description": "List all currently active Deriv trading symbols (volatility indices, forex pairs, commodities).",
        "params": {},
        "run": deriv_active_symbols,
    },
    {
        "name": "deriv_trading_times",
        "description": "Return market opening/closing times for a given date (YYYY-MM-DD), or today if omitted.",
        "params": {"date": "string(optional)"},
        "run": deriv_trading_times,
    },
    {
        "name": "deriv_candles",
        "description": "Fetch real-time OHLC candles for a Deriv symbol (e.g. R_100, frxEURUSD). granularity in seconds (60=1m, 300=5m, 3600=1h).",
        "params": {"symbol": "string", "count": "int", "granularity": "int"},
        "run": deriv_candles,
    },
    {
        "name": "deriv_latest_tick",
        "description": "Return the most recent live tick price for a Deriv symbol.",
        "params": {"symbol": "string"},
        "run": deriv_latest_tick,
    },
    {
        "name": "deriv_proposal",
        "description": "Get a price quote (proposal) for a hypothetical Deriv contract — no order is placed.",
        "params": {
            "contract_type": "string", "symbol": "string", "amount": "float",
            "currency": "string", "duration": "int", "duration_unit": "string",
            "basis": "string", "barrier": "string(optional)",
        },
        "run": deriv_proposal,
    },
    {
        "name": "deriv_live_analysis",
        "description": "Fetch live candles from Deriv and run EAZZU's transparent technical analysis + signal generation on them.",
        "params": {"symbol": "string", "count": "int", "granularity": "int", "min_confidence": "float"},
        "run": deriv_live_analysis,
    },
]
