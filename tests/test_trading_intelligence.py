"""Tests for EAZZU's analysis-only trading-intelligence workflows."""
from __future__ import annotations

from typing import Any, Dict, List


def rising_candles(count: int = 80, start: float = 100.0) -> List[Dict[str, Any]]:
    """Create deterministic OHLCV fixtures for unit testing only."""
    candles: List[Dict[str, Any]] = []
    price = start
    for index in range(count):
        open_price = price
        close_price = open_price + 1.0 + (0.05 if index % 3 else 0.15)
        candles.append(
            {
                "epoch": 1_700_000_000 + index * 300,
                "open": open_price,
                "high": close_price + 0.35,
                "low": open_price - 0.25,
                "close": close_price,
                "volume": 1000 + index * 4,
            }
        )
        price = close_price
    return candles


def test_packaged_knowledge_is_complete_and_readable():
    from eazzu.trading.intelligence import KnowledgeBase

    knowledge = KnowledgeBase()
    validation = knowledge.validate()
    assert validation["is_valid"] is True
    assert validation["total"] == 12
    profile = knowledge.instrument_profile("R_75")
    assert profile is not None
    assert profile["deriv_symbol"] == "R_75"


def test_analysis_covers_multiple_non_indicator_domains():
    from eazzu.trading.intelligence import TechnicalAnalysisEngine

    report = TechnicalAnalysisEngine().analyze(rising_candles(), symbol="R_75", timeframe="5m")
    assert report.metrics["trend"]["direction"] == "bullish"
    assert report.market_structure["bias"] in {"bullish", "range"}
    assert "patterns" in report.price_action
    assert "rolling_high_20" in report.liquidity
    assert report.volume["available"] is True
    assert report.regime["name"] in {"trend", "high_volatility", "range"}
    assert report.knowledge_context["profile_found"] is True


def test_signal_generation_records_and_learns_from_clear_outcome(tmp_path):
    from eazzu.trading.intelligence import AdaptiveSignalTracker, SignalGenerator

    ledger = tmp_path / "signal-ledger.json"
    tracker = AdaptiveSignalTracker(ledger)
    tracker.MIN_SEGMENT_SAMPLES = 1
    result = SignalGenerator(tracker=tracker).generate(
        rising_candles(),
        symbol="R_75",
        timeframe="5m",
        min_confidence=0.40,
    )
    signal = result["signal"]
    assert signal is not None
    assert signal["direction"] == "bullish"
    assert tracker.record_signal(signal)["recorded"] is True

    target = float(signal["take_profit"])
    entry = float(signal["entry_price"])
    resolved = tracker.resolve_signal(
        signal["id"],
        [
            {
                "epoch": 1_700_100_000,
                "open": entry,
                "high": target + 0.5,
                "low": entry - 0.01,
                "close": target,
                "volume": 1500,
            }
        ],
    )
    assert resolved["outcome"]["status"] == "win"
    assert resolved["learning_applied"] is True
    summary = tracker.summary()
    assert summary["outcomes"]["resolved"] == 1
    assert summary["outcomes"]["wins"] == 1

    source = signal["evidence"][0]["source"]
    weight, learning = tracker.evidence_weight(source, "R_75", "5m", "bullish")
    assert learning["learned"] is True
    assert weight >= 1.0


def test_agent_registry_exposes_intelligence_tools():
    from eazzu.tools import REGISTRY

    names = {tool["name"] for tool in REGISTRY}
    assert {"list_trading_knowledge", "analyze_market", "generate_signal", "resolve_signal", "signal_tracker_summary"} <= names


def test_cli_knowledge_and_analysis_workflows(tmp_path):
    import io
    import json
    from contextlib import redirect_stdout

    from eazzu.cli import main

    candles_path = tmp_path / "candles.json"
    candles_path.write_text(
        json.dumps({"symbol": "R_75", "timeframe": "5m", "candles": rising_candles()}),
        encoding="utf-8",
    )

    knowledge_output = io.StringIO()
    with redirect_stdout(knowledge_output):
        assert main(["trade", "knowledge"]) == 0
    assert "_MASTER_GUIDE.json" in knowledge_output.getvalue()

    analysis_output = io.StringIO()
    with redirect_stdout(analysis_output):
        assert main(["trade", "analyze", "--candles", str(candles_path)]) == 0
    assert '"metrics"' in analysis_output.getvalue()
    assert '"knowledge_context"' in analysis_output.getvalue()
