"""Agent Orchestrator — coordinates all agents and manages lifecycle.

Converted from infinite-loop-sound's orchestrator.ts. Runs every enabled agent
against caller-supplied candles/ticks and aggregates results into a single
state snapshot.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from eazzu.agents.types import AgentMessage, AgentResult
from eazzu.agents.strategy_agent import run_strategy_agent
from eazzu.agents.risk_agent import run_risk_agent
from eazzu.agents.news_agent import run_news_agent
from eazzu.agents.sentiment_agent import run_sentiment_agent
from eazzu.agents.volatility_agent import run_volatility_agent
from eazzu.agents.liquidity_agent import run_liquidity_agent
from eazzu.agents.correlation_agent import run_correlation_agent
from eazzu.agents.execution_flow_agent import run_execution_flow_agent
from eazzu.agents.pattern_agent import run_pattern_agent
from eazzu.agents.optimization_agent import run_optimization_agent
from eazzu.agents.automation_agent import run_automation_agent
from eazzu.agents.web_scraping_agent import run_web_scraping_agent
from eazzu.agents.self_learning_agent import get_learned_weights, get_strategy_performance

ACTIVE_AGENTS = [
    "strategy-agent",
    "risk-agent",
    "news-agent",
    "sentiment-agent",
    "volatility-agent",
    "liquidity-agent",
    "correlation-agent",
    "execution-flow-agent",
    "pattern-agent",
    "optimization-agent",
    "automation-agent",
    "web-scraping-agent",
    "self-learning-agent",
]

_state: Dict[str, Any] = {
    "isRunning": False,
    "lastRun": 0,
    "results": {},
    "messageLog": [],
    "activeAgents": list(ACTIVE_AGENTS),
}


def get_orchestrator_state() -> Dict[str, Any]:
    return {
        "isRunning": _state["isRunning"],
        "lastRun": _state["lastRun"],
        "results": {k: v.to_dict() for k, v in _state["results"].items()},
        "messageLog": [m.to_dict() for m in _state["messageLog"]],
        "activeAgents": list(_state["activeAgents"]),
    }


def run_full_analysis(
    pair: str,
    timeframe: str,
    candles: List[Dict[str, Any]],
    ticks: Optional[List[Dict[str, Any]]] = None,
    balance: float = 10000.0,
    other_assets: Optional[Dict[str, List[Dict[str, Any]]]] = None,
    current_epoch: Optional[float] = None,
    news_score: float = 0.0,
    social_score: float = 0.0,
    market_score: float = 0.0,
    run_optimization: bool = True,
    run_automation: bool = True,
    run_web_scraping: bool = False,
) -> Dict[str, Any]:
    global _state
    _state["isRunning"] = True
    ticks = ticks or []
    other_assets = other_assets or {}
    if current_epoch is None:
        current_epoch = time.time()

    results: Dict[str, AgentResult] = {}
    log: List[AgentMessage] = []

    results["strategy-agent"] = run_strategy_agent(pair, timeframe, candles, ticks)
    results["risk-agent"] = run_risk_agent(balance=balance)
    results["news-agent"] = run_news_agent(current_epoch, pair)
    results["sentiment-agent"] = run_sentiment_agent(news_score, social_score, market_score)
    results["volatility-agent"] = run_volatility_agent(pair, timeframe, candles)
    results["liquidity-agent"] = run_liquidity_agent(pair, timeframe, candles)
    if other_assets:
        results["correlation-agent"] = run_correlation_agent(pair, candles, other_assets)
    results["execution-flow-agent"] = run_execution_flow_agent(pair, candles, ticks)
    results["pattern-agent"] = run_pattern_agent(pair, timeframe, candles)

    if run_optimization:
        results["optimization-agent"] = run_optimization_agent()
    if run_automation:
        results["automation-agent"] = run_automation_agent()
    if run_web_scraping:
        results["web-scraping-agent"] = run_web_scraping_agent()

    for r in results.values():
        for sig in r.signals:
            log.append(AgentMessage(
                id=f"{r.agent_id}-{sig.id}",
                agent_id=r.agent_id,
                type="signal",
                timestamp=sig.timestamp,
                content=f"{sig.strategy}: {sig.direction} {sig.pair} @ {sig.confidence:.0%}",
            ))

    _state["results"] = results
    _state["messageLog"] = log
    _state["lastRun"] = time.time() * 1000
    _state["isRunning"] = False

    return get_orchestrator_state()
