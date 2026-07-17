"""
Price Action Indicator
Simple price action analysis for confluence
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class PriceActionResult:
    """Price action analysis result"""
    trend: str  # 'up', 'down', 'sideways'
    momentum: float  # -1.0 to 1.0
    strength: float  # 0.0 to 1.0
    recent_direction: str  # Direction of last few candles
    candle_pattern: str  # Detected candle pattern


class PriceActionIndicator:
    """
    Price Action Analysis
    Analyzes price movement patterns without traditional indicators
    """

    def __init__(self, lookback: int = 10):
        self.lookback = lookback

    def calculate(self, highs: List[float], lows: List[float],
                  closes: List[float]) -> Optional[PriceActionResult]:
        """
        Calculate price action analysis
        Returns PriceActionResult or None if insufficient data
        """
        if len(closes) < self.lookback:
            return None

        recent_closes = closes[-self.lookback:]
        recent_highs = highs[-self.lookback:]
        recent_lows = lows[-self.lookback:]

        # Determine trend using linear regression slope
        price_changes = [recent_closes[i] - recent_closes[i-1]
                        for i in range(1, len(recent_closes))]
        avg_change = sum(price_changes) / len(price_changes)

        # Trend determination
        if avg_change > 0.001:
            trend = 'up'
        elif avg_change < -0.001:
            trend = 'down'
        else:
            trend = 'sideways'

        # Calculate momentum
        total_range = max(recent_highs) - min(recent_lows)
        if total_range > 0:
            momentum = avg_change / (total_range / self.lookback)
        else:
            momentum = 0
        momentum = max(-1, min(1, momentum))

        # Calculate strength
        consistent_count = sum(1 for c in price_changes if (c > 0) == (avg_change > 0))
        strength = consistent_count / len(price_changes)

        # Recent direction (last 3 candles)
        last_3 = price_changes[-3:]
        if sum(last_3) > 0.01:
            recent_direction = 'up'
        elif sum(last_3) < -0.01:
            recent_direction = 'down'
        else:
            recent_direction = 'neutral'

        # Simple candle pattern detection
        last_close = closes[-1]
        last_open = closes[-2] if len(closes) > 1 else closes[-1]
        last_high = highs[-1]
        last_low = lows[-1]

        body = abs(last_close - last_open)
        upper_wick = last_high - max(last_close, last_open)
        lower_wick = min(last_close, last_open) - last_low

        if upper_wick > body * 2 and lower_wick < body * 0.5:
            candle_pattern = 'shooting_star'
        elif lower_wick > body * 2 and upper_wick < body * 0.5:
            candle_pattern = 'hammer'
        elif body < (last_high - last_low) * 0.3:
            candle_pattern = 'doji'
        elif last_close > last_open:
            candle_pattern = 'bullish'
        else:
            candle_pattern = 'bearish'

        return PriceActionResult(
            trend=trend,
            momentum=momentum,
            strength=strength,
            recent_direction=recent_direction,
            candle_pattern=candle_pattern
        )

    def get_signal(self, result: PriceActionResult) -> Optional[Dict[str, Any]]:
        """Get trading signal from price action result"""
        if result.trend == 'up' and result.momentum > 0.3:
            return {'action': 'buy', 'confidence': result.strength * result.momentum}
        elif result.trend == 'down' and result.momentum < -0.3:
            return {'action': 'sell', 'confidence': result.strength * abs(result.momentum)}
        elif result.candle_pattern == 'hammer':
            return {'action': 'buy', 'confidence': 0.6}
        elif result.candle_pattern == 'shooting_star':
            return {'action': 'sell', 'confidence': 0.6}
        return {'action': 'neutral', 'confidence': 0.0}

    @staticmethod
    def to_dict(result: PriceActionResult) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'trend': result.trend,
            'momentum': result.momentum,
            'strength': result.strength,
            'recent_direction': result.recent_direction,
            'candle_pattern': result.candle_pattern
        }
