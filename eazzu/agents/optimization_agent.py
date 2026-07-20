"""Optimization Agent — analyzes signal outcomes and suggests parameter fixes.

Converted from infinite-loop-sound's optimization-agent.ts. Uses an in-memory
signal optimizer that tracks failure patterns and recommends safe parameter
adjustments.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, Dict, List, Optional

from eazzu.agents.types import AgentConfig, AgentResult

OPTIMIZATION_AGENT_CONFIG = AgentConfig(
    id="optimization-agent",
    name="Optimization Agent",
    description=(
        "Analyzes SL-hit patterns, auto-applies safe parameter fixes, and "
        "tracks improvement history across all traded pairs and sessions."
    ),
    enabled=True,
    priority="high",
    interval_sec=60,
    instruments=["all"],
    timeframes=["all"],
)

CAUSE_LABELS = {
    "sl_placement": "SL Placement",
    "timing": "Timing",
    "confluence_failure": "Confluence Failure",
    "session_mismatch": "Session Mismatch",
    "overtrading": "Overtrading",
    "news_interference": "News Interference",
}


class SignalOptimizer:
    """Tracks signal outcomes and detects failure patterns."""

    def __init__(self) -> None:
        self._outcomes: List[Dict[str, Any]] = []
        self._recommendations: List[Dict[str, Any]] = []
        self._fix_history: List[Dict[str, Any]] = []

    def record_outcome(self, outcome: Dict[str, Any]) -> None:
        self._outcomes.append(outcome)
        if len(self._outcomes) > 500:
            self._outcomes.pop(0)

    def analyze(self) -> Dict[str, Any]:
        if len(self._outcomes) < 10:
            return {
                "totalOutcomes": len(self._outcomes),
                "recommendations": [],
                "rootCauses": [],
                "improvement": 0.0,
            }

        losses = [o for o in self._outcomes if o.get("outcome") == "loss"]
        wins = [o for o in self._outcomes if o.get("outcome") == "win"]
        total = len(self._outcomes)
        win_rate = len(wins) / total

        cause_counts: Dict[str, int] = defaultdict(int)
        for loss in losses:
            for cause in loss.get("root_causes", ["sl_placement"]):
                cause_counts[cause] += 1

        root_causes = sorted(
            [{"cause": k, "label": CAUSE_LABELS.get(k, k), "count": v, "pct": v / max(len(losses), 1) * 100} for k, v in cause_counts.items()],
            key=lambda x: x["count"],
            reverse=True,
        )

        recommendations: List[Dict[str, Any]] = []
        for rc in root_causes[:3]:
            if rc["cause"] == "sl_placement":
                recommendations.append({
                    "action": "widen_sl",
                    "description": f"Widen SL by 15% — {rc['count']} losses from SL placement",
                    "confidence": min(0.9, rc["pct"] / 100 + 0.3),
                    "param": "stop_loss_mult",
                    "current": 1.0,
                    "suggested": 1.15,
                })
            elif rc["cause"] == "timing":
                recommendations.append({
                    "action": "delay_entry",
                    "description": f"Add 1-bar confirmation delay — {rc['count']} timing losses",
                    "confidence": min(0.8, rc["pct"] / 100 + 0.2),
                    "param": "confirmation_bars",
                    "current": 0,
                    "suggested": 1,
                })
            elif rc["cause"] == "confluence_failure":
                recommendations.append({
                    "action": "raise_threshold",
                    "description": f"Raise min confluence to 4 — {rc['count']} confluence failures",
                    "confidence": min(0.85, rc["pct"] / 100 + 0.25),
                    "param": "min_confluence",
                    "current": 3,
                    "suggested": 4,
                })
            elif rc["cause"] == "session_mismatch":
                recommendations.append({
                    "action": "restrict_session",
                    "description": f"Restrict to London/NY overlap — {rc['count']} session mismatch losses",
                    "confidence": min(0.75, rc["pct"] / 100 + 0.15),
                    "param": "allowed_sessions",
                    "current": ["all"],
                    "suggested": ["london", "overlap", "ny"],
                })

        recent_wr = len([o for o in self._outcomes[-20:] if o.get("outcome") == "win"]) / min(20, total)
        improvement = recent_wr - win_rate

        return {
            "totalOutcomes": total,
            "winRate": win_rate,
            "recentWinRate": recent_wr,
            "improvement": improvement,
            "rootCauses": root_causes,
            "recommendations": recommendations,
        }

    def apply_fix(self, recommendation: Dict[str, Any]) -> Dict[str, Any]:
        self._fix_history.append({
            "action": recommendation["action"],
            "param": recommendation.get("param"),
            "from": recommendation.get("current"),
            "to": recommendation.get("suggested"),
            "appliedAt": time.time() * 1000,
        })
        return {"applied": True, "fix": self._fix_history[-1]}

    def history(self) -> List[Dict[str, Any]]:
        return list(self._fix_history)


_optimizer: Optional[SignalOptimizer] = None


def _get_optimizer() -> SignalOptimizer:
    global _optimizer
    if _optimizer is None:
        _optimizer = SignalOptimizer()
    return _optimizer


def record_signal_outcome(
    pair: str,
    strategy: str,
    outcome: str,
    root_causes: Optional[List[str]] = None,
    pnl_pips: Optional[float] = None,
) -> Dict[str, Any]:
    _get_optimizer().record_outcome({
        "pair": pair,
        "strategy": strategy,
        "outcome": outcome,
        "root_causes": root_causes or [],
        "pnl_pips": pnl_pips,
        "timestamp": time.time() * 1000,
    })
    return {"recorded": True}


def run_optimization_agent() -> AgentResult:
    start = time.time()
    analysis = _get_optimizer().analyze()

    insights: List[str] = [
        f"Analyzed {analysis['totalOutcomes']} outcomes — WR: {analysis.get('winRate', 0):.1%}",
    ]
    if analysis.get("improvement", 0) > 0:
        insights.append(f"Improvement detected: +{analysis['improvement']:.1%} recent vs overall")
    for rec in analysis.get("recommendations", []):
        insights.append(f"Suggestion: {rec['description']} (confidence: {rec['confidence']:.0%})")

    return AgentResult(
        agent_id=OPTIMIZATION_AGENT_CONFIG.id,
        status="completed",
        timestamp=time.time() * 1000,
        output=analysis,
        insights=insights,
        duration=(time.time() - start) * 1000,
    )


def apply_optimization_fix(action: str, param: str, current: Any, suggested: Any) -> Dict[str, Any]:
    return _get_optimizer().apply_fix({
        "action": action,
        "param": param,
        "current": current,
        "suggested": suggested,
    })


def get_optimization_history() -> List[Dict[str, Any]]:
    return _get_optimizer().history()
