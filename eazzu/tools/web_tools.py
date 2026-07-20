"""Advanced web access tools — scraping, search, content extraction, headers, sitemaps, RSS.

Pure stdlib (urllib + regex). No external dependencies. Each function returns
JSON-serialisable dicts for the EAZZU agent registry.
"""
from __future__ import annotations

import gzip
import io
import json
import re
import socket
import ssl
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def _fetch(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 15,
           max_bytes: int = 500_000) -> Dict[str, Any]:
    hdrs = {"User-Agent": DEFAULT_UA, "Accept-Encoding": "gzip, deflate", "Accept": "*/*"}
    if headers:
        hdrs.update(headers)
    req = Request(url, headers=hdrs)
    with urlopen(req, timeout=timeout, context=_CTX) as r:
        raw = r.read(max_bytes)
        if r.headers.get("Content-Encoding") == "gzip":
            try:
                raw = gzip.decompress(raw)
            except Exception:
                pass
        body = raw.decode("utf-8", errors="replace")
        return {
            "status": r.status,
            "url": r.geturl(),
            "headers": dict(r.headers),
            "body": body,
        }


def _strip_html(html: str) -> str:
    """Remove scripts, styles, tags — return readable text."""
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;", " ", html)
    html = re.sub(r"&amp;", "&", html)
    html = re.sub(r"&lt;", "<", html)
    html = re.sub(r"&gt;", ">", html)
    html = re.sub(r"&quot;", '"', html)
    html = re.sub(r"&#39;", "'", html)
    return re.sub(r"\s+", " ", html).strip()


def web_fetch(url: str, timeout: int = 15, max_bytes: int = 200_000) -> Dict[str, Any]:
    """Fetch a URL and return status, headers, and body (truncated)."""
    try:
        result = _fetch(url, timeout=timeout, max_bytes=max_bytes)
        result["body"] = result["body"][:max_bytes]
        return result
    except HTTPError as e:
        return {"error": "http_error", "status": e.code, "message": str(e)}
    except Exception as e:
        return {"error": "fetch_failed", "message": f"{type(e).__name__}: {e}"}


def web_scrape(url: str, selector: Optional[str] = None, timeout: int = 15) -> Dict[str, Any]:
    """Scrape a page: return title, text, links, images, and meta tags.

    If a CSS-like tag selector is given (e.g. 'h1', 'p', 'div.content'), only
    matching elements' text is returned in the 'selected' field.
    """
    try:
        result = _fetch(url, timeout=timeout)
        html = result["body"]
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        title = title_match.group(1).strip() if title_match else ""
        text = _strip_html(html)
        links = list(set(re.findall(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE)))
        images = list(set(re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)))
        meta = {}
        for m in re.finditer(r'<meta\s+([^>]+)>', html, re.IGNORECASE):
            attrs = m.group(1)
            name = re.search(r'(?:name|property)=["\']([^"\']+)["\']', attrs)
            content = re.search(r'content=["\']([^"\']*)["\']', attrs)
            if name and content:
                meta[name.group(1)] = content.group(1)
        selected: List[str] = []
        if selector:
            tag = selector.split(".")[0].split("#")[0] or selector
            pattern = rf"<{tag}[^>]*>(.*?)</{tag}>"
            selected = [_strip_html(m) for m in re.findall(pattern, html, re.IGNORECASE | re.DOTALL)]
        return {
            "url": result["url"],
            "status": result["status"],
            "title": title,
            "text": text[:10_000],
            "links": [urljoin(url, l) for l in links[:100]],
            "images": [urljoin(url, i) for i in images[:50]],
            "meta": meta,
            "selected": selected[:50],
        }
    except Exception as e:
        return {"error": "scrape_failed", "message": f"{type(e).__name__}: {e}"}


def web_search(query: str, num_results: int = 10) -> Dict[str, Any]:
    """Search the web using DuckDuckGo's HTML endpoint (no API key required)."""
    try:
        url = f"https://html.duckduckgo.com/html/?q={query.replace(' ', '+')}"
        result = _fetch(url, timeout=20)
        html = result["body"]
        results = []
        for m in re.finditer(
            r'<a[^>]+class="result__a"[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
            html, re.DOTALL,
        ):
            link = m.group(1)
            title = _strip_html(m.group(2))
            if link.startswith("//duckduckgo.com/l/?uddg="):
                from urllib.parse import parse_qs, unquote
                parsed = parse_qs(urlparse(link).query)
                link = unquote(parsed.get("uddg", [link])[0])
            results.append({"title": title, "url": link})
            if len(results) >= num_results:
                break
        return {"query": query, "results": results}
    except Exception as e:
        return {"error": "search_failed", "message": f"{type(e).__name__}: {e}"}


