"""Trading and market-analysis tools exposed to the EAZZU agent.

All functions are analysis-only. They accept caller-supplied candle data, do not
fetch market prices, and cannot submit broker orders or calculate a position size.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, Optional


def _error(code: str, exc: Exception) -> Dict[str, Any]:
    return {"error": code, "message": str(exc)}


def list_strategies() -> Dict[str, Any]:
    """List bundled strategy lineages and safe analysis capabilities."""
    return {
        "scalpers": [
            "deriv_scalper (Bot2 lineage — modular EMA/RSI + risk manager)",
            "deriv_perpetual_scalper (multi-indicator confluence)",
            "deriv_v75_scalper (Volatility-75 tuned)",
        ],
        "signal": [
            "deriv_signal_bot (legacy agentic trend, momentum, volatility components)",
            "eazzu_intelligence (transparent multi-domain confluence + adaptive outcome tracker)",
        ],
        "analysis": [
            "trend and EMA alignment",
            "market structure and break-of-structure",
            "momentum and oscillator context",
            "volatility and ATR-based protective levels",
            "candlestick price action, liquidity sweeps, and observed-volume context",
            "packaged instrument and session reference context",
        ],
        "streams": ["forexstream (async tick stream + storage)"],
        "note": "Analysis and signal tools do not execute orders. Use caller-supplied candles and review the result independently.",
    }


def backtest_strategy(strategy: str = "deriv_scalper", symbol: str = "R_75", days: int = 30) -> Dict[str, Any]:
    """Prepare a legacy backtest invocation without running it or placing orders."""
    return {
        "strategy": strategy,
        "symbol": symbol,
        "days": days,
        "command": f"eazzu trade backtest --strategy {strategy} --symbol {symbol} --days {days}",
        "note": "Legacy backtest engines live under eazzu.trading.*; this wrapper does not run heavy jobs autonomously.",
    }


def list_trading_knowledge() -> Dict[str, Any]:
    """List and validate the JSON knowledge documents packaged with EAZZU."""
    try:
        from eazzu.trading.intelligence import KnowledgeBase

        knowledge = KnowledgeBase()
        return {"validation": knowledge.validate(), "documents": knowledge.documents()}
    except Exception as exc:  # pragma: no cover - defensive agent boundary
        return _error("knowledge_unavailable", exc)


def analyze_market(
    candles: Iterable[Dict[str, Any]],
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze supplied OHLCV candles across several independent technical domains."""
    try:
        from eazzu.trading.intelligence import TechnicalAnalysisEngine

        return TechnicalAnalysisEngine().analyze(candles, symbol=symbol, timeframe=timeframe).to_dict()
    except Exception as exc:
        return _error("analysis_failed", exc)


def generate_signal(
    candles: Iterable[Dict[str, Any]],
    symbol: Optional[str] = None,
    timeframe: Optional[str] = None,
    min_confidence: float = 0.56,
    risk_multiple: float = 1.5,
    reward_multiple: float = 2.0,
    expiry_bars: int = 12,
    ledger_path: Optional[str] = None,
    record: bool = True,
) -> Dict[str, Any]:
    """Generate and optionally record a transparent, analysis-only signal."""
    try:
        from eazzu.trading.intelligence import AdaptiveSignalTracker, SignalGenerator

        tracker = AdaptiveSignalTracker(ledger_path)
        result = SignalGenerator(tracker=tracker).generate(
            candles,
            symbol=symbol,
            timeframe=timeframe,
            min_confidence=float(min_confidence),
            risk_multiple=float(risk_multiple),
            reward_multiple=float(reward_multiple),
            expiry_bars=int(expiry_bars),
        )
        if result.get("signal") and record:
            result["tracking"] = tracker.record_signal(result["signal"])
        else:
            result["tracking"] = {"recorded": False, "reason": "no_signal" if not result.get("signal") else "record_disabled"}
        return result
    except Exception as exc:
        return _error("signal_generation_failed", exc)


def resolve_signal(
    signal_id: str,
    future_candles: Iterable[Dict[str, Any]],
    ledger_path: Optional[str] = None,
) -> Dict[str, Any]:
    """Resolve one recorded signal against subsequent OHLCV candles and learn only from clear outcomes."""
    try:
        from eazzu.trading.intelligence import AdaptiveSignalTracker

        return AdaptiveSignalTracker(ledger_path).resolve_signal(signal_id, future_candles)
    except Exception as exc:
        return _error("signal_resolution_failed", exc)


def signal_tracker_summary(ledger_path: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    """Return outcome statistics and bounded per-evidence learning state."""
    try:
        from eazzu.trading.intelligence import AdaptiveSignalTracker

        tracker = AdaptiveSignalTracker(ledger_path)
        return {"summary": tracker.summary(), "recent_signals": tracker.list_signals(int(limit))}
    except Exception as exc:
        return _error("signal_tracker_unavailable", exc)


TOOLS = [
    {
        "name": "list_strategies",
        "description": "List bundled strategy lineages and analysis-only trading capabilities.",
        "params": {},
        "run": list_strategies,
    },
    {
        "name": "backtest_strategy",
        "description": "Prepare a bundled strategy backtest invocation without executing a broker order.",
        "params": {"strategy": "string", "symbol": "string", "days": "int"},
        "run": backtest_strategy,
    },
    {
        "name": "list_trading_knowledge",
        "description": "List and validate EAZZU's packaged trading-reference JSON documents.",
        "params": {},
        "run": list_trading_knowledge,
    },
    {
        "name": "analyze_market",
        "description": "Run transparent technical, structure, price-action, liquidity, volatility, and volume analysis on supplied OHLCV candles.",
        "params": {"candles": "array[object]", "symbol": "string(optional)", "timeframe": "string(optional)"},
        "run": analyze_market,
    },
    {
        "name": "generate_signal",
        "description": "Generate an analysis-only confluence signal from supplied OHLCV candles and optionally record it for later evaluation.",
        "params": {
            "candles": "array[object]",
            "symbol": "string(optional)",
            "timeframe": "string(optional)",
            "min_confidence": "float(optional)",
            "risk_multiple": "float(optional)",
            "reward_multiple": "float(optional)",
            "expiry_bars": "int(optional)",
            "ledger_path": "string(optional)",
            "record": "bool(optional)",
        },
        "run": generate_signal,
    },
    {
        "name": "resolve_signal",
        "description": "Evaluate a previously recorded signal against subsequent candles and update adaptive statistics only for clear outcomes.",
        "params": {"signal_id": "string", "future_candles": "array[object]", "ledger_path": "string(optional)"},
        "run": resolve_signal,
    },
    {
        "name": "signal_tracker_summary",
        "description": "Show signal outcomes, evidence-performance statistics, and the bounded learning state.",
        "params": {"ledger_path": "string(optional)", "limit": "int(optional)"},
        "run": signal_tracker_summary,
    },
]
