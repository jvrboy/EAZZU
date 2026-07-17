"""Embedding-focused providers: Voyage, Jina, Nomic."""
from __future__ import annotations

from eazzu.providers.core.base_provider import BaseProvider, ChatResponse
from eazzu.providers.core.http import post_json
from eazzu.providers.core.registry import register_provider


@register_provider
class Voyage(BaseProvider):
    name = "voyage"
    default_base_url = "https://api.voyageai.com/v1"
    default_model = "voyage-3-large"
    category = "embedding"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        texts = [m.content for m in messages if m.role != "system"]
        data = post_json(
            f"{self.base_url}/embeddings",
            self._headers(),
            {"model": model, "input": texts},
            self.timeout,
        )
        vecs = [d["embedding"] for d in data.get("data", [])]
        return ChatResponse(
            provider=self.name, model=model,
            content=f"<{len(vecs)} embedding vectors of dim {len(vecs[0]) if vecs else 0}>",
            raw={"embeddings": vecs, "usage": data.get("usage", {})},
        )


@register_provider
class Jina(BaseProvider):
    name = "jina"
    default_base_url = "https://api.jina.ai/v1"
    default_model = "jina-embeddings-v3"
    category = "embedding"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        texts = [m.content for m in messages if m.role != "system"]
        data = post_json(
            f"{self.base_url}/embeddings",
            self._headers(),
            {"model": model, "input": texts},
            self.timeout,
        )
        vecs = [d["embedding"] for d in data.get("data", [])]
        return ChatResponse(
            provider=self.name, model=model,
            content=f"<{len(vecs)} embedding vectors>",
            raw={"embeddings": vecs},
        )


@register_provider
class Nomic(BaseProvider):
    name = "nomic"
    default_base_url = "https://api-atlas.nomic.ai/v1"
    default_model = "nomic-embed-text-v1.5"
    category = "embedding"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        texts = [m.content for m in messages if m.role != "system"]
        data = post_json(
            f"{self.base_url}/embedding/text",
            self._headers(),
            {"model": model, "texts": texts, "task_type": kwargs.pop("task_type", "search_document")},
            self.timeout,
        )
        vecs = data.get("embeddings", [])
        return ChatResponse(
            provider=self.name, model=model,
            content=f"<{len(vecs)} embedding vectors>",
            raw={"embeddings": vecs},
        )
