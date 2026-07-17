"""
Signal Engine
=============
High-accuracy signal generation system combining all analysis components.
"""

import numpy as np
import uuid
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from core.logger import signal_logger, system_logger
from core.types import (
    TradingSignal, SignalStrength, Direction, AgentVote,
    CouncilDecision, MarketData, TechnicalIndicators, SignalType
)
from analysis.indicators import TechnicalAnalyzer, PatternDetector
from models.ml_models import EnsemblePredictor, ModelPrediction
from agents.signal_agents import BaseAgent, AgentFactory
from council.voting_system import VotingCouncil, MultiTimeframeCouncil


class SignalEngine:
    """
    Main signal generation engine.
    Combines technical analysis, ML predictions, agent votes, and council decisions.
    """
    
    def __init__(
        self,
        symbol: str,
        asset_class: str,
        timeframe: str,
        agents: List[BaseAgent],
        council: Optional[VotingCouncil] = None,
        ml_predictor: Optional[EnsemblePredictor] = None,
        min_confidence: float = 0.65,
        signal_expiry_minutes: int = 30
    ):
        self.symbol = symbol
        self.asset_class = asset_class
        self.timeframe = timeframe
        self.agents = agents
        self.council = council or VotingCouncil()
        self.ml_predictor = ml_predictor
        self.min_confidence = min_confidence
        self.signal_expiry = timedelta(minutes=signal_expiry_minutes)
        
        self.analyzer = TechnicalAnalyzer()
        self.pattern_detector = PatternDetector()
        
        self.active_signals: List[TradingSignal] = []
        self.signal_history: List[TradingSignal] = []
        
        self.stats = {
            'total_generated': 0,
            'buy_signals': 0,
            'sell_signals': 0,
            'avg_confidence': 0.0,
            'avg_consensus': 0.0
        }
        
        system_logger.info(
            f"SignalEngine initialized for {symbol} {timeframe} | "
            f"Agents: {len(agents)} | Min confidence: {min_confidence:.0%}"
        )
    
    def generate_signal(
        self,
        market_data: MarketData,
        ml_prediction: Optional[ModelPrediction] = None
    ) -> Optional[TradingSignal]:
        """
        Generate a trading signal from market data.
        Full pipeline: indicators -> agents -> council -> signal.
        """
        # Step 1: Calculate technical indicators
        indicators = self.analyzer.analyze(market_data)
        
        # Step 2: Get ML prediction if available
        if ml_prediction is None and self.ml_predictor and self.ml_predictor.is_trained:
            try:
                ml_prediction = self.ml_predictor.predict(market_data, indicators)
            except Exception as e:
                system_logger.warning(f"ML prediction failed: {e}")
        
        # Step 3: Collect votes from all agents
        votes: List[AgentVote] = []
        for agent in self.agents:
            if not agent.is_active:
                continue
            try:
                vote = agent.analyze(market_data, indicators, ml_prediction)
                votes.append(vote)
            except Exception as e:
                system_logger.warning(f"Agent {agent.name} error: {e}")
        
        if len(votes) < 4:
            system_logger.debug("Insufficient agent votes")
            return None
        
        # Step 4: Council deliberation
        council_decision = self.council.deliberate(
            symbol=self.symbol,
            timeframe=self.timeframe,
            agents=self.agents,
            votes=votes
        )
        
        if council_decision is None:
            return None
        
        # Step 5: Check minimum confidence
        if council_decision.confidence < self.min_confidence:
            system_logger.debug(
                f"Confidence {council_decision.confidence:.2%} below threshold"
            )
            return None
        
        # Step 6: Build trading signal
        signal = self._build_signal(
            market_data=market_data,
            indicators=indicators,
            council_decision=council_decision,
            votes=votes,
            ml_prediction=ml_prediction
        )
        
        if signal:
            self._update_stats(signal)
            self.active_signals.append(signal)
            self.signal_history.append(signal)
            
            # Log signal
            signal_logger.log_signal({
                'symbol': signal.symbol,
                'signal_type': signal.signal_type,
                'confidence': signal.confidence,
                'entry_price': signal.entry_price,
                'stop_loss': signal.stop_loss,
                'take_profit': signal.take_profit,
                'timeframe': signal.timeframe,
                'agreeing_agents': sum(1 for v in votes if 
                    (signal.direction == Direction.BULLISH and v.direction in [Direction.BULLISH, Direction.STRONG_BULLISH]) or
                    (signal.direction == Direction.BEARISH and v.direction in [Direction.BEARISH, Direction.STRONG_BEARISH])),
                'total_agents': len(votes)
            })
            
            system_logger.info(
                f"SIGNAL: {signal.signal_type} {self.symbol} {self.timeframe} | "
                f"Confidence: {signal.confidence:.1%} | "
                f"Entry: {signal.entry_price:.5f} | "
                f"SL: {signal.stop_loss:.5f} | "
                f"TP: {signal.take_profit:.5f}"
            )
        
        return signal
    
    def _build_signal(
        self,
        market_data: MarketData,
        indicators: TechnicalIndicators,
        council_decision: CouncilDecision,
        votes: List[AgentVote],
        ml_prediction: Optional[ModelPrediction]
    ) -> Optional[TradingSignal]:
        """Build complete trading signal from council decision."""
        
        closes = market_data.closes
        current_price = closes[-1]
        atr = indicators.atr_14
        
        # Determine signal type
        if council_decision.direction == Direction.BULLISH:
            if council_decision.confidence > 0.8:
                signal_type = "STRONG_BUY"
            else:
                signal_type = "BUY"
        elif council_decision.direction == Direction.BEARISH:
            if council_decision.confidence > 0.8:
                signal_type = "STRONG_SELL"
            else:
                signal_type = "SELL"
        else:
            return None
        
        # Determine strength
        if council_decision.confidence > 0.85:
            strength = SignalStrength.VERY_STRONG
        elif council_decision.confidence > 0.75:
            strength = SignalStrength.STRONG
        elif council_decision.confidence > 0.65:
            strength = SignalStrength.MODERATE
        else:
            strength = SignalStrength.WEAK
        
        # Calculate entry, stop loss, and take profit
        if signal_type in ["BUY", "STRONG_BUY"]:
            entry = current_price
            stop_loss = current_price - (atr * 1.5)
            take_profit = current_price + (atr * 2.5)
        else:
            entry = current_price
            stop_loss = current_price + (atr * 1.5)
            take_profit = current_price - (atr * 2.5)
        
        # Risk/reward ratio
        risk = abs(entry - stop_loss)
        reward = abs(take_profit - entry)
        risk_reward = reward / risk if risk > 0 else 0
        
        # Skip if risk/reward is poor
        if risk_reward < 1.2:
            system_logger.debug(f"Poor risk/reward ratio: {risk_reward:.2f}")
            return None
        
        # Timeframe in minutes
        tf_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '4h': 240, '1d': 1440
        }.get(self.timeframe, 5)
        
        # Expected pips
        expected_pips = abs(take_profit - entry)
        if self.asset_class == "forex":
            expected_pips *= 10000  # Convert to pips
        elif self.asset_class == "crypto":
            expected_pips *= 100    # Convert to percentage points
        
        # Collect indicator snapshot
        indicator_snapshot = {
            'rsi': indicators.rsi_14,
            'macd_hist': indicators.macd_histogram,
            'bb_position': indicators.bb_position,
            'adx': indicators.adx,
            'atr': indicators.atr_14,
            'volume_ratio': indicators.volume_ratio,
            'trend_strength': indicators.trend_strength,
            'volatility': indicators.volatility,
        }
        
        # Detect patterns
        patterns = self.pattern_detector.detect_patterns(market_data.candles[-10:])
        if patterns:
            indicator_snapshot['patterns'] = list(patterns.keys())
        
        signal = TradingSignal(
            id=str(uuid.uuid4())[:8],
            timestamp=datetime.now(),
            symbol=self.symbol,
            asset_class=self.asset_class,
            timeframe=self.timeframe,
            signal_type=signal_type,
            direction=council_decision.direction,
            entry_price=round(entry, 5),
            stop_loss=round(stop_loss, 5),
            take_profit=round(take_profit, 5),
            confidence=council_decision.confidence,
            strength=strength,
            risk_reward_ratio=risk_reward,
            expected_pips=expected_pips,
            timeframe_minutes=tf_minutes,
            indicators=indicator_snapshot,
            agent_votes=votes,
            council_decision=council_decision,
            metadata={
                'ml_prediction': ml_prediction.direction if ml_prediction else None,
                'ml_confidence': ml_prediction.confidence if ml_prediction else 0,
                'risk_level': council_decision.risk_level,
                'strategy': council_decision.strategy[:200]
            },
            expiry=datetime.now() + self.signal_expiry
        )
        
        return signal
    
    def _update_stats(self, signal: TradingSignal):
        """Update signal statistics."""
        self.stats['total_generated'] += 1
        if signal.signal_type in ['BUY', 'STRONG_BUY']:
            self.stats['buy_signals'] += 1
        else:
            self.stats['sell_signals'] += 1
        
        n = self.stats['total_generated']
        self.stats['avg_confidence'] = (
            (self.stats['avg_confidence'] * (n - 1) + signal.confidence) / n
        )
        if signal.council_decision:
            self.stats['avg_consensus'] = (
                (self.stats['avg_consensus'] * (n - 1) + signal.council_decision.consensus_ratio) / n
            )
    
    def cleanup_expired_signals(self):
        """Remove expired signals from active list."""
        now = datetime.now()
        expired = [s for s in self.active_signals if s.expiry and s.expiry < now]
        for s in expired:
            s.status = "expired"
        self.active_signals = [s for s in self.active_signals if s.status == "active"]
        
        if expired:
            system_logger.debug(f"Cleaned up {len(expired)} expired signals")
    
    def get_active_signals(self) -> List[TradingSignal]:
        """Get currently active signals."""
        self.cleanup_expired_signals()
        return self.active_signals
    
    def get_signal_stats(self) -> Dict:
        """Get signal generation statistics."""
        return self.stats.copy()
    
    def get_recent_signals(self, n: int = 20) -> List[TradingSignal]:
        """Get recent signals."""
        return self.signal_history[-n:]


