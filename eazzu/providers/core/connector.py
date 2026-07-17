"""Main Connector class — the unified entry point for all providers."""
from __future__ import annotations

import time
from typing import Any, Iterator, Optional

from eazzu.providers.core.base_provider import BaseProvider, ChatMessage, ChatResponse
from eazzu.providers.core.cache import ResponseCache
from eazzu.providers.core.config import ConfigManager
from eazzu.providers.core.failover import FailoverPolicy
from eazzu.providers.core.registry import PROVIDER_REGISTRY, get_provider, list_providers
from eazzu.providers.core.tracker import UsageTracker


class Connector:
    """
    Unified connector across all registered AI providers.

    Example:
        c = Connector()
        r = c.chat("openai", "Hello!", model="gpt-4o-mini")
        print(r.content, r.cost_usd)
    """

    def __init__(
        self,
        config_manager: Optional[ConfigManager] = None,
        cache: Optional[ResponseCache] = None,
        tracker: Optional[UsageTracker] = None,
        enable_cache: bool = False,
        enable_tracking: bool = True,
    ):
        self.config = config_manager or ConfigManager()
        self.cache = cache or (ResponseCache() if enable_cache else None)
        self.tracker = tracker or (UsageTracker() if enable_tracking else None)
        self._instances: dict[str, BaseProvider] = {}

    # ---------- Registry helpers ---------- #
    def providers(self, category: str | None = None) -> list[str]:
        return list_providers(category)

    def categories(self) -> dict[str, list[str]]:
        cats: dict[str, list[str]] = {}
        for name, cls in PROVIDER_REGISTRY.items():
            cats.setdefault(getattr(cls, "category", "llm"), []).append(name)
        for v in cats.values():
            v.sort()
        return cats

    # ---------- Instance factory ---------- #
    def get_provider(
        self,
        name: str,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs,
    ) -> BaseProvider:
        cache_key = f"{name.lower()}|{base_url or ''}"
        if cache_key in self._instances and not api_key:
            return self._instances[cache_key]
        cls = get_provider(name)
        key = self.config.get(name, explicit=api_key)
        inst = cls(api_key=key, base_url=base_url, **kwargs)
        self._instances[cache_key] = inst
        return inst

    # ---------- Chat ---------- #
    def chat(
        self,
        provider: str,
        messages,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        use_cache: Optional[bool] = None,
        **kwargs,
    ) -> ChatResponse:
        p = self.get_provider(provider, api_key=api_key, base_url=base_url)
        # normalize once for cache key
        norm_msgs = [m.to_dict() for m in p._normalize_messages(messages)]
        eff_model = model or p.default_model
        want_cache = self.cache is not None if use_cache is None else use_cache
        if want_cache and self.cache:
            cached = self.cache.get(provider, eff_model, norm_msgs, kwargs)
            if cached:
                return ChatResponse(**cached)
        t0 = time.time()
        try:
            resp = p.chat(messages, model=model, **kwargs)
            resp.latency_ms = (time.time() - t0) * 1000
            if self.tracker:
                self.tracker.record(resp, success=True)
            if want_cache and self.cache:
                self.cache.set(provider, eff_model, norm_msgs, resp.to_dict(), kwargs)
            return resp
        except Exception:
            if self.tracker:
                self.tracker.record(
                    ChatResponse(provider=provider, model=eff_model, content=""),
                    success=False,
                )
            raise

    def stream(
        self,
        provider: str,
        messages,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        **kwargs,
    ) -> Iterator[str]:
        p = self.get_provider(provider, api_key=api_key, base_url=base_url)
        yield from p.stream(messages, model=model, **kwargs)

    # ---------- Failover ---------- #
    def chat_with_failover(
        self,
        policy: FailoverPolicy,
        messages,
        model: Optional[str] = None,
        **kwargs,
    ) -> ChatResponse:
        last_err: Exception | None = None
        seen = set()
        for provider, attempt in policy.iterate():
            try:
                return self.chat(provider, messages, model=model, **kwargs)
            except Exception as e:
                last_err = e
                seen.add(provider)
                if attempt < policy.max_retries:
                    policy.sleep(attempt)
        raise RuntimeError(
            f"All providers failed: {sorted(seen)}. Last error: {last_err}"
        )
