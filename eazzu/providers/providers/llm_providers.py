"""Non-OpenAI-shape LLM providers: Anthropic, Gemini, Cohere, AI21, Aleph Alpha,
Baidu ERNIE, Tencent Hunyuan, Meta Llama API, Inflection.
"""
from __future__ import annotations

import json
from typing import Iterator

import requests

from eazzu.providers.core.base_provider import BaseProvider, ChatMessage, ChatResponse
from eazzu.providers.core.http import post_json, stream_sse
from eazzu.providers.core.registry import register_provider


# ---------------------------------------------------------------------
# Anthropic (Claude)
# ---------------------------------------------------------------------
@register_provider
class Anthropic(BaseProvider):
    name = "anthropic"
    default_base_url = "https://api.anthropic.com/v1"
    default_model = "claude-3-5-sonnet-latest"
    price_in_per_1k = 0.003
    price_out_per_1k = 0.015

    def _headers(self) -> dict:
        h = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key or "",
            "anthropic-version": "2023-06-01",
        }
        h.update(self.extra_headers)
        return h

    def _split_system(self, messages):
        system_parts = [m.content for m in messages if m.role == "system"]
        chat = [m.to_dict() for m in messages if m.role != "system"]
        return "\n".join(system_parts) if system_parts else None, chat

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        system, chat = self._split_system(messages)
        payload = {
            "model": model,
            "messages": chat,
            "max_tokens": kwargs.pop("max_tokens", 1024),
            **{k: v for k, v in kwargs.items() if v is not None},
        }
        if system:
            payload["system"] = system
        data = post_json(f"{self.base_url}/messages", self._headers(), payload, self.timeout)
        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")
        usage = data.get("usage", {}) or {}
        p = usage.get("input_tokens", 0)
        c = usage.get("output_tokens", 0)
        return ChatResponse(
            provider=self.name, model=model, content=content,
            prompt_tokens=p, completion_tokens=c, total_tokens=p + c,
            cost_usd=self._estimate_cost(p, c), raw=data,
        )

    def _stream_impl(self, messages, model, **kwargs) -> Iterator[str]:
        system, chat = self._split_system(messages)
        payload = {
            "model": model,
            "messages": chat,
            "max_tokens": kwargs.pop("max_tokens", 1024),
            "stream": True,
        }
        if system:
            payload["system"] = system
        with requests.post(
            f"{self.base_url}/messages",
            headers=self._headers(),
            json=payload,
            stream=True,
            timeout=self.timeout,
        ) as r:
            r.raise_for_status()
            for raw in r.iter_lines(decode_unicode=True):
                if not raw or not raw.startswith("data:"):
                    continue
                try:
                    ev = json.loads(raw[5:].strip())
                except json.JSONDecodeError:
                    continue
                if ev.get("type") == "content_block_delta":
                    delta = ev.get("delta", {})
                    if delta.get("type") == "text_delta":
                        yield delta.get("text", "")


# ---------------------------------------------------------------------
# Google Gemini
# ---------------------------------------------------------------------
@register_provider
class Gemini(BaseProvider):
    name = "gemini"
    default_base_url = "https://generativelanguage.googleapis.com/v1beta"
    default_model = "gemini-2.0-flash"
    price_in_per_1k = 0.000075
    price_out_per_1k = 0.0003

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        contents = []
        sys_parts = []
        for m in messages:
            if m.role == "system":
                sys_parts.append(m.content)
            else:
                role = "user" if m.role == "user" else "model"
                contents.append({"role": role, "parts": [{"text": m.content}]})
        payload = {"contents": contents}
        if sys_parts:
            payload["systemInstruction"] = {"parts": [{"text": "\n".join(sys_parts)}]}
        url = f"{self.base_url}/models/{model}:generateContent?key={self.api_key}"
        data = post_json(url, {"Content-Type": "application/json"}, payload, self.timeout)
        content = ""
        for cand in data.get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                content += part.get("text", "")
        um = data.get("usageMetadata", {}) or {}
        p = um.get("promptTokenCount", 0)
        c = um.get("candidatesTokenCount", 0)
        return ChatResponse(
            provider=self.name, model=model, content=content,
            prompt_tokens=p, completion_tokens=c,
            total_tokens=um.get("totalTokenCount", p + c),
            cost_usd=self._estimate_cost(p, c), raw=data,
        )


# Alias: "google" -> Gemini
@register_provider
class Google(Gemini):
    name = "google"


# ---------------------------------------------------------------------
# Cohere
# ---------------------------------------------------------------------
@register_provider
class Cohere(BaseProvider):
    name = "cohere"
    default_base_url = "https://api.cohere.com/v2"
    default_model = "command-r-plus-08-2024"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        payload = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            **{k: v for k, v in kwargs.items() if v is not None},
        }
        data = post_json(f"{self.base_url}/chat", self._headers(), payload, self.timeout)
        content = ""
        for block in data.get("message", {}).get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")
        usage = data.get("usage", {}).get("tokens", {}) or {}
        p = usage.get("input_tokens", 0)
        c = usage.get("output_tokens", 0)
        return ChatResponse(
            provider=self.name, model=model, content=content,
            prompt_tokens=p, completion_tokens=c, total_tokens=p + c,
            cost_usd=self._estimate_cost(p, c), raw=data,
        )


