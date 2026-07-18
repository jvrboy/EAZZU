"""Persistent outcome tracking and bounded adaptive calibration for generated signals."""
from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from .models import Candle, GeneratedSignal, SignalOutcome, utc_now


class AdaptiveSignalTracker:
    """Store signals, resolve their outcomes, and learn from attributable evidence.

    Learning is intentionally bounded and transparent. A source's weight only
    moves after resolved outcomes are recorded; ambiguous or unobserved results
    do not train the model. The tracker never places trades or fetches data.
    """

    SCHEMA_VERSION = 1
    MIN_SEGMENT_SAMPLES = 5

    def __init__(self, storage_path: Optional[Any] = None) -> None:
        default_path = Path.home() / ".eazzu" / "signal_ledger.json"
        configured = storage_path or os.environ.get("EAZZU_SIGNAL_LEDGER") or default_path
        self.storage_path = Path(configured).expanduser()

    @staticmethod
    def _default_state() -> Dict[str, Any]:
        return {
            "schema_version": AdaptiveSignalTracker.SCHEMA_VERSION,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "signals": [],
            "evidence_stats": {"global": {}, "segments": {}},
            "signal_stats": {"global": {}, "segments": {}},
        }

    def _load(self) -> Dict[str, Any]:
        if not self.storage_path.exists():
            return self._default_state()
        try:
            state = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"could not read signal ledger at {self.storage_path}") from exc
        if not isinstance(state, dict) or state.get("schema_version") != self.SCHEMA_VERSION:
            raise ValueError("unsupported or malformed signal ledger schema")
        for key, fallback in self._default_state().items():
            state.setdefault(key, deepcopy(fallback))
        return state

    def _save(self, state: Dict[str, Any]) -> None:
        state["updated_at"] = utc_now()
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile("w", encoding="utf-8", dir=str(self.storage_path.parent), delete=False) as handle:
            json.dump(state, handle, indent=2, sort_keys=True)
            handle.write("\n")
            temporary_path = Path(handle.name)
        temporary_path.replace(self.storage_path)

    @staticmethod
    def _segment_key(symbol: Optional[str], timeframe: Optional[str], direction: Optional[str]) -> str:
        return "|".join((str(symbol or "*").upper(), str(timeframe or "*").lower(), str(direction or "*").lower()))

    @staticmethod
    def _empty_stats() -> Dict[str, Any]:
        return {
            "resolved": 0,
            "wins": 0,
            "losses": 0,
            "expired": 0,
            "ambiguous": 0,
            "sum_r": 0.0,
            "updated_at": None,
        }

    @classmethod
    def _update_stats(cls, bucket: Dict[str, Any], outcome: Mapping[str, Any]) -> None:
        status = outcome.get("status")
        bucket.setdefault("resolved", 0)
        bucket.setdefault("wins", 0)
        bucket.setdefault("losses", 0)
        bucket.setdefault("expired", 0)
        bucket.setdefault("ambiguous", 0)
        bucket.setdefault("sum_r", 0.0)
        if status in {"win", "loss"}:
            bucket["resolved"] += 1
            bucket["wins" if status == "win" else "losses"] += 1
            return_r = outcome.get("return_r")
            if isinstance(return_r, (int, float)):
                bucket["sum_r"] += float(return_r)
        elif status == "expired":
            bucket["expired"] += 1
        elif status == "ambiguous":
            bucket["ambiguous"] += 1
        bucket["updated_at"] = utc_now()

    @classmethod
    def _stats_snapshot(cls, stats: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
        stats = stats or cls._empty_stats()
        resolved = int(stats.get("resolved", 0) or 0)
        wins = int(stats.get("wins", 0) or 0)
        losses = int(stats.get("losses", 0) or 0)
        sum_r = float(stats.get("sum_r", 0.0) or 0.0)
        return {
            "resolved": resolved,
            "wins": wins,
            "losses": losses,
            "expired": int(stats.get("expired", 0) or 0),
            "ambiguous": int(stats.get("ambiguous", 0) or 0),
            "win_rate": round(wins / resolved, 4) if resolved else None,
            "average_r": round(sum_r / resolved, 4) if resolved else None,
            "total_r": round(sum_r, 4),
            "updated_at": stats.get("updated_at"),
        }

    def _select_stats(
        self,
        state: Mapping[str, Any],
        category: str,
        subject: str,
        symbol: Optional[str],
        timeframe: Optional[str],
        direction: Optional[str],
    ) -> Tuple[Mapping[str, Any], str]:
        pools = state.get(category, {})
        segment_key = self._segment_key(symbol, timeframe, direction)
        segment = pools.get("segments", {}).get(f"{subject}::{segment_key}")
        if segment and int(segment.get("resolved", 0) or 0) >= self.MIN_SEGMENT_SAMPLES:
            return segment, "segment"
        global_stats = pools.get("global", {}).get(subject)
        if global_stats and int(global_stats.get("resolved", 0) or 0) >= self.MIN_SEGMENT_SAMPLES:
            return global_stats, "global"
        return self._empty_stats(), "insufficient_data"

    @staticmethod
    def _extract_signal(signal: Any) -> Dict[str, Any]:
        if isinstance(signal, GeneratedSignal):
            payload = signal.to_dict()
        elif isinstance(signal, Mapping):
            payload = dict(signal)
        else:
            raise ValueError("signal must be a GeneratedSignal or mapping")
        required = {"id", "direction", "entry_price", "stop_loss", "take_profit", "evidence"}
        missing = sorted(field for field in required if field not in payload)
        if missing:
            raise ValueError(f"signal is missing required fields: {', '.join(missing)}")
        if payload["direction"] not in {"bullish", "bearish"}:
            raise ValueError("signal direction must be bullish or bearish")
        return payload

    def record_signal(self, signal: Any) -> Dict[str, Any]:
        """Persist a generated signal unless an identical id already exists."""
        payload = self._extract_signal(signal)
        state = self._load()
        existing = next((row for row in state["signals"] if row.get("signal", {}).get("id") == payload["id"]), None)
        if existing:
            return {"recorded": False, "reason": "already_recorded", "signal_id": payload["id"], "ledger": str(self.storage_path)}
        state["signals"].append({"signal": payload, "outcome": None, "recorded_at": utc_now()})
        self._save(state)
        return {"recorded": True, "signal_id": payload["id"], "ledger": str(self.storage_path)}

    @staticmethod
    def _normalize_future_candles(candles: Iterable[Any]) -> List[Candle]:
        return [item if isinstance(item, Candle) else Candle.from_mapping(item) for item in candles]

    def evaluate_signal(self, signal: Any, future_candles: Iterable[Any]) -> SignalOutcome:
        """Resolve a signal deterministically against its subsequent candle path.

        A candle hitting both stop and target has an unknowable intrabar order and
        is marked ``ambiguous`` rather than being used for performance learning.
        """
        payload = self._extract_signal(signal)
        candles = self._normalize_future_candles(future_candles)
        if not candles:
            return SignalOutcome(payload["id"], "pending", utc_now(), None, None, 0, "no_future_candles")
        direction = payload["direction"]
        entry = float(payload["entry_price"])
        stop = float(payload["stop_loss"])
        target = float(payload["take_profit"])
        risk = abs(entry - stop)
        if risk <= 0:
            raise ValueError("signal stop loss must differ from its entry price")
        expiry_bars = max(int(payload.get("expiry_bars", 12) or 12), 1)

        for index, candle in enumerate(candles[:expiry_bars], start=1):
            if direction == "bullish":
                target_hit = candle.high >= target
                stop_hit = candle.low <= stop
            else:
                target_hit = candle.low <= target
                stop_hit = candle.high >= stop
            if target_hit and stop_hit:
                return SignalOutcome(
                    payload["id"], "ambiguous", utc_now(), None, None, index,
                    "target_and_stop_touched_in_same_candle",
                    {"high": candle.high, "low": candle.low, "target": target, "stop": stop},
                )
            if target_hit:
                reward_r = abs(target - entry) / risk
                return SignalOutcome(payload["id"], "win", utc_now(), target, reward_r, index, "take_profit_hit")
            if stop_hit:
                return SignalOutcome(payload["id"], "loss", utc_now(), stop, -1.0, index, "stop_loss_hit")

        observed = candles[:expiry_bars]
        exit_price = observed[-1].close
        signed_move = (exit_price - entry) if direction == "bullish" else (entry - exit_price)
        return_r = signed_move / risk
        return SignalOutcome(
            payload["id"], "expired", utc_now(), exit_price, return_r, len(observed),
            "expiry_reached_without_stop_or_target",
        )

    def _apply_learning(self, state: Dict[str, Any], signal: Mapping[str, Any], outcome: Mapping[str, Any]) -> None:
        """Update evidence and signal performance only for unambiguous resolved outcomes."""
        if outcome.get("status") not in {"win", "loss"}:
            return
        symbol = signal.get("symbol")
        timeframe = signal.get("timeframe")
        direction = signal.get("direction")
        signal_key = self._segment_key(symbol, timeframe, direction)
        signal_global = state["signal_stats"]["global"].setdefault("all", self._empty_stats())
        signal_segment = state["signal_stats"]["segments"].setdefault(f"all::{signal_key}", self._empty_stats())
        self._update_stats(signal_global, outcome)
        self._update_stats(signal_segment, outcome)
        for evidence in signal.get("evidence", []):
            if not isinstance(evidence, Mapping) or not evidence.get("source"):
                continue
            source = str(evidence["source"])
            global_stats = state["evidence_stats"]["global"].setdefault(source, self._empty_stats())
            segment_stats = state["evidence_stats"]["segments"].setdefault(f"{source}::{signal_key}", self._empty_stats())
            self._update_stats(global_stats, outcome)
            self._update_stats(segment_stats, outcome)

    def resolve_signal(self, signal_id: str, future_candles: Iterable[Any]) -> Dict[str, Any]:
        """Evaluate a recorded signal, persist its outcome, and update learnable stats."""
        state = self._load()
        record = next((row for row in state["signals"] if row.get("signal", {}).get("id") == signal_id), None)
        if record is None:
            raise KeyError(f"signal '{signal_id}' is not present in the ledger")
        if record.get("outcome") is not None:
            return {"resolved": False, "reason": "already_resolved", "signal_id": signal_id, "outcome": record["outcome"]}
        outcome = self.evaluate_signal(record["signal"], future_candles).to_dict()
        if outcome["status"] == "pending":
            return {"resolved": False, "reason": "pending", "signal_id": signal_id, "outcome": outcome}
        record["outcome"] = outcome
        self._apply_learning(state, record["signal"], outcome)
        self._save(state)
        return {
            "resolved": True,
            "signal_id": signal_id,
            "outcome": outcome,
            "learning_applied": outcome["status"] in {"win", "loss"},
            "summary": self._summary_from_state(state),
        }

    def evidence_weight(
        self,
        source: str,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        """Return a conservative evidence multiplier from historical outcomes."""
        state = self._load()
        stats, scope = self._select_stats(state, "evidence_stats", source, symbol, timeframe, direction)
        snapshot = self._stats_snapshot(stats)
        if scope == "insufficient_data":
            return 1.0, {"source": source, "scope": scope, "weight": 1.0, "learned": False, **snapshot}
        win_rate = float(snapshot["win_rate"] or 0.5)
        average_r = float(snapshot["average_r"] or 0.0)
        weight = 1.0 + (win_rate - 0.5) * 0.45 + max(-0.12, min(0.12, average_r * 0.06))
        weight = max(0.75, min(1.25, weight))
        return round(weight, 4), {"source": source, "scope": scope, "weight": round(weight, 4), "learned": True, **snapshot}

    def calibrate_confidence(
        self,
        base_confidence: float,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> Tuple[float, Dict[str, Any]]:
        """Apply a bounded empirical outcome adjustment to aggregate confidence."""
        state = self._load()
        stats, scope = self._select_stats(state, "signal_stats", "all", symbol, timeframe, direction)
        snapshot = self._stats_snapshot(stats)
        base = max(0.0, min(1.0, float(base_confidence)))
        if scope == "insufficient_data":
            return base, {"scope": scope, "base_confidence": round(base, 4), "adjustment": 0.0, "learned": False, **snapshot}
        win_rate = float(snapshot["win_rate"] or 0.5)
        average_r = float(snapshot["average_r"] or 0.0)
        adjustment = max(-0.12, min(0.12, (win_rate - 0.5) * 0.18 + average_r * 0.04))
        calibrated = max(0.20, min(0.90, base + adjustment))
        return round(calibrated, 4), {
            "scope": scope,
            "base_confidence": round(base, 4),
            "adjustment": round(adjustment, 4),
            "calibrated_confidence": round(calibrated, 4),
            "learned": True,
            **snapshot,
        }

    def calibration_context(
        self,
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        direction: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Expose the current calibration state without modifying stored data."""
        _, calibration = self.calibrate_confidence(0.5, symbol, timeframe, direction)
        return {
            "ledger": str(self.storage_path),
            "adaptive_learning": True,
            "sample_scope": calibration["scope"],
            "resolved_samples": calibration["resolved"],
            "win_rate": calibration["win_rate"],
            "average_r": calibration["average_r"],
        }

    def _summary_from_state(self, state: Mapping[str, Any]) -> Dict[str, Any]:
        signal_stats = self._stats_snapshot(state.get("signal_stats", {}).get("global", {}).get("all"))
        signals = list(state.get("signals", []))
        outcomes = [record.get("outcome") for record in signals if record.get("outcome")]
        sources = {
            source: self._stats_snapshot(stats)
            for source, stats in sorted(state.get("evidence_stats", {}).get("global", {}).items())
        }
        return {
            "ledger": str(self.storage_path),
            "schema_version": state.get("schema_version"),
            "signals_recorded": len(signals),
            "signals_pending": sum(1 for record in signals if record.get("outcome") is None),
            "outcomes": signal_stats,
            "outcome_status_counts": {
                status: sum(1 for outcome in outcomes if outcome and outcome.get("status") == status)
                for status in ("win", "loss", "expired", "ambiguous")
            },
            "evidence_performance": sources,
            "updated_at": state.get("updated_at"),
        }

    def summary(self) -> Dict[str, Any]:
        """Return performance and evidence-learning metrics for the current ledger."""
        return self._summary_from_state(self._load())

    def list_signals(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return newest recorded signals and their outcomes without exposing mutable state."""
        if limit <= 0:
            raise ValueError("limit must be positive")
        state = self._load()
        rows = state.get("signals", [])[-limit:]
        return list(reversed(deepcopy(rows)))
