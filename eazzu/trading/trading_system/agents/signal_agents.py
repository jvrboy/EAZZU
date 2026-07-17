"""
Signal Agents
=============
Specialized AI agents for different analysis strategies.
Each agent has unique expertise and contributes to the council decision.
"""

import numpy as np
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
from enum import Enum

from core.logger import agent_logger
from core.types import (
    MarketData, TechnicalIndicators, AgentVote, 
    Direction, MarketRegime, OHLCV
)
from analysis.indicators import TechnicalAnalyzer, PatternDetector
from models.ml_models import EnsemblePredictor, ModelPrediction


class AgentType(Enum):
    """Types of analysis agents."""
    TREND = "trend"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    PATTERN = "pattern"
    ML_PREDICTOR = "ml_predictor"
    SUPPORT_RESISTANCE = "support_resistance"
    SENTIMENT = "sentiment"


class BaseAgent(ABC):
    """Base class for all signal agents."""
    
    def __init__(self, name: str, agent_type: AgentType, weight: float = 1.0):
        self.name = name
        self.agent_type = agent_type
        self.weight = weight
        self.analyzer = TechnicalAnalyzer()
        self.pattern_detector = PatternDetector()
        self.is_active = True
        self.performance_score = 1.0
        self.total_signals = 0
        self.successful_signals = 0
        
        agent_logger.info(f"Agent '{name}' ({agent_type.value}) initialized")
    
    @abstractmethod
    def analyze(self, market_data: MarketData, 
                indicators: TechnicalIndicators,
                ml_prediction: Optional[ModelPrediction] = None) -> AgentVote:
        """Analyze market and return vote."""
        pass
    
    def update_performance(self, was_correct: bool):
        """Update performance tracking."""
        self.total_signals += 1
        if was_correct:
            self.successful_signals += 1
        
        if self.total_signals > 0:
            self.performance_score = self.successful_signals / self.total_signals
    
    def get_confidence(self) -> float:
        """Get agent's current confidence based on performance."""
        return 0.5 + 0.5 * self.performance_score


class TrendAgent(BaseAgent):
    """
    Trend-following agent using moving averages and trend strength.
    Specializes in identifying and following established trends.
    """
    
    def __init__(self):
        super().__init__("TrendMaster", AgentType.TREND, weight=1.2)
    
    def analyze(self, market_data: MarketData,
                indicators: TechnicalIndicators,
                ml_prediction: Optional[ModelPrediction] = None) -> AgentVote:
        
        closes = market_data.closes
        reasons = []
        score = 0.0
        
        # Moving average alignment
        if closes[-1] > indicators.sma_20 > indicators.sma_50:
            score += 0.3
            reasons.append("Price above SMA20 > SMA50 (bullish)")
        elif closes[-1] < indicators.sma_20 < indicators.sma_50:
            score -= 0.3
            reasons.append("Price below SMA20 < SMA50 (bearish)")
        
        if closes[-1] > indicators.sma_200:
            score += 0.2
            reasons.append("Price above SMA200")
        elif closes[-1] < indicators.sma_200:
            score -= 0.2
            reasons.append("Price below SMA200")
        
        # EMA crossovers
        if indicators.ema_12 > indicators.ema_26:
            score += 0.2
            reasons.append("EMA12 > EMA26 (bullish cross)")
        else:
            score -= 0.2
            reasons.append("EMA12 < EMA26 (bearish cross)")
        
        # ADX trend strength
        if indicators.adx > 25:
            if indicators.adx_plus_di > indicators.adx_minus_di:
                score += 0.2
                reasons.append(f"Strong uptrend (ADX={indicators.adx:.1f})")
            else:
                score -= 0.2
                reasons.append(f"Strong downtrend (ADX={indicators.adx:.1f})")
        
        # Trend slope
        slope, _, r_value, _, _ = self.analyzer.trend_line(closes, 20)
        if slope > 0:
            score += 0.1 * r_value
            reasons.append(f"Upward slope (r={r_value:.2f})")
        else:
            score -= 0.1 * r_value
            reasons.append(f"Downward slope (r={r_value:.2f})")
        
        # Ichimoku cloud
        if closes[-1] > indicators.ichimoku_senkou_a and closes[-1] > indicators.ichimoku_senkou_b:
            score += 0.15
            reasons.append("Price above Ichimoku cloud")
        elif closes[-1] < indicators.ichimoku_senkou_a and closes[-1] < indicators.ichimoku_senkou_b:
            score -= 0.15
            reasons.append("Price below Ichimoku cloud")
        
        # Determine direction
        if score > 0.3:
            direction = Direction.STRONG_BULLISH if score > 0.6 else Direction.BULLISH
        elif score < -0.3:
            direction = Direction.STRONG_BEARISH if score < -0.6 else Direction.BEARISH
        else:
            direction = Direction.NEUTRAL
        
        confidence = min(abs(score), 1.0)
        
        return AgentVote(
            agent_name=self.name,
            agent_type=self.agent_type.value,
            direction=direction,
            confidence=confidence,
            reasoning="; ".join(reasons),
            indicators_used=["SMA", "EMA", "ADX", "Ichimoku", "Trend Line"],
            weight=self.weight * self.get_confidence()
        )


