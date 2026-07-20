"""Notes, knowledge capture & personal wiki tools.

Structured notebooks with sections, pages, tags, and full-text search.
Persists to a JSON store on disk so notes survive across sessions.
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path

_STORE_PATH = Path.home() / ".eazzu" / "notes.json"


def _load() -> dict:
    if _STORE_PATH.exists():
        try:
            return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"notebooks": {}}
    return {"notebooks": {}}


def _save(store: dict) -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _create_notebook(name):
    store = _load()
    if name not in store["notebooks"]:
        store["notebooks"][name] = {"sections": {}, "created": _now()}
        _save(store)
    return {"notebook": name, "created": store["notebooks"][name]["created"]}


def _add_page(notebook, section, title, body, tags=None):
    store = _load()
    nb = store["notebooks"].setdefault(notebook, {"sections": {}, "created": _now()})
    sec = nb["sections"].setdefault(section, {"pages": []})
    page = {"id": f"p{len(sec['pages']) + 1}", "title": title, "body": body, "tags": tags or [], "created": _now(), "updated": _now()}
    sec["pages"].append(page)
    _save(store)
    return page


def _search(query):
    store = _load()
    q = query.lower()
    results = []
    for nb_name, nb in store["notebooks"].items():
        for sec_name, sec in nb["sections"].items():
            for page in sec["pages"]:
                if q in page["title"].lower() or q in page["body"].lower() or any(q in t.lower() for t in page.get("tags", [])):
                    results.append({"notebook": nb_name, "section": sec_name, "page": page})
    return results


def _tag_search(tag):
    store = _load()
    results = []
    for nb_name, nb in store["notebooks"].items():
        for sec_name, sec in nb["sections"].items():
            for page in sec["pages"]:
                if tag.lower() in [t.lower() for t in page.get("tags", [])]:
                    results.append({"notebook": nb_name, "section": sec_name, "page": page})
    return results


def _list_notebooks():
    store = _load()
    out = {}
    for name, nb in store["notebooks"].items():
        sections = {sec_name: len(sec["pages"]) for sec_name, sec in nb["sections"].items()}
        out[name] = {"sections": sections, "page_count": sum(sections.values())}
    return out


def _delete_page(notebook, section, page_id):
    store = _load()
    sec = store.get("notebooks", {}).get(notebook, {}).get("sections", {}).get(section, {})
    before = len(sec.get("pages", []))
    sec["pages"] = [p for p in sec.get("pages", []) if p["id"] != page_id]
    _save(store)
    return {"deleted": before > len(sec["pages"]), "remaining": len(sec["pages"])}


def _wiki_link(body, pages):
    for p in pages:
        title = p["title"]
        body = re.sub(r"\[\[" + re.escape(title) + r"\]\]", f"[{title}](#page-{p['id']})", body)
    return body


TOOLS: list[dict] = [
    {
        "name": "notes_create_notebook",
        "description": "Create a new notebook (or no-op if it exists).",
        "params": {"name": "string"},
        "run": lambda a: _create_notebook(a.get("name", "")),
    },
    {
        "name": "notes_add_page",
        "description": "Add a page to a notebook section with title, body, and tags.",
        "params": {"notebook": "string", "section": "string", "title": "string", "body": "string", "tags": "list"},
        "run": lambda a: _add_page(a.get("notebook", ""), a.get("section", ""), a.get("title", ""), a.get("body", ""), a.get("tags", [])),
    },
    {
        "name": "notes_search",
        "description": "Full-text search across all notebooks, sections, and pages (matches title, body, tags).",
        "params": {"query": "string"},
        "run": lambda a: {"results": _search(a.get("query", ""))},
    },
    {
        "name": "notes_tag_search",
        "description": "Find all pages tagged with a given tag.",
        "params": {"tag": "string"},
        "run": lambda a: {"results": _tag_search(a.get("tag", ""))},
    },
    {
        "name": "notes_list_notebooks",
        "description": "List all notebooks with their sections and page counts.",
        "params": {},
        "run": lambda a: _list_notebooks(),
    },
    {
        "name": "notes_delete_page",
        "description": "Delete a page by its id from a notebook section.",
        "params": {"notebook": "string", "section": "string", "page_id": "string"},
        "run": lambda a: _delete_page(a.get("notebook", ""), a.get("section", ""), a.get("page_id", "")),
    },
    {
        "name": "notes_wiki_link",
        "description": "Convert [[Page Title]] wiki-links in a body to Markdown links using a list of known pages.",
        "params": {"body": "string", "pages": "list"},
        "run": lambda a: {"body": _wiki_link(a.get("body", ""), a.get("pages", []))},
    },
]
