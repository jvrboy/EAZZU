"""TradingView MCP adapter — charts, indicators, screeners, alerts.

TradingView does not expose a public REST API for data. This adapter provides:
  1. A lightweight TradingView webhook receiver (for alert callbacks)
  2. A chart-image URL builder for embedding TradingView charts
  3. A scanner/screener URL builder for TradingView's public screener pages
  4. An indicator reference library (built-in + custom Pine Script snippets)

For live data, pair this with the Deriv API client (forex/synthetic indices)
or the MT5 bridge (broker data).
"""
from __future__ import annotations

import json
from typing import Optional

INDICATORS = {
    "rsi": {"name": "Relative Strength Index", "category": "momentum", "period_default": 14, "pine": "rsi(close, 14)"},
    "macd": {"name": "Moving Average Convergence Divergence", "category": "momentum", "period_default": "12,26,9", "pine": "macd(12, 26, 9)"},
    "ema": {"name": "Exponential Moving Average", "category": "trend", "period_default": 20, "pine": "ema(close, 20)"},
    "sma": {"name": "Simple Moving Average", "category": "trend", "period_default": 20, "pine": "sma(close, 20)"},
    "bollinger": {"name": "Bollinger Bands", "category": "volatility", "period_default": "20,2", "pine": "bb(close, 20, 2)"},
    "atr": {"name": "Average True Range", "category": "volatility", "period_default": 14, "pine": "atr(14)"},
    "stochastic": {"name": "Stochastic Oscillator", "category": "momentum", "period_default": "14,3,3", "pine": "stoch(close, high, low, 14)"},
    "adx": {"name": "Average Directional Index", "category": "trend", "period_default": 14, "pine": "adx(14)"},
    "ichimoku": {"name": "Ichimoku Cloud", "category": "trend", "period_default": "9,26,52", "pine": "ichimoku(9, 26, 52)"},
    "vwap": {"name": "Volume Weighted Average Price", "category": "volume", "period_default": 0, "pine": "vwap"},
    "obv": {"name": "On Balance Volume", "category": "volume", "period_default": 0, "pine": "obv"},
    "cci": {"name": "Commodity Channel Index", "category": "momentum", "period_default": 20, "pine": "cci(close, 20)"},
    "williams": {"name": "Williams %R", "category": "momentum", "period_default": 14, "pine": "williams(14)"},
    "mfi": {"name": "Money Flow Index", "category": "volume", "period_default": 14, "pine": "mfi(close, high, low, volume, 14)"},
    "supertrend": {"name": "Supertrend", "category": "trend", "period_default": "10,3", "pine": "supertrend(10, 3)"},
    "parabolic_sar": {"name": "Parabolic SAR", "category": "trend", "period_default": "0.02,0.2", "pine": "sar(0.02, 0.02, 0.2)"},
}

