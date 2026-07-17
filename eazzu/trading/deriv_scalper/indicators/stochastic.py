"""
Stochastic Oscillator Indicator
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class StochasticResult:
    """Stochastic calculation result"""
    k: float  # %K line
    d: float  # %D line
    signal: str  # 'overbought', 'oversold', 'neutral', 'bullish_cross', 'bearish_cross'
    momentum: float  # -1.0 to 1.0


class StochasticIndicator:
    """
    Stochastic Oscillator
    Momentum indicator comparing closing price to price range
    """

    def __init__(self, k_period: int = 14, d_period: int = 3,
                 overbought: float = 80, oversold: float = 20):
        self.k_period = k_period
        self.d_period = d_period
        self.overbought = overbought
        self.oversold = oversold
        self._prev_k = None
        self._prev_d = None

    def calculate(self, highs: List[float], lows: List[float],
                  closes: List[float]) -> Optional[StochasticResult]:
        """
        Calculate Stochastic Oscillator
        Returns StochasticResult or None if insufficient data
        """
        if len(closes) < self.k_period or len(highs) < self.k_period or len(lows) < self.k_period:
            return None

        # Calculate %K
        recent_closes = closes[-self.k_period:]
        recent_highs = highs[-self.k_period:]
        recent_lows = lows[-self.k_period:]

        current_close = closes[-1]
        highest_high = max(recent_highs)
        lowest_low = min(recent_lows)

        if highest_high != lowest_low:
            k = 100 * (current_close - lowest_low) / (highest_high - lowest_low)
        else:
            k = 50

        # Calculate %D (SMA of %K)
        if self._prev_k is None:
            self._prev_k = k
            d = k
        else:
            # Simple smoothing for demo
            d = (self._prev_k + k) / 2

        self._prev_k = k
        prev_d = self._prev_d or d
        self._prev_d = d

        # Determine signal
        if k >= self.overbought:
            signal = 'overbought'
        elif k <= self.oversold:
            signal = 'oversold'
        elif prev_d < self.oversold and d >= self.oversold:
            signal = 'bullish_cross'
        elif prev_d > self.overbought and d <= self.overbought:
            signal = 'bearish_cross'
        else:
            signal = 'neutral'

        # Calculate momentum
        momentum = (k - 50) / 50  # -1.0 to 1.0

        return StochasticResult(
            k=k,
            d=d,
            signal=signal,
            momentum=momentum
        )

    def get_signal(self, result: StochasticResult) -> Optional[Dict[str, Any]]:
        """Get trading signal from Stochastic result"""
        if result.signal == 'oversold' or result.signal == 'bullish_cross':
            return {'action': 'buy', 'confidence': abs(result.momentum)}
        elif result.signal == 'overbought' or result.signal == 'bearish_cross':
            return {'action': 'sell', 'confidence': abs(result.momentum)}
        elif result.k > 50:
            return {'action': 'bullish_bias', 'confidence': result.momentum}
        else:
            return {'action': 'bearish_bias', 'confidence': abs(result.momentum)}

    @staticmethod
    def to_dict(result: StochasticResult) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'k': result.k,
            'd': result.d,
            'signal': result.signal,
            'momentum': result.momentum
        }
