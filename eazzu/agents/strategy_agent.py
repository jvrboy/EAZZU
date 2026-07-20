"""Strategy Agent — multi-strategy confluence evaluation.

Converted from infinite-loop-sound's strategy-agent.ts. Uses the pattern,
volatility, and liquidity agents as strategy detectors and combines their
output into a confluence score with adaptive weighting.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from eazzu.agents.types import (
    AgentConfig,
    AgentMessage,
    AgentResult,
    AgentSignal,
    StrategyRecommendation,
)
from eazzu.agents.pattern_agent import run_pattern_agent
from eazzu.agents.volatility_agent import run_volatility_agent
from eazzu.agents.liquidity_agent import run_liquidity_agent

STRATEGY_AGENT_CONFIG = AgentConfig(
    id="strategy-agent",
    name="Strategy Agent",
    description=(
        "Multi-strategy confluence engine that evaluates pattern, volatility, "
        "and liquidity detectors and selects the highest-probability setups."
    ),
    enabled=True,
    priority="critical",
    interval_sec=30,
    instruments=["all"],
    timeframes=["M5", "M15", "M30", "H1", "H4"],
)

_performance_cache: Dict[str, Dict[str, int]] = {}


def update_performance(strategy_id: str, won: bool) -> None:
    rec = _performance_cache.setdefault(strategy_id, {"wins": 0, "total": 0})
    rec["total"] += 1
    if won:
        rec["wins"] += 1


def _adaptive_weight(strategy_id: str, base: float) -> float:
    rec = _performance_cache.get(strategy_id)
    if not rec or rec["total"] < 5:
        return base
    wr = rec["wins"] / rec["total"]
    mult = 1.2 if wr > 0.6 else 1.0 if wr > 0.5 else 0.7
    return base * mult


def run_strategy_agent(
    pair: str,
    timeframe: str,
    candles: List[Dict[str, Any]],
    ticks: Optional[List[Dict[str, Any]]] = None,
) -> AgentResult:
    start = time.time()
    signals: List[AgentSignal] = []
    insights: List[str] = []
    messages: List[AgentMessage] = []
    ticks = ticks or []

    try:
        pattern = run_pattern_agent(pair, timeframe, candles)
        vol = run_volatility_agent(pair, timeframe, candles)
        liq = run_liquidity_agent(pair, timeframe, candles)

        hits: List[Dict[str, Any]] = []
        p_out = pattern.output or {}
        for pat in p_out.get("patterns", []):
            side = "BUY" if pat["bias"] == "bull" else "SELL" if pat["bias"] == "bear" else None
            if side:
                hits.append({"name": pat["name"], "side": side, "weight": pat["confidence"], "source": "pattern", "note": pat["note"]})

        v_out = vol.output or {}
        if v_out.get("regime") in ("expansion", "extreme"):
            hits.append({"name": "VolatilityBreakout", "side": "BUY", "weight": 60, "source": "volatility", "note": f"ATR {v_out.get('atrPercentile')}th pctile"})
        elif v_out.get("regime") == "contraction":
            hits.append({"name": "VolatilitySqueeze", "side": "SELL", "weight": 45, "source": "volatility", "note": "Squeeze — breakout pending"})

        l_out = liq.output or {}
        flow = l_out.get("flowDirection", "neutral")
        if flow != "neutral":
            hits.append({"name": "LiquidityFlow", "side": "BUY" if flow == "bullish" else "SELL", "weight": 55, "source": "liquidity", "note": f"Flow {flow}"})

        buy_score = sum(_adaptive_weight(h["name"], h["weight"]) for h in hits if h["side"] == "BUY")
        sell_score = sum(_adaptive_weight(h["name"], h["weight"]) for h in hits if h["side"] == "SELL")
        total_weight = sum(h["weight"] for h in hits)
        direction = "BUY" if buy_score > sell_score else "SELL" if sell_score > buy_score else None
        confidence = max(buy_score, sell_score) / total_weight if total_weight > 0 else 0.0

        recommendations = [
            StrategyRecommendation(
                strategy_id=h["name"],
                strategy_name=h["name"],
                pair=pair,
                direction=h["side"],
                confidence=h["weight"] / 20,
                score=h["weight"],
                win_rate=0.6,
                profit_factor=1.5,
                session="any",
                reason=h["note"],
                timestamp=time.time() * 1000,
            )
            for h in sorted(hits, key=lambda x: x["weight"], reverse=True)[:5]
        ]

        if len(hits) >= 3:
            top_side = "BUY" if buy_score > sell_score else "SELL"
            agreeing = sum(1 for h in hits if h["side"] == top_side)
            if agreeing >= 3:
                insights.append(f"STRONG CONFLUENCE: {agreeing}/{len(hits)} strategies agree on {top_side}.")
                messages.append(AgentMessage(
                    id=str(uuid.uuid4()), agent_id=STRATEGY_AGENT_CONFIG.id, type="signal",
                    timestamp=time.time() * 1000,
                    content=f"Multi-strategy confluence: {agreeing} strategies agree on {top_side}",
                ))

        signals = [
            AgentSignal(
                id=str(uuid.uuid4()), strategy=h["name"], pair=pair, direction=h["side"],
                confidence=h["weight"] / 20, score=h["weight"], timestamp=time.time() * 1000,
            )
            for h in hits
        ]

        return AgentResult(
            agent_id=STRATEGY_AGENT_CONFIG.id,
            status="completed",
            timestamp=time.time() * 1000,
            output={
                "direction": direction,
                "confidence": confidence,
                "buyScore": buy_score,
                "sellScore": sell_score,
                "recommendations": [r.__dict__ for r in recommendations],
                "hitCount": len(hits),
                "messages": [m.to_dict() for m in messages],
            },
            signals=signals,
            insights=insights or [f"{len(hits)} strategy hits evaluated"],
            duration=(time.time() - start) * 1000,
        )
    except Exception as exc:
        return AgentResult(
            agent_id=STRATEGY_AGENT_CONFIG.id,
            status="error",
            timestamp=time.time() * 1000,
            errors=[str(exc)],
            duration=(time.time() - start) * 1000,
        )
