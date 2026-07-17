"""
Bollinger Bands Indicator
"""

from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import statistics


@dataclass
class BollingerResult:
    """Bollinger Bands calculation result"""
    upper_band: float
    middle_band: float
    lower_band: float
    bandwidth: float
    position: float  # 0.0 = lower band, 1.0 = upper band
    signal: str  # 'oversold', 'overbought', 'neutral'


class BollingerBandsIndicator:
    """
    Bollinger Bands
    Volatility indicator with upper and lower bands
    """

    def __init__(self, period: int = 20, std_dev: float = 2.0):
        self.period = period
        self.std_dev = std_dev

    def calculate(self, prices: List[float]) -> Optional[BollingerResult]:
        """
        Calculate Bollinger Bands from price list
        Returns BollingerResult or None if insufficient data
        """
        if len(prices) < self.period:
            return None

        recent_prices = prices[-self.period:]

        # Calculate middle band (SMA)
        middle_band = statistics.mean(recent_prices)

        # Calculate standard deviation
        std = statistics.stdev(recent_prices)

        # Calculate bands
        upper_band = middle_band + (std * self.std_dev)
        lower_band = middle_band - (std * self.std_dev)

        # Calculate bandwidth
        bandwidth = (upper_band - lower_band) / middle_band if middle_band != 0 else 0

        # Calculate position (where is current price relative to bands)
        current_price = prices[-1]
        if upper_band != lower_band:
            position = (current_price - lower_band) / (upper_band - lower_band)
        else:
            position = 0.5

        # Determine signal
        if position <= 0.2:
            signal = 'oversold'
        elif position >= 0.8:
            signal = 'overbought'
        else:
            signal = 'neutral'

        return BollingerResult(
            upper_band=upper_band,
            middle_band=middle_band,
            lower_band=lower_band,
            bandwidth=bandwidth,
            position=position,
            signal=signal
        )

    def get_signal(self, result: BollingerResult) -> Optional[Dict[str, Any]]:
        """Get trading signal from Bollinger result"""
        if result.signal == 'oversold':
            return {'action': 'buy', 'confidence': 1.0 - result.position}
        elif result.signal == 'overbought':
            return {'action': 'sell', 'confidence': result.position}
        elif result.position < 0.5:
            return {'action': 'bullish_bias', 'confidence': 0.5 - result.position}
        else:
            return {'action': 'bearish_bias', 'confidence': result.position - 0.5}

    @staticmethod
    def to_dict(result: BollingerResult) -> Dict[str, Any]:
        """Convert result to dictionary"""
        return {
            'upper_band': result.upper_band,
            'middle_band': result.middle_band,
            'lower_band': result.lower_band,
            'bandwidth': result.bandwidth,
            'position': result.position,
            'signal': result.signal
        }
