"""Research helpers — quick web lookups the agent can chain."""
from __future__ import annotations

import json
from typing import Any
from urllib.parse import quote_plus
from urllib.request import Request, urlopen


def web_search(query: str, limit: int = 5) -> dict[str, Any]:
    """Free DuckDuckGo instant-answer lookup — good enough for smoke tests."""
    url = f"https://duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&no_redirect=1"
    try:
        req = Request(url, headers={"User-Agent": "eazzu/1.0"})
        with urlopen(req, timeout=15) as r:
            data = json.loads(r.read().decode("utf-8", errors="replace") or "{}")
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
    topics = []
    for t in (data.get("RelatedTopics") or [])[:limit]:
        if "Text" in t and "FirstURL" in t:
            topics.append({"text": t["Text"], "url": t["FirstURL"]})
    return {
        "query": query,
        "abstract": data.get("AbstractText") or None,
        "abstract_url": data.get("AbstractURL") or None,
        "topics": topics,
    }


TOOLS = [
    {"name": "web_search",
     "description": "Quick web search (DuckDuckGo instant answer + related topics).",
     "params": {"query": "string", "limit": "int"}, "run": web_search},
]
