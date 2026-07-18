"""Transparent, dependency-light market analysis utilities.

The engine is deliberately deterministic: it derives all outputs from the candles
provided by the caller and never fetches market data, predicts certainty, or
submits broker orders.
"""
from __future__ import annotations

import math
from statistics import mean, pstdev
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from .knowledge import KnowledgeBase
from .models import AnalysisResult, Candle, utc_now


MINIMUM_CANDLES = 30


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, float(value)))


def _safe_div(numerator: float, denominator: float, default: float = 0.0) -> float:
    return numerator / denominator if denominator else default


def _round(value: Optional[float], digits: int = 6) -> Optional[float]:
    return round(float(value), digits) if value is not None else None


def _ema(values: Sequence[float], period: int) -> float:
    """Return a recursive EMA, using available history when it is shorter than period."""
    if not values:
        return 0.0
    alpha = 2.0 / (max(int(period), 1) + 1.0)
    result = float(values[0])
    for value in values[1:]:
        result = alpha * float(value) + (1.0 - alpha) * result
    return result


def _ema_series(values: Sequence[float], period: int) -> List[float]:
    if not values:
        return []
    alpha = 2.0 / (max(int(period), 1) + 1.0)
    result = float(values[0])
    series = [result]
    for value in values[1:]:
        result = alpha * float(value) + (1.0 - alpha) * result
        series.append(result)
    return series


def _rsi(closes: Sequence[float], period: int = 14) -> float:
    if len(closes) < 2:
        return 50.0
    window = closes[-(period + 1):]
    gains = [max(float(window[index]) - float(window[index - 1]), 0.0) for index in range(1, len(window))]
    losses = [max(float(window[index - 1]) - float(window[index]), 0.0) for index in range(1, len(window))]
    avg_gain = mean(gains) if gains else 0.0
    avg_loss = mean(losses) if losses else 0.0
    if avg_loss == 0:
        return 100.0 if avg_gain else 50.0
    relative_strength = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + relative_strength))


def _true_ranges(candles: Sequence[Candle]) -> List[float]:
    if not candles:
        return []
    ranges = [candles[0].high - candles[0].low]
    for current, previous in zip(candles[1:], candles[:-1]):
        ranges.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
    return ranges


def _atr(candles: Sequence[Candle], period: int = 14) -> float:
    ranges = _true_ranges(candles)
    if not ranges:
        return 0.0
    return mean(ranges[-period:])