def web_headers(url: str, timeout: int = 10) -> Dict[str, Any]:
    """Fetch only HTTP headers (HEAD request) for a URL."""
    try:
        req = Request(url, method="HEAD", headers={"User-Agent": DEFAULT_UA})
        with urlopen(req, timeout=timeout, context=_CTX) as r:
            return {"url": r.geturl(), "status": r.status, "headers": dict(r.headers)}
    except HTTPError as e:
        return {"error": "http_error", "status": e.code, "message": str(e)}
    except Exception as e:
        return {"error": "headers_failed", "message": f"{type(e).__name__}: {e}"}


def web_extract_text(url: str, timeout: int = 15) -> Dict[str, Any]:
    """Fetch a page and return only the cleaned readable text content."""
    try:
        result = _fetch(url, timeout=timeout)
        return {"url": result["url"], "text": _strip_html(result["body"])[:20_000]}
    except Exception as e:
        return {"error": "extract_failed", "message": f"{type(e).__name__}: {e}"}


def web_extract_links(url: str, timeout: int = 15) -> Dict[str, Any]:
    """Fetch a page and return all unique links found."""
    try:
        result = _fetch(url, timeout=timeout)
        html = result["body"]
        links = list(set(re.findall(r'href=["\']([^"\']+)["\']', html, re.IGNORECASE)))
        return {"url": result["url"], "links": [urljoin(url, l) for l in sorted(links)[:200]]}
    except Exception as e:
        return {"error": "links_failed", "message": f"{type(e).__name__}: {e}"}


def web_extract_images(url: str, timeout: int = 15) -> Dict[str, Any]:
    """Fetch a page and return all unique image URLs found."""
    try:
        result = _fetch(url, timeout=timeout)
        html = result["body"]
        images = list(set(re.findall(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)))
        return {"url": result["url"], "images": [urljoin(url, i) for i in sorted(images)[:100]]}
    except Exception as e:
        return {"error": "images_failed", "message": f"{type(e).__name__}: {e}"}


def web_sitemap(url: str, timeout: int = 20) -> Dict[str, Any]:
    """Fetch and parse a sitemap.xml, returning all URLs listed."""
    try:
        sitemap_url = urljoin(url, "/sitemap.xml")
        result = _fetch(sitemap_url, timeout=timeout)
        root = ET.fromstring(result["body"])
        ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
        urls = [loc.text for loc in root.findall(".//sm:loc", ns) if loc.text]
        return {"sitemap": sitemap_url, "url_count": len(urls), "urls": urls[:500]}
    except Exception as e:
        return {"error": "sitemap_failed", "message": f"{type(e).__name__}: {e}"}


def web_rss(url: str, timeout: int = 15) -> Dict[str, Any]:
    """Fetch and parse an RSS/Atom feed, returning recent items."""
    try:
        result = _fetch(url, timeout=timeout)
        root = ET.fromstring(result["body"])
        items = []
        for item in root.findall(".//item")[:20]:
            title = item.findtext("title", "")
            link = item.findtext("link", "")
            desc = item.findtext("description", "")
            pub = item.findtext("pubDate", "")
            items.append({"title": title, "link": link, "description": desc[:500], "pubDate": pub})
        return {"feed": url, "item_count": len(items), "items": items}
    except Exception as e:
        return {"error": "rss_failed", "message": f"{type(e).__name__}: {e}"}


def web_api_call(url: str, method: str = "GET", headers: Optional[Dict[str, str]] = None,
                 body: Optional[str] = None, timeout: int = 15) -> Dict[str, Any]:
    """Make a generic HTTP API call (GET/POST/PUT/DELETE) and return status + parsed JSON body."""
    try:
        hdrs = {"User-Agent": DEFAULT_UA, "Content-Type": "application/json"}
        if headers:
            hdrs.update(headers)
        data = body.encode("utf-8") if body else None
        req = Request(url, data=data, method=method, headers=hdrs)
        with urlopen(req, timeout=timeout, context=_CTX) as r:
            raw = r.read(200_000).decode("utf-8", errors="replace")
            try:
                parsed = json.loads(raw)
            except Exception:
                parsed = raw[:5_000]
            return {"status": r.status, "url": r.geturl(), "data": parsed}
    except HTTPError as e:
        return {"error": "http_error", "status": e.code, "message": str(e)}
    except Exception as e:
        return {"error": "api_call_failed", "message": f"{type(e).__name__}: {e}"}


