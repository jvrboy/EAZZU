"""Trading / market tools — thin, safe wrappers so the LLM can inspect them
without triggering live orders. Live execution stays behind explicit CLI
sub-commands (`eazzu trade ...`)."""
from __future__ import annotations

from typing import Any


def list_strategies() -> dict[str, Any]:
    return {
        "scalpers": [
            "deriv_scalper (Bot2 lineage — modular EMA/RSI + risk manager)",
            "deriv_perpetual_scalper (multi-indicator confluence)",
            "deriv_v75_scalper (Volatility-75 tuned)",
        ],
        "signal": [
            "deriv_signal_bot (agentic — trend, momentum, volatility agents)",
            "deriv-btcusd-signal-tool (neural + memory)",
        ],
        "streams": ["forexstream (async tick stream + storage)"],
        "note": "Run backtest_strategy for a dry run; live trading needs `eazzu trade live` with `--i-understand-risk`.",
    }


def backtest_strategy(strategy: str = "deriv_scalper", symbol: str = "R_75", days: int = 30) -> dict[str, Any]:
    """Kick off a backtest — placeholder that reports how to invoke the real one."""
    return {
        "strategy": strategy,
        "symbol": symbol,
        "days": days,
        "command": f"eazzu trade backtest --strategy {strategy} --symbol {symbol} --days {days}",
        "note": "Backtest engines live under eazzu.trading.*; this stub keeps the LLM from running heavy jobs autonomously.",
    }


TOOLS = [
    {"name": "list_strategies", "description": "List built-in trading strategies bundled with EAZZU.",
     "params": {}, "run": list_strategies},
    {"name": "backtest_strategy",
     "description": "Prepare a backtest of a bundled strategy (does not execute live orders).",
     "params": {"strategy": "string", "symbol": "string", "days": "int"},
     "run": backtest_strategy},
]
