"""Web & answer search tools.

Instant answers for math, unit/currency conversion, definitions, and
time. Falls back to the web_tools fetcher for full-page extraction.
"""
from __future__ import annotations

import re as _re

try:
    from eazzu.tools.web_tools import fetch_page  # type: ignore
except Exception:
    fetch_page = None


_UNITS = {
    "length": {"m": 1, "km": 1000, "cm": 0.01, "mm": 0.001, "mi": 1609.34, "yd": 0.9144, "ft": 0.3048, "in": 0.0254},
    "mass": {"kg": 1, "g": 0.001, "mg": 1e-6, "lb": 0.453592, "oz": 0.0283495, "t": 1000},
    "volume": {"l": 1, "ml": 0.001, "gal": 3.78541, "qt": 0.946353, "pt": 0.473176, "cup": 0.236588, "fl_oz": 0.0295735},
    "temp": {"c": "c", "f": "f", "k": "k"},
    "time": {"s": 1, "min": 60, "h": 3600, "day": 86400, "week": 604800, "year": 31536000},
    "data": {"b": 1, "kb": 1024, "mb": 1024**2, "gb": 1024**3, "tb": 1024**4, "pb": 1024**5},
}

_CURRENCY_RATES = {
    "USD": 1.0, "EUR": 0.92, "GBP": 0.79, "JPY": 149.5, "AUD": 1.52, "CAD": 1.36,
    "CHF": 0.88, "CNY": 7.24, "INR": 83.2, "ZAR": 18.5, "NGN": 1600, "KES": 149,
}


def _instant_answer(query):
    q = query.strip()
    if _re.fullmatch(r"[\d\s+\-*/().^%]+", q):
        try:
            return {"type": "math", "query": q, "answer": eval(q.replace("^", "**"), {"__builtins__": {}}, {})}
        except Exception:
            pass
    m = _re.match(r"([\d.]+)\s*(\w+)\s+to\s+(\w+)", q, _re.I)
    if m:
        return _convert(float(m.group(1)), m.group(2).lower(), m.group(3).lower())
    m = _re.match(r"([\d.]+)\s*(\w{3})\s+to\s+(\w{3})", q, _re.I)
    if m:
        return _currency_convert(float(m.group(1)), m.group(2).upper(), m.group(3).upper())
    if q.lower().startswith("define "):
        return {"type": "definition", "word": q[7:].strip(), "answer": "Definition lookup requires the web_tools fetcher."}
    if q.lower() in ("time", "what time is it", "now"):
        import time as _t
        return {"type": "time", "answer": _t.strftime("%Y-%m-%d %H:%M:%S")}
    return {"type": "unknown", "answer": "No instant answer matched. Use web_search for full results."}


def _convert(value, src, dst):
    for category, units in _UNITS.items():
        if src in units and dst in units:
            if category == "temp":
                return {"type": "conversion", "value": value, "from": src, "to": dst, "result": _temp_convert(value, src, dst)}
            return {"type": "conversion", "value": value, "from": src, "to": dst, "result": round(value * units[src] / units[dst], 6)}
    return {"type": "conversion", "error": f"cannot convert {src} to {dst}"}


def _temp_convert(value, src, dst):
    c = value if src == "c" else (value - 32) * 5 / 9 if src == "f" else value - 273.15
    if dst == "c":
        return round(c, 2)
    if dst == "f":
        return round(c * 9 / 5 + 32, 2)
    return round(c + 273.15, 2)


def _currency_convert(value, src, dst):
    if src not in _CURRENCY_RATES or dst not in _CURRENCY_RATES:
        return {"type": "currency", "error": f"unsupported currency pair {src}->{dst}"}
    usd = value / _CURRENCY_RATES[src]
    return {"type": "currency", "value": value, "from": src, "to": dst, "result": round(usd * _CURRENCY_RATES[dst], 4), "note": "approximate static rates"}


def _web_search(query, max_results=5):
    if fetch_page:
        try:
            return fetch_page({"url": f"https://duckduckgo.com/html/?q={query.replace(' ', '+')}"})
        except Exception as e:
            return {"error": str(e)}
    return {"error": "web fetcher unavailable — install the web extra or set a fetch backend"}


TOOLS: list[dict] = [
    {
        "name": "search_instant_answer",
        "description": "Compute an instant answer for math, unit conversion (5 km to mi), currency conversion (100 usd to eur), time, or definition queries.",
        "params": {"query": "string"},
        "run": lambda a: _instant_answer(a.get("query", "")),
    },
    {
        "name": "search_unit_convert",
        "description": "Convert a value between units (length, mass, volume, temperature, time, data).",
        "params": {"value": "number", "from": "string", "to": "string"},
        "run": lambda a: _convert(float(a.get("value", 0)), a.get("from", "").lower(), a.get("to", "").lower()),
    },
    {
        "name": "search_currency_convert",
        "description": "Convert an amount between currencies using approximate static rates (USD, EUR, GBP, JPY, AUD, CAD, CHF, CNY, INR, ZAR, NGN, KES).",
        "params": {"value": "number", "from": "string", "to": "string"},
        "run": lambda a: _currency_convert(float(a.get("value", 0)), a.get("from", "").upper(), a.get("to", "").upper()),
    },
    {
        "name": "search_web",
        "description": "Perform a web search via the configured fetcher (defaults to DuckDuckGo HTML). Returns page content for parsing.",
        "params": {"query": "string", "max_results": "int"},
        "run": lambda a: _web_search(a.get("query", ""), int(a.get("max_results", 5))),
    },
    {
        "name": "search_supported_units",
        "description": "List all supported unit categories and their units.",
        "params": {},
        "run": lambda a: {"categories": {k: list(v.keys()) for k, v in _UNITS.items()}},
    },
    {
        "name": "search_supported_currencies",
        "description": "List all supported currency codes for conversion.",
        "params": {},
        "run": lambda a: {"currencies": list(_CURRENCY_RATES.keys())},
    },
]
