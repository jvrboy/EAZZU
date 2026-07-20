"""Web access tools — fetch, scrape, search, and extract content from the web.

Pure-stdlib (urllib + html.parser) so it works on iSH/Alpine without extra
dependencies. Each tool returns JSON-serialisable dicts for the agent registry.
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional
from urllib.parse import quote, urljoin, urlparse
from urllib.request import Request, urlopen

UA = "eazzu/1.1 (+https://github.com/jvrboy/EAZZU)"


def _error(code: str, exc: Exception) -> Dict[str, Any]:
    return {"error": code, "message": str(exc)}


def _fetch(url: str, timeout: int = 20, headers: Optional[Dict[str, str]] = None) -> tuple:
    req = Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urlopen(req, timeout=timeout) as r:
        body = r.read(500_000)
        return r.status, dict(r.headers), body


# ─── HTTP GET / POST ────────────────────────────────────────────────────

def http_get(url: str, timeout: int = 20) -> Dict[str, Any]:
    try:
        status, headers, body = _fetch(url, timeout)
        text = body.decode("utf-8", errors="replace")
        return {"status": status, "url": url, "headers": {k: v for k, v in headers.items()},
                "body": text[:50_000], "body_length": len(text)}
    except Exception as exc:
        return _error("http_get_failed", exc)


def http_post(url: str, data: Optional[Dict[str, Any]] = None, json_body: Optional[Dict[str, Any]] = None,
              timeout: int = 20) -> Dict[str, Any]:
    try:
        body_bytes = b""
        headers = {"User-Agent": UA}
        if json_body is not None:
            body_bytes = json.dumps(json_body).encode()
            headers["Content-Type"] = "application/json"
        elif data is not None:
            from urllib.parse import urlencode
            body_bytes = urlencode(data).encode()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
        req = Request(url, data=body_bytes, headers=headers, method="POST")
        with urlopen(req, timeout=timeout) as r:
            text = r.read(500_000).decode("utf-8", errors="replace")
            return {"status": r.status, "url": r.geturl(), "body": text[:50_000]}
    except Exception as exc:
        return _error("http_post_failed", exc)


def http_head(url: str, timeout: int = 15) -> Dict[str, Any]:
    try:
        req = Request(url, headers={"User-Agent": UA}, method="HEAD")
        with urlopen(req, timeout=timeout) as r:
            return {"status": r.status, "url": r.geturl(), "headers": dict(r.headers)}
    except Exception as exc:
        return _error("http_head_failed", exc)


# ─── HTML text extraction ───────────────────────────────────────────────

class _TextExtractor(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "head"}

    def __init__(self):
        super().__init__()
        self.parts: List[str] = []
        self.links: List[Dict[str, str]] = []
        self._skip = 0
        self._tag = None
        self._href = None
        self._link_text: List[str] = []

    def handle_starttag(self, tag, attrs):
        self._tag = tag
        if tag in self.SKIP:
            self._skip += 1
        if tag == "a":
            d = dict(attrs)
            self._href = d.get("href")
            self._link_text = []

    def handle_endtag(self, tag):
        if tag in self.SKIP and self._skip > 0:
            self._skip -= 1
        if tag == "a" and self._href:
            text = "".join(self._link_text).strip()
            if text:
                self.links.append({"href": self._href, "text": text})
            self._href = None
            self._link_text = []

    def handle_data(self, data):
        if self._skip > 0:
            return
        if self._href is not None:
            self._link_text.append(data)
        t = data.strip()
        if t:
            self.parts.append(t)


def extract_text(url: str, timeout: int = 20) -> Dict[str, Any]:
    try:
        status, headers, body = _fetch(url, timeout)
        html = body.decode("utf-8", errors="replace")
        parser = _TextExtractor()
        parser.feed(html)
        text = re.sub(r"\s+", " ", " ".join(parser.parts)).strip()
        base = url
        for link in parser.links:
            link["absolute"] = urljoin(base, link["href"])
        return {"url": url, "status": status, "title": _extract_title(html),
                "text": text[:50_000], "links": parser.links[:200],
                "link_count": len(parser.links)}
    except Exception as exc:
        return _error("extract_failed", exc)


def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return re.sub(r"\s+", " ", m.group(1)).strip() if m else ""


def extract_links(url: str, timeout: int = 20) -> Dict[str, Any]:
    try:
        status, _, body = _fetch(url, timeout)
        html = body.decode("utf-8", errors="replace")
        parser = _TextExtractor()
        parser.feed(html)
        links = [{"href": urljoin(url, l["href"]), "text": l["text"]} for l in parser.links]
        return {"url": url, "links": links[:300], "count": len(links)}
    except Exception as exc:
        return _error("links_failed", exc)


def extract_meta(url: str, timeout: int = 20) -> Dict[str, Any]:
    try:
        status, _, body = _fetch(url, timeout)
        html = body.decode("utf-8", errors="replace")
        title = _extract_title(html)
        desc = ""
        m = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=["\']([^"\']*)["\']', html, re.IGNORECASE)
        if m:
            desc = m.group(1)
        og = {}
        for prop, val in re.findall(r'<meta[^>]+property=["\']og:([^"\']+)["\'][^>]+content=["\']([^"\']*)["\']', html, re.IGNORECASE):
            og[prop] = val
        return {"url": url, "title": title, "description": desc, "open_graph": og}
    except Exception as exc:
        return _error("meta_failed", exc)


def web_search(query: str, count: int = 10) -> Dict[str, Any]:
    try:
        url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
        status, _, body = _fetch(url, timeout=25)
        html = body.decode("utf-8", errors="replace")
        results = []
        for m in re.finditer(r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.DOTALL):
            href = m.group(1)
            text = re.sub(r"<[^>]+>", "", m.group(2))
            text = re.sub(r"\s+", " ", text).strip()
            if href.startswith("//duckduckgo.com/l/"):
                href = re.sub(r"^//duckduckgo.com/l/\?uddg=", "", href)
                from urllib.parse import unquote
                href = unquote(href.split("&")[0])
            results.append({"title": text, "url": href})
            if len(results) >= count:
                break
        return {"query": query, "results": results, "count": len(results)}
    except Exception as exc:
        return _error("search_failed", exc)


def fetch_json(url: str, timeout: int = 20, headers: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
    try:
        status, hdrs, body = _fetch(url, timeout, headers)
        data = json.loads(body.decode("utf-8", errors="replace"))
        return {"status": status, "url": url, "data": data}
    except json.JSONDecodeError as exc:
        return _error("json_decode_failed", exc)
    except Exception as exc:
        return _error("fetch_json_failed", exc)


def download_file(url: str, path: str, timeout: int = 60, max_bytes: int = 10_000_000) -> Dict[str, Any]:
    try:
        req = Request(url, headers={"User-Agent": UA})
        with urlopen(req, timeout=timeout) as r:
            total = 0
            with open(path, "wb") as f:
                while True:
                    chunk = r.read(65536)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > max_bytes:
                        f.close()
                        return {"error": "max_bytes_exceeded", "bytes": total, "path": path}
                    f.write(chunk)
        return {"url": url, "path": path, "bytes": total, "status": r.status}
    except Exception as exc:
        return _error("download_failed", exc)


def url_info(url: str) -> Dict[str, Any]:
    try:
        p = urlparse(url)
        return {"scheme": p.scheme, "netloc": p.netloc, "path": p.path,
                "query": p.query, "fragment": p.fragment, "params": p.params,
                "is_https": p.scheme == "https"}
    except Exception as exc:
        return _error("url_info_failed", exc)


TOOLS = [
    {"name": "http_get", "description": "Fetch a URL with GET and return status, headers and body.",
     "params": {"url": "string", "timeout": "int"}, "run": http_get},
    {"name": "http_post", "description": "POST form or JSON data to a URL and return the response.",
     "params": {"url": "string", "data": "object(optional)", "json_body": "object(optional)", "timeout": "int"},
     "run": http_post},
    {"name": "http_head", "description": "Fetch only headers for a URL.",
     "params": {"url": "string", "timeout": "int"}, "run": http_head},
    {"name": "extract_text", "description": "Fetch a URL and extract visible text, title and links from the HTML.",
     "params": {"url": "string", "timeout": "int"}, "run": extract_text},
    {"name": "extract_links", "description": "Extract all hyperlinks from a web page.",
     "params": {"url": "string", "timeout": "int"}, "run": extract_links},
    {"name": "extract_meta", "description": "Extract page title, description and Open Graph metadata.",
     "params": {"url": "string", "timeout": "int"}, "run": extract_meta},
    {"name": "web_search", "description": "Search the web via DuckDuckGo (no API key required).",
     "params": {"query": "string", "count": "int"}, "run": web_search},
    {"name": "fetch_json", "description": "Fetch a URL and parse the response as JSON.",
     "params": {"url": "string", "timeout": "int", "headers": "object(optional)"}, "run": fetch_json},
    {"name": "download_file", "description": "Download a file from a URL to a local path.",
     "params": {"url": "string", "path": "string", "timeout": "int", "max_bytes": "int"}, "run": download_file},
    {"name": "url_info", "description": "Parse a URL and return its components.",
     "params": {"url": "string"}, "run": url_info},
]
