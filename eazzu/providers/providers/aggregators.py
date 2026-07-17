"""Aggregators / inference platforms with non-OpenAI shapes:
Hugging Face, Replicate, Modal.
(Groq/Together/Fireworks/etc. are already registered in openai_compatible.py)
"""
from __future__ import annotations

import time

from eazzu.providers.core.base_provider import BaseProvider, ChatResponse
from eazzu.providers.core.http import post_json, get_json
from eazzu.providers.core.registry import register_provider


@register_provider
class HuggingFace(BaseProvider):
    name = "huggingface"
    default_base_url = "https://api-inference.huggingface.co/models"
    default_model = "meta-llama/Meta-Llama-3-8B-Instruct"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)
        url = f"{self.base_url}/{model}"
        payload = {
            "inputs": prompt,
            "parameters": {
                "max_new_tokens": kwargs.pop("max_tokens", 512),
                **{k: v for k, v in kwargs.items() if v is not None},
            },
        }
        data = post_json(url, self._headers(), payload, self.timeout)
        content = ""
        if isinstance(data, list) and data:
            content = data[0].get("generated_text", "") if isinstance(data[0], dict) else str(data[0])
        elif isinstance(data, dict):
            content = data.get("generated_text", "") or str(data)
        return ChatResponse(
            provider=self.name, model=model, content=content, raw={"data": data},
        )


@register_provider
class Replicate(BaseProvider):
    name = "replicate"
    default_base_url = "https://api.replicate.com/v1"
    default_model = "meta/meta-llama-3-70b-instruct"

    def _headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Token {self.api_key}",
        }

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        prompt = "\n".join(f"{m.role}: {m.content}" for m in messages)
        payload = {"input": {"prompt": prompt, **{k: v for k, v in kwargs.items() if v is not None}}}
        create = post_json(
            f"{self.base_url}/models/{model}/predictions",
            self._headers(), payload, self.timeout,
        )
        pred_id = create.get("id")
        url = create.get("urls", {}).get("get")
        # Poll
        for _ in range(60):
            time.sleep(1)
            data = get_json(url, self._headers(), timeout=self.timeout)
            if data.get("status") in ("succeeded", "failed", "canceled"):
                break
        output = data.get("output", "")
        if isinstance(output, list):
            output = "".join(output)
        return ChatResponse(
            provider=self.name, model=model, content=str(output), raw=data,
        )


@register_provider
class Modal(BaseProvider):
    """Custom Modal deployed endpoints — user supplies base_url pointing at their function."""
    name = "modal"
    default_base_url = ""  # user-provided
    default_model = "custom"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        if not self.base_url:
            raise RuntimeError("Modal provider needs base_url of the deployed endpoint.")
        payload = {
            "messages": [m.to_dict() for m in messages],
            "model": model,
            **{k: v for k, v in kwargs.items() if v is not None},
        }
        data = post_json(self.base_url, self._headers(), payload, self.timeout)
        content = data.get("content") or data.get("output") or str(data)
        return ChatResponse(
            provider=self.name, model=model, content=str(content), raw=data,
        )
