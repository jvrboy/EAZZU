"""Expanded tools — optimization, automation, web scraping, advanced indicators, anomaly clustering.

Wraps the new agents and trading modules so the EAZZU agent can invoke them
as tools alongside the existing tool registry.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _error(code: str, exc: Exception) -> Dict[str, Any]:
    return {"error": code, "message": str(exc)}


# ─── Optimization ────────────────────────────────────────────────────────

def run_optimization_analysis() -> Dict[str, Any]:
    """Analyze signal outcomes, detect failure patterns, and suggest parameter fixes."""
    try:
        from eazzu.agents.optimization_agent import run_optimization_agent
        return run_optimization_agent().to_dict()
    except Exception as exc:
        return _error("optimization_failed", exc)


def record_optimization_outcome(
    pair: str, strategy: str, outcome: str,
    root_causes: Optional[List[str]] = None, pnl_pips: Optional[float] = None,
) -> Dict[str, Any]:
    """Record a signal outcome for the optimization agent to analyze."""
    try:
        from eazzu.agents.optimization_agent import record_signal_outcome
        return record_signal_outcome(pair, strategy, outcome, root_causes, pnl_pips)
    except Exception as exc:
        return _error("optimization_record_failed", exc)


def apply_optimization_fix(action: str, param: str, current: Any, suggested: Any) -> Dict[str, Any]:
    """Apply a parameter fix recommended by the optimization agent."""
    try:
        from eazzu.agents.optimization_agent import apply_optimization_fix as _apply
        return _apply(action, param, current, suggested)
    except Exception as exc:
        return _error("optimization_apply_failed", exc)


def get_optimization_history() -> Dict[str, Any]:
    """Get the history of applied optimization fixes."""
    try:
        from eazzu.agents.optimization_agent import get_optimization_history
        return {"history": get_optimization_history()}
    except Exception as exc:
        return _error("optimization_history_failed", exc)


# ─── Automation ──────────────────────────────────────────────────────────

def run_automation_check() -> Dict[str, Any]:
    """Check automation engine health and get schedule suggestions."""
    try:
        from eazzu.agents.automation_agent import run_automation_agent
        return run_automation_agent().to_dict()
    except Exception as exc:
        return _error("automation_check_failed", exc)


def add_automation_schedule(schedule_id: str, pair: str, timeframe: str, interval_sec: int) -> Dict[str, Any]:
    """Add a new automation scan schedule."""
    try:
        from eazzu.agents.automation_agent import add_automation_schedule
        return add_automation_schedule(schedule_id, pair, timeframe, interval_sec)
    except Exception as exc:
        return _error("automation_add_failed", exc)


def remove_automation_schedule(schedule_id: str) -> Dict[str, Any]:
    """Remove an automation scan schedule."""
    try:
        from eazzu.agents.automation_agent import remove_automation_schedule
        return remove_automation_schedule(schedule_id)
    except Exception as exc:
        return _error("automation_remove_failed", exc)


def toggle_automation_schedule(schedule_id: str, enabled: bool) -> Dict[str, Any]:
    """Enable or disable an automation schedule."""
    try:
        from eazzu.agents.automation_agent import toggle_automation_schedule
        return toggle_automation_schedule(schedule_id, enabled)
    except Exception as exc:
        return _error("automation_toggle_failed", exc)


def record_automation_scan(schedule_id: str, signals_found: int = 0) -> Dict[str, Any]:
    """Record that an automation scan was executed."""
    try:
        from eazzu.agents.automation_agent import record_automation_scan
        return record_automation_scan(schedule_id, signals_found)
    except Exception as exc:
        return _error("automation_record_failed", exc)


def get_automation_state() -> Dict[str, Any]:
    """Get the current automation engine state and all schedules."""
    try:
        from eazzu.agents.automation_agent import get_automation_state
        return get_automation_state()
    except Exception as exc:
        return _error("automation_state_failed", exc)

# ─── Web Scraping ────────────────────────────────────────────────────────

def scrape_news(days: int = 3, limit: int = 50) -> Dict[str, Any]:
    """Scrape financial news from public economic calendar feeds."""
    try:
        from eazzu.agents.web_scraping_agent import scrape_financial_news
        return scrape_financial_news(days, limit)
    except Exception as exc:
        return _error("scrape_failed", exc)


def run_web_scraping() -> Dict[str, Any]:
    """Run the web scraping agent and return agent-formatted results."""
    try:
        from eazzu.agents.web_scraping_agent import run_web_scraping_agent
        return run_web_scraping_agent().to_dict()
    except Exception as exc:
        return _error("web_scraping_failed", exc)

# ─── Advanced Indicators ──────────────────────────────────────────────────

def compute_advanced_score(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute a composite advanced technical score from 10+ indicators."""
    try:
        from eazzu.trading.advanced_indicators import advanced_score
        return advanced_score(candles)
    except Exception as exc:
        return _error("advanced_score_failed", exc)


