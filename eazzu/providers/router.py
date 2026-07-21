"""Provider router — multi-provider, multi-key rotation with automatic failover.

This is the magic behind "say hi and it randomly picks any AI provider with a
configured key and responds; if that key burns out mid-task, transparently
shift to another key/provider and keep going without user intervention".

Design
------
* ``ProviderRouter`` wraps the existing ``Connector``. It is constructed from
  the ``ConfigManager`` and automatically discovers every LLM provider that
  has one or more API keys configured (env var or encrypted keystore).
* Each key is wrapped as an ``Endpoint`` (provider, api_key, base_url, model)
  with runtime health state: consecutive failures, cooldown deadline,
  average latency, success rate.
* On every ``chat()`` / ``stream()`` call the router:
    1. Builds a candidate list of healthy endpoints (not in cooldown, not
       disabled), in shuffled/weighted order.
    2. Tries the first; on failure marks it (cooldown on 429 / 401 / 402 /
       403 / 5xx / timeout / connection error), then tries the next.
    3. Updates health (success resets strike count; failure increments it).
    4. Returns the first successful response — caller never sees the churn.
* Persistent health state is kept in memory only (per-process). Stats are
  persisted to ``~/.eazzu/router_stats.json`` for across-session learning.
* The router is used automatically by ``Agent`` when no explicit provider
  is forced (``provider="auto"``), and falls back to the legacy single-
  provider behavior when a real provider name is passed.
"""
from __future__ import annotations

import json
import os
import random
import re
import threading
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Callable, Iterator, Optional

from eazzu.providers import Connector
from eazzu.providers.core.base_provider import ChatMessage, ChatResponse
from eazzu.providers.core.config import ConfigManager, ENV_VAR_MAP
from eazzu.providers.core.registry import PROVIDER_REGISTRY

# Ensure all provider classes are registered (side-effect import).
import eazzu.providers.providers  # noqa: F401

# Errors we consider "key / provider exhausted" and retry with another endpoint.
# 401 = bad key, 402 = payment/quota, 403 = forbidden/suspended, 429 = rate limit,
# 5xx = provider-side outage, plus network-level errors.
_RETRYABLE_STATUS = {401, 402, 403, 429, 500, 502, 503, 504, 520, 529}
_RETRYABLE_EXN_PATTERNS = (
    r"timed?\s*out",
    r"connection\s*(error|refused|reset|aborted)",
    r"dns",
    r"reset\s*by\s*peer",
    r"sslerror",
    r"remote\s*disconnected",
    r"temporarily unavailable",
    r"overloaded",
    r"capacity",
    r"quota",
    r"rate\s*limit",
    r"insufficient",
    r"billing",
    r"invalid.api.key",
    r"unauthorized",
    r"forbidden",
    r"context.length",
    r"too\s*many\s*requests",
    r"model.*overloaded",
    r"try again",
    r"upstream",
    r"timeout",
)
_RETRYABLE_RE = re.compile("|".join(_RETRYABLE_EXN_PATTERNS), re.IGNORECASE)

# How many consecutive failures before an endpoint is put into cooldown.
_DEFAULT_STRIKES = 3
_DEFAULT_COOLDOWN = 30.0  # seconds, doubles on repeat
_MAX_COOLDOWN = 600.0
_DEFAULT_TIMEOUT = 120


def _is_retryable(status: int | None, err: Exception | None) -> tuple[bool, float]:
    """Return (should_retry, retry_after_hint_seconds)."""
    if status is not None:
        if status in _RETRYABLE_STATUS:
            return True, 5.0 if status == 429 else 0.0
        if 500 <= status < 600:
            return True, 2.0
        return False, 0.0
    if err is not None and _RETRYABLE_RE.search(str(err)):
        # Try to parse Retry-After from exception text if present.
        m = re.search(r"retry[_\- ]after[^\d]*(\d+)", str(err), re.IGNORECASE)
        return True, float(m.group(1)) if m else 1.0
    return False, 0.0


def _extract_status(err: Exception) -> int | None:
    """Pull HTTP status from common requests/urllib exception shapes."""
    # requests.HTTPError has response
    resp = getattr(err, "response", None)
    if resp is not None:
        return getattr(resp, "status_code", None)
    # RuntimeError from http.py: "HTTP 429: ..."
    m = re.match(r"HTTP\s+(\d{3})", str(err))
    if m:
        return int(m.group(1))
    return None


