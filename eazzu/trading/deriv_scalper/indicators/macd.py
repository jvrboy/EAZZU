"""
MACD (Moving Average Convergence Divergence) Indicator
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class MACDResult:
    """MACD calculation result"""
    macd_line: float
    signal_line: float
    histogram: float
    crossover: str  # 'bullish', 'bearish', 'none'
    divergence: float  # -1.0 to 1.0


class MACDIndicator:
    """
    MACD (Moving Average Convergence Divergence)
    Trend-following momentum indicator
    """

    def __init__(self, fast: int = 12, slow: int = 26, signal: int = 9):
        self.fast = fast
        self.slow = slow
        self.signal = signal

    def _ema(self, prices: List[float], period: int) -> float:
        """Calculate EMA"""
        if len(prices) < period:
            return prices[-1] if prices else 0

        multiplier = 2 / (period + 1)
        ema = sum(prices[:period]) / period

        for price in prices[period:]:
            ema = (price - ema) * multiplier + ema

        return ema

    def calculate(self, prices: List[float]) -> Optional[MACDResult]:
        """
        Calculate MACD from price list
        Returns MACDResult or None if insufficient data
        """
        min_period = self.slow + self.signal
        if len(prices) < min_period:
            return None

        # Calculate MACD line
        ema_fast = self._ema(prices, self.fast)
        ema_slow = self._ema(prices, self.slow)
        macd_line = ema_fast - ema_slow

        # Calculate signal line (EMA of MACD)
        # We need historical MACD values for this
        macd_values = []
        for i in range(self.slow - 1, len(prices)):
            ema_f = self._ema(prices[:i+1], self.fast)
            ema_s = self._ema(prices[:i+1], self.slow)
            macd_values.append(ema_f - ema_s)

        if len(macd_values) < self.signal:
            signal_line = macd_line
        else:
            signal_line = self._ema(macd_values[-self.signal:], self.signal)

        histogram = macd_line - signal_line

        # Determine crossover
        if len(macd_values) >= 2:
            prev_hist = macd_values[-2] - (self._ema(macd_values[-self.signal-1:-1], self.signal) if len(macd_values) >= self.signal + 1 else macd_values[-2])
            if prev_hist < 0 and histogram > 0:
                crossover = 'bullish'
            elif prev_hist > 0 and histogram < 0:
                crossover = 'bearish'
            else:
                crossover = 'none'
        else:
            crossover = 'none'

        # Calculate divergence (simplified)
        if histogram != 0:
            divergence = histogram / abs(histogram) * min(abs(histogram) / 1.0, 1.0)
        else:
            divergence = 0

        return MACDResult(
            macd_line=macd_line,
            signal_line=signal_line,
            histogram=histogram,
            crossover=crossover,
            divergence=divergence
        )

    def get_signal(self, result: MACDResult) -> Optional[Dict[str, Any]]:
        """Get trading signal from MACD result"""
        if result.crossover == 'bullish':
            return {'action': 'buy', 'confidence': min(abs(result.histogram) * 2, 1.0)}
        elif result.crossover == 'bearish':
            return {'action': 'sell', 'confidence': min(abs(result.histogram) * 2, 1.0)}
        elif result.histogram > 0:
            return {'action': 'bullish_bias', 'confidence': min(result.histogram, 1.0)}
        elif result.histogram < 0:
            return {'action': 'bearish_bias', 'confidence': min(abs(result.histogram), 1.0)}
        return {'action': 'neutral', 'confidence': 0.0}

    @staticmethod
    def to_dict(result: MACDResult) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'macd_line': result.macd_line,
            'signal_line': result.signal_line,
            'histogram': result.histogram,
            'crossover': result.crossover,
            'divergence': result.divergence
        }
