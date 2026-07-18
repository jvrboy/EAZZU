"""Confluence-based, analysis-only signal generation."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from .analytics import TechnicalAnalysisEngine
from .models import AnalysisResult, Evidence, GeneratedSignal


class SignalGenerator:
    """Generate an auditable directional hypothesis from several evidence domains.

    This class does not connect to brokers, submit orders, calculate position
    sizes, or claim that a signal will be profitable.
    """

    def __init__(self, analyzer: Optional[TechnicalAnalysisEngine] = None, tracker: Any = None) -> None:
        self.analyzer = analyzer or TechnicalAnalysisEngine()
        self.tracker = tracker

    @staticmethod
    def _score(value: float, low: float = 0.0, high: float = 1.0) -> float:
        return max(low, min(high, float(value)))

    def _weight(self, source: str, symbol: Optional[str], timeframe: Optional[str], direction: str) -> Tuple[float, Dict[str, Any]]:
        if self.tracker is None:
            return 1.0, {"source": source, "weight": 1.0, "learned": False}
        return self.tracker.evidence_weight(source, symbol, timeframe, direction)

    def _evidence(
        self,
        source: str,
        direction: str,
        raw_score: float,
        rationale: str,
        symbol: Optional[str],
        timeframe: Optional[str],
        details: Optional[Dict[str, Any]] = None,
    ) -> Evidence:
        weight, learning = self._weight(source, symbol, timeframe, direction)
        return Evidence(
            source=source,
            direction=direction,
            raw_score=round(self._score(raw_score), 4),
            weight=round(float(weight), 4),
            score=round(self._score(raw_score) * float(weight), 4),
            rationale=rationale,
            details={**(details or {}), "learning": learning},
        )

    def build_evidence(self, analysis: AnalysisResult) -> List[Evidence]:
        """Convert structured analysis into independently attributable evidence."""
        symbol, timeframe = analysis.symbol, analysis.timeframe
        metrics = analysis.metrics
        trend = metrics["trend"]
        momentum = metrics["momentum"]
        volatility = metrics["volatility"]
        structure = analysis.market_structure
        price_action = analysis.price_action
        liquidity = analysis.liquidity
        volume = analysis.volume
        evidence: List[Evidence] = []

        if trend["direction"] in {"bullish", "bearish"}:
            raw = 0.50 + min(0.25, trend["efficiency_ratio"] * 0.35) + min(0.15, trend["ema_separation_atr"] * 0.10)
            evidence.append(
                self._evidence(
                    "trend",
                    trend["direction"],
                    raw,
                    "Price, EMA alignment, and slope point in the same direction.",
                    symbol,
                    timeframe,
                    {"direction": trend["direction"], "efficiency_ratio": trend["efficiency_ratio"], "ema_separation_atr": trend["ema_separation_atr"]},
                )
            )

        structure_direction = structure["bias"] if structure["bias"] in {"bullish", "bearish"} else structure["break_of_structure"]
        if structure_direction in {"bullish", "bearish"}:
            raw = 0.58 if structure["break_of_structure"] == structure_direction else 0.52
            if structure["trend_alignment"] == structure_direction:
                raw += 0.12
            evidence.append(
                self._evidence(
                    "market_structure",
                    structure_direction,
                    raw,
                    "Swing structure and/or a recent break of structure supports this direction.",
                    symbol,
                    timeframe,
                    {"bias": structure["bias"], "break_of_structure": structure["break_of_structure"], "trend_alignment": structure["trend_alignment"]},
                )
            )

        momentum_direction: Optional[str] = None
        momentum_score = 0.0
        rsi = float(momentum["rsi_14"])
        histogram = float(momentum["macd_histogram"])
        roc = float(momentum["roc_10_pct"])
        stochastic = float(momentum["stochastic_k_14"])
        if rsi >= 52 and histogram > 0 and roc >= 0:
            momentum_direction = "bullish"
            momentum_score = 0.52 + min(0.16, (rsi - 50) / 100.0) + min(0.12, abs(roc) / 20.0)
            if 20 < stochastic < 88:
                momentum_score += 0.05
        elif rsi <= 48 and histogram < 0 and roc <= 0:
            momentum_direction = "bearish"
            momentum_score = 0.52 + min(0.16, (50 - rsi) / 100.0) + min(0.12, abs(roc) / 20.0)
            if 12 < stochastic < 80:
                momentum_score += 0.05
        if momentum_direction:
            evidence.append(
                self._evidence(
                    "momentum",
                    momentum_direction,
                    momentum_score,
                    "RSI, MACD histogram, and rate of change align directionally.",
                    symbol,
                    timeframe,
                    {"rsi_14": rsi, "macd_histogram": histogram, "roc_10_pct": roc, "stochastic_k_14": stochastic},
                )
            )

        patterns = set(price_action.get("patterns", []))
        if {"bullish_engulfing", "bullish_pin_bar"} & patterns:
            evidence.append(
                self._evidence(
                    "price_action",
                    "bullish",
                    0.66 if "bullish_engulfing" in patterns else 0.58,
                    "A bullish reversal or continuation candle pattern is present.",
                    symbol,
                    timeframe,
                    {"patterns": sorted(patterns), "close_location": price_action["close_location"]},
                )
            )
        if {"bearish_engulfing", "bearish_pin_bar"} & patterns:
            evidence.append(
                self._evidence(
                    "price_action",
                    "bearish",
                    0.66 if "bearish_engulfing" in patterns else 0.58,
                    "A bearish reversal or continuation candle pattern is present.",
                    symbol,
                    timeframe,
                    {"patterns": sorted(patterns), "close_location": price_action["close_location"]},
                )
            )

        if liquidity["low_sweep"]:
            evidence.append(
                self._evidence(
                    "liquidity",
                    "bullish",
                    0.68,
                    "Price swept the recent rolling low and closed back above it.",
                    symbol,
                    timeframe,
                    {"low_sweep": True, "rolling_low_20": liquidity["rolling_low_20"]},
                )
            )
        if liquidity["high_sweep"]:
            evidence.append(
                self._evidence(
                    "liquidity",
                    "bearish",
                    0.68,
                    "Price swept the recent rolling high and closed back below it.",
                    symbol,
                    timeframe,
                    {"high_sweep": True, "rolling_high_20": liquidity["rolling_high_20"]},
                )
            )

        if analysis.regime["name"] == "trend" and trend["direction"] in {"bullish", "bearish"}:
            evidence.append(
                self._evidence(
                    "regime",
                    trend["direction"],
                    0.57,
                    "The current efficiency and EMA separation classify the market as trending.",
                    symbol,
                    timeframe,
                    dict(analysis.regime),
                )
            )

        if volume.get("available") and volume.get("relative_activity") == "high":
            candle_direction = price_action["candle_direction"]
            obv_direction = volume.get("obv_proxy_direction")
            volume_direction = "bullish" if candle_direction == "bullish" and obv_direction == "positive" else "bearish" if candle_direction == "bearish" and obv_direction == "negative" else None
            if volume_direction:
                evidence.append(
                    self._evidence(
                        "volume",
                        volume_direction,
                        0.58,
                        "Above-average observed volume confirms the latest directional candle.",
                        symbol,
                        timeframe,
                        dict(volume),
                    )
                )
        return evidence

    @staticmethod
    def _decision(evidence: List[Evidence]) -> Tuple[Optional[str], float, int, Dict[str, float]]:
        totals = {"bullish": 0.0, "bearish": 0.0}
        counts = {"bullish": 0, "bearish": 0}
        for item in evidence:
            if item.direction in totals:
                totals[item.direction] += item.score
                counts[item.direction] += 1
        direction = "bullish" if totals["bullish"] > totals["bearish"] else "bearish" if totals["bearish"] > totals["bullish"] else None
        if direction is None:
            return None, 0.0, 0, totals
        opposite = "bearish" if direction == "bullish" else "bullish"
        dominance = (totals[direction] - totals[opposite]) / max(totals[direction] + totals[opposite], 1e-9)
        average_support = totals[direction] / max(counts[direction], 1)
        confidence = 0.30 + 0.30 * max(dominance, 0.0) + 0.32 * max(average_support - 0.45, 0.0) + min(0.10, counts[direction] * 0.025)
        return direction, min(confidence, 0.95), counts[direction], totals

    @staticmethod
    def _protective_levels(analysis: AnalysisResult, direction: str, risk_multiple: float, reward_multiple: float) -> Tuple[float, float, float]:
        entry = float(analysis.metrics["price"])
        atr = float(analysis.metrics["volatility"]["atr_14"])
        if atr <= 0:
            raise ValueError("ATR is zero, so protective levels cannot be calculated")
        last_high = analysis.market_structure.get("last_swing_high") or {}
        last_low = analysis.market_structure.get("last_swing_low") or {}
        if direction == "bullish":
            atr_stop = entry - atr * risk_multiple
            swing_stop = float(last_low.get("price", atr_stop)) - atr * 0.15
            stop_loss = min(atr_stop, swing_stop)
            risk = entry - stop_loss
            take_profit = entry + risk * reward_multiple
        else:
            atr_stop = entry + atr * risk_multiple
            swing_stop = float(last_high.get("price", atr_stop)) + atr * 0.15
            stop_loss = max(atr_stop, swing_stop)
            risk = stop_loss - entry
            take_profit = entry - risk * reward_multiple
        return entry, stop_loss, take_profit

    def generate_from_analysis(
        self,
        analysis: AnalysisResult,
        min_confidence: float = 0.56,
        risk_multiple: float = 1.5,
        reward_multiple: float = 2.0,
        expiry_bars: int = 12,
    ) -> Dict[str, Any]:
        """Generate a signal from analysis or explain why the engine abstained."""
        if not 0.0 < min_confidence < 1.0:
            raise ValueError("min_confidence must be between 0 and 1")
        if risk_multiple <= 0 or reward_multiple <= 0 or expiry_bars <= 0:
            raise ValueError("risk_multiple, reward_multiple, and expiry_bars must be positive")
        evidence = self.build_evidence(analysis)
        direction, base_confidence, support_count, totals = self._decision(evidence)
        tracker_context: Dict[str, Any] = {"learning_enabled": self.tracker is not None}
        if self.tracker is not None:
            tracker_context.update(self.tracker.calibration_context(analysis.symbol, analysis.timeframe, direction))

        reasons: List[str] = []
        if direction is None:
            reasons.append("Directional evidence was tied or unavailable.")
        elif support_count < 2:
            reasons.append("Fewer than two independent evidence domains support the leading direction.")
        if direction is not None and base_confidence < min_confidence:
            reasons.append("Confluence confidence is below the requested threshold.")
        if analysis.regime["name"] == "chop":
            reasons.append("The efficiency reading classifies the market as choppy; the engine abstains.")
        if analysis.metrics["volatility"]["atr_14"] <= 0:
            reasons.append("ATR is not positive, so protective levels cannot be calculated.")

        calibrated_confidence = base_confidence
        if direction is not None and self.tracker is not None:
            calibrated_confidence, calibration = self.tracker.calibrate_confidence(
                base_confidence,
                analysis.symbol,
                analysis.timeframe,
                direction,
            )
            tracker_context["calibration"] = calibration
        if direction is not None and calibrated_confidence < min_confidence:
            reasons.append("Outcome-based calibration reduced confidence below the requested threshold.")

        if reasons:
            return {
                "analysis": analysis.to_dict(),
                "signal": None,
                "decision": {
                    "status": "no_signal",
                    "direction": direction,
                    "base_confidence": round(base_confidence, 4),
                    "calibrated_confidence": round(calibrated_confidence, 4),
                    "support_count": support_count,
                    "evidence_totals": {key: round(value, 4) for key, value in totals.items()},
                    "reasons": reasons,
                    "evidence": [item.to_dict() for item in evidence],
                },
            }

        entry, stop_loss, take_profit = self._protective_levels(analysis, direction, risk_multiple, reward_multiple)
        quality = "high" if calibrated_confidence >= 0.72 and support_count >= 4 else "moderate" if calibrated_confidence >= 0.62 else "watchlist"
        signal = GeneratedSignal.create(
            symbol=analysis.symbol,
            timeframe=analysis.timeframe,
            direction=direction,
            entry_price=entry,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward_ratio=reward_multiple,
            confidence=calibrated_confidence,
            quality=quality,
            expiry_bars=expiry_bars,
            evidence=evidence,
            analysis=analysis.to_dict(),
            knowledge_context=analysis.knowledge_context,
            tracker_context=tracker_context,
            warnings=[
                "Analysis-only output: no broker order, position size, or investment recommendation is produced.",
                *analysis.warnings,
            ],
        )
        return {
            "analysis": analysis.to_dict(),
            "signal": signal.to_dict(),
            "decision": {
                "status": "signal_generated",
                "direction": direction,
                "base_confidence": round(base_confidence, 4),
                "calibrated_confidence": round(calibrated_confidence, 4),
                "support_count": support_count,
                "evidence_totals": {key: round(value, 4) for key, value in totals.items()},
            },
        }

    def generate(
        self,
        candles: Iterable[Any],
        symbol: Optional[str] = None,
        timeframe: Optional[str] = None,
        min_confidence: float = 0.56,
        risk_multiple: float = 1.5,
        reward_multiple: float = 2.0,
        expiry_bars: int = 12,
    ) -> Dict[str, Any]:
        """Analyze supplied candles and return a signal or a documented abstention."""
        analysis = self.analyzer.analyze(candles, symbol=symbol, timeframe=timeframe)
        return self.generate_from_analysis(
            analysis,
            min_confidence=min_confidence,
            risk_multiple=risk_multiple,
            reward_multiple=reward_multiple,
            expiry_bars=expiry_bars,
        )
