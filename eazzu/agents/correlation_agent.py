"""Correlation Matrix Agent — cross-asset correlation monitoring for hedging.

Converted from infinite-loop-sound's correlation-agent.ts.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List

from eazzu.agents.types import AgentResult


def _pearson(a: List[float], b: List[float]) -> float:
    n = min(len(a), len(b))
    if n < 3:
        return 0.0
    ma = sum(a[-n:]) / n
    mb = sum(b[-n:]) / n
    num = da = db = 0.0
    for i in range(len(a) - n, len(a)):
        xa = a[i] - ma
        xb = b[i] - mb
        num += xa * xb
        da += xa * xa
        db += xb * xb
    den = (da * db) ** 0.5
    return num / den if den > 0 else 0.0


def run_correlation_agent(
    primary: str,
    candles: List[Dict[str, Any]],
    other_assets: Dict[str, List[Dict[str, Any]]],
) -> AgentResult:
    start = time.time()
    primary_returns = [
        (candles[i]["close"] - candles[i - 1]["close"]) / (candles[i - 1]["close"] or 1)
        for i in range(1, len(candles))
    ]

    correlations: List[Dict[str, Any]] = []
    for pair, other in other_assets.items():
        if len(other) < 5:
            continue
        other_returns = [
            (other[i]["close"] - other[i - 1]["close"]) / (other[i - 1]["close"] or 1)
            for i in range(1, len(other))
        ]
        corr = _pearson(primary_returns, other_returns)
        regime = "aligned" if corr > 0.7 else "diverged" if corr < -0.5 else "neutral"
        correlations.append({"pair": pair, "correlation": corr, "regime": regime})

    avg = sum(c["correlation"] for c in correlations) / max(len(correlations), 1)
    div_score = round((1 - abs(avg)) * 100)
    hedge = any(c["regime"] == "diverged" for c in correlations)

    return AgentResult(
        agent_id="correlation-agent",
        status="completed",
        timestamp=time.time() * 1000,
        output={
            "correlations": correlations,
            "avgCorrelation": avg,
            "diversificationScore": div_score,
            "hedgeOpportunity": hedge,
        },
        insights=[
            f"Avg correlation: {avg:.2f}. Diversification: {div_score}/100. "
            f"Hedge opportunity: {'YES' if hedge else 'no'}."
        ],
        duration=(time.time() - start) * 1000,
    )
