"""Cloud hyperscaler providers: AWS Bedrock, Vertex AI, IBM watsonx,
Cloudflare Workers AI, Oracle OCI Generative AI.
"""
from __future__ import annotations

import json

from eazzu.providers.core.base_provider import BaseProvider, ChatResponse
from eazzu.providers.core.http import post_json
from eazzu.providers.core.registry import register_provider


# ---------------------------------------------------------------------
# AWS Bedrock — uses boto3 lazily
# ---------------------------------------------------------------------
@register_provider
class AWSBedrock(BaseProvider):
    name = "aws_bedrock"
    default_model = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    default_base_url = ""

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        try:
            import boto3
        except ImportError as e:
            raise RuntimeError("pip install boto3 to use AWS Bedrock.") from e
        region = self.extra_config.get("region", "us-east-1")
        client = boto3.client("bedrock-runtime", region_name=region)
        # Bedrock Converse API (multi-model unified)
        converse_msgs = []
        system = []
        for m in messages:
            if m.role == "system":
                system.append({"text": m.content})
            else:
                converse_msgs.append({
                    "role": "user" if m.role == "user" else "assistant",
                    "content": [{"text": m.content}],
                })
        kwargs_boto = dict(modelId=model, messages=converse_msgs)
        if system:
            kwargs_boto["system"] = system
        resp = client.converse(**kwargs_boto)
        content = ""
        for block in resp.get("output", {}).get("message", {}).get("content", []):
            content += block.get("text", "")
        usage = resp.get("usage", {}) or {}
        p = usage.get("inputTokens", 0)
        c = usage.get("outputTokens", 0)
        return ChatResponse(
            provider=self.name, model=model, content=content,
            prompt_tokens=p, completion_tokens=c, total_tokens=p + c,
            raw=resp,
        )


# ---------------------------------------------------------------------
# Google Vertex AI (uses google-auth for tokens)
# ---------------------------------------------------------------------
@register_provider
class VertexAI(BaseProvider):
    name = "vertex_ai"
    default_model = "gemini-1.5-pro-002"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        try:
            import google.auth
            from google.auth.transport.requests import Request
        except ImportError as e:
            raise RuntimeError("pip install google-auth to use Vertex AI.") from e
        project = self.extra_config.get("project") or self.extra_config.get("project_id")
        location = self.extra_config.get("location", "us-central1")
        if not project:
            raise RuntimeError("Vertex AI requires project id (pass project=<id>).")
        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        creds.refresh(Request())
        url = (
            f"https://{location}-aiplatform.googleapis.com/v1/projects/{project}"
            f"/locations/{location}/publishers/google/models/{model}:generateContent"
        )
        contents = []
        for m in messages:
            if m.role == "system":
                continue
            role = "user" if m.role == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m.content}]})
        headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
        }
        data = post_json(url, headers, {"contents": contents}, self.timeout)
        content = ""
        for cand in data.get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                content += part.get("text", "")
        um = data.get("usageMetadata", {}) or {}
        return ChatResponse(
            provider=self.name, model=model, content=content,
            prompt_tokens=um.get("promptTokenCount", 0),
            completion_tokens=um.get("candidatesTokenCount", 0),
            total_tokens=um.get("totalTokenCount", 0),
            raw=data,
        )


# ---------------------------------------------------------------------
# IBM watsonx.ai
# ---------------------------------------------------------------------
@register_provider
class WatsonX(BaseProvider):
    name = "watsonx"
    default_base_url = "https://us-south.ml.cloud.ibm.com"
    default_model = "meta-llama/llama-3-3-70b-instruct"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        project_id = self.extra_config.get("project_id")
        if not project_id:
            raise RuntimeError("watsonx requires project_id=<id>")
        url = f"{self.base_url}/ml/v1/text/chat?version=2024-05-01"
        payload = {
            "model_id": model,
            "project_id": project_id,
            "messages": [m.to_dict() for m in messages],
        }
        data = post_json(url, self._headers(), payload, self.timeout)
        choices = data.get("choices") or []
        content = choices[0]["message"]["content"] if choices else ""
        usage = data.get("usage", {}) or {}
        p = usage.get("prompt_tokens", 0)
        c = usage.get("completion_tokens", 0)
        return ChatResponse(
            provider=self.name, model=model, content=content,
            prompt_tokens=p, completion_tokens=c, total_tokens=p + c, raw=data,
        )


# ---------------------------------------------------------------------
# Cloudflare Workers AI
# ---------------------------------------------------------------------
@register_provider
class Cloudflare(BaseProvider):
    name = "cloudflare"
    default_base_url = "https://api.cloudflare.com/client/v4"
    default_model = "@cf/meta/llama-3.3-70b-instruct-fp8-fast"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        account_id = self.extra_config.get("account_id")
        if not account_id:
            raise RuntimeError("Cloudflare Workers AI requires account_id=<id>")
        url = f"{self.base_url}/accounts/{account_id}/ai/run/{model}"
        payload = {"messages": [m.to_dict() for m in messages]}
        data = post_json(url, self._headers(), payload, self.timeout)
        result = data.get("result", {})
        content = result.get("response", "") if isinstance(result, dict) else str(result)
        return ChatResponse(
            provider=self.name, model=model, content=content, raw=data,
        )


# ---------------------------------------------------------------------
# Oracle OCI Generative AI (basic REST wrapper)
# ---------------------------------------------------------------------
@register_provider
class OracleOCI(BaseProvider):
    name = "oci"
    default_model = "cohere.command-r-plus"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        try:
            import oci
        except ImportError as e:
            raise RuntimeError("pip install oci to use Oracle OCI Generative AI.") from e
        compartment_id = self.extra_config.get("compartment_id")
        if not compartment_id:
            raise RuntimeError("OCI requires compartment_id=<id>")
        config = oci.config.from_file(
            self.extra_config.get("config_path", "~/.oci/config"),
            self.extra_config.get("profile", "DEFAULT"),
        )
        endpoint = self.extra_config.get(
            "endpoint", "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"
        )
        client = oci.generative_ai_inference.GenerativeAiInferenceClient(
            config=config, service_endpoint=endpoint
        )
        chat_details = oci.generative_ai_inference.models.ChatDetails(
            compartment_id=compartment_id,
            serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(model_id=model),
            chat_request=oci.generative_ai_inference.models.GenericChatRequest(
                messages=[
                    {"role": m.role.upper(),
                     "content": [{"type": "TEXT", "text": m.content}]}
                    for m in messages
                ],
                api_format="GENERIC",
            ),
        )
        resp = client.chat(chat_details)
        content = ""
        try:
            content = resp.data.chat_response.choices[0].message.content[0].text
        except Exception:
            content = str(resp.data)
        return ChatResponse(
            provider=self.name, model=model, content=content, raw={"status": "ok"},
        )
