"""JSON input helpers for the analysis-only trading workflows."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from .models import Candle


CANDLE_LIST_KEYS = ("candles", "data", "history", "ohlcv")


def load_json(path: str) -> Any:
    """Load a UTF-8 JSON document from an explicit user-provided path."""
    candidate = Path(path).expanduser()
    if not candidate.exists() or not candidate.is_file():
        raise FileNotFoundError(f"JSON file not found: {candidate}")
    try:
        return json.loads(candidate.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON in {candidate}") from exc


def load_candles(path: str) -> Tuple[List[Candle], Dict[str, Any]]:
    """Load and normalize a JSON list of OHLCV candles.

    Supported forms are either a top-level list, or an object containing one of
    ``candles``, ``data``, ``history``, or ``ohlcv``. Top-level ``symbol`` and
    ``timeframe`` fields are returned as metadata when present.
    """
    payload = load_json(path)
    metadata: Dict[str, Any] = {"source": str(Path(path).expanduser())}
    raw_candles: Any = payload
    if isinstance(payload, dict):
        metadata.update({key: payload[key] for key in ("symbol", "timeframe") if key in payload})
        raw_candles = next((payload[key] for key in CANDLE_LIST_KEYS if isinstance(payload.get(key), list)), None)
    if not isinstance(raw_candles, list):
        raise ValueError("candle JSON must be a list or contain a candle list under candles/data/history/ohlcv")
    candles = [Candle.from_mapping(item) for item in raw_candles]
    if not candles:
        raise ValueError("candle JSON contains no candles")
    return candles, metadata


def load_signal(path: str) -> Dict[str, Any]:
    """Load a generated signal object, optionally wrapped under a ``signal`` key."""
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError("signal JSON must be an object")
    signal = payload.get("signal", payload)
    if not isinstance(signal, dict):
        raise ValueError("signal JSON must contain an object under 'signal'")
    return signal
