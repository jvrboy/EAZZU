"""Base provider abstraction — all connectors inherit from BaseProvider."""
from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Iterator, Optional


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant"
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass
class ChatResponse:
    provider: str
    model: str
    content: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    cost_usd: float = 0.0
    raw: dict = field(default_factory=dict)
    latency_ms: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    def __str__(self) -> str:
        return self.content


class BaseProvider(ABC):
    """Base class for all AI provider connectors.

    Sub-classes must override:
      - name (class attribute)
      - default_model
      - _chat_impl(messages, model, **kwargs) -> ChatResponse
      - optionally _stream_impl(messages, model, **kwargs) -> Iterator[str]
    """

    name: str = "base"
    default_model: str = ""
    default_base_url: str = ""
    # Approx pricing $ per 1K tokens. Override in subclass for accurate costs.
    price_in_per_1k: float = 0.0
    price_out_per_1k: float = 0.0
    category: str = "llm"  # llm | image | audio | search | embedding | multimodal

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 120,
        extra_headers: Optional[dict] = None,
        **kwargs,
    ):
        self.api_key = api_key
        self.base_url = base_url or self.default_base_url
        self.timeout = timeout
        self.extra_headers = extra_headers or {}
        self.extra_config = kwargs

    # ---------- Public API ---------- #
    def chat(
        self,
        messages: list[ChatMessage] | list[dict] | str,
        model: Optional[str] = None,
        **kwargs,
    ) -> ChatResponse:
        msgs = self._normalize_messages(messages)
        model = model or self.default_model
        return self._chat_impl(msgs, model, **kwargs)

    def stream(
        self,
        messages: list[ChatMessage] | list[dict] | str,
        model: Optional[str] = None,
        **kwargs,
    ) -> Iterator[str]:
        msgs = self._normalize_messages(messages)
        model = model or self.default_model
        yield from self._stream_impl(msgs, model, **kwargs)

    # ---------- Overridable ---------- #
    @abstractmethod
    def _chat_impl(
        self, messages: list[ChatMessage], model: str, **kwargs
    ) -> ChatResponse:
        ...

    def _stream_impl(
        self, messages: list[ChatMessage], model: str, **kwargs
    ) -> Iterator[str]:
        # Default fallback: emit the whole non-streamed response.
        resp = self._chat_impl(messages, model, **kwargs)
        yield resp.content

    # ---------- Helpers ---------- #
    @staticmethod
    def _normalize_messages(messages) -> list[ChatMessage]:
        if isinstance(messages, str):
            return [ChatMessage(role="user", content=messages)]
        out = []
        for m in messages:
            if isinstance(m, ChatMessage):
                out.append(m)
            elif isinstance(m, dict):
                out.append(ChatMessage(role=m.get("role", "user"), content=m.get("content", "")))
            else:
                out.append(ChatMessage(role="user", content=str(m)))
        return out

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        h.update(self.extra_headers)
        return h

    def _estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (
            prompt_tokens / 1000 * self.price_in_per_1k
            + completion_tokens / 1000 * self.price_out_per_1k
        )

    def _messages_to_openai_format(self, messages: list[ChatMessage]) -> list[dict]:
        return [m.to_dict() for m in messages]
