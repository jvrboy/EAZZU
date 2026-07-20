"""HuggingFace MCP adapter — models, datasets, spaces, papers search.

Uses the HuggingFace public REST API (no token required for read-only access).
If a token is set via ``HF_TOKEN``, it's included for higher rate limits and
private resources.
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Optional

_API = "https://huggingface.co/api"


def _hf_request(path: str, token: Optional[str] = None, timeout: float = 30) -> dict:
    url = f"{_API}/{path.lstrip('/')}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return {"error": f"HTTP {exc.code}", "detail": exc.read().decode("utf-8", errors="replace")[:500]}
    except urllib.error.URLError as exc:
        return {"error": str(exc)}


def search_models(query: str, limit: int = 10, sort: str = "downloads", token: Optional[str] = None) -> dict:
    return {"models": _hf_request(f"models?search={query}&limit={limit}&sort={sort}", token)}


def search_datasets(query: str, limit: int = 10, token: Optional[str] = None) -> dict:
    return {"datasets": _hf_request(f"datasets?search={query}&limit={limit}", token)}


def search_spaces(query: str, limit: int = 10, token: Optional[str] = None) -> dict:
    return {"spaces": _hf_request(f"spaces?search={query}&limit={limit}", token)}


def search_papers(query: str, limit: int = 10, token: Optional[str] = None) -> dict:
    return {"papers": _hf_request(f"papers?search={query}&limit={limit}", token)}


def get_model_info(model_id: str, token: Optional[str] = None) -> dict:
    return _hf_request(f"models/{model_id}", token)


def get_model_files(model_id: str, token: Optional[str] = None) -> dict:
    return {"files": _hf_request(f"models/{model_id}/tree/main", token)}


def whoami(token: str) -> dict:
    return _hf_request("whoami-v2", token)


def list_organizations(token: Optional[str] = None) -> dict:
    return {"orgs": _hf_request("organizations", token)}
