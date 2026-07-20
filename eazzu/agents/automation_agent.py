"""Automation Agent — monitors automation engine health and schedule performance.

Converted from infinite-loop-sound's automation-agent.ts. Manages scan
schedules, reports on dispatch health, and suggests optimal scan times.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from eazzu.agents.types import AgentConfig, AgentResult

AUTOMATION_AGENT_CONFIG = AgentConfig(
    id="automation-agent",
    name="Automation Agent",
    description=(
        "Monitors automation engine health, reports schedule performance, "
        "suggests optimal scan times, and detects dispatch issues."
    ),
    enabled=True,
    priority="medium",
    interval_sec=60,
    instruments=["all"],
    timeframes=["all"],
)


class AutomationEngine:
    """In-memory automation schedule manager."""

    def __init__(self) -> None:
        self._schedules: Dict[str, Dict[str, Any]] = {}
        self._signals: List[Dict[str, Any]] = []
        self._state: Dict[str, Any] = {
            "isRunning": False,
            "lastScan": 0,
            "totalScans": 0,
            "totalSignals": 0,
            "errors": 0,
        }

    def add_schedule(self, schedule_id: str, pair: str, timeframe: str, interval_sec: int, enabled: bool = True) -> Dict[str, Any]:
        self._schedules[schedule_id] = {
            "id": schedule_id,
            "pair": pair,
            "timeframe": timeframe,
            "intervalSec": interval_sec,
            "enabled": enabled,
            "lastRun": 0,
            "runCount": 0,
            "signalCount": 0,
            "createdAt": time.time() * 1000,
        }
        return {"added": schedule_id}

    def remove_schedule(self, schedule_id: str) -> Dict[str, Any]:
        self._schedules.pop(schedule_id, None)
        return {"removed": schedule_id}

    def toggle_schedule(self, schedule_id: str, enabled: bool) -> Dict[str, Any]:
        if schedule_id in self._schedules:
            self._schedules[schedule_id]["enabled"] = enabled
            return {"toggled": schedule_id, "enabled": enabled}
        return {"error": "schedule_not_found"}

    def record_scan(self, schedule_id: str, signals_found: int = 0) -> None:
        if schedule_id in self._schedules:
            s = self._schedules[schedule_id]
            s["lastRun"] = time.time() * 1000
            s["runCount"] += 1
            s["signalCount"] += signals_found
            self._state["totalScans"] += 1
            self._state["totalSignals"] += signals_found
            self._state["lastScan"] = s["lastRun"]

    def record_error(self) -> None:
        self._state["errors"] += 1

    def get_state(self) -> Dict[str, Any]:
        return {
            "state": dict(self._state),
            "schedules": list(self._schedules.values()),
            "activeSchedules": sum(1 for s in self._schedules.values() if s["enabled"]),
        }

    def suggest_optimal_times(self) -> List[Dict[str, Any]]:
        """Suggest optimal scan times based on signal density by hour."""
        hour_signals: Dict[int, int] = {}
        for sig in self._signals:
            hour = int(time.gmtime(sig.get("timestamp", 0) / 1000).tm_hour)
            hour_signals[hour] = hour_signals.get(hour, 0) + 1

        if not hour_signals:
            return [
                {"hour": 7, "reason": "London open — high volatility"},
                {"hour": 12, "reason": "London/NY overlap — peak liquidity"},
                {"hour": 13, "reason": "US session — strong directional moves"},
            ]

        sorted_hours = sorted(hour_signals.items(), key=lambda x: x[1], reverse=True)
        return [{"hour": h, "signalCount": c, "reason": f"Historical peak: {c} signals"} for h, c in sorted_hours[:5]]


_engine: Optional[AutomationEngine] = None


def _get_engine() -> AutomationEngine:
    global _engine
    if _engine is None:
        _engine = AutomationEngine()
    return _engine


def run_automation_agent() -> AgentResult:
    start = time.time()
    engine = _get_engine()
    state = engine.get_state()
    suggestions = engine.suggest_optimal_times()

    insights: List[str] = [
        f"Engine: {state['state']['totalScans']} scans, {state['state']['totalSignals']} signals, {state['state']['errors']} errors",
        f"Active schedules: {state['activeSchedules']}/{len(state['schedules'])}",
    ]
    if suggestions:
        top = suggestions[0]
        insights.append(f"Optimal scan hour: {top['hour']:02d}:00 UTC ({top['reason']})")

    return AgentResult(
        agent_id=AUTOMATION_AGENT_CONFIG.id,
        status="completed",
        timestamp=time.time() * 1000,
        output={"state": state, "suggestions": suggestions},
        insights=insights,
        duration=(time.time() - start) * 1000,
    )


def add_automation_schedule(schedule_id: str, pair: str, timeframe: str, interval_sec: int) -> Dict[str, Any]:
    return _get_engine().add_schedule(schedule_id, pair, timeframe, interval_sec)


def remove_automation_schedule(schedule_id: str) -> Dict[str, Any]:
    return _get_engine().remove_schedule(schedule_id)


def toggle_automation_schedule(schedule_id: str, enabled: bool) -> Dict[str, Any]:
    return _get_engine().toggle_schedule(schedule_id, enabled)


def record_automation_scan(schedule_id: str, signals_found: int = 0) -> Dict[str, Any]:
    _get_engine().record_scan(schedule_id, signals_found)
    return {"recorded": True, "scheduleId": schedule_id, "signalsFound": signals_found}


def get_automation_state() -> Dict[str, Any]:
    return _get_engine().get_state()