PINE_STRATEGIES = {
    "ema_cross": {
        "name": "EMA Crossover Strategy",
        "description": "Buy when fast EMA crosses above slow EMA, sell on cross below",
        "code": '//@version=5\nstrategy("EMA Crossover", overlay=true)\nfastLen = input(9, "Fast EMA")\nslowLen = input(21, "Slow EMA")\nfast = ta.ema(close, fastLen)\nslow = ta.ema(close, slowLen)\nplot(fast, color=color.blue, title="Fast")\nplot(slow, color=color.red, title="Slow")\nif ta.crossover(fast, slow)\n    strategy.entry("Long", strategy.long)\nif ta.crossunder(fast, slow)\n    strategy.entry("Short", strategy.short)',
    },
    "rsi_reversal": {
        "name": "RSI Reversal Strategy",
        "description": "Buy when RSI < 30 (oversold), sell when RSI > 70 (overbought)",
        "code": '//@version=5\nstrategy("RSI Reversal", overlay=false)\nrsiLen = input(14, "RSI Length")\noversold = input(30, "Oversold")\noverbought = input(70, "Overbought")\nr = ta.rsi(close, rsiLen)\nplot(r, color=color.purple)\nhline(oversold, color=color.green)\nhline(overbought, color=color.red)\nif ta.crossover(r, oversold)\n    strategy.entry("Long", strategy.long)\nif ta.crossunder(r, overbought)\n    strategy.entry("Short", strategy.short)',
    },
    "bollinger_breakout": {
        "name": "Bollinger Bands Breakout",
        "description": "Buy when price breaks above upper band, sell on lower band",
        "code": '//@version=5\nstrategy("BB Breakout", overlay=true)\nlength = input(20, "BB Length")\nmult = input(2.0, "BB Mult")\n[mid, upper, lower] = ta.bb(close, length, mult)\nplot(upper, color=color.red)\nplot(mid, color=color.orange)\nplot(lower, color=color.green)\nif ta.crossover(close, upper)\n    strategy.entry("Long", strategy.long)\nif ta.crossunder(close, lower)\n    strategy.entry("Short", strategy.short)',
    },
    "macd_divergence": {
        "name": "MACD Divergence Detector",
        "description": "Detect bullish/bearish MACD divergences",
        "code": '//@version=5\nindicator("MACD Divergence", overlay=false)\n[macdLine, signalLine, histLine] = ta.macd(close, 12, 26, 9)\nplot(macdLine, color=color.blue)\nplot(signalLine, color=color.red)\nplot(histLine, color=color.green, style=plot.style_histogram)\n// Divergence detection logic would go here',
    },
    "supertrend_trend": {
        "name": "Supertrend Following",
        "description": "Follow the supertrend direction for entries",
        "code": '//@version=5\nstrategy("Supertrend Follow", overlay=true)\natrPeriod = input(10, "ATR Period")\nmult = input(3.0, "Multiplier")\n[st, dir] = ta.supertrend(mult, atrPeriod)\nplot(st, color=dir == -1 and dir[1] == -1 ? color.green : color.red)\nif dir == -1 and dir[1] == 1\n    strategy.entry("Long", strategy.long)\nif dir == 1 and dir[1] == -1\n    strategy.entry("Short", strategy.short)',
    },
}


def chart_url(symbol: str, interval: str = "60", theme: str = "dark", studies: Optional[list[str]] = None) -> dict:
    studies_param = ",".join(studies or ["STD;EMA", "STD;RSI"])
    return {
        "symbol": symbol,
        "interval": interval,
        "theme": theme,
        "url": f"https://s.tradingview.com/widgetembed/?symbol={symbol}&interval={interval}&theme={theme}&studies={studies_param}",
    }


def screener_url(market: str = "crypto", columns: Optional[list[str]] = None) -> dict:
    cols = ",".join(columns or ["exchange", "name", "change", "volume", "market_cap_basic"])
    return {
        "market": market,
        "url": f"https://www.tradingview.com/screener/?market={market}&columns={cols}",
    }


def list_indicators() -> dict:
    return {"indicators": INDICATORS, "count": len(INDICATORS)}


def get_indicator(name: str) -> dict:
    name = name.lower().strip()
    if name not in INDICATORS:
        return {"error": f"unknown indicator '{name}'. Available: {sorted(INDICATORS)}"}
    return INDICATORS[name]


def list_strategies() -> dict:
    return {"strategies": PINE_STRATEGIES, "count": len(PINE_STRATEGIES)}


def get_strategy(name: str) -> dict:
    name = name.lower().strip()
    if name not in PINE_STRATEGIES:
        return {"error": f"unknown strategy '{name}'. Available: {sorted(PINE_STRATEGIES)}"}
    return PINE_STRATEGIES[name]


def webhook_receiver(payload: dict, secret: Optional[str] = None) -> dict:
    """Process a TradingView webhook alert payload."""
    if not isinstance(payload, dict):
        return {"error": "payload must be a JSON object"}
    return {
        "received": True,
        "alert": payload.get("alert") or payload.get("message", ""),
        "symbol": payload.get("ticker") or payload.get("symbol", ""),
        "action": payload.get("action") or payload.get("side", ""),
        "price": payload.get("price"),
        "time": payload.get("time"),
        "raw": payload,
    }
