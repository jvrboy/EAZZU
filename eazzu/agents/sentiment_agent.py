"""Sentiment Agent — market sentiment analysis from multiple sources.

Converted from infinite-loop-sound's sentiment-agent.ts. Caller-supplied
news/social metrics drive the score; no external I/O.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from eazzu.agents.types import AgentConfig, AgentResult, SentimentAssessment

SENTIMENT_AGENT_CONFIG = AgentConfig(
    id="sentiment-agent",
    name="Sentiment Agent",
    description="Market mood scoring from news, social, and technical sources.",
    enabled=True,
    priority="medium",
    interval_sec=60,
    instruments=["all"],
    timeframes=["all"],
)


def run_sentiment_agent(
    news_score: float = 0.0,
    social_score: float = 0.0,
    market_score: float = 0.0,
    trending_topics: Optional[List[str]] = None,
) -> AgentResult:
    start = time.time()
    sources = [
        {"name": "News", "sentiment": news_score, "weight": 0.4},
        {"name": "Social", "sentiment": social_score, "weight": 0.35},
        {"name": "Market", "sentiment": market_score, "weight": 0.25},
    ]
    overall = sum(s["sentiment"] * s["weight"] for s in sources)
    confidence = min(1.0, abs(overall) * 1.5 + 0.3)
    bias = "BULLISH" if overall > 0.15 else "BEARISH" if overall < -0.15 else "NEUTRAL"

    assessment = SentimentAssessment(
        overall_sentiment=overall,
        confidence=confidence,
        sources=sources,
        trending_topics=trending_topics or [],
        recommended_bias=bias,
    )

    insights: List[str] = [
        f"Overall sentiment: {overall:+.2f} ({bias})",
        f"Confidence: {confidence * 100:.0f}%",
    ]

    return AgentResult(
        agent_id=SENTIMENT_AGENT_CONFIG.id,
        status="completed",
        timestamp=time.time() * 1000,
        output={"sentiment": assessment.__dict__},
        insights=insights,
        duration=(time.time() - start) * 1000,
    )
