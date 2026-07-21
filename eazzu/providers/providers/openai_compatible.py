"""
OpenAI-compatible base — used by OpenAI itself and many providers whose API
mirrors OpenAI (Groq, Together, Fireworks, DeepSeek, Moonshot, xAI, OpenRouter,
Deepinfra, Perplexity, Cerebras, SambaNova, Anyscale, FriendliAI, Novita,
Lepton, Kluster, Mistral, Zhipu, Yi, MiniMax, Qwen, NVIDIA NIM, etc.).
"""
from __future__ import annotations

import json
import time
from typing import Iterator

import requests

from eazzu.providers.core.base_provider import BaseProvider, ChatMessage, ChatResponse
from eazzu.providers.core.http import post_json, stream_sse
from eazzu.providers.core.registry import register_provider


class OpenAICompatibleProvider(BaseProvider):
    """Generic OpenAI-compatible chat/completions client."""

    default_base_url = "https://api.openai.com/v1"
    default_model = "gpt-4o-mini"
    endpoint_path = "/chat/completions"
    price_in_per_1k = 0.0
    price_out_per_1k = 0.0

    def _chat_impl(self, messages: list[ChatMessage], model: str, **kwargs) -> ChatResponse:
        url = f"{self.base_url.rstrip('/')}{self.endpoint_path}"
        payload = {
            "model": model,
            "messages": self._messages_to_openai_format(messages),
            **{k: v for k, v in kwargs.items() if v is not None},
        }
        data = post_json(url, self._headers(), payload, self.timeout)
        choices = data.get("choices") or []
        content = ""
        if choices:
            content = choices[0].get("message", {}).get("content", "") or ""
        usage = data.get("usage", {}) or {}
        p = usage.get("prompt_tokens", 0) or 0
        c = usage.get("completion_tokens", 0) or 0
        return ChatResponse(
            provider=self.name,
            model=model,
            content=content,
            prompt_tokens=p,
            completion_tokens=c,
            total_tokens=usage.get("total_tokens", p + c),
            cost_usd=self._estimate_cost(p, c),
            raw=data,
        )

    def _stream_impl(self, messages: list[ChatMessage], model: str, **kwargs) -> Iterator[str]:
        url = f"{self.base_url.rstrip('/')}{self.endpoint_path}"
        payload = {
            "model": model,
            "messages": self._messages_to_openai_format(messages),
            "stream": True,
            **{k: v for k, v in kwargs.items() if v is not None},
        }
        for chunk in stream_sse(url, self._headers(), payload, self.timeout):
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            content = delta.get("content")
            if content:
                yield content


# =====================================================================
# Concrete OpenAI-compatible providers
# =====================================================================

@register_provider
class OpenAI(OpenAICompatibleProvider):
    name = "openai"
    default_base_url = "https://api.openai.com/v1"
    default_model = "gpt-4o-mini"
    price_in_per_1k = 0.00015
    price_out_per_1k = 0.0006


@register_provider
class DeepSeek(OpenAICompatibleProvider):
    name = "deepseek"
    default_base_url = "https://api.deepseek.com/v1"
    default_model = "deepseek-chat"
    price_in_per_1k = 0.00014
    price_out_per_1k = 0.00028


@register_provider
class Groq(OpenAICompatibleProvider):
    name = "groq"
    default_base_url = "https://api.groq.com/openai/v1"
    default_model = "llama-3.3-70b-versatile"
    price_in_per_1k = 0.00059
    price_out_per_1k = 0.00079


@register_provider
class Together(OpenAICompatibleProvider):
    name = "together"
    default_base_url = "https://api.together.xyz/v1"
    default_model = "meta-llama/Llama-3.3-70B-Instruct-Turbo"


@register_provider
class Fireworks(OpenAICompatibleProvider):
    name = "fireworks"
    default_base_url = "https://api.fireworks.ai/inference/v1"
    default_model = "accounts/fireworks/models/llama-v3p3-70b-instruct"


@register_provider
class Mistral(OpenAICompatibleProvider):
    name = "mistral"
    default_base_url = "https://api.mistral.ai/v1"
    default_model = "mistral-large-latest"
    price_in_per_1k = 0.002
    price_out_per_1k = 0.006


@register_provider
class XAI(OpenAICompatibleProvider):
    name = "xai"
    default_base_url = "https://api.x.ai/v1"
    default_model = "grok-2-latest"


@register_provider
class OpenRouter(OpenAICompatibleProvider):
    name = "openrouter"
    default_base_url = "https://openrouter.ai/api/v1"
    default_model = "openai/gpt-4o-mini"


@register_provider
class DeepInfra(OpenAICompatibleProvider):
    name = "deepinfra"
    default_base_url = "https://api.deepinfra.com/v1/openai"
    default_model = "meta-llama/Meta-Llama-3.1-70B-Instruct"


@register_provider
class Perplexity(OpenAICompatibleProvider):
    name = "perplexity"
    default_base_url = "https://api.perplexity.ai"
    default_model = "sonar"
    category = "search"


@register_provider
class Cerebras(OpenAICompatibleProvider):
    name = "cerebras"
    default_base_url = "https://api.cerebras.ai/v1"
    default_model = "llama3.3-70b"