class MomentumAgent(BaseAgent):
    """
    Momentum agent using RSI, MACD, Stochastic, and other oscillators.
    Identifies overbought/oversold conditions and momentum shifts.
    """
    
    def __init__(self):
        super().__init__("MomentumForce", AgentType.MOMENTUM, weight=1.1)
    
    def analyze(self, market_data: MarketData,
                indicators: TechnicalIndicators,
                ml_prediction: Optional[ModelPrediction] = None) -> AgentVote:
        
        reasons = []
        score = 0.0
        
        # RSI analysis
        if indicators.rsi_14 > 70:
            score -= 0.25
            reasons.append(f"RSI overbought ({indicators.rsi_14:.1f})")
        elif indicators.rsi_14 < 30:
            score += 0.25
            reasons.append(f"RSI oversold ({indicators.rsi_14:.1f})")
        elif 40 <= indicators.rsi_14 <= 60:
            reasons.append(f"RSI neutral ({indicators.rsi_14:.1f})")
        else:
            if indicators.rsi_14 > 55:
                score += 0.1
                reasons.append(f"RSI bullish bias ({indicators.rsi_14:.1f})")
            else:
                score -= 0.1
                reasons.append(f"RSI bearish bias ({indicators.rsi_14:.1f})")
        
        # MACD analysis
        if indicators.macd_histogram > 0 and indicators.macd_line > indicators.macd_signal:
            score += 0.25
            reasons.append("MACD bullish (hist>0, line>signal)")
        elif indicators.macd_histogram < 0 and indicators.macd_line < indicators.macd_signal:
            score -= 0.25
            reasons.append("MACD bearish (hist<0, line<signal)")
        
        # MACD divergence check
        closes = market_data.closes
        if len(closes) >= 20:
            recent_closes = closes[-10:]
            recent_macd = [indicators.macd_line] * 10  # Simplified
            
            if recent_closes[-1] > recent_closes[0] and indicators.macd_line < indicators.macd_line * 0.9:
                score -= 0.2
                reasons.append("Bearish MACD divergence")
            elif recent_closes[-1] < recent_closes[0] and indicators.macd_line > indicators.macd_line * 1.1:
                score += 0.2
                reasons.append("Bullish MACD divergence")
        
        # Stochastic
        if indicators.stochastic_k > 80 and indicators.stochastic_d > 80:
            score -= 0.15
            reasons.append("Stochastic overbought")
        elif indicators.stochastic_k < 20 and indicators.stochastic_d < 20:
            score += 0.15
            reasons.append("Stochastic oversold")
        
        # Stochastic cross
        if indicators.stochastic_k > indicators.stochastic_d:
            score += 0.1
            reasons.append("Stochastic K > D")
        else:
            score -= 0.1
            reasons.append("Stochastic K < D")
        
        # Williams %R
        if indicators.williams_r > -20:
            score -= 0.1
            reasons.append("Williams %R overbought")
        elif indicators.williams_r < -80:
            score += 0.1
            reasons.append("Williams %R oversold")
        
        # CCI
        if indicators.cci_20 > 100:
            score -= 0.1
            reasons.append("CCI overbought")
        elif indicators.cci_20 < -100:
            score += 0.1
            reasons.append("CCI oversold")
        
        # MFI
        if indicators.mfi_14 > 80:
            score -= 0.1
            reasons.append("MFI overbought")
        elif indicators.mfi_14 < 20:
            score += 0.1
            reasons.append("MFI oversold")
        
        # Determine direction
        if score > 0.4:
            direction = Direction.STRONG_BULLISH if score > 0.7 else Direction.BULLISH
        elif score < -0.4:
            direction = Direction.STRONG_BEARISH if score < -0.7 else Direction.BEARISH
        else:
            direction = Direction.NEUTRAL
        
        confidence = min(abs(score), 1.0)
        
        return AgentVote(
            agent_name=self.name,
            agent_type=self.agent_type.value,
            direction=direction,
            confidence=confidence,
            reasoning="; ".join(reasons),
            indicators_used=["RSI", "MACD", "Stochastic", "Williams %R", "CCI", "MFI"],
            weight=self.weight * self.get_confidence()
        )


