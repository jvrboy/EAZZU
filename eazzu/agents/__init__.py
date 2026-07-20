"""Multi-agent trading intelligence system.

Converted from infinite-loop-sound's TypeScript agent suite into portable
Python. Each agent is a pure function over caller-supplied data — no I/O, no
broker orders — returning JSON-serialisable results suitable for the EAZZU
agent tool registry.
"""
from eazzu.agents.types import (
    AgentConfig,
    AgentMessage,
    AgentResult,
    AgentSignal,
    RiskAssessment,
    NewsAssessment,
    SentimentAssessment,
    StrategyRecommendation,
    BacktestResult,
)
from eazzu.agents.orchestrator import run_full_analysis, get_orchestrator_state

__all__ = [
    "AgentConfig",
    "AgentMessage",
    "AgentResult",
    "AgentSignal",
    "RiskAssessment",
    "NewsAssessment",
    "SentimentAssessment",
    "StrategyRecommendation",
    "BacktestResult",
    "run_full_analysis",
    "get_orchestrator_state",
]
