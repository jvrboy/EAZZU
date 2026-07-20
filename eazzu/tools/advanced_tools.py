"""Advanced trading tools — backtest, decision, monitor, portfolio, stream.

Converted from infinite-loop-sound's src/tools/ TypeScript engines into
portable Python. Each tool is analysis-only and operates on caller-supplied
data, returning JSON-serialisable dicts for the EAZZU agent registry.
"""
from __future__ import annotations

import math
import time
from typing import Any, Dict, List, Optional


def _error(code: str, exc: Exception) -> Dict[str, Any]:
    return {"error": code, "message": str(exc)}


# ─── Backtest Engine ─────────────────────────────────────────────────────

def backtest(
    bars: List[Dict[str, Any]],
    initial_balance: float = 10000.0,
    slippage: float = 0.0,
    commission: float = 0.0,
    strategy: str = "ema_cross",
) -> Dict[str, Any]:
    """Run a simple backtest over historical OHLCV bars using built-in strategies."""
    try:
        balance = initial_balance
        trades: List[Dict[str, Any]] = []
        position: Optional[Dict[str, Any]] = None
        equity_curve: List[float] = [balance]

        for i, bar in enumerate(bars):
            if i < 26:
                continue
            closes = [b["close"] for b in bars[: i + 1]]
            ema_fast = _ema(closes, 12)[-1]
            ema_slow = _ema(closes, 26)[-1]
            price = bar["close"]

            if strategy == "ema_cross":
                if position is None and ema_fast > ema_slow:
                    position = {"entry": price, "time": bar.get("timestamp", i), "size": balance * 0.02 / (price or 1)}
                elif position is not None and ema_fast < ema_slow:
                    exit_price = price
                    profit = (exit_price - position["entry"]) * position["size"] - slippage - commission
                    balance += profit
                    trades.append({
                        "entryTime": position["time"],
                        "exitTime": bar.get("timestamp", i),
                        "entryPrice": position["entry"],
                        "exitPrice": exit_price,
                        "size": position["size"],
                        "type": "long",
                        "profit": profit,
                        "profitPercent": profit / (position["entry"] * position["size"]) * 100 if position["entry"] * position["size"] > 0 else 0,
                        "holdTime": bar.get("timestamp", i) - position["time"],
                    })
                    position = None
            equity_curve.append(balance)

        wins = sum(1 for t in trades if t["profit"] > 0)
        losses = sum(1 for t in trades if t["profit"] < 0)
        total = len(trades)
        gross_profit = sum(t["profit"] for t in trades if t["profit"] > 0)
        gross_loss = abs(sum(t["profit"] for t in trades if t["profit"] < 0))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0
        peak = balance
        max_dd = 0.0
        for v in equity_curve:
            if v > peak:
                peak = v
            dd = (peak - v) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        return {
            "strategy": strategy,
            "initialBalance": initial_balance,
            "finalBalance": balance,
            "totalTrades": total,
            "winningTrades": wins,
            "losingTrades": losses,
            "winRate": wins / total if total > 0 else 0,
            "totalProfit": balance - initial_balance,
            "grossProfit": gross_profit,
            "grossLoss": gross_loss,
            "profitFactor": profit_factor,
            "maxDrawdown": max_dd,
            "trades": trades,
            "equityCurve": equity_curve,
        }
    except Exception as exc:
        return _error("backtest_failed", exc)


def _ema(values: List[float], period: int) -> List[float]:
    if not values:
        return []
    k = 2.0 / (period + 1)
    emas: List[float] = [values[0]]
    for v in values[1:]:
        emas.append(v * k + emas[-1] * (1 - k))
    return emas


# ─── Decision Engine ─────────────────────────────────────────────────────