class VolatilityAgent(BaseAgent):
    """
    Volatility-based agent analyzing Bollinger Bands, ATR, and volatility regimes.
    Identifies volatility contractions (squeeze) and expansions.
    """
    
    def __init__(self):
        super().__init__("VolatilityEdge", AgentType.VOLATILITY, weight=0.9)
    
    def analyze(self, market_data: MarketData,
                indicators: TechnicalIndicators,
                ml_prediction: Optional[ModelPrediction] = None) -> AgentVote:
        
        closes = market_data.closes
        reasons = []
        score = 0.0
        
        # Bollinger Band position
        bb_pos = indicators.bb_position
        
        if bb_pos > 0.95:
            score -= 0.3
            reasons.append(f"Price at upper BB ({bb_pos:.2f})")
        elif bb_pos < 0.05:
            score += 0.3
            reasons.append(f"Price at lower BB ({bb_pos:.2f})")
        elif 0.4 <= bb_pos <= 0.6:
            reasons.append(f"Price in BB middle ({bb_pos:.2f})")
        
        # Bollinger Band width (squeeze detection)
        bb_width = indicators.bb_width
        
        # Calculate historical BB width for comparison
        if len(closes) >= 100:
            hist_volatility = np.std(np.diff(closes[-100:]) / closes[-100:-1])
            current_vol = indicators.atr_14 / closes[-1] if closes[-1] > 0 else 0
            
            if current_vol < hist_volatility * 0.5:
                reasons.append("Volatility squeeze detected - potential breakout")
                # Squeeze often precedes directional move
                if closes[-1] > closes[-5]:
                    score += 0.15
                else:
                    score -= 0.15
        
        # ATR analysis
        atr_pct = indicators.atr_14 / closes[-1] * 100 if closes[-1] > 0 else 0
        
        if atr_pct < 0.1:
            reasons.append(f"Very low volatility ({atr_pct:.3f}%)")
        elif atr_pct > 0.5:
            reasons.append(f"High volatility ({atr_pct:.3f}%)")
            # In high volatility, fade extremes
            if bb_pos > 0.9:
                score -= 0.2
            elif bb_pos < 0.1:
                score += 0.2
        
        # Band walking
        if bb_pos > 0.8 and bb_pos > 0.5:
            score += 0.1  # Walking upper band = bullish
            reasons.append("Walking upper BB")
        elif bb_pos < 0.2 and bb_pos < 0.5:
            score -= 0.1  # Walking lower band = bearish
            reasons.append("Walking lower BB")
        
        # Keltner vs Bollinger
        # Simplified: use ATR as proxy
        if indicators.atr_14 < indicators.atr_7:
            reasons.append("ATR contracting - volatility decreasing")
        else:
            reasons.append("ATR expanding - volatility increasing")
        
        # Determine direction
        if score > 0.3:
            direction = Direction.BULLISH
        elif score < -0.3:
            direction = Direction.BEARISH
        else:
            direction = Direction.NEUTRAL
        
        confidence = min(abs(score) + 0.1, 1.0)
        
        return AgentVote(
            agent_name=self.name,
            agent_type=self.agent_type.value,
            direction=direction,
            confidence=confidence,
            reasoning="; ".join(reasons),
            indicators_used=["Bollinger Bands", "ATR", "Volatility Regime"],
            weight=self.weight * self.get_confidence()
        )


