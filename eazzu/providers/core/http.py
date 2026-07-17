"""Shared HTTP helper using requests, with streaming support."""
from __future__ import annotations

import json
from typing import Iterator, Optional

import requests


def post_json(url: str, headers: dict, payload: dict, timeout: int = 120) -> dict:
    r = requests.post(url, headers=headers, json=payload, timeout=timeout)
    if not r.ok:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
    return r.json()


def get_json(url: str, headers: dict, params: Optional[dict] = None, timeout: int = 60) -> dict:
    r = requests.get(url, headers=headers, params=params, timeout=timeout)
    if not r.ok:
        raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
    return r.json()


def stream_sse(url: str, headers: dict, payload: dict, timeout: int = 300) -> Iterator[dict]:
    """Yield JSON payloads from an SSE (data: {...}) stream."""
    with requests.post(url, headers=headers, json=payload, timeout=timeout, stream=True) as r:
        if not r.ok:
            raise RuntimeError(f"HTTP {r.status_code}: {r.text[:500]}")
        for raw in r.iter_lines(decode_unicode=True):
            if not raw:
                continue
            line = raw.strip()
            if line.startswith("data:"):
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    yield json.loads(data)
                except json.JSONDecodeError:
                    continue