@register_provider
class SambaNova(OpenAICompatibleProvider):
    name = "sambanova"
    default_base_url = "https://api.sambanova.ai/v1"
    default_model = "Meta-Llama-3.3-70B-Instruct"


@register_provider
class Anyscale(OpenAICompatibleProvider):
    name = "anyscale"
    default_base_url = "https://api.endpoints.anyscale.com/v1"
    default_model = "meta-llama/Meta-Llama-3-70B-Instruct"


@register_provider
class FriendliAI(OpenAICompatibleProvider):
    name = "friendliai"
    default_base_url = "https://inference.friendli.ai/v1"
    default_model = "meta-llama-3.1-70b-instruct"


@register_provider
class Novita(OpenAICompatibleProvider):
    name = "novita"
    default_base_url = "https://api.novita.ai/v3/openai"
    default_model = "meta-llama/llama-3.1-70b-instruct"


@register_provider
class Lepton(OpenAICompatibleProvider):
    name = "lepton"
    default_base_url = "https://api.lepton.ai/api/v1"
    default_model = "llama3-70b"


@register_provider
class Kluster(OpenAICompatibleProvider):
    name = "kluster"
    default_base_url = "https://api.kluster.ai/v1"
    default_model = "klusterai/Meta-Llama-3.1-405B-Instruct-Turbo"


@register_provider
class Moonshot(OpenAICompatibleProvider):
    name = "moonshot"
    default_base_url = "https://api.moonshot.cn/v1"
    default_model = "moonshot-v1-8k"


@register_provider
class Zhipu(OpenAICompatibleProvider):
    name = "zhipu"
    default_base_url = "https://open.bigmodel.cn/api/paas/v4"
    default_model = "glm-4-plus"


@register_provider
class Yi(OpenAICompatibleProvider):
    name = "yi"
    default_base_url = "https://api.lingyiwanwu.com/v1"
    default_model = "yi-large"


@register_provider
class MiniMax(OpenAICompatibleProvider):
    name = "minimax"
    default_base_url = "https://api.minimax.chat/v1"
    default_model = "abab6.5s-chat"


@register_provider
class Qwen(OpenAICompatibleProvider):
    """Alibaba DashScope in OpenAI-compatible mode."""
    name = "qwen"
    default_base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    default_model = "qwen-plus"


@register_provider
class NvidiaNIM(OpenAICompatibleProvider):
    name = "nvidia_nim"
    default_base_url = "https://integrate.api.nvidia.com/v1"
    default_model = "meta/llama-3.3-70b-instruct"


@register_provider
class Upstage(OpenAICompatibleProvider):
    name = "upstage"
    default_base_url = "https://api.upstage.ai/v1/solar"
    default_model = "solar-pro"


@register_provider
class Reka(OpenAICompatibleProvider):
    name = "reka"
    default_base_url = "https://api.reka.ai/v1"
    default_model = "reka-core"
    endpoint_path = "/chat"


@register_provider
class Writer(OpenAICompatibleProvider):
    name = "writer"
    default_base_url = "https://api.writer.com/v1"
    default_model = "palmyra-x-004"


@register_provider
class AzureOpenAI(OpenAICompatibleProvider):
    default_base_url = ""
    default_model = "gpt-4o"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        deployment = self.extra_config.get("deployment") or model
        api_version = self.extra_config.get("api_version", "2024-06-01")
        url = (
            f"{self.base_url.rstrip('/')}/openai/deployments/{deployment}"
            f"/chat/completions?api-version={api_version}"
        )
        headers = {"Content-Type": "application/json", "api-key": self.api_key or ""}
        headers.update(self.extra_headers)
        payload = {
            "messages": self._messages_to_openai_format(messages),
            **{k: v for k, v in kwargs.items() if v is not None},
        }
        data = post_json(url, headers, payload, self.timeout)
        choices = data.get("choices") or []
        content = choices[0]["message"]["content"] if choices else ""
        usage = data.get("usage", {}) or {}
        p = usage.get("prompt_tokens", 0)
        c = usage.get("completion_tokens", 0)
        return ChatResponse(
            provider=self.name, model=deployment, content=content,
            prompt_tokens=p, completion_tokens=c,
            total_tokens=usage.get("total_tokens", p + c),
            cost_usd=self._estimate_cost(p, c), raw=data,
        )


@register_provider
class FreemodelOpenAI(OpenAICompatibleProvider):
    """freemodel.dev in OpenAI-compatible mode — serves GPT-5.5, o3, gpt-4o, etc.
    Use with a freemodel.dev API key. Base URL: https://api.freemodel.dev/v1
    """
    name = "freemodel"
    default_base_url = "https://api.freemodel.dev/v1"
    default_model = "gpt-5.5"


@register_provider
class FreemodelCodex(OpenAICompatibleProvider):
    """freemodel.dev OpenAI-Responses endpoint for Codex CLI compatibility
    (model_provider = 'freemodel' with wire_api = 'responses' in the Codex config).
    For chat we still use /chat/completions.
    """
    name = "freemodel_codex"
    default_base_url = "https://api.freemodel.dev/v1"
    default_model = "gpt-5.5"