class PatternAgent(BaseAgent):
    """
    Pattern recognition agent detecting candlestick patterns and chart patterns.
    """
    
    def __init__(self):
        super().__init__("PatternHunter", AgentType.PATTERN, weight=1.0)
    
    def analyze(self, market_data: MarketData,
                indicators: TechnicalIndicators,
                ml_prediction: Optional[ModelPrediction] = None) -> AgentVote:
        
        candles = market_data.candles
        reasons = []
        score = 0.0
        
        # Detect candlestick patterns
        patterns = self.pattern_detector.detect_patterns(candles[-10:])
        pattern_bias = self.pattern_detector.get_pattern_bias(patterns)
        
        if patterns:
            top_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)[:3]
            for name, conf in top_patterns:
                reasons.append(f"Pattern: {name} ({conf:.0%})")
        
        score += pattern_bias * 0.4
        
        # Detect support/resistance proximity
        highs = market_data.highs
        lows = market_data.lows
        closes = market_data.closes
        
        support_levels, resistance_levels = self.analyzer.detect_support_resistance(closes)
        
        current_price = closes[-1]
        
        # Check proximity to support
        for support in support_levels[-3:]:
            if abs(current_price - support) / current_price < 0.005:  # Within 0.5%
                score += 0.25
                reasons.append(f"Near support at {support:.5f}")
                break
        
        # Check proximity to resistance
        for resistance in resistance_levels[-3:]:
            if abs(current_price - resistance) / current_price < 0.005:
                score -= 0.25
                reasons.append(f"Near resistance at {resistance:.5f}")
                break
        
        # Volume confirmation
        if indicators.volume_ratio > 1.5:
            reasons.append(f"High volume ({indicators.volume_ratio:.1f}x)")
            score *= 1.2  # Strengthen signal on volume
        elif indicators.volume_ratio < 0.5:
            reasons.append(f"Low volume ({indicators.volume_ratio:.1f}x)")
            score *= 0.8  # Weaken signal on low volume
        
        # Parabolic SAR
        if indicators.psar_trend == "bullish":
            score += 0.1
            reasons.append("PSAR bullish")
        elif indicators.psar_trend == "bearish":
            score -= 0.1
            reasons.append("PSAR bearish")
        
        # Determine direction
        if score > 0.3:
            direction = Direction.STRONG_BULLISH if score > 0.6 else Direction.BULLISH
        elif score < -0.3:
            direction = Direction.STRONG_BEARISH if score < -0.6 else Direction.BEARISH
        else:
            direction = Direction.NEUTRAL
        
        confidence = min(abs(score), 1.0)
        
        return AgentVote(
            agent_name=self.name,
            agent_type=self.agent_type.value,
            direction=direction,
            confidence=confidence,
            reasoning="; ".join(reasons),
            indicators_used=["Candlestick Patterns", "Support/Resistance", "Volume", "PSAR"],
            weight=self.weight * self.get_confidence()
        )


