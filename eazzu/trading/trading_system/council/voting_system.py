"""
Council Voting System
=====================
Democratic decision-making system where agents vote on trading signals.
Implements weighted voting with consensus requirements.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

from core.logger import system_logger
from core.types import (
    AgentVote, CouncilDecision, Direction, 
    TradingSignal, SignalStrength, MarketData, TechnicalIndicators
)
from agents.signal_agents import BaseAgent


class VotingCouncil:
    """
    Council of agents that vote on trading decisions.
    Uses weighted voting with configurable thresholds.
    """
    
    def __init__(
        self,
        name: str = "TradingCouncil",
        min_consensus: float = 0.6,
        min_votes_required: int = 4,
        strong_signal_threshold: float = 0.75
    ):
        self.name = name
        self.min_consensus = min_consensus
        self.min_votes_required = min_votes_required
        self.strong_signal_threshold = strong_signal_threshold
        self.vote_history: List[CouncilDecision] = []
        
        system_logger.info(
            f"VotingCouncil '{name}' initialized | "
            f"Consensus: {min_consensus:.0%} | Min votes: {min_votes_required}"
        )
    
    def deliberate(
        self,
        symbol: str,
        timeframe: str,
        agents: List[BaseAgent],
        votes: List[AgentVote]
    ) -> Optional[CouncilDecision]:
        """
        Conduct council deliberation on trading signal.
        
        Returns CouncilDecision if consensus reached, None otherwise.
        """
        if len(votes) < self.min_votes_required:
            system_logger.warning(
                f"Insufficient votes: {len(votes)}/{self.min_votes_required}"
            )
            return None
        
        # Calculate weighted votes by direction
        bullish_score = 0.0
        bearish_score = 0.0
        neutral_score = 0.0
        total_weight = 0.0
        
        for vote in votes:
            weight = vote.weight * vote.confidence
            total_weight += vote.weight
            
            if vote.direction in [Direction.BULLISH, Direction.STRONG_BULLISH]:
                bullish_score += weight
                if vote.direction == Direction.STRONG_BULLISH:
                    bullish_score += weight * 0.3  # Bonus for strong
            elif vote.direction in [Direction.BEARISH, Direction.STRONG_BEARISH]:
                bearish_score += weight
                if vote.direction == Direction.STRONG_BEARISH:
                    bearish_score += weight * 0.3
            else:
                neutral_score += weight
        
        # Normalize
        if total_weight > 0:
            bullish_score /= total_weight
            bearish_score /= total_weight
            neutral_score /= total_weight
        
        # Determine outcome
        scores = {
            Direction.BULLISH: bullish_score,
            Direction.BEARISH: bearish_score,
            Direction.NEUTRAL: neutral_score
        }
        
        winning_direction = max(scores, key=scores.get)
        winning_score = scores[winning_direction]
        
        # Calculate consensus ratio
        if winning_direction != Direction.NEUTRAL:
            opposition = bearish_score if winning_direction == Direction.BULLISH else bullish_score
            consensus_ratio = winning_score / (winning_score + opposition) if (winning_score + opposition) > 0 else 0
        else:
            consensus_ratio = neutral_score
        
        # Check if consensus threshold met
        if consensus_ratio < self.min_consensus:
            system_logger.debug(
                f"No consensus: {winning_direction.name} {consensus_ratio:.2%} "
                f"(threshold: {self.min_consensus:.0%})"
            )
            return None
        
        # Determine signal strength
        if consensus_ratio >= self.strong_signal_threshold:
            strength = "strong"
            confidence = min(winning_score * 1.2, 1.0)
        else:
            strength = "moderate"
            confidence = winning_score
        
        # Build strategy description
        strategy = self._build_strategy(votes, winning_direction)
        
        # Determine risk level
        risk_level = self._assess_risk(votes, winning_direction)
        
        decision = CouncilDecision(
            timestamp=datetime.now(),
            symbol=symbol,
            timeframe=timeframe,
            direction=winning_direction,
            confidence=confidence,
            consensus_ratio=consensus_ratio,
            votes=votes,
            strategy=strategy,
            risk_level=risk_level
        )
        
        self.vote_history.append(decision)
        
        # Keep history manageable
        if len(self.vote_history) > 1000:
            self.vote_history = self.vote_history[-500:]
        
        system_logger.info(
            f"Council decision: {winning_direction.name} | "
            f"Confidence: {confidence:.2%} | "
            f"Consensus: {consensus_ratio:.2%} | "
            f"Strength: {strength}"
        )
        
        return decision
    
    def _build_strategy(self, votes: List[AgentVote], direction: Direction) -> str:
        """Build strategy description from votes."""
        # Collect reasoning from agreeing agents
        agreeing = [v for v in votes if 
                    (direction == Direction.BULLISH and v.direction in [Direction.BULLISH, Direction.STRONG_BULLISH]) or
                    (direction == Direction.BEARISH and v.direction in [Direction.BEARISH, Direction.STRONG_BEARISH])]
        
        reasons = []
        for v in sorted(agreeing, key=lambda x: x.confidence, reverse=True)[:3]:
            reasons.append(f"{v.agent_name}: {v.reasoning[:60]}")
        
        return " | ".join(reasons)
    
    def _assess_risk(self, votes: List[AgentVote], direction: Direction) -> str:
        """Assess risk level based on vote disagreement."""
        # Count opposing votes
        if direction == Direction.BULLISH:
            opposing = sum(1 for v in votes if v.direction in [Direction.BEARISH, Direction.STRONG_BEARISH])
        else:
            opposing = sum(1 for v in votes if v.direction in [Direction.BULLISH, Direction.STRONG_BULLISH])
        
        total = len(votes)
        opposition_ratio = opposing / total if total > 0 else 0
        
        if opposition_ratio > 0.4:
            return "high"
        elif opposition_ratio > 0.2:
            return "medium"
        else:
            return "low"
    
    def get_recent_performance(self, n: int = 20) -> Dict[str, float]:
        """Get recent council performance metrics."""
        recent = self.vote_history[-n:]
        
        if not recent:
            return {"accuracy": 0.5, "confidence": 0.5, "consensus": 0.5}
        
        avg_confidence = np.mean([d.confidence for d in recent])
        avg_consensus = np.mean([d.consensus_ratio for d in recent])
        
        return {
            "accuracy": avg_confidence,  # Proxy for accuracy
            "confidence": avg_confidence,
            "consensus": avg_consensus,
            "total_decisions": len(self.vote_history)
        }


class MultiTimeframeCouncil:
    """
    Council that aggregates decisions across multiple timeframes.
    Higher timeframes provide context for final decision.
    """
    
    TIMEFRAME_WEIGHTS = {
        '1m': 0.05,
        '5m': 0.10,
        '15m': 0.10,
        '30m': 0.10,
        '1h': 0.15,
        '4h': 0.25,
        '1d': 0.25
    }
    
    def __init__(self):
        self.councils: Dict[str, VotingCouncil] = {}
        system_logger.info("MultiTimeframeCouncil initialized")
    
    def get_or_create_council(self, timeframe: str) -> VotingCouncil:
        """Get or create council for timeframe."""
        if timeframe not in self.councils:
            self.councils[timeframe] = VotingCouncil(f"Council_{timeframe}")
        return self.councils[timeframe]
    
    def aggregate_across_timeframes(
        self,
        timeframe_decisions: Dict[str, CouncilDecision]
    ) -> Optional[CouncilDecision]:
        """
        Aggregate council decisions across timeframes.
        Higher timeframes carry more weight.
        """
        if not timeframe_decisions:
            return None
        
        # Calculate weighted direction
        bullish_score = 0.0
        bearish_score = 0.0
        total_weight = 0.0
        all_votes = []
        
        for tf, decision in timeframe_decisions.items():
            weight = self.TIMEFRAME_WEIGHTS.get(tf, 0.1)
            total_weight += weight
            
            if decision.direction in [Direction.BULLISH, Direction.STRONG_BULLISH]:
                bullish_score += weight * decision.confidence
            elif decision.direction in [Direction.BEARISH, Direction.STRONG_BEARISH]:
                bearish_score += weight * decision.confidence
            
            all_votes.extend(decision.votes)
        
        if total_weight == 0:
            return None
        
        # Determine final direction
        if bullish_score > bearish_score:
            final_direction = Direction.BULLISH
            confidence = bullish_score / total_weight
            consensus = bullish_score / (bullish_score + bearish_score) if (bullish_score + bearish_score) > 0 else 0
        elif bearish_score > bullish_score:
            final_direction = Direction.BEARISH
            confidence = bearish_score / total_weight
            consensus = bearish_score / (bullish_score + bearish_score) if (bullish_score + bearish_score) > 0 else 0
        else:
            return None
        
        # Create aggregate decision
        return CouncilDecision(
            timestamp=datetime.now(),
            symbol=timeframe_decisions[list(timeframe_decisions.keys())[0]].symbol,
            timeframe="aggregate",
            direction=final_direction,
            confidence=confidence,
            consensus_ratio=consensus,
            votes=all_votes,
            strategy=f"Multi-timeframe consensus: {final_direction.name}",
            risk_level="medium"
        )
