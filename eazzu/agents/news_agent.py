"""News Agent — economic calendar monitor and news-spike-follow signals.

Converted from infinite-loop-sound's news-agent.ts. Caller supplies cached
events via :func:`set_news_events`; the agent itself performs no network I/O.
"""
from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from eazzu.agents.types import (
    AgentConfig,
    AgentMessage,
    AgentResult,
    NewsAssessment,
    NewsEventAssessment,
)

NEWS_AGENT_CONFIG = AgentConfig(
    id="news-agent",
    name="News Agent",
    description=(
        "Economic calendar monitor that tracks medium/low/high impact events "
        "and generates News Spike Follow signals with instrument-specific win rates."
    ),
    enabled=True,
    priority="high",
    interval_sec=60,
    instruments=["NZDUSD", "USDCHF", "AUDUSD", "USDCAD", "USDJPY", "EURUSD", "GBPUSD", "SPX500"],
    timeframes=["H1"],
)

NEWS_PERFORMANCE: Dict[str, Dict[str, Any]] = {
    "NZDUSD": {"wr": 76.6, "pf": 3.28, "better": "high (slight)"},
    "USDCHF": {"wr": 74.6, "pf": 2.93, "better": "med/low"},
    "AUDUSD": {"wr": 64.9, "pf": 1.85, "better": "med/low (slight)"},
    "USDCAD": {"wr": 62.5, "pf": 1.67, "better": "med/low"},
    "USDJPY": {"wr": 61.7, "pf": 1.61, "better": "med/low (slight)"},
    "EURUSD": {"wr": 59.8, "pf": 1.49, "better": "med/low (slight)"},
    "SPX500": {"wr": 56.5, "pf": 1.3, "better": "med/low (slight)"},
    "GBPUSD": {"wr": 55.8, "pf": 1.26, "better": "high"},
}

_cached_events: List[NewsEventAssessment] = []
_last_fetch: float = 0.0


def set_news_events(events: List[Dict[str, Any]]) -> None:
    global _cached_events, _last_fetch
    _cached_events = [
        NewsEventAssessment(
            title=e.get("title", ""),
            impact=e.get("impact", "low"),
            currency=e.get("currency", ""),
            epoch=float(e.get("epoch", 0)),
            forecast=e.get("forecast"),
            previous=e.get("previous"),
        )
        for e in events
    ]
    _last_fetch = time.time() * 1000


def run_news_agent(current_epoch: float, pair: Optional[str] = None) -> AgentResult:
    start = time.time()
    insights: List[str] = []
    messages: List[AgentMessage] = []

    now_ms = current_epoch * 1000
    window_start = now_ms - 3_600_000
    window_end = now_ms + 86_400_000

    upcoming = sorted(
        [e for e in _cached_events if window_start < e.epoch * 1000 <= window_end and e.epoch * 1000 > now_ms],
        key=lambda e: e.epoch,
    )
    active = sorted(
        [e for e in _cached_events if window_start <= e.epoch * 1000 <= now_ms],
        key=lambda e: e.epoch,
        reverse=True,
    )

    has_high = any(e.impact == "high" for e in upcoming)
    has_medium = any(e.impact == "medium" for e in upcoming)

    impact_level = "low"
    recommended_action = "trade"
    if has_high:
        impact_level = "high"
        recommended_action = "news-trade"
        insights.append(
            "HIGH IMPACT event upcoming — use News Spike Follow strategy for best results"
        )
    elif has_medium:
        impact_level = "medium"
        insights.append(
            "Medium impact events detected — med/low spike follow has proven edge on several pairs"
        )

    affected: set = set()
    for e in [*upcoming, *active]:
        if pair and e.currency and e.currency in pair:
            affected.add(pair)
        if e.currency == "USD":
            for p in ["NZDUSD", "USDCHF", "AUDUSD", "USDCAD", "USDJPY", "EURUSD", "GBPUSD"]:
                affected.add(p)

    enriched: List[NewsEventAssessment] = []
    for e in upcoming:
        implication = None
        if e.currency == "USD":
            top = sorted(NEWS_PERFORMANCE.items(), key=lambda kv: kv[1]["pf"], reverse=True)[:3]
            implication = "Top pairs for USD news: " + ", ".join(
                f"{p} ({d['wr']}% WR, {d['pf']}x PF)" for p, d in top
            )
        enriched.append(
            NewsEventAssessment(
                title=e.title,
                impact=e.impact,
                currency=e.currency,
                epoch=e.epoch,
                forecast=e.forecast,
                previous=e.previous,
                strategy_implication=implication,
            )
        )

    if active:
        messages.append(
            AgentMessage(
                id=str(uuid.uuid4()),
                agent_id=NEWS_AGENT_CONFIG.id,
                type="signal",
                timestamp=time.time() * 1000,
                content=f"{len(active)} active news event(s) — check for spike follow entry",
                data={"events": [e.__dict__ for e in active]},
            )
        )

    assessment = NewsAssessment(
        upcoming_events=enriched,
        active_events=active,
        impact_level=impact_level,
        recommended_action=recommended_action,
        affected_pairs=sorted(affected),
    )

    high_n = sum(1 for e in upcoming if e.impact == "high")
    med_n = sum(1 for e in upcoming if e.impact == "medium")
    low_n = sum(1 for e in upcoming if e.impact == "low")
    insights.append(f"Next 24h: {len(upcoming)} events ({high_n} high, {med_n} medium, {low_n} low)")
    insights.append(f"Recommended: {recommended_action} — {len(affected)} pairs affected")

    return AgentResult(
        agent_id=NEWS_AGENT_CONFIG.id,
        status="completed",
        timestamp=time.time() * 1000,
        output={"assessment": assessment.__dict__},
        insights=insights,
        duration=(time.time() - start) * 1000,
    )