class MLAgent(BaseAgent):
    """
    Machine Learning agent using trained ensemble models.
    Provides predictions based on historical pattern recognition.
    """
    
    def __init__(self, predictor: Optional[EnsemblePredictor] = None):
        super().__init__("NeuralPredictor", AgentType.ML_PREDICTOR, weight=1.3)
        self.predictor = predictor
    
    def set_predictor(self, predictor: EnsemblePredictor):
        """Set the ML predictor model."""
        self.predictor = predictor
    
    def analyze(self, market_data: MarketData,
                indicators: TechnicalIndicators,
                ml_prediction: Optional[ModelPrediction] = None) -> AgentVote:
        
        reasons = []
        score = 0.0
        
        if ml_prediction is None and self.predictor and self.predictor.is_trained:
            ml_prediction = self.predictor.predict(market_data, indicators)
        
        if ml_prediction is None:
            return AgentVote(
                agent_name=self.name,
                agent_type=self.agent_type.value,
                direction=Direction.NEUTRAL,
                confidence=0.0,
                reasoning="No ML prediction available",
                indicators_used=[],
                weight=0
            )
        
        # Convert prediction to score
        if ml_prediction.direction == 'BUY':
            score += ml_prediction.confidence * 0.8
            reasons.append(f"ML predicts BUY ({ml_prediction.confidence:.1%})")
        elif ml_prediction.direction == 'SELL':
            score -= ml_prediction.confidence * 0.8
            reasons.append(f"ML predicts SELL ({ml_prediction.confidence:.1%})")
        else:
            reasons.append(f"ML predicts HOLD ({ml_prediction.probability_hold:.1%})")
        
        # Probability distribution analysis
        prob_spread = abs(ml_prediction.probability_up - ml_prediction.probability_down)
        reasons.append(f"Probability spread: {prob_spread:.3f}")
        
        if prob_spread > 0.3:
            score *= 1.2  # High confidence prediction
        
        # Determine direction
        if score > 0.3:
            direction = Direction.BULLISH if score < 0.6 else Direction.STRONG_BULLISH
        elif score < -0.3:
            direction = Direction.BEARISH if score > -0.6 else Direction.STRONG_BEARISH
        else:
            direction = Direction.NEUTRAL
        
        confidence = ml_prediction.confidence
        
        return AgentVote(
            agent_name=self.name,
            agent_type=self.agent_type.value,
            direction=direction,
            confidence=confidence,
            reasoning="; ".join(reasons),
            indicators_used=["Ensemble ML", "Random Forest", "Gradient Boosting", "Neural Network"],
            weight=self.weight * self.get_confidence()
        )


