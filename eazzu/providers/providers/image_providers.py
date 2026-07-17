"""Image / video / multimodal generation providers."""
from __future__ import annotations

import time

from eazzu.providers.core.base_provider import BaseProvider, ChatResponse
from eazzu.providers.core.http import post_json, get_json
from eazzu.providers.core.registry import register_provider


@register_provider
class Stability(BaseProvider):
    name = "stability"
    default_base_url = "https://api.stability.ai/v2beta/stable-image/generate/core"
    default_model = "core"
    category = "image"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        import requests
        prompt = "\n".join(m.content for m in messages if m.role != "system")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }
        r = requests.post(
            self.base_url,
            headers=headers,
            files={"prompt": (None, prompt)},
            data={"output_format": kwargs.pop("output_format", "png")},
            timeout=self.timeout,
        )
        r.raise_for_status()
        data = r.json()
        return ChatResponse(
            provider=self.name, model=model,
            content=f"<image_base64:{len(data.get('image',''))}bytes>",
            raw=data,
        )


@register_provider
class BlackForestLabs(BaseProvider):
    name = "black_forest_labs"
    default_base_url = "https://api.bfl.ai/v1"
    default_model = "flux-pro-1.1"
    category = "image"

    def _headers(self):
        return {"x-key": self.api_key or "", "Content-Type": "application/json"}

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        prompt = "\n".join(m.content for m in messages if m.role != "system")
        create = post_json(
            f"{self.base_url}/{model}", self._headers(),
            {"prompt": prompt, **{k: v for k, v in kwargs.items() if v is not None}},
            self.timeout,
        )
        pid = create.get("id")
        for _ in range(60):
            time.sleep(1)
            data = get_json(f"{self.base_url}/get_result?id={pid}", self._headers())
            if data.get("status") in ("Ready", "Error"):
                break
        return ChatResponse(
            provider=self.name, model=model,
            content=data.get("result", {}).get("sample", "") if isinstance(data.get("result"), dict) else str(data.get("result", "")),
            raw=data,
        )


@register_provider
class Flux(BlackForestLabs):
    name = "flux"


@register_provider
class Runway(BaseProvider):
    name = "runway"
    default_base_url = "https://api.dev.runwayml.com/v1"
    default_model = "gen4_turbo"
    category = "image"

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-Runway-Version": "2024-11-06",
            "Content-Type": "application/json",
        }

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        prompt = "\n".join(m.content for m in messages if m.role != "system")
        payload = {
            "model": model,
            "promptText": prompt,
            **{k: v for k, v in kwargs.items() if v is not None},
        }
        data = post_json(f"{self.base_url}/image_to_video", self._headers(), payload, self.timeout)
        return ChatResponse(
            provider=self.name, model=model, content=data.get("id", "") or str(data), raw=data,
        )


@register_provider
class Pika(BaseProvider):
    name = "pika"
    default_base_url = "https://api.pika.art/v1"
    default_model = "pika-2.0"
    category = "image"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        prompt = "\n".join(m.content for m in messages if m.role != "system")
        data = post_json(
            f"{self.base_url}/generate",
            self._headers(), {"prompt": prompt, "model": model}, self.timeout,
        )
        return ChatResponse(provider=self.name, model=model, content=str(data.get("video_url", data)), raw=data)


@register_provider
class Leonardo(BaseProvider):
    name = "leonardo"
    default_base_url = "https://cloud.leonardo.ai/api/rest/v1"
    default_model = "leonardo-phoenix"
    category = "image"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        prompt = "\n".join(m.content for m in messages if m.role != "system")
        payload = {
            "prompt": prompt,
            "modelId": kwargs.pop("model_id", "b24e16ff-06e3-43eb-8d33-4416c2d75876"),
            "num_images": kwargs.pop("num_images", 1),
        }
        data = post_json(
            f"{self.base_url}/generations", self._headers(), payload, self.timeout
        )
        return ChatResponse(
            provider=self.name, model=model,
            content=str(data.get("sdGenerationJob", {}).get("generationId", "")) or str(data),
            raw=data,
        )


@register_provider
class Fal(BaseProvider):
    name = "fal"
    default_base_url = "https://fal.run"
    default_model = "fal-ai/flux/dev"
    category = "image"

    def _headers(self):
        return {"Authorization": f"Key {self.api_key}", "Content-Type": "application/json"}

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        prompt = "\n".join(m.content for m in messages if m.role != "system")
        data = post_json(
            f"{self.base_url}/{model}",
            self._headers(),
            {"prompt": prompt, **{k: v for k, v in kwargs.items() if v is not None}},
            self.timeout,
        )
        imgs = data.get("images") or []
        content = imgs[0].get("url") if imgs and isinstance(imgs[0], dict) else str(data)
        return ChatResponse(provider=self.name, model=model, content=str(content), raw=data)


@register_provider
class Luma(BaseProvider):
    name = "luma"
    default_base_url = "https://api.lumalabs.ai/dream-machine/v1"
    default_model = "ray-2"
    category = "image"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        prompt = "\n".join(m.content for m in messages if m.role != "system")
        data = post_json(
            f"{self.base_url}/generations",
            self._headers(),
            {"prompt": prompt, "model": model},
            self.timeout,
        )
        return ChatResponse(provider=self.name, model=model, content=str(data.get("id", data)), raw=data)


@register_provider
class Kling(BaseProvider):
    name = "kling"
    default_base_url = "https://api.klingai.com/v1"
    default_model = "kling-v1"
    category = "image"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        prompt = "\n".join(m.content for m in messages if m.role != "system")
        data = post_json(
            f"{self.base_url}/videos/text2video",
            self._headers(),
            {"prompt": prompt, "model_name": model},
            self.timeout,
        )
        return ChatResponse(provider=self.name, model=model, content=str(data), raw=data)


@register_provider
class Midjourney(BaseProvider):
    """Unofficial/proxy — user supplies base_url of proxy service."""
    name = "midjourney"
    default_base_url = ""
    default_model = "v6"
    category = "image"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        if not self.base_url:
            raise RuntimeError("Midjourney has no official public API; set base_url to your proxy.")
        prompt = "\n".join(m.content for m in messages if m.role != "system")
        data = post_json(
            f"{self.base_url.rstrip('/')}/imagine",
            self._headers(),
            {"prompt": prompt, "version": model},
            self.timeout,
        )
        return ChatResponse(provider=self.name, model=model, content=str(data), raw=data)
