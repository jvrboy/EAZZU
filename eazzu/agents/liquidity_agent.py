"""Liquidity Flow Agent — detects liquidity zones, stop hunts, order flow imbalance.

Converted from infinite-loop-sound's liquidity-agent.ts.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

from eazzu.agents.types import AgentResult


def run_liquidity_agent(
    pair: str,
    timeframe: str,
    candles: List[Dict[str, Any]],
) -> AgentResult:
    start = time.time()
    zones: List[Dict[str, Any]] = []
    recent = candles[-50:]

    for i in range(5, len(recent) - 2):
        c = recent[i]
        nxt = recent[i + 1]
        upper_wick = max(c["high"] - max(c["open"], c["close"]), 0)
        lower_wick = max(min(c["open"], c["close"]) - c["low"], 0)
        body = abs(c["close"] - c["open"])

        if upper_wick > body * 2 and nxt["close"] < c["high"]:
            zones.append({
                "price": c["high"],
                "type": "sell-side",
                "strength": upper_wick / (body + 0.001),
                "lastTested": c.get("epoch", 0),
                "swept": nxt["high"] > c["high"],
            })
        if lower_wick > body * 2 and nxt["close"] > c["low"]:
            zones.append({
                "price": c["low"],
                "type": "buy-side",
                "strength": lower_wick / (body + 0.001),
                "lastTested": c.get("epoch", 0),
                "swept": nxt["low"] < c["low"],
            })

    buy_side = [z for z in zones if z["type"] == "buy-side"]
    sell_side = [z for z in zones if z["type"] == "sell-side"]
    if buy_side and sell_side:
        if len(buy_side) > len(sell_side) * 1.3:
            flow = "bullish"
        elif len(sell_side) > len(buy_side) * 1.3:
            flow = "bearish"
        else:
            flow = "neutral"
    else:
        flow = "neutral"

    swept = [z for z in zones if z["swept"]]
    stop_hunt = len(swept) >= 2
    imbalance = (len(buy_side) - len(sell_side)) / max(len(zones), 1)

    return AgentResult(
        agent_id="liquidity-agent",
        status="completed",
        timestamp=time.time() * 1000,
        output={
            "zones": zones,
            "stopHunt": stop_hunt,
            "flowDirection": flow,
            "imbalance": imbalance,
        },
        insights=[
            f"{len(zones)} liquidity zones found. Flow: {flow}. "
            f"Stop hunt: {'YES' if stop_hunt else 'no'}."
        ],
        duration=(time.time() - start) * 1000,
    )
