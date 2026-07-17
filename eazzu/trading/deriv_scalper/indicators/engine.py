"""
Indicator Engine
Combines multiple indicators for confluence-based trading signals
"""

from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

from ..config import TradingConfig
from .rsi import RSIIndicator, RSIResult
from .macd import MACDIndicator, MACDResult
from .ema import EMAIndicator, EMAResult
from .bollinger import BollingerBandsIndicator, BollingerResult
from .stochastic import StochasticIndicator, StochasticResult
from .atr import ATRIndicator, ATRResult
from .price_action import PriceActionIndicator, PriceActionResult


@dataclass
class IndicatorResult:
    """Combined result from all indicators"""
    timestamp: float
    symbol: str
    close: float

    # Individual indicator results
    rsi: Optional[RSIResult] = None
    macd: Optional[MACDResult] = None
    ema: Optional[EMAResult] = None
    bollinger: Optional[BollingerResult] = None
    stochastic: Optional[StochasticResult] = None
    atr: Optional[ATRResult] = None
    price_action: Optional[PriceActionResult] = None

    # Confluence analysis
    buy_signals: List[Dict[str, Any]] = field(default_factory=list)
    sell_signals: List[Dict[str, Any]] = field(default_factory=list)
    confluence_score: float = 0.0
    recommended_direction: Optional[str] = None