def compute_ttm_squeeze(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute TTM Squeeze (Bollinger inside Keltner) with momentum histogram."""
    try:
        from eazzu.trading.advanced_indicators import ttm_squeeze
        result = ttm_squeeze(candles)
        return {
            "squeezeOn": result["squeezeOn"][-1] if result["squeezeOn"] else False,
            "momentum": result["momentum"][-1] if result["momentum"] else 0,
            "bollingerUpper": result["bollingerUpper"][-1],
            "bollingerLower": result["bollingerLower"][-1],
            "keltnerUpper": result["keltnerUpper"][-1],
            "keltnerLower": result["keltnerLower"][-1],
        }
    except Exception as exc:
        return _error("ttm_squeeze_failed", exc)


def compute_aroon(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute Aroon Up/Down and oscillator."""
    try:
        from eazzu.trading.advanced_indicators import aroon
        result = aroon(candles)
        return {
            "up": result["up"][-1],
            "down": result["down"][-1],
            "oscillator": result["oscillator"][-1],
        }
    except Exception as exc:
        return _error("aroon_failed", exc)


def compute_choppiness(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute Choppiness Index — values <38.2 indicate trending, >61.8 choppy."""
    try:
        from eazzu.trading.advanced_indicators import choppiness
        result = choppiness(candles)
        return {"value": result[-1] if result else None}
    except Exception as exc:
        return _error("choppiness_failed", exc)

# ─── Anomaly Clustering ────────────────────────────────────────────────────

def detect_market_anomalies(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Detect market anomalies (spikes, gaps, volume surges, range breaks)."""
    try:
        from eazzu.trading.anomaly_cluster import detect_anomalies
        events = detect_anomalies(candles)
        return {"events": events, "count": len(events)}
    except Exception as exc:
        return _error("anomaly_detect_failed", exc)


def cluster_market_anomalies(candles: List[Dict[str, Any]], max_gap: int = 5) -> Dict[str, Any]:
    """Cluster detected anomalies by bar proximity to find market storms."""
    try:
        from eazzu.trading.anomaly_cluster import detect_anomalies, cluster_anomalies
        events = detect_anomalies(candles)
        clusters = cluster_anomalies(events, candles, max_gap)
        return {"clusters": clusters, "totalEvents": len(events), "totalClusters": len(clusters)}
    except Exception as exc:
        return _error("anomaly_cluster_failed", exc)


# ─── Tool Registry ────────────────────────────────────────────────────────

TOOLS = [
    {"name": "run_optimization_analysis", "description": "Analyze signal outcomes, detect failure patterns, and suggest parameter fixes.", "params": {}, "run": run_optimization_analysis},
    {"name": "record_optimization_outcome", "description": "Record a signal outcome for the optimization agent to analyze.", "params": {"pair": "string", "strategy": "string", "outcome": "string", "root_causes": "array[string](optional)", "pnl_pips": "float(optional)"}, "run": record_optimization_outcome},
    {"name": "apply_optimization_fix", "description": "Apply a parameter fix recommended by the optimization agent.", "params": {"action": "string", "param": "string", "current": "any", "suggested": "any"}, "run": apply_optimization_fix},
    {"name": "get_optimization_history", "description": "Get the history of applied optimization fixes.", "params": {}, "run": get_optimization_history},
    {"name": "run_automation_check", "description": "Check automation engine health and get schedule suggestions.", "params": {}, "run": run_automation_check},
    {"name": "add_automation_schedule", "description": "Add a new automation scan schedule.", "params": {"schedule_id": "string", "pair": "string", "timeframe": "string", "interval_sec": "int"}, "run": add_automation_schedule},
    {"name": "remove_automation_schedule", "description": "Remove an automation scan schedule.", "params": {"schedule_id": "string"}, "run": remove_automation_schedule},
    {"name": "toggle_automation_schedule", "description": "Enable or disable an automation schedule.", "params": {"schedule_id": "string", "enabled": "bool"}, "run": toggle_automation_schedule},
    {"name": "record_automation_scan", "description": "Record that an automation scan was executed.", "params": {"schedule_id": "string", "signals_found": "int"}, "run": record_automation_scan},
    {"name": "get_automation_state", "description": "Get the current automation engine state and all schedules.", "params": {}, "run": get_automation_state},
    {"name": "scrape_news", "description": "Scrape financial news from public economic calendar feeds.", "params": {"days": "int(optional)", "limit": "int(optional)"}, "run": scrape_news},
    {"name": "run_web_scraping", "description": "Run the web scraping agent and return agent-formatted results.", "params": {}, "run": run_web_scraping},
    {"name": "compute_advanced_score", "description": "Compute a composite advanced technical score from 10+ indicators (Williams %R, CCI, OBV, Aroon, Vortex, TTM, MFI, Awesome Osc, Choppiness).", "params": {"candles": "array[object]"}, "run": compute_advanced_score},
    {"name": "compute_ttm_squeeze", "description": "Compute TTM Squeeze (Bollinger inside Keltner) with momentum histogram.", "params": {"candles": "array[object]"}, "run": compute_ttm_squeeze},
    {"name": "compute_aroon", "description": "Compute Aroon Up/Down and oscillator.", "params": {"candles": "array[object]"}, "run": compute_aroon},
    {"name": "compute_choppiness", "description": "Compute Choppiness Index — values <38.2 indicate trending, >61.8 choppy.", "params": {"candles": "array[object]"}, "run": compute_choppiness},
    {"name": "detect_market_anomalies", "description": "Detect market anomalies (spikes, gaps, volume surges, range breaks).", "params": {"candles": "array[object]"}, "run": detect_market_anomalies},
    {"name": "cluster_market_anomalies", "description": "Cluster detected anomalies by bar proximity to find market storms.", "params": {"candles": "array[object]", "max_gap": "int(optional)"}, "run": cluster_market_anomalies},
]