def _linear_slope(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    x_bar = (len(values) - 1) / 2.0
    y_bar = mean(values)
    denominator = sum((index - x_bar) ** 2 for index in range(len(values)))
    if denominator == 0:
        return 0.0
    return sum((index - x_bar) * (value - y_bar) for index, value in enumerate(values)) / denominator


def _swing_points(candles: Sequence[Candle], radius: int = 2) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    highs: List[Dict[str, Any]] = []
    lows: List[Dict[str, Any]] = []
    for index in range(radius, len(candles) - radius):
        high = candles[index].high
        low = candles[index].low
        left = candles[index - radius:index]
        right = candles[index + 1:index + radius + 1]
        adjacent = list(left) + list(right)
        if adjacent and all(high >= candle.high for candle in adjacent):
            highs.append({"index": index, "price": high, "timestamp": candles[index].timestamp})
        if adjacent and all(low <= candle.low for candle in adjacent):
            lows.append({"index": index, "price": low, "timestamp": candles[index].timestamp})
    return highs, lows


def _last_pair(items: Sequence[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], Optional[Dict[str, Any]]]:
    if len(items) < 2:
        return None, items[-1] if items else None
    return items[-2], items[-1]


class TechnicalAnalysisEngine:
    """Derive a single reproducible analysis report from OHLCV candles."""

    def __init__(self, knowledge_base: Optional[KnowledgeBase] = None) -> None:
        self.knowledge_base = knowledge_base or KnowledgeBase()

    @staticmethod
    def normalize_candles(candles: Iterable[Any]) -> List[Candle]:
        """Normalize mappings or already-normalized candles."""
        normalised: List[Candle] = []
        for item in candles:
            normalised.append(item if isinstance(item, Candle) else Candle.from_mapping(item))
        if len(normalised) < MINIMUM_CANDLES:
            raise ValueError(f"at least {MINIMUM_CANDLES} valid OHLC candles are required")
        return normalised

    def analyze(
        self,
        candles: Iterable[Any],
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
    ) -> AnalysisResult:
        """Compute all available analysis domains using only supplied candle history."""
        series = self.normalize_candles(candles)
        closes = [candle.close for candle in series]
        highs = [candle.high for candle in series]
        lows = [candle.low for candle in series]
        latest = series[-1]
        atr_14 = _atr(series, 14)
        previous_20 = series[-21:-1] if len(series) >= 21 else series[:-1]
        previous_high = max((candle.high for candle in previous_20), default=latest.high)
        previous_low = min((candle.low for candle in previous_20), default=latest.low)

        ema_9_series = _ema_series(closes, 9)
        ema_12_series = _ema_series(closes, 12)
        ema_20_series = _ema_series(closes, 20)
        ema_21_series = _ema_series(closes, 21)
        ema_26_series = _ema_series(closes, 26)
        ema_50_series = _ema_series(closes, 50)
        ema_200_series = _ema_series(closes, 200)
        macd_series = [fast - slow for fast, slow in zip(ema_12_series, ema_26_series)]
        macd_signal_series = _ema_series(macd_series, 9)

        ema_9 = ema_9_series[-1]
        ema_20 = ema_20_series[-1]
        ema_21 = ema_21_series[-1]
        ema_50 = ema_50_series[-1]
        ema_200 = ema_200_series[-1]
        macd = macd_series[-1]
        macd_signal = macd_signal_series[-1]
        macd_histogram = macd - macd_signal
        rsi_14 = _rsi(closes, 14)

        bb_window = closes[-20:]
        bb_mid = mean(bb_window)
        bb_std = pstdev(bb_window) if len(bb_window) > 1 else 0.0
        bb_upper = bb_mid + 2.0 * bb_std
        bb_lower = bb_mid - 2.0 * bb_std
        bb_width_pct = _safe_div(bb_upper - bb_lower, bb_mid) * 100.0
        bb_position = _safe_div(latest.close - bb_lower, bb_upper - bb_lower, 0.5)

        stochastic_window = min(14, len(series))
        stochastic_high = max(highs[-stochastic_window:])
        stochastic_low = min(lows[-stochastic_window:])
        stochastic_k = 100.0 * _safe_div(latest.close - stochastic_low, stochastic_high - stochastic_low, 0.5)
        roc_period = min(10, len(closes) - 1)
        roc_10 = 100.0 * _safe_div(latest.close - closes[-(roc_period + 1)], closes[-(roc_period + 1)]) if roc_period else 0.0

        slope_window = min(20, len(closes))
        normalized_slope_pct = 100.0 * _safe_div(_linear_slope(closes[-slope_window:]), mean(closes[-slope_window:]))
        efficiency_window = min(20, len(closes) - 1)
        directional_move = abs(latest.close - closes[-(efficiency_window + 1)]) if efficiency_window else 0.0
        travelled = sum(abs(closes[index] - closes[index - 1]) for index in range(len(closes) - efficiency_window, len(closes))) if efficiency_window else 0.0
        efficiency_ratio = _safe_div(directional_move, travelled)
        ema_separation_atr = _safe_div(abs(ema_20 - ema_50), atr_14)

        trend_direction = "neutral"
        if latest.close > ema_20 > ema_50 and normalized_slope_pct > 0:
            trend_direction = "bullish"
        elif latest.close < ema_20 < ema_50 and normalized_slope_pct < 0:
            trend_direction = "bearish"

        swing_highs, swing_lows = _swing_points(series)
        prior_swing_high, latest_swing_high = _last_pair(swing_highs)
        prior_swing_low, latest_swing_low = _last_pair(swing_lows)
        structural_bias = "range"
        if prior_swing_high and latest_swing_high and prior_swing_low and latest_swing_low:
            if latest_swing_high["price"] > prior_swing_high["price"] and latest_swing_low["price"] > prior_swing_low["price"]:
                structural_bias = "bullish"
            elif latest_swing_high["price"] < prior_swing_high["price"] and latest_swing_low["price"] < prior_swing_low["price"]:
                structural_bias = "bearish"
        if structural_bias == "range" and trend_direction != "neutral" and efficiency_ratio >= 0.35:
            structural_bias = trend_direction

        bos = "none"
        if latest.close > previous_high:
            bos = "bullish"
        elif latest.close < previous_low:
            bos = "bearish"

        candle_range = latest.high - latest.low
        body = abs(latest.close - latest.open)
        upper_wick = latest.high - max(latest.open, latest.close)
        lower_wick = min(latest.open, latest.close) - latest.low
        body_ratio = _safe_div(body, candle_range)
        close_location = _safe_div(latest.close - latest.low, candle_range, 0.5)
        prior = series[-2]
        bullish_engulfing = latest.close > latest.open and prior.close < prior.open and latest.close >= prior.open and latest.open <= prior.close
        bearish_engulfing = latest.close < latest.open and prior.close > prior.open and latest.open >= prior.close and latest.close <= prior.open
        inside_bar = latest.high <= prior.high and latest.low >= prior.low
        bullish_pin = lower_wick > body * 2.0 and close_location >= 0.60
        bearish_pin = upper_wick > body * 2.0 and close_location <= 0.40
        doji = body_ratio <= 0.10
        patterns: List[str] = []
        if bullish_engulfing:
            patterns.append("bullish_engulfing")
        if bearish_engulfing:
            patterns.append("bearish_engulfing")
        if bullish_pin:
            patterns.append("bullish_pin_bar")
        if bearish_pin:
            patterns.append("bearish_pin_bar")
        if inside_bar:
            patterns.append("inside_bar")
        if doji:
            patterns.append("doji")

        tolerance = max(atr_14 * 0.20, abs(latest.close) * 0.0001)
        equal_highs = bool(prior_swing_high and latest_swing_high and abs(prior_swing_high["price"] - latest_swing_high["price"]) <= tolerance)
        equal_lows = bool(prior_swing_low and latest_swing_low and abs(prior_swing_low["price"] - latest_swing_low["price"]) <= tolerance)
        high_sweep = latest.high > previous_high and latest.close < previous_high
        low_sweep = latest.low < previous_low and latest.close > previous_low
        high_distance_atr = _safe_div(previous_high - latest.close, atr_14)
        low_distance_atr = _safe_div(latest.close - previous_low, atr_14)

        volumes = [candle.volume for candle in series if candle.volume is not None]
        volume_available = len(volumes) >= 5
        volume_report: Dict[str, Any]
        if volume_available and latest.volume is not None:
            baseline_volumes = [candle.volume for candle in series[-21:-1] if candle.volume is not None]
            average_volume = mean(baseline_volumes) if baseline_volumes else mean(volumes)
            volume_ratio = _safe_div(latest.volume, average_volume, 1.0)
            signed_volume = 0.0
            for current, previous_candle in zip(series[1:], series[:-1]):
                if current.volume is not None:
                    signed_volume += current.volume if current.close >= previous_candle.close else -current.volume
            volume_report = {
                "available": True,
                "latest": _round(latest.volume),
                "average_20": _round(average_volume),
                "ratio_to_average": _round(volume_ratio, 4),
                "relative_activity": "high" if volume_ratio >= 1.4 else "low" if volume_ratio <= 0.7 else "normal",
                "obv_proxy_direction": "positive" if signed_volume > 0 else "negative" if signed_volume < 0 else "flat",
            }
        else:
            volume_report = {
                "available": False,
                "latest": None,
                "average_20": None,
                "ratio_to_average": None,
                "relative_activity": "unavailable",
                "obv_proxy_direction": "unavailable",
            }

        atr_pct = 100.0 * _safe_div(atr_14, latest.close)
        average_range = mean(_true_ranges(series[-21:-1])) if len(series) >= 21 else atr_14
        range_expansion = _safe_div(candle_range, average_range, 1.0)
        regime_name = "range"
        if atr_pct > 2.5 or range_expansion >= 1.8:
            regime_name = "high_volatility"
        elif efficiency_ratio >= 0.48 and ema_separation_atr >= 0.45:
            regime_name = "trend"
        elif efficiency_ratio <= 0.24:
            regime_name = "chop"
        elif atr_pct < 0.25:
            regime_name = "low_volatility"

        warnings: List[str] = []
        if len(series) < 60:
            warnings.append("Fewer than 60 candles were supplied; trend and regime readings have reduced context.")
        if len(series) < 200:
            warnings.append("Fewer than 200 candles were supplied; the long EMA uses the available history only.")
        if not volume_available:
            warnings.append("Volume analysis is unavailable because the input lacks sufficient volume values.")
        if atr_14 <= 0:
            warnings.append("ATR is zero; protective levels cannot be sized reliably from this candle sequence.")

        metrics = {
            "price": _round(latest.close),
            "trend": {
                "direction": trend_direction,
                "ema_9": _round(ema_9),
                "ema_20": _round(ema_20),
                "ema_21": _round(ema_21),
                "ema_50": _round(ema_50),
                "ema_200": _round(ema_200),
                "slope_pct_per_bar": _round(normalized_slope_pct, 6),
                "efficiency_ratio": _round(efficiency_ratio, 4),
                "ema_separation_atr": _round(ema_separation_atr, 4),
            },
            "momentum": {
                "rsi_14": _round(rsi_14, 4),
                "stochastic_k_14": _round(stochastic_k, 4),
                "roc_10_pct": _round(roc_10, 4),
                "macd": _round(macd),
                "macd_signal": _round(macd_signal),
                "macd_histogram": _round(macd_histogram),
            },
            "volatility": {
                "atr_14": _round(atr_14),
                "atr_pct": _round(atr_pct, 4),
                "bollinger_upper": _round(bb_upper),
                "bollinger_mid": _round(bb_mid),
                "bollinger_lower": _round(bb_lower),
                "bollinger_width_pct": _round(bb_width_pct, 4),
                "bollinger_position": _round(bb_position, 4),
                "range_expansion": _round(range_expansion, 4),
            },
            "levels": {
                "rolling_high_20": _round(previous_high),
                "rolling_low_20": _round(previous_low),
                "range_position_20": _round(_safe_div(latest.close - previous_low, previous_high - previous_low, 0.5), 4),
            },
        }
        market_structure = {
            "bias": structural_bias,
            "trend_alignment": trend_direction,
            "break_of_structure": bos,
            "last_swing_high": latest_swing_high,
            "last_swing_low": latest_swing_low,
            "swing_high_count": len(swing_highs),
            "swing_low_count": len(swing_lows),
        }
        price_action = {
            "patterns": patterns,
            "candle_direction": "bullish" if latest.close > latest.open else "bearish" if latest.close < latest.open else "neutral",
            "body_ratio": _round(body_ratio, 4),
            "upper_wick_ratio": _round(_safe_div(upper_wick, candle_range), 4),
            "lower_wick_ratio": _round(_safe_div(lower_wick, candle_range), 4),
            "close_location": _round(close_location, 4),
        }
        liquidity = {
            "rolling_high_20": _round(previous_high),
            "rolling_low_20": _round(previous_low),
            "distance_to_high_atr": _round(high_distance_atr, 4),
            "distance_to_low_atr": _round(low_distance_atr, 4),
            "equal_highs": equal_highs,
            "equal_lows": equal_lows,
            "high_sweep": high_sweep,
            "low_sweep": low_sweep,
            "nearest_pool": "highs" if abs(high_distance_atr) < abs(low_distance_atr) else "lows",
        }
        regime = {
            "name": regime_name,
            "efficiency_ratio": _round(efficiency_ratio, 4),
            "atr_pct": _round(atr_pct, 4),
            "range_expansion": _round(range_expansion, 4),
            "trend_strength": _round(ema_separation_atr, 4),
        }
        return AnalysisResult(
            symbol=symbol,
            timeframe=timeframe,
            candle_count=len(series),
            generated_at=utc_now(),
            metrics=metrics,
            market_structure=market_structure,
            price_action=price_action,
            liquidity=liquidity,
            volume=volume_report,
            regime=regime,
            knowledge_context=self.knowledge_base.context_for(symbol),
            warnings=warnings,
        )
