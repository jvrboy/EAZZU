"""Agent system type definitions.

Portable dataclasses mirroring the infinite-loop-sound TypeScript agent
contracts. All fields are JSON-serialisable so results can flow through the
EAZZU agent transcript and tool registry unchanged.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


AgentStatus = str  # "idle" | "running" | "completed" | "error"
AgentPriority = str  # "critical" | "high" | "medium" | "low"


@dataclass
class AgentConfig:
    id: str
    name: str
    description: str
    enabled: bool = True
    priority: AgentPriority = "medium"
    interval_sec: int = 60
    instruments: List[str] = field(default_factory=lambda: ["all"])
    timeframes: List[str] = field(default_factory=lambda: ["all"])


@dataclass
class AgentMessage:
    id: str
    agent_id: str
    type: str  # "info" | "warning" | "signal" | "trade" | "error" | "insight"
    timestamp: float
    content: str
    data: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agentId": self.agent_id,
            "type": self.type,
            "timestamp": self.timestamp,
            "content": self.content,
            "data": self.data,
        }


@dataclass
class AgentSignal:
    id: str
    strategy: str
    pair: str
    direction: str  # "BUY" | "SELL"
    confidence: float
    score: float
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "strategy": self.strategy,
            "pair": self.pair,
            "direction": self.direction,
            "confidence": self.confidence,
            "score": self.score,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


@dataclass
class AgentResult:
    agent_id: str
    status: AgentStatus
    timestamp: float
    output: Optional[Dict[str, Any]] = None
    signals: List[AgentSignal] = field(default_factory=list)
    insights: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    duration: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agentId": self.agent_id,
            "status": self.status,
            "timestamp": self.timestamp,
            "output": self.output,
            "signals": [s.to_dict() for s in self.signals],
            "insights": self.insights,
            "errors": self.errors,
            "duration": self.duration,
        }


@dataclass
class StrategyRecommendation:
    strategy_id: str
    strategy_name: str
    pair: str
    direction: str
    confidence: float
    score: float
    win_rate: float
    profit_factor: float
    session: str  # "night" | "day" | "any"
    reason: str
    entry: Optional[float] = None
    sl: Optional[float] = None
    tp: Optional[float] = None
    timestamp: float = 0.0


@dataclass
class RiskAssessment:
    max_position_size: float
    daily_loss_limit: float
    current_daily_pnl: float
    risk_per_trade: float
    kelly_fraction: float
    consecutive_losses: int
    should_halt: bool
    reason: Optional[str] = None
    position_count: int = 0
    max_positions: int = 2
    available_margin: float = 0.0


@dataclass
class NewsEventAssessment:
    title: str
    impact: str  # "high" | "medium" | "low"
    currency: str
    epoch: float
    forecast: Optional[str] = None
    previous: Optional[str] = None
    strategy_implication: Optional[str] = None


@dataclass
class NewsAssessment:
    upcoming_events: List[NewsEventAssessment] = field(default_factory=list)
    active_events: List[NewsEventAssessment] = field(default_factory=list)
    impact_level: str = "low"
    recommended_action: str = "trade"
    affected_pairs: List[str] = field(default_factory=list)


@dataclass
class SentimentAssessment:
    overall_sentiment: float
    confidence: float
    sources: List[Dict[str, Any]] = field(default_factory=list)
    trending_topics: List[str] = field(default_factory=list)
    recommended_bias: str = "NEUTRAL"


@dataclass
class BacktestResult:
    strategy_id: str
    pair: str
    timeframe: str
    period: Dict[str, float]
    total_trades: int
    wins: int
    losses: int
    scratches: int
    win_rate: float
    profit_factor: float
    avg_r_multiple: float
    total_r: float
    max_drawdown: float
    max_consecutive_losses: int
