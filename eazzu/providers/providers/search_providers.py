"""Web search APIs: Tavily, Serper, Exa, Bing, Brave, You.com."""
from __future__ import annotations

import json

from eazzu.providers.core.base_provider import BaseProvider, ChatResponse
from eazzu.providers.core.http import post_json, get_json
from eazzu.providers.core.registry import register_provider


def _q(messages) -> str:
    return "\n".join(m.content for m in messages if m.role != "system")


@register_provider
class Tavily(BaseProvider):
    name = "tavily"
    default_base_url = "https://api.tavily.com"
    default_model = "search"
    category = "search"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        payload = {
            "api_key": self.api_key, "query": _q(messages),
            "search_depth": kwargs.pop("search_depth", "basic"),
            "max_results": kwargs.pop("max_results", 5),
        }
        data = post_json(f"{self.base_url}/search", {"Content-Type": "application/json"}, payload, self.timeout)
        summary = data.get("answer") or "\n".join(
            f"- {r['title']}: {r['url']}" for r in data.get("results", [])
        )
        return ChatResponse(provider=self.name, model=model, content=summary, raw=data)


@register_provider
class Serper(BaseProvider):
    name = "serper"
    default_base_url = "https://google.serper.dev"
    default_model = "google-search"
    category = "search"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        headers = {"X-API-KEY": self.api_key or "", "Content-Type": "application/json"}
        data = post_json(
            f"{self.base_url}/search", headers,
            {"q": _q(messages), **kwargs}, self.timeout,
        )
        summary = "\n".join(
            f"- {r.get('title')}: {r.get('link')}" for r in data.get("organic", [])[:5]
        )
        return ChatResponse(provider=self.name, model=model, content=summary, raw=data)


@register_provider
class Exa(BaseProvider):
    name = "exa"
    default_base_url = "https://api.exa.ai"
    default_model = "exa-search"
    category = "search"

    def _headers(self):
        return {"x-api-key": self.api_key or "", "Content-Type": "application/json"}

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        payload = {"query": _q(messages), "numResults": kwargs.pop("num_results", 5)}
        data = post_json(f"{self.base_url}/search", self._headers(), payload, self.timeout)
        summary = "\n".join(f"- {r['title']}: {r['url']}" for r in data.get("results", []))
        return ChatResponse(provider=self.name, model=model, content=summary, raw=data)


@register_provider
class Bing(BaseProvider):
    name = "bing"
    default_base_url = "https://api.bing.microsoft.com/v7.0"
    default_model = "web-search"
    category = "search"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        headers = {"Ocp-Apim-Subscription-Key": self.api_key or ""}
        data = get_json(f"{self.base_url}/search", headers, params={"q": _q(messages)}, timeout=self.timeout)
        items = data.get("webPages", {}).get("value", [])
        summary = "\n".join(f"- {i['name']}: {i['url']}" for i in items[:5])
        return ChatResponse(provider=self.name, model=model, content=summary, raw=data)


@register_provider
class Brave(BaseProvider):
    name = "brave"
    default_base_url = "https://api.search.brave.com/res/v1"
    default_model = "web-search"
    category = "search"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        headers = {"X-Subscription-Token": self.api_key or "", "Accept": "application/json"}
        data = get_json(f"{self.base_url}/web/search", headers, params={"q": _q(messages)}, timeout=self.timeout)
        items = data.get("web", {}).get("results", [])
        summary = "\n".join(f"- {i['title']}: {i['url']}" for i in items[:5])
        return ChatResponse(provider=self.name, model=model, content=summary, raw=data)


@register_provider
class You(BaseProvider):
    name = "you"
    default_base_url = "https://chat-api.you.com"
    default_model = "smart"
    category = "search"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        headers = {"X-API-Key": self.api_key or "", "Content-Type": "application/json"}
        payload = {"query": _q(messages), "chat_mode": model}
        data = post_json(self.base_url, headers, payload, self.timeout)
        return ChatResponse(
            provider=self.name, model=model,
            content=data.get("answer", "") or str(data), raw=data,
        )
