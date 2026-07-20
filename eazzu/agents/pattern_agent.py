"""Pattern Recognition Agent — candlestick + indicator pattern detection.

Converted from infinite-loop-sound's pattern-agent.ts. Uses lightweight inline
indicators (RSI, MACD, ATR, Bollinger) to avoid heavy numpy dependencies so
the module imports cleanly on iSH/Alpine.
"""
from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional

from eazzu.agents.types import AgentResult


def _rsi(closes: List[float], period: int = 14) -> List[float]:
    if len(closes) < period + 1:
        return [50.0] * len(closes)
    gains: List[float] = []
    losses: List[float] = []
    for i in range(1, len(closes)):
        diff = closes[i] - closes[i - 1]
        gains.append(max(diff, 0.0))
        losses.append(max(-diff, 0.0))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    rsis: List[float] = []
    for i in range(period, len(closes)):
        if i > period:
            avg_gain = (avg_gain * (period - 1) + gains[i - 1]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i - 1]) / period
        rs = avg_gain / avg_loss if avg_loss > 0 else 100.0
        rsis.append(100.0 - 100.0 / (1.0 + rs))
    return rsis


def _macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, List[float]]:
    def ema(values: List[float], period: int) -> List[float]:
        k = 2.0 / (period + 1)
        emas: List[float] = [values[0]] if values else []
        for v in values[1:]:
            emas.append(v * k + emas[-1] * (1 - k))
        return emas

    if len(closes) < slow:
        return {"macd": [], "signal": [], "hist": []}
    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = ema(macd_line, signal) if len(macd_line) >= signal else []
    hist = [m - s for m, s in zip(macd_line[-len(signal_line):], signal_line)]
    return {"macd": macd_line, "signal": signal_line, "hist": hist}


def _heikin_ashi(candles: List[Dict[str, Any]]) -> List[Dict[str, float]]:
    ha: List[Dict[str, float]] = []
    for i, c in enumerate(candles):
        close = (c["open"] + c["high"] + c["low"] + c["close"]) / 4
        if i == 0:
            op = c["open"]
        else:
            op = (ha[i - 1]["open"] + ha[i - 1]["close"]) / 2
        hi = max(c["high"], op, close)
        lo = min(c["low"], op, close)
        ha.append({"open": op, "high": hi, "low": lo, "close": close})
    return ha


def _clamp(n: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, n))


def _detect_engulfing(candles: List[Dict[str, Any]]) -> Optional[str]:
    if len(candles) < 2:
        return None
    c = candles[-1]
    p = candles[-2]
    bull = p["close"] < p["open"] and c["close"] > c["open"] and c["close"] >= p["open"] and c["open"] <= p["close"]
    bear = p["close"] > p["open"] and c["close"] < c["open"] and c["close"] <= p["open"] and c["open"] >= p["close"]
    if bull:
        return "bull"
    if bear:
        return "bear"
    return None


def _detect_pin_bar(candles: List[Dict[str, Any]]) -> Optional[str]:
    if len(candles) < 2:
        return None
    c = candles[-1]
    body = abs(c["close"] - c["open"])
    upper = max(c["high"] - max(c["open"], c["close"]), 0)
    lower = max(min(c["open"], c["close"]) - c["low"], 0)
    if lower > body * 2 and upper < body:
        return "bull"
    if upper > body * 2 and lower < body:
        return "bear"
    return None


def _is_doji(candles: List[Dict[str, Any]]) -> bool:
    if not candles:
        return False
    c = candles[-1]
    body = abs(c["close"] - c["open"])
    rng = c["high"] - c["low"]
    return rng > 0 and body <= rng * 0.1


def run_pattern_agent(
    pair: str,
    timeframe: str,
    candles: List[Dict[str, Any]],
) -> AgentResult:
    start = time.time()
    patterns: List[Dict[str, Any]] = []

    if len(candles) < 35:
        return AgentResult(
            agent_id="pattern-agent",
            status="completed",
            timestamp=time.time() * 1000,
            output={"patterns": [], "compositeBias": "neutral", "compositeScore": 0},
            insights=["Insufficient candles for pattern scan"],
            duration=(time.time() - start) * 1000,
        )

    closes = [c["close"] for c in candles]
    last = len(closes) - 1

    eng = _detect_engulfing(candles)
    if eng:
        patterns.append({"name": "Engulfing", "bias": eng, "confidence": 72, "category": "candlestick", "note": f"{eng} engulfing on last bar"})
    pin = _detect_pin_bar(candles)
    if pin:
        patterns.append({"name": "Pin Bar", "bias": pin, "confidence": 68, "category": "candlestick", "note": f"{pin} pin-bar rejection"})
    if _is_doji(candles):
        patterns.append({"name": "Doji", "bias": "neutral", "confidence": 55, "category": "candlestick", "note": "Indecision at current levels"})

    rsi_vals = _rsi(closes, 14)
    r = rsi_vals[-1] if rsi_vals else 50.0
    if r < 30:
        patterns.append({"name": "RSI Oversold", "bias": "bull", "confidence": _clamp(50 + (30 - r)), "category": "momentum", "note": f"RSI {r:.1f} — oversold"})
    elif r > 70:
        patterns.append({"name": "RSI Overbought", "bias": "bear", "confidence": _clamp(50 + (r - 70)), "category": "momentum", "note": f"RSI {r:.1f} — overbought"})

    macd_vals = _macd(closes)
    hist = macd_vals["hist"][-1] if macd_vals["hist"] else 0.0
    if abs(hist) > 0:
        patterns.append({
            "name": "MACD Histogram",
            "bias": "bull" if hist > 0 else "bear",
            "confidence": _clamp(50 + math.tanh(hist * 200) * 30),
            "category": "momentum",
            "note": f"MACD hist {'positive' if hist > 0 else 'negative'}",
        })

    ha = _heikin_ashi(candles)
    if len(ha) >= 3:
        last_ha = ha[-1]
        prev_ha = ha[-2]
        if last_ha["close"] > last_ha["open"] and last_ha["close"] > prev_ha["close"]:
            ha_trend = "up"
        elif last_ha["close"] < last_ha["open"] and last_ha["close"] < prev_ha["close"]:
            ha_trend = "down"
        else:
            ha_trend = "flat"
    else:
        ha_trend = "flat"

    patterns.sort(key=lambda p: p["confidence"], reverse=True)

    weights = {"candlestick": 1.2, "trend": 1.0, "momentum": 0.8, "volatility": 0.6}
    weighted = 0.0
    total_w = 0.0
    for p in patterns:
        w = weights.get(p["category"], 1.0) * (p["confidence"] / 100.0)
        d = 1 if p["bias"] == "bull" else -1 if p["bias"] == "bear" else 0
        weighted += d * w
        total_w += w
    composite = round((weighted / total_w) * 100) if total_w > 0 else 0
    bias = "bull" if composite > 15 else "bear" if composite < -15 else "neutral"

    return AgentResult(
        agent_id="pattern-agent",
        status="completed",
        timestamp=time.time() * 1000,
        output={
            "patterns": patterns,
            "compositeBias": bias,
            "compositeScore": composite,
            "haTrend": ha_trend,
        },
        insights=[
            f"{len(patterns)} patterns detected. Composite: {bias} ({composite:+d}). HA trend: {ha_trend}."
        ],
        duration=(time.time() - start) * 1000,
    )
