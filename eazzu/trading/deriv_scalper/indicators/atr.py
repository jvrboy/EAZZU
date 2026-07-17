"""
ATR (Average True Range) Indicator
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class ATRResult:
    """ATR calculation result"""
    atr: float
    atr_percent: float  # ATR as percentage of price
    volatility: str  # 'high', 'medium', 'low'
    raw_range: float


class ATRIndicator:
    """
    Average True Range (ATR)
    Market volatility indicator
    """

    def __init__(self, period: int = 14):
        self.period = period

    def calculate(self, highs: List[float], lows: List[float],
                  closes: List[float]) -> Optional[ATRResult]:
        """
        Calculate ATR from OHLC data
        Returns ATRResult or None if insufficient data
        """
        if len(closes) < self.period + 1:
            return None

        # Calculate True Range for each period
        true_ranges = []
        for i in range(1, len(closes)):
            high = highs[i]
            low = lows[i]
            prev_close = closes[i-1]

            tr1 = high - low
            tr2 = abs(high - prev_close)
            tr3 = abs(low - prev_close)

            true_range = max(tr1, tr2, tr3)
            true_ranges.append(true_range)

        # Calculate ATR (using simple moving average for simplicity)
        if len(true_ranges) < self.period:
            atr = sum(true_ranges) / len(true_ranges)
        else:
            atr = sum(true_ranges[-self.period:]) / self.period

        current_price = closes[-1]

        # Calculate ATR as percentage
        atr_percent = (atr / current_price) * 100 if current_price != 0 else 0

        # Determine volatility level
        if atr_percent > 0.5:
            volatility = 'high'
        elif atr_percent > 0.2:
            volatility = 'medium'
        else:
            volatility = 'low'

        return ATRResult(
            atr=atr,
            atr_percent=atr_percent,
            volatility=volatility,
            raw_range=true_ranges[-1] if true_ranges else 0
        )

    def get_signal(self, result: ATRResult) -> Optional[Dict[str, Any]]:
        """Get volatility signal from ATR result"""
        # ATR is mainly used for position sizing and stop loss
        # Not typically a direct trading signal
        return {
            'action': 'info',
            'confidence': 1.0,
            'volatility': result.volatility,
            'atr_percent': result.atr_percent
        }

    @staticmethod
    def to_dict(result: ATRResult) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'atr': result.atr,
            'atr_percent': result.atr_percent,
            'volatility': result.volatility,
            'raw_range': result.raw_range
        }
