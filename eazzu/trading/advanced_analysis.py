"""Advanced technical analysis tools — extended indicator suite.

Pure-Python implementations of advanced technical indicators and analysis
methods that go beyond the base suite in ``eazzu.trading.intelligence``.

All functions accept a list of candle dicts with keys: open, high, low, close,
volume (optional), epoch/time (optional). No third-party dependencies.

Indicators implemented:
  * VWAP (Volume Weighted Average Price)
  * VWMA (Volume Weighted Moving Average)
  * Hull Moving Average
  * Keltner Channels
  * Donchian Channels
  * Williams %R
  * MFI (Money Flow Index)
  * CCI (Commodity Channel Index)
  * OBV (On Balance Volume)
  * Aroon Oscillator
  * Chande Momentum Oscillator (CMO)
  * TRIX
  * TEMA (Triple EMA)
  * DEMA (Double EMA)
  * ZigZag
  * Heikin-Ashi candles
  * Renko brick generation
  * Pivot Points (classic, Camarilla, Woodie)
  * Market Profile (basic)
  * Correlation analysis
  * Multi-timeframe analysis
"""
from __future__ import annotations

import math
from typing import Optional


def _closes(candles: list[dict]) -> list[float]:
    return [float(c["close"]) for c in candles]


def _highs(candles: list[dict]) -> list[float]:
    return [float(c["high"]) for c in candles]


def _lows(candles: list[dict]) -> list[float]:
    return [float(c["low"]) for c in candles]


def _volumes(candles: list[dict]) -> list[float]:
    return [float(c.get("volume", 0)) for c in candles]


def _typical_prices(candles: list[dict]) -> list[float]:
    return [(float(c["high"]) + float(c["low"]) + float(c["close"])) / 3 for c in candles]


def sma(values: list[float], period: int) -> list[Optional[float]]:
    out = [None] * len(values)
    for i in range(period - 1, len(values)):
        out[i] = sum(values[i - period + 1 : i + 1]) / period
    return out


def ema(values: list[float], period: int) -> list[Optional[float]]:
    out = [None] * len(values)
    k = 2 / (period + 1)
    for i in range(len(values)):
        if i < period - 1:
            continue
        if i == period - 1:
            out[i] = sum(values[:period]) / period
        else:
            out[i] = values[i] * k + out[i - 1] * (1 - k)
    return out


# ------------------------------------------------------------------ VWAP #
def vwap(candles: list[dict]) -> list[Optional[float]]:
    """Volume Weighted Average Price — cumulative."""
    closes = _closes(candles)
    highs = _highs(candles)
    lows = _lows(candles)
    vols = _volumes(candles)
    out = [None] * len(candles)
    cum_pv = 0.0
    cum_v = 0.0
    for i in range(len(candles)):
        tp = (highs[i] + lows[i] + closes[i]) / 3
        cum_pv += tp * vols[i]
        cum_v += vols[i]
        out[i] = cum_pv / cum_v if cum_v > 0 else tp
    return out


def vwma(candles: list[dict], period: int = 20) -> list[Optional[float]]:
    """Volume Weighted Moving Average."""
    closes = _closes(candles)
    vols = _volumes(candles)
    out = [None] * len(candles)
    for i in range(period - 1, len(candles)):
        pv = sum(closes[j] * vols[j] for j in range(i - period + 1, i + 1))
        v = sum(vols[j] for j in range(i - period + 1, i + 1))
        out[i] = pv / v if v > 0 else closes[i]
    return out


