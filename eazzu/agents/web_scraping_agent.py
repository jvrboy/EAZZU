"""Web Scraping Agent — fetches financial news from public sources.

Converted from infinite-loop-sound's web-scraping-agent.ts. Uses urllib from
the standard library to fetch economic calendar data without external
dependencies. Results are cached for 5 minutes.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

from eazzu.agents.types import AgentConfig, AgentResult

WEB_SCRAPING_AGENT_CONFIG = AgentConfig(
    id="web-scraping-agent",
    name="Web Scraping Agent",
    description="Fetches real financial news from public economic calendar feeds.",
    enabled=True,
    priority="medium",
    interval_sec=300,
    instruments=["all"],
    timeframes=["all"],
)

_cache: Optional[Dict[str, Any]] = None
_cache_time: float = 0.0
_CACHE_TTL = 5 * 60 * 1000


def scrape_financial_news(days: int = 3, limit: int = 50) -> Dict[str, Any]:
    """Fetch financial news items. Returns cached result if fresh enough."""
    global _cache, _cache_time

    if _cache and (time.time() * 1000 - _cache_time) < _CACHE_TTL:
        return _cache

    items: List[Dict[str, Any]] = []
    try:
        url = "https://nfs.faireconomy.media/latest.json"
        req = Request(url, headers={"User-Agent": "EAZZU/1.0"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            for entry in data[:limit]:
                items.append({
                    "title": entry.get("title", ""),
                    "impact": entry.get("impact", "low"),
                    "currency": entry.get("country", ""),
                    "eventTime": entry.get("date", ""),
                    "forecast": entry.get("forecast"),
                    "previous": entry.get("previous"),
                    "source": "faireconomy.media",
                })
    except (URLError, json.JSONDecodeError, OSError):
        pass

    result = {
        "items": items,
        "count": len(items),
        "fetchedAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _cache = result
    _cache_time = time.time() * 1000
    return result


def run_web_scraping_agent() -> AgentResult:
    start = time.time()
    try:
        result = scrape_financial_news()
        high_impact = [i for i in result["items"] if i.get("impact") == "high"]
        insights: List[str] = [
            f"Scraped {result['count']} news items ({len(high_impact)} high impact)",
        ]
        if high_impact:
            currencies = list(set(i["currency"] for i in high_impact if i.get("currency")))
            insights.append(f"High impact currencies: {', '.join(currencies)}")

        return AgentResult(
            agent_id=WEB_SCRAPING_AGENT_CONFIG.id,
            status="completed",
            timestamp=time.time() * 1000,
            output={"news": result["items"], "count": result["count"]},
            insights=insights,
            duration=(time.time() - start) * 1000,
        )
    except Exception as exc:
        return AgentResult(
            agent_id=WEB_SCRAPING_AGENT_CONFIG.id,
            status="error",
            timestamp=time.time() * 1000,
            errors=[str(exc)],
            duration=(time.time() - start) * 1000,
        )
