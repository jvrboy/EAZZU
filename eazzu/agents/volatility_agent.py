"""Volatility Regime Agent — ATR/Bollinger regime classification and forecast.

Converted from infinite-loop-sound's volatility-agent.ts.
"""
from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional

from eazzu.agents.types import AgentResult


def _atr(candles: List[Dict[str, Any]], period: int = 14) -> List[float]:
    trs: List[float] = []
    for i in range(1, len(candles)):
        c = candles[i]
        prev = candles[i - 1]
        tr = max(
            c["high"] - c["low"],
            abs(c["high"] - prev["close"]),
            abs(c["low"] - prev["close"]),
        )
        trs.append(tr)
    atrs: List[float] = []
    for i in range(period - 1, len(trs)):
        atrs.append(sum(trs[i - period + 1 : i + 1]) / period)
    return atrs


def _bollinger_width(candles: List[Dict[str, Any]], period: int = 20) -> float:
    slice_ = candles[-period:]
    closes = [c["close"] for c in slice_]
    if not closes:
        return 0.0
    mean = sum(closes) / len(closes)
    variance = sum((c - mean) ** 2 for c in closes) / len(closes)
    std = math.sqrt(variance)
    return (4 * std) / (mean or 1.0)


def run_volatility_agent(
    pair: str,
    timeframe: str,
    candles: List[Dict[str, Any]],
) -> AgentResult:
    start = time.time()
    if len(candles) < 35:
        return AgentResult(
            agent_id="volatility-agent",
            status="completed",
            timestamp=time.time() * 1000,
            output={"regime": "normal", "atrPercentile": 0, "bbWidth": 0, "forecast": "stable", "recommendedSize": 1.0},
            insights=["Insufficient candles for volatility analysis"],
            duration=(time.time() - start) * 1000,
        )

    period = 14
    atrs = _atr(candles, period)
    current_atr = atrs[-1] if atrs else 0.0
    sorted_atrs = sorted(atrs)
    rank = sorted_atrs.index(current_atr) if current_atr in sorted_atrs else 0
    atr_percentile = round((rank / max(len(sorted_atrs), 1)) * 100)

    bb_width = _bollinger_width(candles, 20)

    regime = "normal"
    if atr_percentile > 90:
        regime = "extreme"
    elif atr_percentile > 70:
        regime = "expansion"
    elif atr_percentile < 20:
        regime = "contraction"

    recent = atrs[-5:]
    trend = recent[-1] - recent[0] if len(recent) >= 2 else 0.0
    if current_atr > 0:
        if trend > current_atr * 0.1:
            forecast = "expanding"
        elif trend < -current_atr * 0.1:
            forecast = "contracting"
        else:
            forecast = "stable"
    else:
        forecast = "stable"

    size = {"extreme": 0.5, "expansion": 0.75, "contraction": 1.25, "normal": 1.0}[regime]

    return AgentResult(
        agent_id="volatility-agent",
        status="completed",
        timestamp=time.time() * 1000,
        output={
            "regime": regime,
            "atrPercentile": atr_percentile,
            "bbWidth": bb_width,
            "forecast": forecast,
            "recommendedSize": size,
        },
        insights=[
            f"Volatility: {regime} (ATR {atr_percentile}th pctile). "
            f"Forecast: {forecast}. Size multiplier: {size}x."
        ],
        duration=(time.time() - start) * 1000,
    )
