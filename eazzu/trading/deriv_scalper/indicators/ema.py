"""
EMA (Exponential Moving Average) Indicator
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class EMAResult:
    """EMA calculation result"""
    fast_ema: float
    slow_ema: float
    trend_ema: float
    price: float
    trend: str  # 'bullish', 'bearish', 'neutral'
    alignment: float  # 0.0 to 1.0


class EMAIndicator:
    """
    Exponential Moving Average (EMA)
    Used for trend detection and crossover strategies
    """

    def __init__(self, fast_period: int = 9, slow_period: int = 21, trend_lookback: int = 50):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.trend_lookback = trend_lookback

    def _calculate_ema(self, prices: List[float], period: int) -> float:
        """Calculate EMA"""
        if len(prices) < period:
            return prices[-1] if prices else 0

        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period

        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema

        return ema

    def calculate(self, prices: List[float]) -> Optional[EMAResult]:
        """
        Calculate EMA indicators from price list
        Returns EMAResult or None if insufficient data
        """
        if len(prices) < self.trend_lookback:
            return None

        # Calculate EMAs
        fast_ema = self._calculate_ema(prices, self.fast_period)
        slow_ema = self._calculate_ema(prices, self.slow_period)
        trend_ema = self._calculate_ema(prices, self.trend_lookback)

        current_price = prices[-1]

        # Determine trend
        if current_price > trend_ema and fast_ema > slow_ema:
            trend = 'bullish'
        elif current_price < trend_ema and fast_ema < slow_ema:
            trend = 'bearish'
        elif fast_ema > slow_ema:
            trend = 'bullish'
        elif fast_ema < slow_ema:
            trend = 'bearish'
        else:
            trend = 'neutral'

        # Calculate alignment strength
        alignment = 0.0
        if trend == 'bullish':
            if current_price > trend_ema:
                alignment += 0.33
            if fast_ema > slow_ema:
                alignment += 0.33
            if current_price > fast_ema:
                alignment += 0.34
        elif trend == 'bearish':
            if current_price < trend_ema:
                alignment += 0.33
            if fast_ema < slow_ema:
                alignment += 0.33
            if current_price < fast_ema:
                alignment += 0.34

        return EMAResult(
            fast_ema=fast_ema,
            slow_ema=slow_ema,
            trend_ema=trend_ema,
            price=current_price,
            trend=trend,
            alignment=alignment
        )

    def get_signal(self, result: EMAResult) -> Optional[Dict[str, Any]]:
        """Get trading signal from EMA result"""
        if result.trend == 'bullish':
            return {'action': 'buy', 'confidence': result.alignment}
        elif result.trend == 'bearish':
            return {'action': 'sell', 'confidence': result.alignment}
        return {'action': 'neutral', 'confidence': 0.0}

    @staticmethod
    def to_dict(result: EMAResult) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'fast_ema': result.fast_ema,
            'slow_ema': result.slow_ema,
            'trend_ema': result.trend_ema,
            'price': result.price,
            'trend': result.trend,
            'alignment': result.alignment
        }