# ------------------------------------------------------------------ HMA #
def hull_ma(values: list[float], period: int) -> list[Optional[float]]:
    """Hull Moving Average — reduces lag while smoothing."""
    half = max(1, period // 2)
    sqrt_p = max(1, int(math.sqrt(period)))
    ema_half = ema(values, half)
    ema_full = ema(values, period)
    raw = []
    for i in range(len(values)):
        if ema_half[i] is not None and ema_full[i] is not None:
            raw.append(2 * ema_half[i] - ema_full[i])
        else:
            raw.append(None)
    valid = [v if v is not None else 0 for v in raw]
    out = [None] * len(values)
    k = 2 / (sqrt_p + 1)
    for i in range(len(values)):
        if raw[i] is None:
            continue
        if i == 0 or out[i - 1] is None:
            out[i] = valid[i]
        else:
            out[i] = valid[i] * k + out[i - 1] * (1 - k)
    return out


# ----------------------------------------------------------- Keltner/Donchian #
def keltner_channels(candles: list[dict], ema_period: int = 20, atr_period: int = 10, mult: float = 2.0) -> dict:
    """Keltner Channels — EMA with ATR-based bands."""
    closes = _closes(candles)
    ema_vals = ema(closes, ema_period)
    atr_vals = atr(candles, atr_period)
    upper = [None] * len(candles)
    lower = [None] * len(candles)
    middle = [None] * len(candles)
    for i in range(len(candles)):
        if ema_vals[i] is not None and atr_vals[i] is not None:
            middle[i] = ema_vals[i]
            upper[i] = ema_vals[i] + mult * atr_vals[i]
            lower[i] = ema_vals[i] - mult * atr_vals[i]
    return {"upper": upper, "middle": middle, "lower": lower}


def donchian_channels(candles: list[dict], period: int = 20) -> dict:
    """Donchian Channels — highest high / lowest low over period."""
    highs = _highs(candles)
    lows = _lows(candles)
    upper = [None] * len(candles)
    lower = [None] * len(candles)
    middle = [None] * len(candles)
    for i in range(period - 1, len(candles)):
        hh = max(highs[i - period + 1 : i + 1])
        ll = min(lows[i - period + 1 : i + 1])
        upper[i] = hh
        lower[i] = ll
        middle[i] = (hh + ll) / 2
    return {"upper": upper, "middle": middle, "lower": lower}


# --------------------------------------------------------------- ATR #
def atr(candles: list[dict], period: int = 14) -> list[Optional[float]]:
    """Average True Range."""
    highs = _highs(candles)
    lows = _lows(candles)
    closes = _closes(candles)
    trs = [0.0] * len(candles)
    for i in range(len(candles)):
        if i == 0:
            trs[i] = highs[i] - lows[i]
        else:
            trs[i] = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
    return sma(trs, period)


# --------------------------------------------------------- Williams %R #
def williams_r(candles: list[dict], period: int = 14) -> list[Optional[float]]:
    """Williams %R — momentum oscillator 0 to -100."""
    highs = _highs(candles)
    lows = _lows(candles)
    closes = _closes(candles)
    out = [None] * len(candles)
    for i in range(period - 1, len(candles)):
        hh = max(highs[i - period + 1 : i + 1])
        ll = min(lows[i - period + 1 : i + 1])
        denom = hh - ll
        out[i] = ((hh - closes[i]) / denom * -100) if denom > 0 else -50
    return out


# ------------------------------------------------------------------ MFI #
def mfi(candles: list[dict], period: int = 14) -> list[Optional[float]]:
    """Money Flow Index — volume-weighted RSI."""
    tps = _typical_prices(candles)
    vols = _volumes(candles)
    out = [None] * len(candles)
    for i in range(period, len(candles)):
        pos_flow = 0.0
        neg_flow = 0.0
        for j in range(i - period + 1, i + 1):
            if j == 0:
                continue
            rmf = tps[j] * vols[j]
            if tps[j] > tps[j - 1]:
                pos_flow += rmf
            else:
                neg_flow += rmf
        if neg_flow == 0:
            out[i] = 100.0
        else:
            mfr = pos_flow / neg_flow
            out[i] = 100 - 100 / (1 + mfr)
    return out


# ------------------------------------------------------------------ CCI #
def cci(candles: list[dict], period: int = 20) -> list[Optional[float]]:
    """Commodity Channel Index."""
    tps = _typical_prices(candles)
    out = [None] * len(candles)
    for i in range(period - 1, len(candles)):
        window = tps[i - period + 1 : i + 1]
        sma_val = sum(window) / period
        mad = sum(abs(t - sma_val) for t in window) / period
        out[i] = (tps[i] - sma_val) / (0.015 * mad) if mad > 0 else 0
    return out


# ------------------------------------------------------------------ OBV #
def obv(candles: list[dict]) -> list[float]:
    """On Balance Volume — cumulative volume based on close direction."""
    closes = _closes(candles)
    vols = _volumes(candles)
    out = [0.0] * len(candles)
    for i in range(1, len(candles)):
        if closes[i] > closes[i - 1]:
            out[i] = out[i - 1] + vols[i]
        elif closes[i] < closes[i - 1]:
            out[i] = out[i - 1] - vols[i]
        else:
            out[i] = out[i - 1]
    return out


# ------------------------------------------------------------------ Aroon #
def aroon(candles: list[dict], period: int = 25) -> dict:
    """Aroon Up/Down and Oscillator."""
    highs = _highs(candles)
    lows = _lows(candles)
    up = [None] * len(candles)
    down = [None] * len(candles)
    osc = [None] * len(candles)
    for i in range(period, len(candles)):
        window_h = highs[i - period : i + 1]
        window_l = lows[i - period : i + 1]
        bars_since_high = period - window_h.index(max(window_h))
        bars_since_low = period - window_l.index(min(window_l))
        up[i] = ((period - bars_since_high) / period) * 100
        down[i] = ((period - bars_since_low) / period) * 100
        osc[i] = up[i] - down[i]
    return {"aroon_up": up, "aroon_down": down, "oscillator": osc}


# ------------------------------------------------------------------ CMO #
def cmo(candles: list[dict], period: int = 14) -> list[Optional[float]]:
    """Chande Momentum Oscillator."""
    closes = _closes(candles)
    out = [None] * len(candles)
    for i in range(period, len(candles)):
        gains = 0.0
        losses = 0.0
        for j in range(i - period + 1, i + 1):
            diff = closes[j] - closes[j - 1]
            if diff > 0:
                gains += diff
            else:
                losses += abs(diff)
        total = gains + losses
        out[i] = ((gains - losses) / total * 100) if total > 0 else 0
    return out


# ------------------------------------------------------------------ TRIX #
def trix(candles: list[dict], period: int = 12) -> list[Optional[float]]:
    """TRIX — triple-smoothed EMA rate of change."""
    closes = _closes(candles)
    e1 = ema(closes, period)
    e1_valid = [v if v is not None else 0 for v in e1]
    e2 = ema(e1_valid, period)
    e2_valid = [v if v is not None else 0 for v in e2]
    e3 = ema(e2_valid, period)
    out = [None] * len(candles)
    for i in range(1, len(candles)):
        if e3[i] is not None and e3[i - 1] is not None and e3[i - 1] != 0:
            out[i] = ((e3[i] - e3[i - 1]) / e3[i - 1]) * 100
    return out


# --------------------------------------------------------- DEMA / TEMA #
def dema(values: list[float], period: int) -> list[Optional[float]]:
    """Double Exponential Moving Average."""
    e1 = ema(values, period)
    e1_valid = [v if v is not None else 0 for v in e1]
    e2 = ema(e1_valid, period)
    out = [None] * len(values)
    for i in range(len(values)):
        if e1[i] is not None and e2[i] is not None:
            out[i] = 2 * e1[i] - e2[i]
    return out


def tema(values: list[float], period: int) -> list[Optional[float]]:
    """Triple Exponential Moving Average."""
    e1 = ema(values, period)
    e1_valid = [v if v is not None else 0 for v in e1]
    e2 = ema(e1_valid, period)
    e2_valid = [v if v is not None else 0 for v in e2]
    e3 = ema(e2_valid, period)
    out = [None] * len(values)
    for i in range(len(values)):
        if e1[i] is not None and e2[i] is not None and e3[i] is not None:
            out[i] = 3 * e1[i] - 3 * e2[i] + e3[i]
    return out


# ------------------------------------------------------------------ ZigZag #
def zigzag(candles: list[dict], threshold: float = 5.0) -> list[dict]:
    """ZigZag indicator — identify significant turning points."""
    if len(candles) < 2:
        return []
    highs = _highs(candles)
    lows = _lows(candles)
    pivots = [{"index": 0, "type": "high" if highs[0] > lows[0] else "low", "value": highs[0] if highs[0] > lows[0] else lows[0]}]
    last_pivot = pivots[0]
    for i in range(1, len(candles)):
        if last_pivot["type"] == "high":
            if highs[i] > last_pivot["value"]:
                pivots[-1] = {"index": i, "type": "high", "value": highs[i]}
                last_pivot = pivots[-1]
            elif lows[i] < last_pivot["value"] * (1 - threshold / 100):
                pivots.append({"index": i, "type": "low", "value": lows[i]})
                last_pivot = pivots[-1]
        else:
            if lows[i] < last_pivot["value"]:
                pivots[-1] = {"index": i, "type": "low", "value": lows[i]}
                last_pivot = pivots[-1]
            elif highs[i] > last_pivot["value"] * (1 + threshold / 100):
                pivots.append({"index": i, "type": "high", "value": highs[i]})
                last_pivot = pivots[-1]
    return pivots


# ----------------------------------------------------------- Heikin-Ashi #
def heikin_ashi(candles: list[dict]) -> list[dict]:
    """Convert standard candles to Heikin-Ashi candles."""
    out = []
    prev_ha_close = 0.0
    prev_ha_open = 0.0
    for i, c in enumerate(candles):
        o, h, l, cl = float(c["open"]), float(c["high"]), float(c["low"]), float(c["close"])
        ha_close = (o + h + l + cl) / 4
        if i == 0:
            ha_open = (o + cl) / 2
        else:
            ha_open = (prev_ha_open + prev_ha_close) / 2
        ha_high = max(h, ha_open, ha_close)
        ha_low = min(l, ha_open, ha_close)
        out.append({"open": ha_open, "high": ha_high, "low": ha_low, "close": ha_close})
        prev_ha_open = ha_open
        prev_ha_close = ha_close
    return out


# ------------------------------------------------------------------ Renko #
def renko(candles: list[dict], brick_size: Optional[float] = None) -> list[dict]:
    """Generate Renko bricks from candle data."""
    if not candles:
        return []
    closes = _closes(candles)
    if brick_size is None:
        ranges = [abs(closes[i] - closes[i - 1]) for i in range(1, len(closes))]
        brick_size = sum(ranges) / len(ranges) if ranges else 1.0
    bricks = []
    price = closes[0]
    direction = 0
    for close in closes:
        diff = close - price
        if direction >= 0 and diff >= brick_size:
            n = int(diff / brick_size)
            for _ in range(n):
                bricks.append({"price": price + brick_size, "direction": "up"})
                price += brick_size
            direction = 1
        elif direction <= 0 and diff <= -brick_size:
            n = int(abs(diff) / brick_size)
            for _ in range(n):
                bricks.append({"price": price - brick_size, "direction": "down"})
                price -= brick_size
            direction = -1
    return {"bricks": bricks, "brick_size": brick_size, "count": len(bricks)}


# ----------------------------------------------------------- Pivot Points #
def pivot_points(candles: list[dict], method: str = "classic") -> dict:
    """Calculate pivot points (classic, camarilla, woodie)."""
    if not candles:
        return {"error": "no candles"}
    last = candles[-1]
    h, l, c = float(last["high"]), float(last["low"]), float(last["close"])
    o = float(last.get("open", c))
    if method == "classic":
        pivot = (h + l + c) / 3
        return {
            "pivot": pivot,
            "r1": 2 * pivot - l, "s1": 2 * pivot - h,
            "r2": pivot + (h - l), "s2": pivot - (h - l),
            "r3": h + 2 * (pivot - l), "s3": l - 2 * (h - pivot),
        }
    elif method == "camarilla":
        pivot = (h + l + c) / 3
        r = h - l
        return {
            "pivot": pivot,
            "r1": c + r * 1.1 / 12, "s1": c - r * 1.1 / 12,
            "r2": c + r * 1.1 / 6, "s2": c - r * 1.1 / 6,
            "r3": c + r * 1.1 / 4, "s3": c - r * 1.1 / 4,
            "r4": c + r * 1.1 / 2, "s4": c - r * 1.1 / 2,
        }
    elif method == "woodie":
        pivot = (h + l + 2 * c) / 4
        return {
            "pivot": pivot,
            "r1": 2 * pivot - l, "s1": 2 * pivot - h,
            "r2": pivot + (h - l), "s2": pivot - (h - l),
        }
    return {"error": f"unknown method '{method}'"}


# ----------------------------------------------------------- Correlation #
def correlation(candles_a: list[dict], candles_b: list[dict], period: int = 20) -> dict:
    """Pearson correlation between two candle series (close prices)."""
    a = _closes(candles_a)[-period:]
    b = _closes(candles_b)[-period:]
    if len(a) != len(b) or len(a) < 2:
        return {"error": "need equal-length series with at least 2 points"}
    n = len(a)
    mean_a = sum(a) / n
    mean_b = sum(b) / n
    cov = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
    std_a = math.sqrt(sum((x - mean_a) ** 2 for x in a))
    std_b = math.sqrt(sum((x - mean_b) ** 2 for x in b))
    r = cov / (std_a * std_b) if std_a > 0 and std_b > 0 else 0
    return {"correlation": round(r, 4), "period": n, "interpretation": "positive" if r > 0.3 else ("negative" if r < -0.3 else "neutral")}


# --------------------------------------------------- Multi-timeframe #
def multi_timeframe(candles: list[dict], timeframes: Optional[list[int]] = None) -> dict:
    """Aggregate candles to multiple timeframes and compute trend for each."""
    if not candles:
        return {"error": "no candles"}
    tfs = timeframes or [5, 15, 60, 240, 1440]
    closes = _closes(candles)
    results = {}
    for tf in tfs:
        if tf <= 1 or len(closes) < tf:
            continue
        agg_closes = []
        for i in range(0, len(candles) - tf + 1, tf):
            chunk = candles[i : i + tf]
            agg_closes.append({
                "open": chunk[0]["open"],
                "high": max(float(c["high"]) for c in chunk),
                "low": min(float(c["low"]) for c in chunk),
                "close": chunk[-1]["close"],
                "volume": sum(float(c.get("volume", 0)) for c in chunk),
            })
        if len(agg_closes) < 10:
            results[f"tf_{tf}"] = {"trend": "insufficient_data", "candles": len(agg_closes)}
            continue
        ema_fast = ema([c["close"] for c in agg_closes], 9)
        ema_slow = ema([c["close"] for c in agg_closes], 21)
        last_fast = ema_fast[-1]
        last_slow = ema_slow[-1]
        if last_fast and last_slow:
            trend = "bullish" if last_fast > last_slow else "bearish"
        else:
            trend = "neutral"
        results[f"tf_{tf}"] = {"trend": trend, "ema_fast": last_fast, "ema_slow": last_slow, "candles": len(agg_closes)}
    return {"timeframes": results, "agreement": _trend_agreement(results)}


def _trend_agreement(results: dict) -> str:
    trends = [v.get("trend") for v in results.values() if isinstance(v, dict)]
    bulls = sum(1 for t in trends if t == "bullish")
    bears = sum(1 for t in trends if t == "bearish")
    if bulls > bears and bulls >= len(trends) * 0.6:
        return "strong_bullish"
    if bears > bulls and bears >= len(trends) * 0.6:
        return "strong_bearish"
    if bulls > bears:
        return "mild_bullish"
    if bears > bulls:
        return "mild_bearish"
    return "mixed"


# ----------------------------------------------------------- Full Analysis #
def full_analysis(candles: list[dict]) -> dict:
    """Run all advanced indicators and return a comprehensive analysis."""
    if len(candles) < 30:
        return {"error": "need at least 30 candles for advanced analysis"}
    closes = _closes(candles)
    return {
        "vwap": vwap(candles)[-1],
        "vwma_20": vwma(candles, 20)[-1],
        "hull_ma": hull_ma(closes, 20)[-1],
        "keltner": {k: v[-1] if isinstance(v, list) else v for k, v in keltner_channels(candles).items()},
        "donchian": {k: v[-1] if isinstance(v, list) else v for k, v in donchian_channels(candles).items()},
        "atr_14": atr(candles, 14)[-1],
        "williams_r": williams_r(candles)[-1],
        "mfi_14": mfi(candles)[-1],
        "cci_20": cci(candles)[-1],
        "obv": obv(candles)[-1],
        "aroon": {k: v[-1] if isinstance(v, list) else v for k, v in aroon(candles).items()},
        "cmo": cmo(candles)[-1],
        "trix": trix(candles)[-1],
        "dema_20": dema(closes, 20)[-1],
        "tema_20": tema(closes, 20)[-1],
        "zigzag_pivots": zigzag(candles)[-5:],
        "heikin_ashi_last": heikin_ashi(candles)[-1] if candles else None,
        "renko": renko(candles),
        "pivot_classic": pivot_points(candles, "classic"),
        "pivot_camarilla": pivot_points(candles, "camarilla"),
        "multi_timeframe": multi_timeframe(candles),
    }


TOOLS: list[dict] = [
    {"name": "calc_vwap", "description": "Calculate Volume Weighted Average Price (VWAP)", "params": {"candles": "list"}, "run": lambda args: {"vwap": vwap(args.get("candles", []))}},
    {"name": "calc_vwma", "description": "Calculate Volume Weighted Moving Average (VWMA)", "params": {"candles": "list", "period": "int"}, "run": lambda args: {"vwma": vwma(args.get("candles", []), int(args.get("period", 20)))}},
    {"name": "calc_hull_ma", "description": "Calculate Hull Moving Average (reduces lag)", "params": {"candles": "list", "period": "int"}, "run": lambda args: {"hull_ma": hull_ma(_closes(args.get("candles", [])), int(args.get("period", 20)))}},
    {"name": "calc_keltner", "description": "Calculate Keltner Channels (EMA + ATR bands)", "params": {"candles": "list", "ema_period": "int", "atr_period": "int", "mult": "float"}, "run": lambda args: keltner_channels(args.get("candles", []), int(args.get("ema_period", 20)), int(args.get("atr_period", 10)), float(args.get("mult", 2.0)))},
    {"name": "calc_donchian", "description": "Calculate Donchian Channels (highest high / lowest low)", "params": {"candles": "list", "period": "int"}, "run": lambda args: donchian_channels(args.get("candles", []), int(args.get("period", 20)))},
    {"name": "calc_atr", "description": "Calculate Average True Range (ATR)", "params": {"candles": "list", "period": "int"}, "run": lambda args: {"atr": atr(args.get("candles", []), int(args.get("period", 14)))}},
    {"name": "calc_williams_r", "description": "Calculate Williams %R momentum oscillator", "params": {"candles": "list", "period": "int"}, "run": lambda args: {"williams_r": williams_r(args.get("candles", []), int(args.get("period", 14)))}},
    {"name": "calc_mfi", "description": "Calculate Money Flow Index (volume-weighted RSI)", "params": {"candles": "list", "period": "int"}, "run": lambda args: {"mfi": mfi(args.get("candles", []), int(args.get("period", 14)))}},
    {"name": "calc_cci", "description": "Calculate Commodity Channel Index (CCI)", "params": {"candles": "list", "period": "int"}, "run": lambda args: {"cci": cci(args.get("candles", []), int(args.get("period", 20)))}},
    {"name": "calc_obv", "description": "Calculate On Balance Volume (OBV)", "params": {"candles": "list"}, "run": lambda args: {"obv": obv(args.get("candles", []))}},
    {"name": "calc_aroon", "description": "Calculate Aroon Up/Down and Oscillator", "params": {"candles": "list", "period": "int"}, "run": lambda args: aroon(args.get("candles", []), int(args.get("period", 25)))},
    {"name": "calc_cmo", "description": "Calculate Chande Momentum Oscillator (CMO)", "params": {"candles": "list", "period": "int"}, "run": lambda args: {"cmo": cmo(args.get("candles", []), int(args.get("period", 14)))}},
    {"name": "calc_trix", "description": "Calculate TRIX (triple-smoothed EMA rate of change)", "params": {"candles": "list", "period": "int"}, "run": lambda args: {"trix": trix(args.get("candles", []), int(args.get("period", 12)))}},
    {"name": "calc_dema", "description": "Calculate Double Exponential Moving Average (DEMA)", "params": {"candles": "list", "period": "int"}, "run": lambda args: {"dema": dema(_closes(args.get("candles", [])), int(args.get("period", 20)))}},
    {"name": "calc_tema", "description": "Calculate Triple Exponential Moving Average (TEMA)", "params": {"candles": "list", "period": "int"}, "run": lambda args: {"tema": tema(_closes(args.get("candles", [])), int(args.get("period", 20)))}},
    {"name": "calc_zigzag", "description": "Identify significant price turning points with ZigZag indicator", "params": {"candles": "list", "threshold": "float"}, "run": lambda args: {"pivots": zigzag(args.get("candles", []), float(args.get("threshold", 5.0)))}},
    {"name": "calc_heikin_ashi", "description": "Convert candles to Heikin-Ashi (smoothed candlesticks)", "params": {"candles": "list"}, "run": lambda args: {"heikin_ashi": heikin_ashi(args.get("candles", []))}},
    {"name": "calc_renko", "description": "Generate Renko bricks from candle data", "params": {"candles": "list", "brick_size": "float"}, "run": lambda args: renko(args.get("candles", []), args.get("brick_size"))},
    {"name": "calc_pivot_points", "description": "Calculate pivot points (classic, camarilla, or woodie)", "params": {"candles": "list", "method": "string"}, "run": lambda args: pivot_points(args.get("candles", []), args.get("method", "classic"))},
    {"name": "calc_correlation", "description": "Pearson correlation between two candle series", "params": {"candles_a": "list", "candles_b": "list", "period": "int"}, "run": lambda args: correlation(args.get("candles_a", []), args.get("candles_b", []), int(args.get("period", 20)))},
    {"name": "calc_multi_timeframe", "description": "Multi-timeframe trend analysis with EMA agreement", "params": {"candles": "list", "timeframes": "list"}, "run": lambda args: multi_timeframe(args.get("candles", []), args.get("timeframes"))},
    {"name": "full_advanced_analysis", "description": "Run all advanced indicators at once for a comprehensive analysis", "params": {"candles": "list"}, "run": lambda args: full_analysis(args.get("candles", []))},
]