@dataclass
class Endpoint:
    provider: str
    api_key: str
    base_url: Optional[str] = None
    model: Optional[str] = None  # if set, always pin to this model
    label: Optional[str] = None  # human label (e.g. "gemini key #3")
    # Runtime state
    strikes: int = 0
    cooldown_until: float = 0.0
    success_count: int = 0
    fail_count: int = 0
    last_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    last_error: str = ""
    last_success_at: float = 0.0

    @property
    def name(self) -> str:
        return self.label or f"{self.provider}:{mask_key(self.api_key)}"

    def is_ready(self, now: float | None = None) -> bool:
        now = now if now is not None else time.time()
        return self.cooldown_until <= now


def mask_key(k: str) -> str:
    if not k:
        return "(no-key)"
    if len(k) <= 8:
        return "***"
    return f"{k[:4]}…{k[-4:]}"


@dataclass
class RouteResult:
    response: Optional[ChatResponse] = None
    provider: Optional[str] = None
    api_key_masked: Optional[str] = None
    endpoint_label: Optional[str] = None
    attempts: int = 0
    errors: list[dict] = field(default_factory=list)
    strategy: str = "random"


class ProviderRouter:
    """Multi-endpoint rotation + failover.

    Parameters
    ----------
    connector:
        A :class:`Connector` to use for the actual calls.
    config:
        :class:`ConfigManager` for API keys.
    strategy:
        One of ``"random"`` (default, uniform over healthy), ``"healthiest"``
        (weight by success rate), ``"fastest"`` (weight by inverse avg latency),
        ``"cheapest"`` (prefer providers with lower per-token cost).
    max_attempts:
        Maximum endpoints to try before raising (default 12).
    extra_providers:
        Explicit list of provider names to restrict to. If None, auto-discovers.
    auto_discover:
        Include every LLM provider with a configured key (default True).
    llm_only:
        Only route to providers in the ``llm`` category (default True).
    """

    def __init__(
        self,
        connector: Optional[Connector] = None,
        config: Optional[ConfigManager] = None,
        strategy: str = "random",
        max_attempts: int = 12,
        extra_providers: Optional[list[str]] = None,
        auto_discover: bool = True,
        llm_only: bool = True,
        persist_path: Optional[Path] = None,
    ) -> None:
        self.connector = connector or Connector()
        self.config = config or ConfigManager()
        self.strategy = strategy
        self.max_attempts = max_attempts
        self._extra_providers = extra_providers or []
        self._auto_discover = auto_discover
        self._llm_only = llm_only
        self._lock = threading.Lock()
        self.endpoints: list[Endpoint] = []
        self._persist_path = persist_path or (
            Path.home() / ".eazzu" / "router_stats.json"
        )
        self._load_state()
        self.discover_endpoints()

    # ------------------------------------------------------------------ setup #
    def discover_endpoints(self) -> list[Endpoint]:
        """Scan config / env / keyfile for LLM providers with at least one key."""
        eps: list[Endpoint] = []
        seen_keys: set[tuple[str, str]] = set()  # de-dupe across sources

        candidates = set(self._extra_providers)
        if self._auto_discover:
            for name, cls in PROVIDER_REGISTRY.items():
                if self._llm_only and getattr(cls, "category", "llm") != "llm":
                    continue
                candidates.add(name)
            # also include ENV_VAR_MAP keys that are LLM-ish (all map values)
            for name in ENV_VAR_MAP.keys():
                candidates.add(name)

        for name in sorted(candidates):
            keys = self._collect_keys(name)
            # Don't instantiate providers with zero keys — they'd just error.
            if not keys:
                continue
            cls = PROVIDER_REGISTRY.get(name)
            if cls is None:
                continue
            if self._llm_only and getattr(cls, "category", "llm") != "llm":
                continue
            default_model = getattr(cls, "default_model", None)
            for idx, key in enumerate(keys):
                sig = (name, key)
                if sig in seen_keys:
                    continue
                seen_keys.add(sig)
                label = f"{name} #{idx+1}" if len(keys) > 1 else name
                eps.append(
                    Endpoint(
                        provider=name,
                        api_key=key,
                        base_url=None,
                        model=default_model,
                        label=label,
                    )
                )
        with self._lock:
            # Preserve stats for keys that already existed.
            existing = {(e.provider, e.api_key): e for e in self.endpoints}
            merged = []
            for e in eps:
                prev = existing.get((e.provider, e.api_key))
                if prev is not None:
                    # Carry over health, but refresh provider/model info in case registry changed.
                    prev.model = e.model
                    prev.label = e.label
                    merged.append(prev)
                else:
                    merged.append(e)
            self.endpoints = merged
            self._save_state()
        return self.endpoints

    def _collect_keys(self, provider: str) -> list[str]:
        """Return all keys available for a provider (env + encrypted file, multi-key)."""
        keys: list[str] = []
        # Env: single key OR comma/space-separated list
        env_name = ENV_VAR_MAP.get(provider.lower())
        env_generic = f"{provider.upper()}_API_KEY"
        for candidate_env in (env_name, env_generic):
            if not candidate_env:
                continue
            raw = os.environ.get(candidate_env, "").strip()
            if raw:
                keys.extend(_split_keys(raw))
        # Encrypted keystore: value may be a single key OR a multi-key blob.
        try:
            v = self.config.get(provider)
        except Exception:
            v = None
        if v:
            keys.extend(_split_keys(v))
        # Dedupe while preserving order
        seen = set()
        out = []
        for k in keys:
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    def refresh(self) -> int:
        """Re-scan for new keys (e.g. after `eazzu keys add`). Returns count."""
        before = len(self.endpoints)
        self.discover_endpoints()
        return len(self.endpoints) - before

    # ---------------------------------------------------------------- routing #
    def _ordered_candidates(self) -> list[Endpoint]:
        with self._lock:
            healthy = [e for e in self.endpoints if e.is_ready()]
            if not healthy:
                # All cooled down — pick the one that comes off cooldown soonest.
                cooled = sorted(self.endpoints, key=lambda e: e.cooldown_until)
                return cooled[:1] if cooled else []

        if self.strategy == "random":
            random.shuffle(healthy)
            return healthy
        if self.strategy == "healthiest":
            # weight = (successes+1)/(attempts+2)
            def score(e):
                att = e.success_count + e.fail_count
                sr = (e.success_count + 1) / (att + 2)
                return sr - 0.01 * e.strikes
            healthy.sort(key=score, reverse=True)
            return healthy
        if self.strategy == "fastest":
            def score(e):
                lat = e.avg_latency_ms or 5000
                return -lat
            healthy.sort(key=score, reverse=True)
            return healthy
        if self.strategy == "cheapest":
            cheap: list[tuple[float, Endpoint]] = []
            for e in healthy:
                cls = PROVIDER_REGISTRY.get(e.provider)
                cost = (getattr(cls, "price_in_per_1k", 0) or 0) + (getattr(cls, "price_out_per_1k", 0) or 0)
                cheap.append((cost, e))
            cheap.sort(key=lambda x: x[0])
            return [e for _, e in cheap]
        # fallback random
        random.shuffle(healthy)
        return healthy

    def _pick_instance(self, ep: Endpoint):
        return self.connector.get_provider(ep.provider, api_key=ep.api_key, base_url=ep.base_url)

    # ------------------------------------------------------------------ chat #
    def chat(
        self,
        messages,
        model: Optional[str] = None,
        max_attempts: Optional[int] = None,
        on_failover: Optional[Callable[[dict], None]] = None,
        **kwargs,
    ) -> RouteResult:
        """Call LLM through the best available endpoint, transparently failing over.

        Candidates are re-evaluated each iteration so endpoints that come off
        cooldown (or were just added via refresh()) become eligible. Up to
        ``max_attempts`` endpoints are tried in total.
        """
        attempts = max(max_attempts or self.max_attempts, len(self.endpoints) * 2)
        result = RouteResult(strategy=self.strategy)
        last_err: Exception | None = None
        non_retryable_err: Exception | None = None
        for _ in range(attempts):
            candidates = self._ordered_candidates()
            if not candidates:
                # All cooled down — briefly sleep and refresh.
                time.sleep(0.5)
                continue
            ep = candidates[0]
            result.attempts += 1
            t0 = time.time()
            try:
                inst = self._pick_instance(ep)
                resp_model = model or ep.model
                resp = inst.chat(messages, model=resp_model, **kwargs)
                lat = (time.time() - t0) * 1000
                self._mark_success(ep, lat)
                resp.latency_ms = lat
                resp.provider = ep.provider  # stamp for tracker
                result.response = resp
                result.provider = ep.provider
                result.api_key_masked = mask_key(ep.api_key)
                result.endpoint_label = ep.label
                self._save_state()
                return result
            except Exception as e:
                last_err = e
                status = _extract_status(e)
                retryable, retry_after = _is_retryable(status, e)
                err_entry = {
                    "endpoint": ep.name,
                    "status": status,
                    "error": f"{type(e).__name__}: {str(e)[:200]}",
                    "retryable": retryable,
                }
                result.errors.append(err_entry)
                if on_failover:
                    try:
                        on_failover(err_entry)
                    except Exception:
                        pass
                self._mark_failure(ep, retryable, retry_after, str(e))
                if not retryable:
                    non_retryable_err = e
                    break
                continue
        self._save_state()
        # If we bailed due to non-retryable error, raise that directly.
        if non_retryable_err is not None:
            raise non_retryable_err
        if last_err is not None:
            raise RuntimeError(
                f"router exhausted ({result.attempts} attempts, {len(result.errors)} errors). "
                f"Last: {result.errors[-1] if result.errors else last_err}"
            ) from last_err
        raise RuntimeError("no healthy endpoints configured — run `eazzu keys add <provider> <key>`")

    # ---------------------------------------------------------------- stream #
    def stream(
        self,
        messages,
        model: Optional[str] = None,
        max_attempts: Optional[int] = None,
        on_failover: Optional[Callable[[dict], None]] = None,
        **kwargs,
    ) -> Iterator[str]:
        """Stream tokens, transparently restarting on a different endpoint if
        the stream dies mid-flight.

        Caveat: when we fail over mid-stream, the new provider will restart
        the whole response (we can't resume a token stream). The caller sees
        only the successful continuation after the partial prefix; we emit
        whatever the new provider produces, not the partial (avoids
        gibberish). Callers sensitive to this should check result metadata.
        """
        attempts = max_attempts or self.max_attempts
        for _ in range(attempts):
            candidates = self._ordered_candidates()
            if not candidates:
                break
            ep = candidates[0]
            t0 = time.time()
            try:
                inst = self._pick_instance(ep)
                resp_model = model or ep.model
                buf: list[str] = []
                failed = False
                try:
                    for chunk in inst.stream(messages, model=resp_model, **kwargs):
                        buf.append(chunk)
                        yield chunk
                except Exception as e:
                    failed = True
                    status = _extract_status(e)
                    retryable, retry_after = _is_retryable(status, e)
                    if on_failover:
                        try:
                            on_failover({
                                "endpoint": ep.name,
                                "status": status,
                                "error": f"(stream) {type(e).__name__}: {str(e)[:200]}",
                                "retryable": retryable,
                                "partial_chars": sum(len(c) for c in buf),
                            })
                        except Exception:
                            pass
                    self._mark_failure(ep, retryable, retry_after, str(e))
                    if not retryable:
                        raise
                    continue
                lat = (time.time() - t0) * 1000
                self._mark_success(ep, lat)
                self._save_state()
                return
            except Exception:
                continue
        raise RuntimeError("router exhausted all endpoints while streaming")

    # ---------------------------------------------------------- health bookkeeping #
    def _mark_success(self, ep: Endpoint, latency_ms: float) -> None:
        with self._lock:
            ep.strikes = 0
            ep.cooldown_until = 0.0
            ep.success_count += 1
            ep.last_latency_ms = latency_ms
            # EMA average
            ep.avg_latency_ms = (
                latency_ms if ep.avg_latency_ms == 0 else 0.7 * ep.avg_latency_ms + 0.3 * latency_ms
            )
            ep.last_success_at = time.time()
            ep.last_error = ""

    def _mark_failure(self, ep: Endpoint, retryable: bool, retry_after: float, msg: str) -> None:
        with self._lock:
            ep.fail_count += 1
            ep.last_error = msg[:200]
            if not retryable:
                # Non-retryable: cool briefly so we don't hammer, but will be retried if user asks again.
                ep.cooldown_until = time.time() + 30
                return
            ep.strikes += 1
            # On any retryable failure, add a small cooldown so the router
            # prefers a different endpoint on the next iteration (prevents
            # hammering a rate-limited/empty-key endpoint in a tight loop).
            if ep.strikes >= _DEFAULT_STRIKES or retry_after > 0:
                cd = max(retry_after, min(_DEFAULT_COOLDOWN * (2 ** max(0, ep.strikes - _DEFAULT_STRIKES)), _MAX_COOLDOWN))
            else:
                cd = 1.0  # short hop-skip so next() picks a different endpoint
            ep.cooldown_until = time.time() + cd

    def reset_health(self) -> None:
        with self._lock:
            for ep in self.endpoints:
                ep.strikes = 0
                ep.cooldown_until = 0
                ep.fail_count = 0
                ep.last_error = ""
        self._save_state()

    # ------------------------------------------------------------ diagnostics #
    def status(self) -> dict:
        with self._lock:
            now = time.time()
            ready = sum(1 for e in self.endpoints if e.is_ready(now))
            cooled = len(self.endpoints) - ready
            return {
                "strategy": self.strategy,
                "total_endpoints": len(self.endpoints),
                "healthy": ready,
                "cooling_down": cooled,
                "endpoints": [
                    {
                        "label": e.label,
                        "provider": e.provider,
                        "key": mask_key(e.api_key),
                        "model": e.model,
                        "ready": e.is_ready(now),
                        "cooldown_remaining_s": max(0, round(e.cooldown_until - now, 1)),
                        "successes": e.success_count,
                        "failures": e.fail_count,
                        "strikes": e.strikes,
                        "avg_latency_ms": round(e.avg_latency_ms, 1),
                        "last_error": e.last_error,
                    }
                    for e in sorted(self.endpoints, key=lambda x: (not x.is_ready(now), x.provider))
                ],
            }

    # ----------------------------------------------------------- persist state #
    def _save_state(self) -> None:
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "strategy": self.strategy,
                "endpoints": [
                    {
                        "provider": e.provider,
                        "key_masked": mask_key(e.api_key),
                        # Don't persist raw keys — just stats, keyed by provider+mask.
                        "strikes": e.strikes,
                        "cooldown_until": e.cooldown_until,
                        "success_count": e.success_count,
                        "fail_count": e.fail_count,
                        "avg_latency_ms": e.avg_latency_ms,
                        "last_error": e.last_error,
                    }
                    for e in self.endpoints
                ],
            }
            tmp = self._persist_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(data, indent=2))
            tmp.replace(self._persist_path)
        except OSError:
            pass

    def _load_state(self) -> None:
        try:
            if self._persist_path.is_file():
                data = json.loads(self._persist_path.read_text())
                if isinstance(data, dict):
                    if data.get("strategy"):
                        self.strategy = data["strategy"]
                    # Stats are merged in discover_endpoints after we build list;
                    # we stash them here for later.
                    self._stashed_stats = {
                        (e["provider"], e["key_masked"]): e for e in data.get("endpoints", [])
                    }
        except Exception:
            self._stashed_stats = {}


def _split_keys(raw: str) -> list[str]:
    """Split a stored value into individual keys.

    Supports: comma-separated, newline-separated, or a JSON list. Keys are
    stripped of whitespace/quotes and duplicates are removed (first occurrence wins).
    """
    raw = (raw or "").strip()
    if not raw:
        return []
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                parts = [str(k).strip().strip("\"'") for k in parsed]
            else:
                parts = [raw]
        except json.JSONDecodeError:
            parts = re.split(r"[\n,]+", raw)
    else:
        parts = re.split(r"[\n,]+", raw)
    cleaned = [p.strip().strip("\"'") for p in parts]
    out: list[str] = []
    seen: set[str] = set()
    for k in cleaned:
        if k and k not in seen:
            seen.add(k)
            out.append(k)
    return out


__all__ = [
    "Endpoint",
    "ProviderRouter",
    "RouteResult",
    "mask_key",
]