def web_robots(url: str, timeout: int = 10) -> Dict[str, Any]:
    """Fetch and parse robots.txt for a domain."""
    try:
        robots_url = urljoin(url, "/robots.txt")
        result = _fetch(robots_url, timeout=timeout)
        lines = result["body"].splitlines()
        rules: List[Dict[str, str]] = []
        current_agent = "*"
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.lower().startswith("user-agent:"):
                current_agent = line.split(":", 1)[1].strip()
            elif line.lower().startswith(("allow:", "disallow:", "crawl-delay:", "sitemap:")):
                key, val = line.split(":", 1)
                rules.append({"agent": current_agent, "rule": key.strip().lower(), "value": val.strip()})
        return {"robots": robots_url, "rules": rules}
    except Exception as e:
        return {"error": "robots_failed", "message": f"{type(e).__name__}: {e}"}


def web_check_status(url: str, timeout: int = 10) -> Dict[str, Any]:
    """Quick check if a URL is reachable and return its status code and response time."""
    try:
        import time as _time
        start = _time.time()
        req = Request(url, headers={"User-Agent": DEFAULT_UA})
        with urlopen(req, timeout=timeout, context=_CTX) as r:
            elapsed = round((_time.time() - start) * 1000, 1)
            return {"url": r.geturl(), "status": r.status, "response_ms": elapsed, "reachable": True}
    except HTTPError as e:
        return {"url": url, "status": e.code, "reachable": True, "error": str(e)}
    except Exception as e:
        return {"url": url, "reachable": False, "error": f"{type(e).__name__}: {e}"}


TOOLS = [
    {"name": "web_fetch", "description": "Fetch a URL (GET) and return status, headers, and body.",
     "params": {"url": "string", "timeout": "int", "max_bytes": "int"}, "run": web_fetch},
    {"name": "web_scrape", "description": "Scrape a page: extract title, text, links, images, meta tags, and optionally selected elements.",
     "params": {"url": "string", "selector": "string(optional)", "timeout": "int"}, "run": web_scrape},
    {"name": "web_search", "description": "Search the web via DuckDuckGo (no API key required) and return titles + URLs.",
     "params": {"query": "string", "num_results": "int"}, "run": web_search},
    {"name": "web_headers", "description": "Fetch only HTTP headers (HEAD request) for a URL.",
     "params": {"url": "string", "timeout": "int"}, "run": web_headers},
    {"name": "web_extract_text", "description": "Fetch a page and return only the cleaned readable text content.",
     "params": {"url": "string", "timeout": "int"}, "run": web_extract_text},
    {"name": "web_extract_links", "description": "Fetch a page and return all unique links found.",
     "params": {"url": "string", "timeout": "int"}, "run": web_extract_links},
    {"name": "web_extract_images", "description": "Fetch a page and return all unique image URLs found.",
     "params": {"url": "string", "timeout": "int"}, "run": web_extract_images},
    {"name": "web_sitemap", "description": "Fetch and parse a sitemap.xml, returning all listed URLs.",
     "params": {"url": "string", "timeout": "int"}, "run": web_sitemap},
    {"name": "web_rss", "description": "Fetch and parse an RSS/Atom feed, returning recent items.",
     "params": {"url": "string", "timeout": "int"}, "run": web_rss},
    {"name": "web_api_call", "description": "Make a generic HTTP API call (GET/POST/PUT/DELETE) and return status + parsed JSON.",
     "params": {"url": "string", "method": "string", "headers": "object(optional)", "body": "string(optional)", "timeout": "int"},
     "run": web_api_call},
    {"name": "web_robots", "description": "Fetch and parse robots.txt for a domain.",
     "params": {"url": "string", "timeout": "int"}, "run": web_robots},
    {"name": "web_check_status", "description": "Quick check if a URL is reachable, returning status code and response time.",
     "params": {"url": "string", "timeout": "int"}, "run": web_check_status},
]
