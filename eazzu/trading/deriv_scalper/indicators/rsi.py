"""
RSI (Relative Strength Index) Indicator
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class RSIResult:
    """RSI calculation result"""
    value: float
    signal: str  # 'overbought', 'oversold', 'neutral'
    strength: float  # 0.0 to 1.0


class RSIIndicator:
    """
    Relative Strength Index (RSI)
    Momentum oscillator measuring speed and change of price movements
    """

    def __init__(self, period: int = 14, overbought: float = 70, oversold: float = 30):
        self.period = period
        self.overbought = overbought
        self.oversold = oversold

    def calculate(self, prices: List[float]) -> Optional[RSIResult]:
        """
        Calculate RSI from price list
        Returns RSIResult or None if insufficient data
        """
        if len(prices) < self.period + 1:
            return None

        # Calculate price changes
        deltas = [prices[i] - prices[i-1] for i in range(1, len(prices))]

        # Separate gains and losses
        gains = [d if d > 0 else 0 for d in deltas[-self.period:]]
        losses = [-d if d < 0 else 0 for d in deltas[-self.period:]]

        # Calculate average gains and losses
        avg_gain = sum(gains) / self.period
        avg_loss = sum(losses) / self.period

        # Handle zero loss case
        if avg_loss == 0:
            rsi = 100
        else:
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))

        # Determine signal
        if rsi >= self.overbought:
            signal = 'overbought'
            strength = min((rsi - self.overbought) / (100 - self.overbought), 1.0)
        elif rsi <= self.oversold:
            signal = 'oversold'
            strength = min((self.oversold - rsi) / self.oversold, 1.0)
        else:
            signal = 'neutral'
            strength = 0.0

        return RSIResult(value=rsi, signal=signal, strength=strength)

    def get_signal(self, result: RSIResult, trade_direction: str) -> Optional[Dict[str, Any]]:
        """
        Get trading signal from RSI result
        trade_direction: 'CALL' or 'PUT'
        """
        if result.signal == 'oversold' and trade_direction == 'CALL':
            return {'action': 'strong_buy', 'confidence': result.strength}
        elif result.signal == 'overbought' and trade_direction == 'PUT':
            return {'action': 'strong_sell', 'confidence': result.strength}
        elif result.signal == 'neutral':
            return {'action': 'neutral', 'confidence': 0.0}
        return None

    @staticmethod
    def to_dict(result: RSIResult) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'value': result.value,
            'signal': result.signal,
            'strength': result.strength
        }
