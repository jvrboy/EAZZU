"""Speech / audio / voice APIs — TTS + STT.
Non-chat, so .chat() is overloaded to route to the appropriate action.
"""
from __future__ import annotations

import base64

import requests

from eazzu.providers.core.base_provider import BaseProvider, ChatResponse
from eazzu.providers.core.http import post_json
from eazzu.providers.core.registry import register_provider


# =============================
# ElevenLabs (TTS)
# =============================
@register_provider
class ElevenLabs(BaseProvider):
    name = "elevenlabs"
    default_base_url = "https://api.elevenlabs.io/v1"
    default_model = "eleven_multilingual_v2"
    category = "audio"

    def _headers(self) -> dict:
        return {"xi-api-key": self.api_key or "", "Content-Type": "application/json"}

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        voice_id = kwargs.pop("voice_id", "21m00Tcm4TlvDq8ikWAM")
        text = "\n".join(m.content for m in messages if m.role != "system")
        url = f"{self.base_url}/text-to-speech/{voice_id}"
        payload = {"text": text, "model_id": model}
        r = requests.post(url, headers=self._headers(), json=payload, timeout=self.timeout)
        r.raise_for_status()
        audio_b64 = base64.b64encode(r.content).decode()
        return ChatResponse(
            provider=self.name, model=model, content=f"<audio_base64:{len(audio_b64)}bytes>",
            raw={"audio_base64": audio_b64, "voice_id": voice_id},
        )


# =============================
# Deepgram (STT)
# =============================
@register_provider
class Deepgram(BaseProvider):
    name = "deepgram"
    default_base_url = "https://api.deepgram.com/v1"
    default_model = "nova-3"
    category = "audio"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        audio_url = kwargs.pop("audio_url", None) or (messages[0].content if messages else None)
        if not audio_url:
            raise RuntimeError("Deepgram needs audio_url or first message content as URL.")
        url = f"{self.base_url}/listen?model={model}"
        headers = {"Authorization": f"Token {self.api_key}", "Content-Type": "application/json"}
        data = post_json(url, headers, {"url": audio_url}, self.timeout)
        transcript = ""
        try:
            transcript = data["results"]["channels"][0]["alternatives"][0]["transcript"]
        except Exception:
            pass
        return ChatResponse(provider=self.name, model=model, content=transcript, raw=data)


# =============================
# AssemblyAI (STT)
# =============================
@register_provider
class AssemblyAI(BaseProvider):
    name = "assemblyai"
    default_base_url = "https://api.assemblyai.com/v2"
    default_model = "best"
    category = "audio"

    def _headers(self):
        return {"authorization": self.api_key or "", "content-type": "application/json"}

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        import time
        audio_url = kwargs.pop("audio_url", None) or (messages[0].content if messages else None)
        create = post_json(
            f"{self.base_url}/transcript",
            self._headers(),
            {"audio_url": audio_url, "speech_model": model},
            self.timeout,
        )
        tid = create["id"]
        for _ in range(90):
            time.sleep(2)
            r = requests.get(f"{self.base_url}/transcript/{tid}", headers=self._headers(), timeout=self.timeout)
            data = r.json()
            if data.get("status") in ("completed", "error"):
                break
        return ChatResponse(
            provider=self.name, model=model, content=data.get("text", ""), raw=data,
        )


# =============================
# Play.ht (TTS)
# =============================
@register_provider
class PlayHT(BaseProvider):
    name = "playht"
    default_base_url = "https://api.play.ht/api/v2"
    default_model = "PlayHT2.0"
    category = "audio"

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "X-USER-ID": self.extra_config.get("user_id", ""),
            "Content-Type": "application/json",
        }

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        text = "\n".join(m.content for m in messages if m.role != "system")
        payload = {
            "text": text,
            "voice_engine": model,
            "voice": kwargs.pop("voice", "s3://voice-cloning-zero-shot/…/default.json"),
        }
        data = post_json(f"{self.base_url}/tts", self._headers(), payload, self.timeout)
        return ChatResponse(
            provider=self.name, model=model,
            content=data.get("audioUrl") or str(data), raw=data,
        )


# =============================
# Resemble AI (TTS)
# =============================
@register_provider
class Resemble(BaseProvider):
    name = "resemble"
    default_base_url = "https://f.cluster.resemble.ai/synthesize"
    default_model = "resemble-tts"
    category = "audio"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        text = "\n".join(m.content for m in messages if m.role != "system")
        payload = {
            "voice_uuid": kwargs.pop("voice_uuid", ""),
            "data": text,
        }
        data = post_json(self.base_url, self._headers(), payload, self.timeout)
        return ChatResponse(
            provider=self.name, model=model,
            content=data.get("audio_content_url") or str(data), raw=data,
        )


# =============================
# Google Cloud Speech
# =============================
@register_provider
class GoogleSpeech(BaseProvider):
    name = "google_speech"
    default_model = "latest_long"
    category = "audio"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        try:
            from google.cloud import speech
        except ImportError as e:
            raise RuntimeError("pip install google-cloud-speech") from e
        client = speech.SpeechClient()
        audio_uri = kwargs.pop("gcs_uri", None) or (messages[0].content if messages else None)
        audio = speech.RecognitionAudio(uri=audio_uri)
        config = speech.RecognitionConfig(
            language_code=kwargs.pop("language_code", "en-US"),
            model=model,
        )
        resp = client.recognize(config=config, audio=audio)
        transcript = " ".join(r.alternatives[0].transcript for r in resp.results if r.alternatives)
        return ChatResponse(provider=self.name, model=model, content=transcript, raw={"ok": True})


# =============================
# AWS Polly (TTS) / Transcribe (STT) — via boto3
# =============================
@register_provider
class AWSPolly(BaseProvider):
    name = "aws_polly"
    default_model = "neural"
    category = "audio"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        try:
            import boto3
        except ImportError as e:
            raise RuntimeError("pip install boto3") from e
        polly = boto3.client("polly", region_name=self.extra_config.get("region", "us-east-1"))
        text = "\n".join(m.content for m in messages if m.role != "system")
        resp = polly.synthesize_speech(
            Text=text,
            OutputFormat=kwargs.pop("output_format", "mp3"),
            VoiceId=kwargs.pop("voice_id", "Joanna"),
            Engine=model,
        )
        audio = resp["AudioStream"].read()
        b64 = base64.b64encode(audio).decode()
        return ChatResponse(
            provider=self.name, model=model,
            content=f"<audio_base64:{len(b64)}bytes>",
            raw={"audio_base64": b64},
        )


# =============================
# Azure AI Speech
# =============================
@register_provider
class AzureSpeech(BaseProvider):
    name = "azure_speech"
    default_model = "en-US-JennyNeural"
    category = "audio"

    def _chat_impl(self, messages, model, **kwargs) -> ChatResponse:
        region = self.extra_config.get("region", "eastus")
        url = f"https://{region}.tts.speech.microsoft.com/cognitiveservices/v1"
        text = "\n".join(m.content for m in messages if m.role != "system")
        ssml = f"""<speak version='1.0' xml:lang='en-US'>
          <voice name='{model}'>{text}</voice></speak>"""
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key or "",
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": kwargs.pop("format", "audio-16khz-32kbitrate-mono-mp3"),
        }
        r = requests.post(url, headers=headers, data=ssml.encode("utf-8"), timeout=self.timeout)
        r.raise_for_status()
        b64 = base64.b64encode(r.content).decode()
        return ChatResponse(
            provider=self.name, model=model,
            content=f"<audio_base64:{len(b64)}bytes>",
            raw={"audio_base64": b64},
        )