class MultiTimeframeSignalEngine:
    """
    Signal engine that operates across multiple timeframes.
    Generates signals for each timeframe and aggregates them.
    """
    
    def __init__(
        self,
        symbol: str,
        asset_class: str,
        timeframes: List[str],
        ml_predictors: Optional[Dict[str, EnsemblePredictor]] = None
    ):
        self.symbol = symbol
        self.asset_class = asset_class
        self.timeframes = timeframes
        self.ml_predictors = ml_predictors or {}
        
        # Create engines for each timeframe
        self.engines: Dict[str, SignalEngine] = {}
        for tf in timeframes:
            # Create specialized agents based on asset class
            if asset_class == "forex":
                agents = AgentFactory.create_forex_specialists(
                    self.ml_predictors.get(tf)
                )
            elif asset_class == "crypto":
                agents = AgentFactory.create_crypto_specialists(
                    self.ml_predictors.get(tf)
                )
            elif asset_class == "synthetic":
                agents = AgentFactory.create_synthetic_specialists(
                    self.ml_predictors.get(tf)
                )
            else:
                agents = AgentFactory.create_standard_agents(
                    self.ml_predictors.get(tf)
                )
            
            self.engines[tf] = SignalEngine(
                symbol=symbol,
                asset_class=asset_class,
                timeframe=tf,
                agents=agents,
                ml_predictor=self.ml_predictors.get(tf)
            )
        
        # Multi-timeframe council
        self.mtf_council = MultiTimeframeCouncil()
        
        system_logger.info(
            f"MultiTimeframeSignalEngine for {symbol} | "
            f"Timeframes: {', '.join(timeframes)}"
        )
    
    def generate_all_signals(
        self,
        timeframe_data: Dict[str, MarketData],
        timeframe_predictions: Optional[Dict[str, ModelPrediction]] = None
    ) -> Dict[str, TradingSignal]:
        """
        Generate signals for all timeframes.
        
        Returns dict of timeframe -> signal (only timeframes with signals).
        """
        signals = {}
        
        for tf, data in timeframe_data.items():
            if tf not in self.engines:
                continue
            
            ml_pred = timeframe_predictions.get(tf) if timeframe_predictions else None
            
            try:
                signal = self.engines[tf].generate_signal(data, ml_pred)
                if signal:
                    signals[tf] = signal
            except Exception as e:
                system_logger.error(f"Signal generation error for {tf}: {e}")
        
        return signals
    
    def get_all_stats(self) -> Dict[str, Dict]:
        """Get stats for all timeframes."""
        return {tf: engine.get_signal_stats() for tf, engine in self.engines.items()}
    
    def get_all_active_signals(self) -> Dict[str, List[TradingSignal]]:
        """Get all active signals across timeframes."""
        return {tf: engine.get_active_signals() for tf, engine in self.engines.items()}
