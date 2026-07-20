"""Multi-agent system tools exposed to the EAZZU agent.

Wraps the eazzu.agents subpackage so the agent can run full multi-agent
analysis, record trade outcomes, and query learned weights as tools.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _error(code: str, exc: Exception) -> Dict[str, Any]:
    return {"error": code, "message": str(exc)}


def run_multi_agent_analysis(
    pair: str,
    timeframe: str,
    candles: List[Dict[str, Any]],
    ticks: Optional[List[Dict[str, Any]]] = None,
    balance: float = 10000.0,
    other_assets: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    news_score: float = 0.0,
    social_score: float = 0.0,
    market_score: float = 0.0,
) -> Dict[str, Any]:
    """Run the full multi-agent analysis pipeline and return aggregated results."""
    try:
        from eazzu.agents.orchestrator import run_full_analysis

        return run_full_analysis(
            pair=pair,
            timeframe=timeframe,
            candles=candles,
            ticks=ticks,
            balance=balance,
            other_assets=other_assets,
            news_score=news_score,
            social_score=social_score,
            market_score=market_score,
        )
    except Exception as exc:
        return _error("multi_agent_failed", exc)


def run_risk_assessment(
    balance: float,
    daily_loss_cap: float = 50.0,
    max_positions: int = 2,
    win_rate: float = 0.6,
    avg_win_loss_ratio: float = 1.5,
) -> Dict[str, Any]:
    """Run the risk agent for position sizing and halt checks."""
    try:
        from eazzu.agents.risk_agent import run_risk_agent

        return run_risk_agent(
            balance=balance,
            daily_loss_cap=daily_loss_cap,
            max_positions=max_positions,
            win_rate=win_rate,
            avg_win_loss_ratio=avg_win_loss_ratio,
        ).to_dict()
    except Exception as exc:
        return _error("risk_assessment_failed", exc)


def record_trade_outcome(
    pair: str,
    timeframe: str,
    strategy: str,
    direction: str,
    confluence_factors: List[str],
    outcome: str,
    pnl_pips: Optional[float] = None,
) -> Dict[str, Any]:
    """Record a signal outcome so the self-learning agent can adjust weights."""
    try:
        from eazzu.agents.self_learning_agent import record_signal_outcome

        return record_signal_outcome(
            pair=pair,
            timeframe=timeframe,
            strategy=strategy,
            direction=direction,
            confluence_factors=confluence_factors,
            outcome=outcome,
            pnl_pips=pnl_pips,
        )
    except Exception as exc:
        return _error("trade_outcome_failed", exc)


def get_learned_weights(pair: str, session: Optional[str] = None) -> Dict[str, Any]:
    """Query the self-learning agent's learned confluence weights."""
    try:
        from eazzu.agents.self_learning_agent import get_learned_weights as _glw

        return _glw(pair, session)
    except Exception as exc:
        return _error("learned_weights_failed", exc)


def list_agents() -> Dict[str, Any]:
    """List all available agents in the multi-agent system."""
    return {
        "agents": [
            {"id": "strategy-agent", "name": "Strategy Agent", "priority": "critical"},
            {"id": "risk-agent", "name": "Risk Agent", "priority": "critical"},
            {"id": "news-agent", "name": "News Agent", "priority": "high"},
            {"id": "sentiment-agent", "name": "Sentiment Agent", "priority": "medium"},
            {"id": "volatility-agent", "name": "Volatility Regime Agent", "priority": "medium"},
            {"id": "liquidity-agent", "name": "Liquidity Flow Agent", "priority": "medium"},
            {"id": "correlation-agent", "name": "Correlation Matrix Agent", "priority": "medium"},
            {"id": "execution-flow-agent", "name": "Execution Flow Agent", "priority": "medium"},
            {"id": "pattern-agent", "name": "Pattern Recognition Agent", "priority": "high"},
            {"id": "self-learning-agent", "name": "Self-Learning Agent", "priority": "medium"},
        ]
    }


TOOLS = [
    {
        "name": "run_multi_agent_analysis",
        "description": "Run the full multi-agent trading analysis pipeline (strategy, risk, news, sentiment, volatility, liquidity, correlation, execution, pattern).",
        "params": {
            "pair": "string",
            "timeframe": "string",
            "candles": "array[object]",
            "ticks": "array[object](optional)",
            "balance": "float(optional)",
            "other_assets": "object(optional)",
            "news_score": "float(optional)",
            "social_score": "float(optional)",
            "market_score": "float(optional)",
        },
        "run": run_multi_agent_analysis,
    },
    {
        "name": "run_risk_assessment",
        "description": "Run the risk agent for Kelly criterion position sizing and halt checks.",
        "params": {"balance": "float", "daily_loss_cap": "float(optional)", "max_positions": "int(optional)", "win_rate": "float(optional)", "avg_win_loss_ratio": "float(optional)"},
        "run": run_risk_assessment,
    },
    {
        "name": "record_trade_outcome",
        "description": "Record a signal outcome so the self-learning agent can adjust confluence weights.",
        "params": {"pair": "string", "timeframe": "string", "strategy": "string", "direction": "string", "confluence_factors": "array[string]", "outcome": "string", "pnl_pips": "float(optional)"},
        "run": record_trade_outcome,
    },
    {
        "name": "get_learned_weights",
        "description": "Query the self-learning agent's learned confluence weights for a pair.",
        "params": {"pair": "string", "session": "string(optional)"},
        "run": get_learned_weights,
    },
    {
        "name": "list_agents",
        "description": "List all available agents in the EAZZU multi-agent system.",
        "params": {},
        "run": list_agents,
    },
]