class SupportResistanceAgent(BaseAgent):
    """
    Agent specializing in support/resistance analysis and pivot points.
    """
    
    def __init__(self):
        super().__init__("LevelFinder", AgentType.SUPPORT_RESISTANCE, weight=0.9)
    
    def analyze(self, market_data: MarketData,
                indicators: TechnicalIndicators,
                ml_prediction: Optional[ModelPrediction] = None) -> AgentVote:
        
        closes = market_data.closes
        highs = market_data.highs
        lows = market_data.lows
        current_price = closes[-1]
        reasons = []
        score = 0.0
        
        # Pivot point analysis
        pivot = indicators.pivot_point
        
        if abs(current_price - pivot) / current_price < 0.002:
            reasons.append(f"Price at pivot {pivot:.5f}")
            score = 0.0  # Neutral at pivot
        elif current_price > pivot:
            score += 0.15
            reasons.append(f"Price above pivot {pivot:.5f}")
        else:
            score -= 0.15
            reasons.append(f"Price below pivot {pivot:.5f}")
        
        # Resistance levels
        for i, level in enumerate([indicators.pivot_r1, indicators.pivot_r2, indicators.pivot_r3], 1):
            distance = (level - current_price) / current_price
            if 0 < distance < 0.01:  # Within 1% above
                score -= 0.15 * (4 - i) / 3  # Closer resistance = more bearish
                reasons.append(f"R{i} resistance at {level:.5f} ({distance:.2%} above)")
            elif -0.01 < distance < 0:  # Price broke through
                score += 0.1
                reasons.append(f"Price broke R{i} at {level:.5f}")
        
        # Support levels
        for i, level in enumerate([indicators.pivot_s1, indicators.pivot_s2, indicators.pivot_s3], 1):
            distance = (current_price - level) / current_price
            if 0 < distance < 0.01:  # Within 1% below
                score += 0.15 * (4 - i) / 3  # Closer support = more bullish
                reasons.append(f"S{i} support at {level:.5f} ({distance:.2%} below)")
            elif -0.01 < distance < 0:  # Price broke below
                score -= 0.1
                reasons.append(f"Price broke S{i} at {level:.5f}")
        
        # Fibonacci levels
        fib_levels = [
            (indicators.fib_236, "23.6%"),
            (indicators.fib_382, "38.2%"),
            (indicators.fib_500, "50.0%"),
            (indicators.fib_618, "61.8%"),
            (indicators.fib_786, "78.6%")
        ]
        
        for level, name in fib_levels:
            if abs(current_price - level) / current_price < 0.005:
                if name in ["38.2%", "50.0%", "61.8%"]:
                    reasons.append(f"At key Fib {name} {level:.5f}")
                break
        
        # Support/Resistance detection
        support_levels, resistance_levels = self.analyzer.detect_support_resistance(closes)
        
        # Check if price is near congestion zone
        if support_levels and resistance_levels:
            range_size = (max(resistance_levels[-3:]) - min(support_levels[-3:])) / current_price
            if range_size < 0.01:  # Less than 1% range
                reasons.append(f"Narrow S/R range ({range_size:.2%}) - potential breakout")
        
        # Determine direction
        if score > 0.3:
            direction = Direction.BULLISH
        elif score < -0.3:
            direction = Direction.BEARISH
        else:
            direction = Direction.NEUTRAL
        
        confidence = min(abs(score) + 0.1, 1.0)
        
        return AgentVote(
            agent_name=self.name,
            agent_type=self.agent_type.value,
            direction=direction,
            confidence=confidence,
            reasoning="; ".join(reasons),
            indicators_used=["Pivot Points", "Fibonacci", "Support/Resistance"],
            weight=self.weight * self.get_confidence()
        )


