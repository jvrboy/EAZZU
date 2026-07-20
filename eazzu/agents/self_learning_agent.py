"""Self-Learning Agent — tracks signal outcomes and adjusts confluence weights.

Converted from infinite-loop-sound's self-learning-agent.ts. Uses an in-memory
weight table instead of Supabase so the module stays portable and dependency
free. Callers may persist the table via :func:`export_weights` / :func:`import_weights`.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

LEARNING_RATE = 0.15

_weights: Dict[str, Dict[str, Any]] = {}


def _session_from_hour(hour_utc: int) -> str:
    if 0 <= hour_utc < 7:
        return "asia"
    if 7 <= hour_utc < 12:
        return "london"
    if 12 <= hour_utc < 16:
        return "overlap"
    if 16 <= hour_utc < 21:
        return "ny"
    return "off"


def record_signal_outcome(
    pair: str,
    timeframe: str,
    strategy: str,
    direction: str,
    confluence_factors: List[str],
    outcome: str,  # "win" | "loss" | "breakeven" | "pending"
    session: Optional[str] = None,
    pnl_pips: Optional[float] = None,
    confidence_at_signal: Optional[float] = None,
) -> Dict[str, Any]:
    insights: List[str] = []
    sess = session or _session_from_hour(int(time.gmtime().tm_hour))
    insights.append(f"Recorded {outcome} for {strategy} on {pair}")

    weights_updated = 0
    if outcome in ("win", "loss"):
        is_win = outcome == "win"
        for factor in confluence_factors:
            key = f"{pair}:{sess}:{strategy}:{factor}"
            rec = _weights.get(key)
            if rec is None:
                _weights[key] = {
                    "weight": 0.55 if is_win else 0.45,
                    "samples": 1,
                    "win_count": 1 if is_win else 0,
                }
                weights_updated += 1
            else:
                target = 1.0 if is_win else 0.0
                new_w = rec["weight"] + LEARNING_RATE * (target - rec["weight"])
                rec["weight"] = max(0.05, min(0.95, new_w))
                rec["samples"] += 1
                if is_win:
                    rec["win_count"] += 1
                weights_updated += 1

    return {
        "recorded": True,
        "weightsUpdated": weights_updated,
        "insights": insights,
    }


def get_learned_weights(pair: str, session: Optional[str] = None) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for key, rec in _weights.items():
        parts = key.split(":")
        if parts[0] != pair:
            continue
        if session and parts[1] != session:
            continue
        result[f"{parts[2]}:{parts[3]}"] = {
            "weight": rec["weight"],
            "samples": rec["samples"],
            "winRate": rec["win_count"] / rec["samples"] if rec["samples"] > 0 else 0,
        }
    return result


def get_strategy_performance() -> Dict[str, Any]:
    total = sum(rec["samples"] for rec in _weights.values())
    wins = sum(rec["win_count"] for rec in _weights.values())
    return {
        "total": total,
        "wins": wins,
        "losses": total - wins,
        "winRate": wins / total if total > 0 else 0,
    }


def export_weights() -> Dict[str, Any]:
    return dict(_weights)


def import_weights(data: Dict[str, Any]) -> None:
    _weights.update(data)