def make_decision(
    symbol: str,
    timeframe: str,
    current_price: float,
    technical_signals: List[Dict[str, Any]],
    risk_metrics: Optional[List[Dict[str, Any]]] = None,
    sentiment: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Combine technical, risk, and sentiment signals into a trading decision."""
    try:
        tech_score = sum(
            (1 if s.get("signal") == "buy" else -1 if s.get("signal") == "sell" else 0) * s.get("strength", 0.5)
            for s in technical_signals
        )
        risk_score = 0.0
        for r in (risk_metrics or []):
            val = r.get("value", 0)
            if r.get("risk") == "high":
                risk_score -= val
            elif r.get("risk") == "low":
                risk_score += val
        sent = (sentiment or {}).get("overall", 0)
        combined = tech_score + risk_score * 0.3 + sent * 0.2
        action = "buy" if combined > 0.5 else "sell" if combined < -0.5 else "hold"
        confidence = min(1.0, abs(combined) / 2.0)

        return {
            "symbol": symbol,
            "action": action,
            "confidence": confidence,
            "reasoning": f"Combined score {combined:+.2f} from {len(technical_signals)} signals",
            "position": {"size": confidence, "stopLoss": current_price * 0.98, "takeProfit": current_price * 1.04},
            "riskRewardRatio": 2.0,
            "conditions": [s.get("indicator", "") for s in technical_signals[:5]],
        }
    except Exception as exc:
        return _error("decision_failed", exc)


# ─── Market Monitor ───────────────────────────────────────────────────────

class MarketMonitor:
    """Real-time market monitoring and alerting (in-memory)."""

    def __init__(self) -> None:
        self._snapshots: Dict[str, List[Dict[str, Any]]] = {}
        self._alerts: Dict[str, List[Dict[str, Any]]] = {}
        self._watchers: Dict[str, Any] = {}
        self._vol_baseline: Dict[str, float] = {}

    def record_snapshot(self, snapshot: Dict[str, Any]) -> None:
        sym = snapshot["symbol"]
        self._snapshots.setdefault(sym, []).append(snapshot)
        if len(self._snapshots[sym]) > 1000:
            self._snapshots[sym].pop(0)

    def check_price_alert(self, symbol: str, price: float, thresholds: Dict[str, float]) -> List[Dict[str, Any]]:
        alerts: List[Dict[str, Any]] = []
        if "high" in thresholds and price >= thresholds["high"]:
            alerts.append({"symbol": symbol, "type": "price", "severity": "warning", "message": f"{symbol} above {thresholds['high']}", "value": price, "threshold": thresholds["high"], "timestamp": time.time() * 1000})
        if "low" in thresholds and price <= thresholds["low"]:
            alerts.append({"symbol": symbol, "type": "price", "severity": "warning", "message": f"{symbol} below {thresholds['low']}", "value": price, "threshold": thresholds["low"], "timestamp": time.time() * 1000})
        self._alerts.setdefault(symbol, []).extend(alerts)
        return alerts

    def get_snapshots(self, symbol: str, limit: int = 100) -> List[Dict[str, Any]]:
        return self._snapshots.get(symbol, [])[-limit:]

    def get_alerts(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        if symbol:
            return self._alerts.get(symbol, [])
        return [a for alerts in self._alerts.values() for a in alerts]


_monitor: Optional[MarketMonitor] = None


def _get_monitor() -> MarketMonitor:
    global _monitor
    if _monitor is None:
        _monitor = MarketMonitor()
    return _monitor


def monitor_snapshot(snapshot: Dict[str, Any]) -> Dict[str, Any]:
    try:
        _get_monitor().record_snapshot(snapshot)
        return {"recorded": True, "symbol": snapshot.get("symbol")}
    except Exception as exc:
        return _error("monitor_failed", exc)


def check_alerts(symbol: str, price: float, high: Optional[float] = None, low: Optional[float] = None) -> Dict[str, Any]:
    try:
        thresholds: Dict[str, float] = {}
        if high is not None:
            thresholds["high"] = high
        if low is not None:
            thresholds["low"] = low
        alerts = _get_monitor().check_price_alert(symbol, price, thresholds)
        return {"symbol": symbol, "alerts": alerts}
    except Exception as exc:
        return _error("alert_check_failed", exc)


# ─── Portfolio Manager ────────────────────────────────────────────────────

class PortfolioManager:
    """Multi-asset portfolio management and rebalancing."""

    def __init__(self, rebalance_threshold: float = 5.0) -> None:
        self._assets: Dict[str, Dict[str, Any]] = {}
        self._history: List[Dict[str, Any]] = []
        self._threshold = rebalance_threshold

    def add_asset(self, symbol: str, quantity: float, entry_price: float, current_price: float) -> None:
        self._assets[symbol] = {"symbol": symbol, "quantity": quantity, "entryPrice": entry_price, "currentPrice": current_price}
        self._update_weights()

    def update_price(self, symbol: str, new_price: float) -> None:
        if symbol in self._assets:
            self._assets[symbol]["currentPrice"] = new_price
            self._update_weights()

    def remove_asset(self, symbol: str) -> None:
        self._assets.pop(symbol, None)
        self._update_weights()

    def _update_weights(self) -> None:
        total_value = sum(a["quantity"] * a["currentPrice"] for a in self._assets.values())
        for a in self._assets.values():
            a["weight"] = (a["quantity"] * a["currentPrice"]) / total_value if total_value > 0 else 0

    def metrics(self) -> Dict[str, Any]:
        total_value = sum(a["quantity"] * a["currentPrice"] for a in self._assets.values())
        total_cost = sum(a["quantity"] * a["entryPrice"] for a in self._assets.values())
        gain = total_value - total_cost
        weights = [a["weight"] for a in self._assets.values()]
        div_score = 1 - max(weights) if weights else 0
        return {
            "totalValue": total_value,
            "totalCost": total_cost,
            "totalGain": gain,
            "totalGainPercent": gain / total_cost * 100 if total_cost > 0 else 0,
            "diversificationScore": round(div_score * 100),
            "assetCount": len(self._assets),
            "assets": list(self._assets.values()),
        }

    def rebalance(self, target_weights: Dict[str, float]) -> Dict[str, Any]:
        total_value = sum(a["quantity"] * a["currentPrice"] for a in self._assets.values())
        allocations: List[Dict[str, Any]] = []
        for sym, target in target_weights.items():
            current = self._assets.get(sym, {}).get("weight", 0)
            diff = target - current
            action = "buy" if diff > self._threshold / 100 else "sell" if diff < -self._threshold / 100 else "hold"
            shares = (diff * total_value) / self._assets.get(sym, {}).get("currentPrice", 1) if action != "hold" else 0
            allocations.append({"asset": sym, "currentAllocation": current, "targetAllocation": target, "difference": diff, "action": action, "shares": shares})
        return {"rebalanceRequired": any(a["action"] != "hold" for a in allocations), "allocations": allocations}


_portfolio: Optional[PortfolioManager] = None


def _get_portfolio() -> PortfolioManager:
    global _portfolio
    if _portfolio is None:
        _portfolio = PortfolioManager()
    return _portfolio


def portfolio_add(symbol: str, quantity: float, entry_price: float, current_price: float) -> Dict[str, Any]:
    try:
        _get_portfolio().add_asset(symbol, quantity, entry_price, current_price)
        return {"added": symbol, "metrics": _get_portfolio().metrics()}
    except Exception as exc:
        return _error("portfolio_add_failed", exc)


def portfolio_update_price(symbol: str, new_price: float) -> Dict[str, Any]:
    try:
        _get_portfolio().update_price(symbol, new_price)
        return {"updated": symbol, "metrics": _get_portfolio().metrics()}
    except Exception as exc:
        return _error("portfolio_update_failed", exc)


def portfolio_metrics() -> Dict[str, Any]:
    try:
        return _get_portfolio().metrics()
    except Exception as exc:
        return _error("portfolio_metrics_failed", exc)


def portfolio_rebalance(target_weights: Dict[str, float]) -> Dict[str, Any]:
    try:
        return _get_portfolio().rebalance(target_weights)
    except Exception as exc:
        return _error("rebalance_failed", exc)


# ─── Sentiment Analyzer ──────────────────────────────────────────────────

class SentimentAnalyzer:
    """Market sentiment analysis from multiple sources (in-memory)."""

    def __init__(self) -> None:
        self._news: List[Dict[str, Any]] = []
        self._social: Dict[str, List[Dict[str, Any]]] = {}

    def add_news(self, item: Dict[str, Any]) -> None:
        self._news.append(item)
        if len(self._news) > 1000:
            self._news.pop(0)

    def add_social(self, symbol: str, metrics: Dict[str, Any]) -> None:
        self._social.setdefault(symbol, []).append(metrics)
        if len(self._social[symbol]) > 500:
            self._social[symbol].pop(0)

    def analyze(self, symbol: str, time_window_ms: float = 86_400_000) -> Dict[str, Any]:
        now = time.time() * 1000
        cutoff = now - time_window_ms
        news = [n for n in self._news if n.get("timestamp", 0) >= cutoff and (n.get("symbol") == symbol or not n.get("symbol"))]
        social = self._social.get(symbol, [])
        news_score = sum(n.get("score", 0) for n in news) / max(len(news), 1)
        social_score = sum(s.get("sentiment", 0) for s in social) / max(len(social), 1)
        overall = news_score * 0.6 + social_score * 0.4
        signal = "strong_buy" if overall > 0.5 else "buy" if overall > 0.15 else "sell" if overall < -0.15 else "strong_sell" if overall < -0.5 else "neutral"
        return {
            "symbol": symbol,
            "overallSentiment": overall,
            "bullishPercent": max(0, overall) * 100,
            "bearishPercent": max(0, -overall) * 100,
            "neutralPercent": (1 - abs(overall)) * 100,
            "signal": signal,
            "confidence": min(1.0, abs(overall) + 0.3),
        }


_sentiment: Optional[SentimentAnalyzer] = None


def _get_sentiment() -> SentimentAnalyzer:
    global _sentiment
    if _sentiment is None:
        _sentiment = SentimentAnalyzer()
    return _sentiment


def add_news_sentiment(item: Dict[str, Any]) -> Dict[str, Any]:
    try:
        _get_sentiment().add_news(item)
        return {"added": True}
    except Exception as exc:
        return _error("news_sentiment_failed", exc)


def analyze_sentiment(symbol: str) -> Dict[str, Any]:
    try:
        return _get_sentiment().analyze(symbol)
    except Exception as exc:
        return _error("sentiment_analysis_failed", exc)


# ─── Data Stream Manager ─────────────────────────────────────────────────

class DataStreamManager:
    """Real-time data streaming and aggregation (in-memory)."""

    def __init__(self, max_buffer: int = 1000) -> None:
        self._streams: Dict[str, Dict[str, Any]] = {}
        self._buffers: Dict[str, List[Dict[str, Any]]] = {}
        self._health: Dict[str, Dict[str, Any]] = {}
        self._sequences: Dict[str, int] = {}
        self._max_buffer = max_buffer

    def subscribe(self, source: str, symbol: str, stream_type: str) -> str:
        stream_id = f"{source}-{symbol}-{stream_type}-{int(time.time() * 1000)}"
        self._streams[stream_id] = {"id": stream_id, "source": source, "symbol": symbol, "type": stream_type, "active": True, "subscriptionTime": time.time() * 1000}
        self._buffers[stream_id] = []
        self._sequences[stream_id] = 0
        self._health[stream_id] = {"streamId": stream_id, "active": True, "messagesReceived": 0, "errors": 0, "latency": 0, "status": "healthy"}
        return stream_id

    def unsubscribe(self, stream_id: str) -> bool:
        if stream_id in self._streams:
            self._streams[stream_id]["active"] = False
            return True
        return False

    def push_data(self, stream_id: str, data: Dict[str, Any]) -> None:
        if stream_id not in self._streams:
            return
        seq = self._sequences[stream_id] + 1
        self._sequences[stream_id] = seq
        self._buffers[stream_id].append({"streamId": stream_id, "timestamp": time.time() * 1000, "data": data, "sequence": seq})
        if len(self._buffers[stream_id]) > self._max_buffer:
            self._buffers[stream_id].pop(0)
        self._health[stream_id]["messagesReceived"] += 1

    def get_buffered_data(self, stream_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        return self._buffers.get(stream_id, [])[-limit:]

    def get_health(self, stream_id: str) -> Optional[Dict[str, Any]]:
        return self._health.get(stream_id)

    def get_active_streams(self) -> List[Dict[str, Any]]:
        return [s for s in self._streams.values() if s["active"]]

    def record_error(self, stream_id: str) -> None:
        if stream_id in self._health:
            self._health[stream_id]["errors"] += 1
            if self._health[stream_id]["errors"] > 10:
                self._health[stream_id]["status"] = "failed"
                self._health[stream_id]["active"] = False
            elif self._health[stream_id]["errors"] > 5:
                self._health[stream_id]["status"] = "degraded"


_stream_mgr: Optional[DataStreamManager] = None


def _get_stream_mgr() -> DataStreamManager:
    global _stream_mgr
    if _stream_mgr is None:
        _stream_mgr = DataStreamManager()
    return _stream_mgr


def stream_subscribe(source: str, symbol: str, stream_type: str = "price") -> Dict[str, Any]:
    try:
        stream_id = _get_stream_mgr().subscribe(source, symbol, stream_type)
        return {"streamId": stream_id, "active": True}
    except Exception as exc:
        return _error("stream_subscribe_failed", exc)


def stream_push(stream_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    try:
        _get_stream_mgr().push_data(stream_id, data)
        return {"pushed": True, "streamId": stream_id}
    except Exception as exc:
        return _error("stream_push_failed", exc)


def stream_health(stream_id: str) -> Dict[str, Any]:
    try:
        health = _get_stream_mgr().get_health(stream_id)
        return health or {"error": "stream_not_found"}
    except Exception as exc:
        return _error("stream_health_failed", exc)


def stream_list_active() -> Dict[str, Any]:
    try:
        return {"streams": _get_stream_mgr().get_active_streams()}
    except Exception as exc:
        return _error("stream_list_failed", exc)


# ─── Tool Registry ────────────────────────────────────────────────────────

TOOLS = [
    {
        "name": "backtest",
        "description": "Run a backtest over historical OHLCV bars using built-in strategies (ema_cross).",
        "params": {"bars": "array[object]", "initial_balance": "float", "strategy": "string"},
        "run": backtest,
    },
    {
        "name": "make_decision",
        "description": "Combine technical, risk, and sentiment signals into a trading decision.",
        "params": {"symbol": "string", "current_price": "float", "technical_signals": "array[object]"},
        "run": make_decision,
    },
    {
        "name": "monitor_snapshot",
        "description": "Record a market snapshot for real-time monitoring.",
        "params": {"snapshot": "object"},
        "run": monitor_snapshot,
    },
    {
        "name": "check_alerts",
        "description": "Check price alerts for a symbol against high/low thresholds.",
        "params": {"symbol": "string", "price": "float", "high": "float(optional)", "low": "float(optional)"},
        "run": check_alerts,
    },
    {
        "name": "portfolio_add",
        "description": "Add or update an asset in the portfolio.",
        "params": {"symbol": "string", "quantity": "float", "entry_price": "float", "current_price": "float"},
        "run": portfolio_add,
    },
    {
        "name": "portfolio_update_price",
        "description": "Update the current price of a portfolio asset.",
        "params": {"symbol": "string", "new_price": "float"},
        "run": portfolio_update_price,
    },
    {
        "name": "portfolio_metrics",
        "description": "Get portfolio metrics including total value, gain, and diversification score.",
        "params": {},
        "run": portfolio_metrics,
    },
    {
        "name": "portfolio_rebalance",
        "description": "Rebalance the portfolio to target weights.",
        "params": {"target_weights": "object"},
        "run": portfolio_rebalance,
    },
    {
        "name": "add_news_sentiment",
        "description": "Add a news item with sentiment score for analysis.",
        "params": {"item": "object"},
        "run": add_news_sentiment,
    },
    {
        "name": "analyze_sentiment",
        "description": "Analyze market sentiment for a symbol from news and social sources.",
        "params": {"symbol": "string"},
        "run": analyze_sentiment,
    },
    {
        "name": "stream_subscribe",
        "description": "Subscribe to a real-time data stream.",
        "params": {"source": "string", "symbol": "string", "stream_type": "string"},
        "run": stream_subscribe,
    },
    {
        "name": "stream_push",
        "description": "Push data to a subscribed stream.",
        "params": {"stream_id": "string", "data": "object"},
        "run": stream_push,
    },
    {
        "name": "stream_health",
        "description": "Get health status of a data stream.",
        "params": {"stream_id": "string"},
        "run": stream_health,
    },
    {
        "name": "stream_list_active",
        "description": "List all active data streams.",
        "params": {},
        "run": stream_list_active,
    },
]
