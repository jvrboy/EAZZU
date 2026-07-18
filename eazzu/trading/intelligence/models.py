"""Typed, serialisable models for the trading-intelligence toolkit."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional
from uuid import uuid4


def utc_now() -> str:
    """Return an ISO-8601 UTC timestamp with an explicit offset."""
    return datetime.now(timezone.utc).isoformat()


def _number(value: Any, field_name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"candle field '{field_name}' must be numeric") from exc
    if number != number or number in (float("inf"), float("-inf")):
        raise ValueError(f"candle field '{field_name}' must be finite")
    return number


@dataclass(frozen=True)
class Candle:
    """One normalized OHLCV candle."""

    open: float
    high: float
    low: float
    close: float
    timestamp: Optional[Any] = None
    volume: Optional[float] = None

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> "Candle":
        """Normalize a JSON-friendly candle mapping and validate its OHLC range."""
        if not isinstance(payload, Mapping):
            raise ValueError("each candle must be a JSON object")
        open_price = _number(payload.get("open"), "open")
        high = _number(payload.get("high"), "high")
        low = _number(payload.get("low"), "low")
        close = _number(payload.get("close"), "close")
        if high < max(open_price, close) or low > min(open_price, close) or high < low:
            raise ValueError("candle OHLC values are inconsistent")
        raw_volume = payload.get("volume", payload.get("tick_volume"))
        volume = _number(raw_volume, "volume") if raw_volume is not None else None
        timestamp = payload.get("timestamp", payload.get("epoch", payload.get("time")))
        return cls(
            open=open_price,
            high=high,
            low=low,
            close=close,
            timestamp=timestamp,
            volume=volume,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Evidence:
    """A transparent contribution to a directional signal decision."""

    source: str
    direction: str
    score: float
    raw_score: float
    weight: float
    rationale: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisResult:
    """Structured multi-tool market analysis generated from a candle sequence."""

    symbol: Optional[str]
    timeframe: Optional[str]
    candle_count: int
    generated_at: str
    metrics: Dict[str, Any]
    market_structure: Dict[str, Any]
    price_action: Dict[str, Any]
    liquidity: Dict[str, Any]
    volume: Dict[str, Any]
    regime: Dict[str, Any]
    knowledge_context: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GeneratedSignal:
    """An analysis-only directional hypothesis; it never submits an order."""

    id: str
    generated_at: str
    symbol: Optional[str]
    timeframe: Optional[str]
    direction: str
    status: str
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward_ratio: float
    confidence: float
    quality: str
    expiry_bars: int
    evidence: List[Evidence]
    analysis: Dict[str, Any]
    knowledge_context: Dict[str, Any]
    tracker_context: Dict[str, Any]
    warnings: List[str] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        symbol: Optional[str],
        timeframe: Optional[str],
        direction: str,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        risk_reward_ratio: float,
        confidence: float,
        quality: str,
        expiry_bars: int,
        evidence: List[Evidence],
        analysis: Dict[str, Any],
        knowledge_context: Dict[str, Any],
        tracker_context: Dict[str, Any],
        warnings: Optional[List[str]] = None,
    ) -> "GeneratedSignal":
        return cls(
            id=uuid4().hex[:16],
            generated_at=utc_now(),
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            status="pending",
            entry_price=round(float(entry_price), 10),
            stop_loss=round(float(stop_loss), 10),
            take_profit=round(float(take_profit), 10),
            risk_reward_ratio=round(float(risk_reward_ratio), 4),
            confidence=round(float(confidence), 4),
            quality=quality,
            expiry_bars=int(expiry_bars),
            evidence=evidence,
            analysis=analysis,
            knowledge_context=knowledge_context,
            tracker_context=tracker_context,
            warnings=list(warnings or []),
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SignalOutcome:
    """A resolved signal outcome, created deterministically from subsequent candles."""

    signal_id: str
    status: str
    resolved_at: str
    exit_price: Optional[float]
    return_r: Optional[float]
    bars_observed: int
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
