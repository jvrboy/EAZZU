"""Execution Flow Agent — spread/slippage analysis and optimal execution strategy.

Converted from infinite-loop-sound's execution-flow-agent.ts.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

from eazzu.agents.types import AgentResult


def run_execution_flow_agent(
    pair: str,
    candles: List[Dict[str, Any]],
    ticks: List[Dict[str, Any]],
) -> AgentResult:
    start = time.time()
    recent_ticks = ticks[-100:]
    spreads = [t["ask"] - t["bid"] for t in recent_ticks if t.get("bid") and t.get("ask") and t["ask"] > t["bid"]]
    avg_spread = sum(spreads) / len(spreads) if spreads else 0.0
    spread_score = max(0, round(100 - avg_spread * 10000))

    recent_candles = candles[-20:]
    ranges = [c["high"] - c["low"] for c in recent_candles]
    avg_range = sum(ranges) / max(len(ranges), 1)
    last_range = ranges[-1] if ranges else 0.0
    vol_ratio = last_range / avg_range if avg_range > 0 else 1.0

    if vol_ratio > 2:
        slippage = "high"
    elif vol_ratio > 1.3:
        slippage = "medium"
    else:
        slippage = "low"

    now = int(time.time())
    window = {"startEpoch": now, "endEpoch": now + 300}

    if slippage == "high":
        strategy = "limit"
    elif slippage == "medium":
        strategy = "twap"
    elif spread_score < 50:
        strategy = "iceberg"
    else:
        strategy = "market"

    urgency = round(max(0, min(100, (100 - spread_score) + vol_ratio * 20)))

    return AgentResult(
        agent_id="execution-flow-agent",
        status="completed",
        timestamp=time.time() * 1000,
        output={
            "optimalWindow": window,
            "recommendedStrategy": strategy,
            "spreadScore": spread_score,
            "slippageRisk": slippage,
            "urgency": urgency,
        },
        insights=[
            f"Execution: {strategy} order. Spread score: {spread_score}/100. "
            f"Slippage risk: {slippage}. Urgency: {urgency}/100."
        ],
        duration=(time.time() - start) * 1000,
    )