class SentimentAgent(BaseAgent):
    """
    Market sentiment agent analyzing volume, price action, and market structure.
    """
    
    def __init__(self):
        super().__init__("SentimentGauge", AgentType.SENTIMENT, weight=0.8)
    
    def analyze(self, market_data: MarketData,
                indicators: TechnicalIndicators,
                ml_prediction: Optional[ModelPrediction] = None) -> AgentVote:
        
        closes = market_data.closes
        volumes = market_data.volumes
        reasons = []
        score = 0.0
        
        # Volume analysis
        if indicators.volume_ratio > 2.0:
            reasons.append(f"Very high volume ({indicators.volume_ratio:.1f}x)")
            if closes[-1] > closes[-2]:
                score += 0.25
                reasons.append("Volume on up move = accumulation")
            else:
                score -= 0.25
                reasons.append("Volume on down move = distribution")
        elif indicators.volume_ratio > 1.5:
            reasons.append(f"Above average volume ({indicators.volume_ratio:.1f}x)")
        elif indicators.volume_ratio < 0.5:
            reasons.append(f"Low volume ({indicators.volume_ratio:.1f}x) - weak conviction")
            score *= 0.7
        
        # OBV trend
        if len(volumes) >= 20:
            obv_sma = np.mean(volumes[-20:])
            if indicators.obv > obv_sma * 1.5:
                score += 0.15
                reasons.append("OBV rising - buying pressure")
            elif indicators.obv < obv_sma * 0.5:
                score -= 0.15
                reasons.append("OBV falling - selling pressure")
        
        # Price structure
        if len(closes) >= 20:
            higher_highs = sum(1 for i in range(-19, 0) if closes[i] > closes[i-1])
            higher_lows = sum(1 for i in range(-19, 0) if lows[i] > lows[i-1])
            
            if higher_highs > 12 and higher_lows > 12:
                score += 0.2
                reasons.append(f"Higher highs/lows structure ({higher_highs}/20)")
            elif higher_highs < 8 and higher_lows < 8:
                score -= 0.2
                reasons.append(f"Lower highs/lows structure ({higher_highs}/20)")
        
        # VWAP position
        if closes[-1] > indicators.vwma:
            score += 0.1
            reasons.append("Price above VWAP")
        else:
            score -= 0.1
            reasons.append("Price below VWAP")
        
        # Market structure (simple swing analysis)
        if len(closes) >= 10:
            recent_high = np.max(highs[-10:])
            recent_low = np.min(lows[-10:])
            
            if closes[-1] > recent_high * 0.998:
                score += 0.15
                reasons.append("Price near recent high")
            elif closes[-1] < recent_low * 1.002:
                score -= 0.15
                reasons.append("Price near recent low")
        
        # Determine direction
        if score > 0.3:
            direction = Direction.BULLISH
        elif score < -0.3:
            direction = Direction.BEARISH
        else:
            direction = Direction.NEUTRAL
        
        confidence = min(abs(score), 1.0)
        
        return AgentVote(
            agent_name=self.name,
            agent_type=self.agent_type.value,
            direction=direction,
            confidence=confidence,
            reasoning="; ".join(reasons),
            indicators_used=["Volume", "OBV", "VWAP", "Market Structure"],
            weight=self.weight * self.get_confidence()
        )


class AgentFactory:
    """Factory for creating agent configurations."""
    
    @staticmethod
    def create_standard_agents(ml_predictor: Optional[EnsemblePredictor] = None) -> List[BaseAgent]:
        """Create the standard set of 7 agents."""
        agents = [
            TrendAgent(),
            MomentumAgent(),
            VolatilityAgent(),
            PatternAgent(),
            MLAgent(ml_predictor),
            SupportResistanceAgent(),
            SentimentAgent()
        ]
        return agents
    
    @staticmethod
    def create_forex_specialists(ml_predictor: Optional[EnsemblePredictor] = None) -> List[BaseAgent]:
        """Create agents optimized for forex markets."""
        agents = AgentFactory.create_standard_agents(ml_predictor)
        # Adjust weights for forex
        for agent in agents:
            if agent.agent_type == AgentType.TREND:
                agent.weight = 1.3  # Trends are more reliable in forex
            elif agent.agent_type == AgentType.VOLATILITY:
                agent.weight = 0.7  # Less important in forex
        return agents
    
    @staticmethod
    def create_crypto_specialists(ml_predictor: Optional[EnsemblePredictor] = None) -> List[BaseAgent]:
        """Create agents optimized for crypto markets."""
        agents = AgentFactory.create_standard_agents(ml_predictor)
        # Adjust weights for crypto
        for agent in agents:
            if agent.agent_type == AgentType.VOLATILITY:
                agent.weight = 1.3  # Volatility is key in crypto
            elif agent.agent_type == AgentType.MOMENTUM:
                agent.weight = 1.2  # Momentum is strong in crypto
        return agents
    
    @staticmethod
    def create_synthetic_specialists(ml_predictor: Optional[EnsemblePredictor] = None) -> List[BaseAgent]:
        """Create agents optimized for synthetic indices."""
        agents = AgentFactory.create_standard_agents(ml_predictor)
        # Adjust weights for synthetic indices
        for agent in agents:
            if agent.agent_type == AgentType.ML_PREDICTOR:
                agent.weight = 1.4  # ML works well on synthetic data
            elif agent.agent_type == AgentType.PATTERN:
                agent.weight = 1.1  # Patterns are reliable on synthetics
        return agents
