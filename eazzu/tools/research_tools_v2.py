"""Enhanced web research tools — deep search, content extraction, site auth.

Provides:
  * ``deep_search`` — multi-query web search with result aggregation
  * ``research_topic`` — full research pipeline (search → fetch → extract → summarize)
  * ``site_login`` — authenticate to any site via form login or API token
  * ``site_request`` — make authenticated requests to any site after login
  * ``extract_article`` — extract main article content from a page
  * ``summarize_url`` — fetch a URL and return a concise text summary
  * ``batch_fetch`` — fetch multiple URLs in sequence and return all bodies

All pure-stdlib (urllib + html.parser). No third-party dependencies.
"""
from __future__ import annotations

import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error
from html.parser import HTMLParser
from typing import Optional

from eazzu.tools.web_tools import http_get, extract_text, extract_links


# ---- Auth session store (in-memory, per-process) ---- #
_SESSIONS: dict[str, dict] = {}  # site_name -> {cookies, headers, token, login_url}


def site_login(site: str, login_url: str, credentials: dict, method: str = "form") -> dict:
    """Authenticate to any site.

    Parameters
    ----------
    site:
        A name for this session (e.g. "github", "custom_api").
    login_url:
        The login endpoint URL.
    credentials:
        * For ``form`` method: {"username": ..., "password": ...} or any form fields
        * For ``token`` method: {"token": ...} or {"api_key": ...}
        * For ``header`` method: {"header_name": "Authorization", "header_value": "Bearer ..."}
    method:
        "form" (POST credentials as form data), "token" (store token for later use),
        or "header" (store auth header for later use).
    """
    if method == "form":
        data = urllib.parse.urlencode(credentials).encode("utf-8")
        req = urllib.request.Request(login_url, data=data, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                cookies = resp.headers.get("Set-Cookie", "")
                body = resp.read().decode("utf-8", errors="replace")[:5000]
                _SESSIONS[site] = {"cookies": cookies, "login_url": login_url, "method": method}
                return {"site": site, "logged_in": True, "status": resp.status, "cookies": cookies[:200], "body_preview": body[:500]}
        except urllib.error.HTTPError as exc:
            return {"site": site, "logged_in": False, "error": f"HTTP {exc.code}", "detail": exc.read().decode("utf-8", errors="replace")[:500]}
        except urllib.error.URLError as exc:
            return {"site": site, "logged_in": False, "error": str(exc)}
    elif method == "token":
        token = credentials.get("token") or credentials.get("api_key") or credentials.get("access_token", "")
        if not token:
            return {"error": "no token provided in credentials"}
        _SESSIONS[site] = {"token": token, "login_url": login_url, "method": method}
        return {"site": site, "logged_in": True, "method": "token"}
    elif method == "header":
        header_name = credentials.get("header_name", "Authorization")
        header_value = credentials.get("header_value", "")
        if not header_value:
            return {"error": "no header_value provided"}
        _SESSIONS[site] = {"headers": {header_name: header_value}, "login_url": login_url, "method": method}
        return {"site": site, "logged_in": True, "method": "header"}
    return {"error": f"unknown method '{method}'. Use form, token, or header."}


def site_request(site: str, url: str, method: str = "GET", data: Optional[dict] = None, timeout: int = 30) -> dict:
    """Make an authenticated request to any site using a stored session."""
    session = _SESSIONS.get(site)
    if not session:
        return {"error": f"no session for site '{site}'. Call site_login first."}
    headers = {}
    if session.get("cookies"):
        headers["Cookie"] = session["cookies"]
    if session.get("token"):
        headers["Authorization"] = f"Bearer {session['token']}"
    if session.get("headers"):
        headers.update(session["headers"])
    body = None
    if data:
        body = json.dumps(data).encode("utf-8") if isinstance(data, (dict, list)) else str(data).encode("utf-8")
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return {"status": resp.status, "headers": dict(resp.headers), "body": raw[:50000], "truncated": len(raw) > 50000}
    except urllib.error.HTTPError as exc:
        return {"error": f"HTTP {exc.code}", "detail": exc.read().decode("utf-8", errors="replace")[:500]}
    except urllib.error.URLError as exc:
        return {"error": str(exc)}


def list_sessions() -> dict:
    return {"sessions": [{"site": k, "method": v.get("method", "unknown"), "login_url": v.get("login_url", "")} for k, v in _SESSIONS.items()], "count": len(_SESSIONS)}


def logout(site: str) -> dict:
    removed = _SESSIONS.pop(site, None)
    return {"site": site, "logged_out": removed is not None}


def deep_search(query: str, max_results: int = 20, engines: Optional[list[str]] = None) -> dict:
    """Multi-query deep search — runs multiple search variations and aggregates."""
    queries = [query]
    if len(query) < 100:
        queries.append(f"{query} tutorial")
        queries.append(f"{query} documentation")
        queries.append(f"{query} examples")
    all_results = []
    seen_urls = set()
    for q in queries[:4]:
        try:
            from eazzu.tools.web_tools import web_search
            results = web_search(q, max_results // 2)
            if isinstance(results, dict) and "results" in results:
                for r in results["results"]:
                    url = r.get("url") or r.get("href") or ""
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(r)
            elif isinstance(results, list):
                for r in results:
                    url = r.get("url") or r.get("href") or ""
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_results.append(r)
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.2)
    return {"query": query, "results": all_results[:max_results], "count": len(all_results[:max_results]), "queries_used": queries[:4]}


def research_topic(topic: str, depth: int = 3, max_sources: int = 5) -> dict:
    """Full research pipeline: search → fetch top sources → extract text → summarize."""
    search = deep_search(topic, max_results=max_sources * 2)
    sources = search.get("results", [])[:max_sources]
    fetched = []
    for source in sources:
        url = source.get("url") or source.get("href") or ""
        if not url:
            continue
        try:
            text = extract_text(url, timeout=20)
            if isinstance(text, dict):
                content = text.get("text", "")[:10000]
            else:
                content = str(text)[:10000]
            fetched.append({
                "url": url,
                "title": source.get("title", ""),
                "content": content,
                "content_length": len(content),
            })
        except Exception as exc:  # noqa: BLE001
            fetched.append({"url": url, "error": str(exc), "content": "", "content_length": 0})
    total_content = "\n\n---\n\n".join(f.get("content", "") for f in fetched if f.get("content"))
    return {
        "topic": topic,
        "sources_found": search.get("count", 0),
        "sources_fetched": len(fetched),
        "sources": [{"url": f["url"], "title": f.get("title", ""), "content_length": f.get("content_length", 0), "error": f.get("error")} for f in fetched],
        "aggregated_text_length": len(total_content),
        "aggregated_text_preview": total_content[:2000],
        "full_text": total_content,
    }


def extract_article(url: str, timeout: int = 20) -> dict:
    """Extract the main article content from a web page (strips nav, ads, etc.)."""
    try:
        resp = http_get(url, timeout)
        if "error" in resp:
            return resp
        html = resp.get("body", "")
        extractor = _ArticleExtractor()
        extractor.feed(html)
        article = extractor.get_article()
        return {
            "url": url,
            "title": extractor.title or "",
            "article": article,
            "word_count": len(article.split()),
            "links": extractor.links[:20],
        }
    except Exception as exc:  # noqa: BLE001
        return {"url": url, "error": str(exc)}


class _ArticleExtractor(HTMLParser):
    SKIP_TAGS = {"script", "style", "nav", "footer", "header", "aside", "noscript", "svg"}

    def __init__(self):
        super().__init__()
        self.title = ""
        self._in_title = False
        self._in_skip = 0
        self._current_text = []
        self._blocks = []
        self._current_tag = ""
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self._in_title = True
        if tag in self.SKIP_TAGS:
            self._in_skip += 1
        if tag in ("p", "article", "section", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6"):
            self._current_tag = tag
            self._current_text = []
        if tag == "a":
            href = dict(attrs).get("href", "")
            if href:
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in self.SKIP_TAGS and self._in_skip > 0:
            self._in_skip -= 1
        if tag in ("p", "article", "section", "li", "h1", "h2", "h3", "h4", "h5", "h6") and self._current_text:
            text = " ".join(self._current_text).strip()
            if len(text) > 50:
                self._blocks.append((tag, text))
            self._current_text = []

    def handle_data(self, data):
        if self._in_title and not self.title:
            self.title = data.strip()
        if self._in_skip == 0 and data.strip():
            self._current_text.append(data.strip())

    def get_article(self) -> str:
        if not self._blocks:
            return ""
        sorted_blocks = sorted(self._blocks, key=lambda x: len(x[1]), reverse=True)
        top = sorted_blocks[:10]
        top_set = {b[1] for b in top}
        ordered = [b[1] for b in self._blocks if b[1] in top_set]
        return "\n\n".join(ordered[:10])


def batch_fetch(urls: list[str], timeout: int = 20) -> dict:
    """Fetch multiple URLs in sequence and return all bodies."""
    results = []
    for url in urls:
        try:
            resp = http_get(url, timeout)
            results.append({"url": url, "status": resp.get("status"), "body": resp.get("body", "")[:10000], "error": resp.get("error")})
        except Exception as exc:  # noqa: BLE001
            results.append({"url": url, "error": str(exc)})
        time.sleep(0.1)
    return {"results": results, "count": len(results)}


TOOLS: list[dict] = [
    {
        "name": "deep_search",
        "description": "Multi-query deep web search with result aggregation across query variations",
        "params": {"query": "string", "max_results": "int"},
        "run": lambda args: deep_search(args.get("query", ""), int(args.get("max_results", 20))),
    },
    {
        "name": "research_topic",
        "description": "Full research pipeline: search → fetch sources → extract text → aggregate",
        "params": {"topic": "string", "depth": "int", "max_sources": "int"},
        "run": lambda args: research_topic(args.get("topic", ""), int(args.get("depth", 3)), int(args.get("max_sources", 5))),
    },
    {
        "name": "site_login",
        "description": "Authenticate to any site via form login, API token, or custom header",
        "params": {"site": "string", "login_url": "string", "credentials": "object", "method": "string"},
        "run": lambda args: site_login(args.get("site", ""), args.get("login_url", ""), args.get("credentials", {}), args.get("method", "form")),
    },
    {
        "name": "site_request",
        "description": "Make an authenticated request to any site using a stored session",
        "params": {"site": "string", "url": "string", "method": "string", "data": "object"},
        "run": lambda args: site_request(args.get("site", ""), args.get("url", ""), args.get("method", "GET"), args.get("data")),
    },
    {
        "name": "list_site_sessions",
        "description": "List all authenticated site sessions",
        "params": {},
        "run": lambda args: list_sessions(),
    },
    {
        "name": "site_logout",
        "description": "Log out from a site and clear its session",
        "params": {"site": "string"},
        "run": lambda args: logout(args.get("site", "")),
    },
    {
        "name": "extract_article",
        "description": "Extract main article content from a web page (strips navigation, ads, scripts)",
        "params": {"url": "string"},
        "run": lambda args: extract_article(args.get("url", "")),
    },
    {
        "name": "batch_fetch",
        "description": "Fetch multiple URLs in sequence and return all bodies",
        "params": {"urls": "list"},
        "run": lambda args: batch_fetch(args.get("urls", [])),
    },
]