class IndicatorEngine:
    """
    Indicator Engine
    Calculates all configured indicators and generates confluence signals
    """

    def __init__(self, config: Optional[TradingConfig] = None):
        self.config = config or TradingConfig()

        # Initialize indicators based on config
        if self.config.use_rsi:
            self.rsi = RSIIndicator(
                period=self.config.rsi_period,
                overbought=self.config.rsi_overbought,
                oversold=self.config.rsi_oversold
            )

        if self.config.use_macd:
            self.macd = MACDIndicator(
                fast=self.config.macd_fast,
                slow=self.config.macd_slow,
                signal=self.config.macd_signal
            )

        if self.config.use_ema:
            self.ema = EMAIndicator(
                fast_period=self.config.ema_fast_period,
                slow_period=self.config.ema_slow_period,
                trend_lookback=self.config.ema_trend_lookback
            )

        if self.config.use_bollinger:
            self.bollinger = BollingerBandsIndicator(
                period=self.config.bollinger_period,
                std_dev=self.config.bollinger_std
            )

        if self.config.use_stochastic:
            self.stochastic = StochasticIndicator(
                k_period=self.config.stochastic_k,
                d_period=self.config.stochastic_d,
                overbought=self.config.stochastic_overbought,
                oversold=self.config.stochastic_oversold
            )

        if self.config.use_atr:
            self.atr = ATRIndicator(period=self.config.atr_period)

        self.price_action = PriceActionIndicator()

    def calculate(self, candles: List[Dict[str, Any]]) -> Optional[IndicatorResult]:
        """
        Calculate all indicators from candle data
        Returns IndicatorResult or None if insufficient data
        """
        if len(candles) < max(self.config.ema_trend_lookback, self.config.rsi_period + 1):
            return None

        # Extract OHLC data
        closes = [c.get('close', c.get('close', 0)) for c in candles]
        highs = [c.get('high', c.get('high', c.get('close', 0))) for c in candles]
        lows = [c.get('low', c.get('low', c.get('close', 0))) for c in candles]

        # Create result
        result = IndicatorResult(
            timestamp=candles[-1].get('epoch', candles[-1].get('time', 0)),
            symbol=self.config.symbol.symbol,
            close=closes[-1]
        )

        # Calculate each indicator
        if self.config.use_rsi and hasattr(self, 'rsi'):
            result.rsi = self.rsi.calculate(closes)

        if self.config.use_macd and hasattr(self, 'macd'):
            result.macd = self.macd.calculate(closes)

        if self.config.use_ema and hasattr(self, 'ema'):
            result.ema = self.ema.calculate(closes)

        if self.config.use_bollinger and hasattr(self, 'bollinger'):
            result.bollinger = self.bollinger.calculate(closes)

        if self.config.use_stochastic and hasattr(self, 'stochastic'):
            result.stochastic = self.stochastic.calculate(highs, lows, closes)

        if self.config.use_atr and hasattr(self, 'atr'):
            result.atr = self.atr.calculate(highs, lows, closes)

        result.price_action = self.price_action.calculate(highs, lows, closes)

        # Analyze confluence
        self._analyze_confluence(result)

        return result

    def _analyze_confluence(self, result: IndicatorResult) -> None:
        """
        Analyze confluence of all indicators
        Determine recommended trading direction
        """
        buy_signals = []
        sell_signals = []

        # RSI signals
        if result.rsi:
            if result.rsi.signal == 'oversold':
                buy_signals.append({'indicator': 'RSI', 'reason': 'oversold', 'confidence': result.rsi.strength})
            elif result.rsi.signal == 'overbought':
                sell_signals.append({'indicator': 'RSI', 'reason': 'overbought', 'confidence': result.rsi.strength})

        # MACD signals
        if result.macd:
            signal = self.macd.get_signal(result.macd)
            if signal:
                if signal['action'] in ('buy', 'bullish_bias'):
                    buy_signals.append({'indicator': 'MACD', 'reason': signal['action'], 'confidence': signal['confidence']})
                elif signal['action'] in ('sell', 'bearish_bias'):
                    sell_signals.append({'indicator': 'MACD', 'reason': signal['action'], 'confidence': signal['confidence']})

        # EMA signals
        if result.ema:
            signal = self.ema.get_signal(result.ema)
            if signal:
                if signal['action'] == 'buy':
                    buy_signals.append({'indicator': 'EMA', 'reason': 'bullish_trend', 'confidence': signal['confidence']})
                elif signal['action'] == 'sell':
                    sell_signals.append({'indicator': 'EMA', 'reason': 'bearish_trend', 'confidence': signal['confidence']})

        # Bollinger signals
        if result.bollinger:
            signal = self.bollinger.get_signal(result.bollinger)
            if signal:
                if signal['action'] == 'buy':
                    buy_signals.append({'indicator': 'Bollinger', 'reason': 'at_lower_band', 'confidence': signal['confidence']})
                elif signal['action'] == 'sell':
                    sell_signals.append({'indicator': 'Bollinger', 'reason': 'at_upper_band', 'confidence': signal['confidence']})

        # Stochastic signals
        if result.stochastic:
            signal = self.stochastic.get_signal(result.stochastic)
            if signal:
                if signal['action'] in ('buy', 'bullish_bias'):
                    buy_signals.append({'indicator': 'Stochastic', 'reason': signal['action'], 'confidence': signal['confidence']})
                elif signal['action'] in ('sell', 'bearish_bias'):
                    sell_signals.append({'indicator': 'Stochastic', 'reason': signal['action'], 'confidence': signal['confidence']})

        # Price action signals
        if result.price_action:
            signal = self.price_action.get_signal(result.price_action)
            if signal:
                if signal['action'] == 'buy':
                    buy_signals.append({'indicator': 'PriceAction', 'reason': result.price_action.candle_pattern, 'confidence': signal['confidence']})
                elif signal['action'] == 'sell':
                    sell_signals.append({'indicator': 'PriceAction', 'reason': result.price_action.candle_pattern, 'confidence': signal['confidence']})

        # Store signals
        result.buy_signals = buy_signals
        result.sell_signals = sell_signals

        # Calculate confluence score
        buy_score = sum(s['confidence'] for s in buy_signals)
        sell_score = sum(s['confidence'] for s in sell_signals)

        if buy_signals or sell_signals:
            total_signals = len(buy_signals) + len(sell_signals)
            result.confluence_score = max(buy_score, sell_score) / max(total_signals, 1)
        else:
            result.confluence_score = 0.0

        # Determine recommended direction
        min_required = self.config.min_indicators_agree

        if len(buy_signals) >= min_required and buy_score > sell_score:
            result.recommended_direction = 'CALL'
        elif len(sell_signals) >= min_required and sell_score > buy_score:
            result.recommended_direction = 'PUT'
        elif buy_score > sell_score * 1.5:
            result.recommended_direction = 'CALL'
        elif sell_score > buy_score * 1.5:
            result.recommended_direction = 'PUT'
        else:
            result.recommended_direction = None  # No clear signal

    def get_trade_signal(self, result: IndicatorResult) -> Tuple[Optional[str], float]:
        """
        Get final trade signal from confluence analysis
        Returns (direction, confidence) tuple
        """
        if not result.recommended_direction:
            return None, 0.0

        # Require minimum confluence
        min_indicators = self.config.min_indicators_agree

        if result.recommended_direction == 'CALL':
            if len(result.buy_signals) >= min_indicators:
                return 'CALL', result.confluence_score
        elif result.recommended_direction == 'PUT':
            if len(result.sell_signals) >= min_indicators:
                return 'PUT', result.confluence_score

        return None, 0.0

    def to_dict(self, result: IndicatorResult) -> Dict[str, Any]:
        """Convert result to dictionary for logging/display"""
        data = {
            'timestamp': result.timestamp,
            'symbol': result.symbol,
            'close': result.close,
            'confluence_score': result.confluence_score,
            'recommended_direction': result.recommended_direction,
            'buy_signals': result.buy_signals,
            'sell_signals': result.sell_signals
        }

        # Add individual indicator values
        if result.rsi:
            data['rsi'] = RSIIndicator.to_dict(result.rsi)
        if result.macd:
            data['macd'] = MACDIndicator.to_dict(result.macd)
        if result.ema:
            data['ema'] = EMAIndicator.to_dict(result.ema)
        if result.bollinger:
            data['bollinger'] = BollingerBandsIndicator.to_dict(result.bollinger)
        if result.stochastic:
            data['stochastic'] = StochasticIndicator.to_dict(result.stochastic)
        if result.atr:
            data['atr'] = ATRIndicator.to_dict(result.atr)
        if result.price_action:
            data['price_action'] = PriceActionIndicator.to_dict(result.price_action)

        return data
