"""Anomaly clusterer — groups detector events into clusters by bar proximity.

Converted from infinite-loop-sound's anomaly-cluster.ts. Useful for identifying
"market storms" — periods of unusual activity vs isolated one-off events.
"""
from __future__ import annotations

from typing import Any, Dict, List


def cluster_anomalies(
    events: List[Dict[str, Any]],
    candles: List[Dict[str, Any]],
    max_gap: int = 5,
) -> List[Dict[str, Any]]:
    """Group events by bar index proximity into clusters.

    Args:
        events: List of dicts with at least 'index' and 'kind' keys.
        candles: Candle list for epoch lookup.
        max_gap: Maximum bar gap to consider events part of the same cluster.

    Returns:
        Clusters sorted by intensity (events per bar), descending.
    """
    if not events:
        return []

    sorted_events = sorted(events, key=lambda e: e["index"])
    clusters: List[Dict[str, Any]] = []
    current: List[Dict[str, Any]] = [sorted_events[0]]

    def flush() -> None:
        if not current:
            return
        start_idx = current[0]["index"]
        end_idx = current[-1]["index"]
        span = max(1, end_idx - start_idx + 1)
        kinds = list(set(e["kind"] for e in current))
        clusters.append({
            "startIdx": start_idx,
            "endIdx": end_idx,
            "size": len(current),
            "intensity": len(current) / span,
            "kinds": kinds,
            "startEpoch": candles[start_idx].get("epoch", 0) if start_idx < len(candles) else 0,
            "endEpoch": candles[end_idx].get("epoch", 0) if end_idx < len(candles) else 0,
        })

    for i in range(1, len(sorted_events)):
        prev = sorted_events[i - 1]
        cur = sorted_events[i]
        if cur["index"] - prev["index"] <= max_gap:
            current.append(cur)
        else:
            flush()
            current = [cur]
    flush()

    return sorted(clusters, key=lambda c: c["intensity"], reverse=True)


def detect_anomalies(candles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Run basic anomaly detectors over candle data and return raw events."""
    events: List[Dict[str, Any]] = []

    for i in range(2, len(candles)):
        c = candles[i]
        prev = candles[i - 1]

        # Spike detection — large candle relative to recent average
        if i >= 10:
            avg_range = sum(candles[j]["high"] - candles[j]["low"] for j in range(i - 10, i)) / 10
            curr_range = c["high"] - c["low"]
            if avg_range > 0 and curr_range > avg_range * 3:
                events.append({"index": i, "kind": "spike-large", "severity": "high"})

        # Gap detection
        if prev["close"] > 0:
            gap_pct = abs(c["open"] - prev["close"]) / prev["close"]
            if gap_pct > 0.01:
                direction = "up" if c["open"] > prev["close"] else "down"
                events.append({"index": i, "kind": f"gap-{direction}", "severity": "medium"})

        # Volume spike
        if i >= 20:
            avg_vol = sum(candles[j].get("volume", 0) for j in range(i - 20, i)) / 20
            if avg_vol > 0 and c.get("volume", 0) > avg_vol * 3:
                events.append({"index": i, "kind": "vol-spike", "severity": "medium"})

        # Range break
        if i >= 20:
            recent_high = max(candles[j]["high"] for j in range(i - 20, i))
            recent_low = min(candles[j]["low"] for j in range(i - 20, i))
            if c["close"] > recent_high:
                events.append({"index": i, "kind": "break-up", "severity": "high"})
            elif c["close"] < recent_low:
                events.append({"index": i, "kind": "break-down", "severity": "high"})

    return events
