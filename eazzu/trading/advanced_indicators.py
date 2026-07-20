"""Advanced technical indicators — pure math, no I/O.

Converted from infinite-loop-sound's advanced-indicators.ts. Contains indicators
not in the base pattern_agent module: Aroon, TTM Squeeze, Choppiness Index,
Williams %R, CCI, OBV, Vortex, MFI, Awesome Oscillator, and a composite
advanced score. All inputs are candle dicts with keys: open, high, low, close,
volume, epoch.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


def _sma(values: List[float], period: int) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(values)
    for i in range(period - 1, len(values)):
        out[i] = sum(values[i - period + 1 : i + 1]) / period
    return out


def _ema(values: List[float], period: int) -> List[Optional[float]]:
    if not values:
        return []
    k = 2.0 / (period + 1)
    out: List[Optional[float]] = [None] * len(values)
    out[0] = values[0]
    for i in range(1, len(values)):
        out[i] = values[i] * k + (out[i - 1] or 0) * (1 - k)
    return out


def _atr(candles: List[Dict[str, Any]], period: int) -> List[Optional[float]]:
    trs: List[float] = []
    for i in range(1, len(candles)):
        c = candles[i]
        prev = candles[i - 1]
        trs.append(max(c["high"] - c["low"], abs(c["high"] - prev["close"]), abs(c["low"] - prev["close"])))
    out: List[Optional[float]] = [None] * len(candles)
    for i in range(period, len(candles)):
        out[i] = sum(trs[i - period : i]) / period
    return out


def aroon(candles: List[Dict[str, Any]], length: int = 25) -> Dict[str, List[Optional[float]]]:
    n = len(candles)
    up: List[Optional[float]] = [None] * n
    down: List[Optional[float]] = [None] * n
    osc: List[Optional[float]] = [None] * n
    for i in range(length, n):
        hi_idx = i
        lo_idx = i
        for j in range(i - length, i + 1):
            if candles[j]["high"] > candles[hi_idx]["high"]:
                hi_idx = j
            if candles[j]["low"] < candles[lo_idx]["low"]:
                lo_idx = j
        up[i] = ((length - (i - hi_idx)) / length) * 100
        down[i] = ((length - (i - lo_idx)) / length) * 100
        osc[i] = (up[i] or 0) - (down[i] or 0)
    return {"up": up, "down": down, "oscillator": osc}


def ttm_squeeze(
    candles: List[Dict[str, Any]],
    bb_len: int = 20,
    bb_mult: float = 2.0,
    kc_len: int = 20,
    kc_mult: float = 1.5,
) -> Dict[str, Any]:
    n = len(candles)
    closes = [c["close"] for c in candles]
    mid = _sma(closes, bb_len)

    bb_upper: List[Optional[float]] = [None] * n
    bb_lower: List[Optional[float]] = [None] * n
    for i in range(bb_len - 1, n):
        m = mid[i]
        if m is None:
            continue
        s = sum((closes[j] - m) ** 2 for j in range(i - bb_len + 1, i + 1))
        dev = math.sqrt(s / bb_len) * bb_mult
        bb_upper[i] = m + dev
        bb_lower[i] = m - dev

    atr_arr = _atr(candles, kc_len)
    kc_mid = _ema(closes, kc_len)
    kc_upper: List[Optional[float]] = [None] * n
    kc_lower: List[Optional[float]] = [None] * n
    for i in range(n):
        if atr_arr[i] is None or kc_mid[i] is None:
            continue
        kc_upper[i] = (kc_mid[i] or 0) + kc_mult * (atr_arr[i] or 0)
        kc_lower[i] = (kc_mid[i] or 0) - kc_mult * (atr_arr[i] or 0)

    squeeze_on: List[bool] = [False] * n
    for i in range(n):
        if bb_upper[i] is None or kc_upper[i] is None:
            continue
        squeeze_on[i] = (bb_lower[i] or 0) > (kc_lower[i] or 0) and (bb_upper[i] or 0) < (kc_upper[i] or 0)

    momentum: List[Optional[float]] = [None] * n
    for i in range(bb_len - 1, n):
        sum_x = sum_y = sum_xy = sum_x2 = 0.0
        for j in range(bb_len):
            x = j
            y = closes[i - bb_len + 1 + j]
            sum_x += x
            sum_y += y
            sum_xy += x * y
            sum_x2 += x * x
        denom = bb_len * sum_x2 - sum_x * sum_x or 1
        momentum[i] = (bb_len * sum_xy - sum_x * sum_y) / denom

    return {
        "squeezeOn": squeeze_on,
        "bollingerMid": mid,
        "bollingerUpper": bb_upper,
        "bollingerLower": bb_lower,
        "keltnerMid": kc_mid,
        "keltnerUpper": kc_upper,
        "keltnerLower": kc_lower,
        "momentum": momentum,
    }


def choppiness(candles: List[Dict[str, Any]], length: int = 14) -> List[Optional[float]]:
    n = len(candles)
    out: List[Optional[float]] = [None] * n
    atr_arr = _atr(candles, 1)
    for i in range(length, n):
        sum_atr = 0.0
        hh = float("-inf")
        ll = float("inf")
        for j in range(i - length + 1, i + 1):
            if atr_arr[j] is not None:
                sum_atr += atr_arr[j] or 0
            if candles[j]["high"] > hh:
                hh = candles[j]["high"]
            if candles[j]["low"] < ll:
                ll = candles[j]["low"]
        rng = hh - ll or 1e-10
        out[i] = (100 * math.log10(sum_atr / rng)) / math.log10(length)
    return out


def williams_r(candles: List[Dict[str, Any]], period: int = 14) -> List[Optional[float]]:
    n = len(candles)
    out: List[Optional[float]] = [None] * n
    for i in range(period - 1, n):
        hh = max(c["high"] for c in candles[i - period + 1 : i + 1])
        ll = min(c["low"] for c in candles[i - period + 1 : i + 1])
        close = candles[i]["close"]
        out[i] = ((hh - close) / (hh - ll) * -100) if hh != ll else -50.0
    return out


def cci(candles: List[Dict[str, Any]], period: int = 20) -> List[Optional[float]]:
    n = len(candles)
    out: List[Optional[float]] = [None] * n
    for i in range(period - 1, n):
        slice_ = candles[i - period + 1 : i + 1]
        tp = [(c["high"] + c["low"] + c["close"]) / 3 for c in slice_]
        mean = sum(tp) / period
        md = sum(abs(t - mean) for t in tp) / period
        out[i] = (tp[-1] - mean) / (0.015 * md) if md > 0 else 0.0
    return out


def obv(candles: List[Dict[str, Any]]) -> List[float]:
    out: List[float] = [0.0]
    for i in range(1, len(candles)):
        if candles[i]["close"] > candles[i - 1]["close"]:
            out.append(out[-1] + candles[i].get("volume", 0))
        elif candles[i]["close"] < candles[i - 1]["close"]:
            out.append(out[-1] - candles[i].get("volume", 0))
        else:
            out.append(out[-1])
    return out


def vortex(candles: List[Dict[str, Any]], period: int = 14) -> Dict[str, List[Optional[float]]]:
    n = len(candles)
    vi_plus: List[Optional[float]] = [None] * n
    vi_minus: List[Optional[float]] = [None] * n
    for i in range(period, n):
        vm_plus = vm_minus = tr_sum = 0.0
        for j in range(i - period + 1, i + 1):
            c = candles[j]
            prev = candles[j - 1]
            tr = max(c["high"] - c["low"], abs(c["high"] - prev["close"]), abs(c["low"] - prev["close"]))
            tr_sum += tr
            vm_plus += abs(c["high"] - prev["low"])
            vm_minus += abs(c["low"] - prev["high"])
        if tr_sum > 0:
            vi_plus[i] = vm_plus / tr_sum
            vi_minus[i] = vm_minus / tr_sum
    return {"viPlus": vi_plus, "viMinus": vi_minus}


def mfi(candles: List[Dict[str, Any]], period: int = 14) -> List[Optional[float]]:
    n = len(candles)
    out: List[Optional[float]] = [None] * n
    for i in range(period, n):
        pos_flow = neg_flow = 0.0
        for j in range(i - period + 1, i + 1):
            c = candles[j]
            prev = candles[j - 1]
            tp = (c["high"] + c["low"] + c["close"]) / 3
            prev_tp = (prev["high"] + prev["low"] + prev["close"]) / 3
            mf = tp * c.get("volume", 0)
            if tp > prev_tp:
                pos_flow += mf
            else:
                neg_flow += mf
        out[i] = (100 * pos_flow / (pos_flow + neg_flow)) if (pos_flow + neg_flow) > 0 else 50.0
    return out


def awesome_oscillator(candles: List[Dict[str, Any]]) -> List[Optional[float]]:
    n = len(candles)
    out: List[Optional[float]] = [None] * n
    for i in range(34, n):
        hl = [c["high"] + c["low"] for c in candles[: i + 1]]
        fast = sum(hl[-5:]) / 5
        slow = sum(hl[-34:]) / 34
        out[i] = fast - slow
    return out


def advanced_score(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate many indicators into a single -100..100 composite score."""
    signals: List[Dict[str, Any]] = []
    n = len(candles)
    if n < 60:
        return {"score": 0, "bias": "neutral", "signals": []}

    closes = [c["close"] for c in candles]

    wr = williams_r(candles)
    wr_val = wr[-1]
    if wr_val is not None:
        v = 1 if wr_val < -80 else -1 if wr_val > -20 else 0
        signals.append({"name": "Williams %R", "value": v, "signal": "bull" if v > 0 else "bear" if v < 0 else "neutral"})

    cci_arr = cci(candles)
    cci_val = cci_arr[-1]
    if cci_val is not None:
        v = 1 if cci_val < -100 else -1 if cci_val > 100 else 0
        signals.append({"name": "CCI", "value": v, "signal": "bull" if v > 0 else "bear" if v < 0 else "neutral"})

    obv_arr = obv(candles)
    if len(obv_arr) >= 5:
        v = 1 if obv_arr[-1] > obv_arr[-5] else -1 if obv_arr[-1] < obv_arr[-5] else 0
        signals.append({"name": "OBV Trend", "value": v, "signal": "bull" if v > 0 else "bear" if v < 0 else "neutral"})

    ar = aroon(candles)
    ar_osc = ar["oscillator"][-1]
    if ar_osc is not None:
        v = 1 if ar_osc > 0 else -1 if ar_osc < 0 else 0
        signals.append({"name": "Aroon Osc", "value": v, "signal": "bull" if v > 0 else "bear" if v < 0 else "neutral"})

    vt = vortex(candles)
    vp = vt["viPlus"][-1]
    vm = vt["viMinus"][-1]
    if vp is not None and vm is not None:
        v = 1 if vp > vm else -1 if vp < vm else 0
        signals.append({"name": "Vortex", "value": v, "signal": "bull" if v > 0 else "bear" if v < 0 else "neutral"})

    sq = ttm_squeeze(candles)
    mom = sq["momentum"][-1]
    if mom is not None:
        v = 1 if mom > 0 else -1 if mom < 0 else 0
        signals.append({"name": "TTM Momentum", "value": v, "signal": "bull" if v > 0 else "bear" if v < 0 else "neutral"})

    mfi_arr = mfi(candles)
    mfi_val = mfi_arr[-1]
    if mfi_val is not None:
        v = 1 if mfi_val < 20 else -1 if mfi_val > 80 else 0
        signals.append({"name": "MFI", "value": v, "signal": "bull" if v > 0 else "bear" if v < 0 else "neutral"})

    ao = awesome_oscillator(candles)
    ao_val = ao[-1]
    if ao_val is not None:
        v = 1 if ao_val > 0 else -1 if ao_val < 0 else 0
        signals.append({"name": "Awesome Osc", "value": v, "signal": "bull" if v > 0 else "bear" if v < 0 else "neutral"})

    ch = choppiness(candles)
    ch_val = ch[-1]
    if ch_val is not None:
        v = 1 if ch_val < 38.2 else 0
        signals.append({"name": "Choppiness", "value": v, "signal": "bull" if v > 0 else "neutral"})

    score = sum(s["value"] * 100 / len(signals) for s in signals) if signals else 0
    bias = "bull" if score > 10 else "bear" if score < -10 else "neutral"
    return {"score": round(score), "bias": bias, "signals": signals}