# ---------------------------------------------------------------------
# AI21 Labs
# ---------------------------------------------------------------------
@register_provider
class AI21(BaseProvider):
    name = "ai21"
    default_base_url = "https://api.ai21.com/studio/v1"
    default_model = "jamba-1.5-large"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        payload = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
            **{k: v for k, v in kwargs.items() if v is not None},
        }
        data = post_json(
            f"{self.base_url}/chat/completions", self._headers(), payload, self.timeout
        )
        choices = data.get("choices") or []
        content = choices[0]["message"]["content"] if choices else ""
        usage = data.get("usage", {}) or {}
        p = usage.get("prompt_tokens", 0)
        c = usage.get("completion_tokens", 0)
        return ChatResponse(
            provider=self.name, model=model, content=content,
            prompt_tokens=p, completion_tokens=c, total_tokens=p + c,
            cost_usd=self._estimate_cost(p, c), raw=data,
        )


# ---------------------------------------------------------------------
# Aleph Alpha
# ---------------------------------------------------------------------
@register_provider
class AlephAlpha(BaseProvider):
    name = "aleph_alpha"
    default_base_url = "https://api.aleph-alpha.com"
    default_model = "luminous-supreme"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        prompt = "\n\n".join(f"{m.role.upper()}: {m.content}" for m in messages)
        payload = {
            "model": model,
            "prompt": prompt,
            "maximum_tokens": kwargs.pop("max_tokens", 512),
        }
        data = post_json(f"{self.base_url}/complete", self._headers(), payload, self.timeout)
        completions = data.get("completions", [])
        content = completions[0]["completion"] if completions else ""
        return ChatResponse(
            provider=self.name, model=model, content=content,
            prompt_tokens=0, completion_tokens=0, total_tokens=0,
            cost_usd=0.0, raw=data,
        )


# ---------------------------------------------------------------------
# Baidu Qianfan / ERNIE
# ---------------------------------------------------------------------
@register_provider
class Baidu(BaseProvider):
    name = "baidu"
    default_base_url = "https://qianfan.baidubce.com/v2"
    default_model = "ernie-4.0-8k"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        payload = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
        }
        data = post_json(
            f"{self.base_url}/chat/completions", self._headers(), payload, self.timeout
        )
        content = ""
        choices = data.get("choices") or []
        if choices:
            content = choices[0].get("message", {}).get("content", "")
        else:
            content = data.get("result", "")
        usage = data.get("usage", {}) or {}
        p = usage.get("prompt_tokens", 0)
        c = usage.get("completion_tokens", 0)
        return ChatResponse(
            provider=self.name, model=model, content=content,
            prompt_tokens=p, completion_tokens=c, total_tokens=p + c,
            cost_usd=self._estimate_cost(p, c), raw=data,
        )


@register_provider
class Ernie(Baidu):
    name = "ernie"


# ---------------------------------------------------------------------
# Tencent Hunyuan (OpenAI-compatible endpoint)
# ---------------------------------------------------------------------
@register_provider
class Tencent(BaseProvider):
    name = "tencent"
    default_base_url = "https://api.hunyuan.cloud.tencent.com/v1"
    default_model = "hunyuan-pro"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        payload = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
        }
        data = post_json(
            f"{self.base_url}/chat/completions", self._headers(), payload, self.timeout
        )
        choices = data.get("choices") or []
        content = choices[0]["message"]["content"] if choices else ""
        usage = data.get("usage", {}) or {}
        p = usage.get("prompt_tokens", 0)
        c = usage.get("completion_tokens", 0)
        return ChatResponse(
            provider=self.name, model=model, content=content,
            prompt_tokens=p, completion_tokens=c, total_tokens=p + c,
            cost_usd=self._estimate_cost(p, c), raw=data,
        )


@register_provider
class Hunyuan(Tencent):
    name = "hunyuan"


# ---------------------------------------------------------------------
# Meta Llama API (openai-compatible on llama.developer.meta.com)
# ---------------------------------------------------------------------
@register_provider
class MetaLlama(BaseProvider):
    name = "meta"
    default_base_url = "https://api.llama.com/v1"
    default_model = "Llama-3.3-70B-Instruct"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        payload = {
            "model": model,
            "messages": [m.to_dict() for m in messages],
        }
        data = post_json(
            f"{self.base_url}/chat/completions", self._headers(), payload, self.timeout
        )
        choices = data.get("choices") or data.get("completion_message", {})
        if isinstance(choices, list) and choices:
            content = choices[0].get("message", {}).get("content", "")
        elif isinstance(choices, dict):
            content = choices.get("content", {}).get("text", "") if isinstance(choices.get("content"), dict) else choices.get("content", "")
        else:
            content = ""
        return ChatResponse(
            provider=self.name, model=model, content=content, raw=data,
        )


@register_provider
class Llama(MetaLlama):
    name = "llama"


# ---------------------------------------------------------------------
# Inflection AI (Pi API)
# ---------------------------------------------------------------------
@register_provider
class Inflection(BaseProvider):
    name = "inflection"
    default_base_url = "https://layercake.pubwestus3.inf7ks8.com/external/api/inference"
    default_model = "inflection_3_pi"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        context = [
            {"type": "Human" if m.role == "user" else "AI", "text": m.content}
            for m in messages if m.role != "system"
        ]
        payload = {"config": model, "context": context}
        data = post_json(self.base_url, self._headers(), payload, self.timeout)
        content = data.get("text", "") or data.get("output", "")
        return ChatResponse(
            provider=self.name, model=model, content=content, raw=data,
        )
