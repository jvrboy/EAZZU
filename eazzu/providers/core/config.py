"""Config manager: env vars + encrypted local config file for API keys."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

try:
    from cryptography.fernet import Fernet
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


DEFAULT_CONFIG_DIR = Path.home() / ".eazzu"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "keys.enc"
DEFAULT_KEY_FILE = DEFAULT_CONFIG_DIR / "master.key"


# Environment variable mapping — env names checked first
ENV_VAR_MAP = {
    # LLM
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
    "google": "GEMINI_API_KEY",
    "cohere": "COHERE_API_KEY",
    "mistral": "MISTRAL_API_KEY",
    "xai": "XAI_API_KEY",
    "meta": "META_API_KEY",
    "llama": "META_API_KEY",
    "ai21": "AI21_API_KEY",
    "writer": "WRITER_API_KEY",
    "aleph_alpha": "ALEPH_ALPHA_API_KEY",
    "deepseek": "DEEPSEEK_API_KEY",
    "dashscope": "DASHSCOPE_API_KEY",
    "qwen": "DASHSCOPE_API_KEY",
    "baidu": "BAIDU_API_KEY",
    "ernie": "BAIDU_API_KEY",
    "tencent": "TENCENT_API_KEY",
    "hunyuan": "TENCENT_API_KEY",
    "zhipu": "ZHIPU_API_KEY",
    "glm": "ZHIPU_API_KEY",
    "moonshot": "MOONSHOT_API_KEY",
    "kimi": "MOONSHOT_API_KEY",
    "minimax": "MINIMAX_API_KEY",
    "yi": "YI_API_KEY",
    "inflection": "INFLECTION_API_KEY",
    "upstage": "UPSTAGE_API_KEY",
    "reka": "REKA_API_KEY",
    # Cloud
    "aws_bedrock": "AWS_ACCESS_KEY_ID",
    "azure_openai": "AZURE_OPENAI_API_KEY",
    "vertex_ai": "GOOGLE_APPLICATION_CREDENTIALS",
    "watsonx": "WATSONX_API_KEY",
    "nvidia_nim": "NVIDIA_API_KEY",
    "cloudflare": "CLOUDFLARE_API_KEY",
    "oci": "OCI_API_KEY",
    # HuggingFace
    "huggingface": "HF_TOKEN",
    "huggingface_endpoint": "HF_TOKEN",
    # Freemodel.dev (serves both OpenAI and Anthropic-compatible routes)
    "freemodel": "FREEMODEL_API_KEY",
    "freemodel_codex": "FREEMODEL_API_KEY",
    # Aggregators
    "huggingface": "HF_API_KEY",
    "replicate": "REPLICATE_API_TOKEN",
    "together": "TOGETHER_API_KEY",
    "fireworks": "FIREWORKS_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "deepinfra": "DEEPINFRA_API_KEY",
    "perplexity": "PERPLEXITY_API_KEY",
    "lepton": "LEPTON_API_KEY",
    "novita": "NOVITA_API_KEY",
    "cerebras": "CEREBRAS_API_KEY",
    "sambanova": "SAMBANOVA_API_KEY",
    "anyscale": "ANYSCALE_API_KEY",
    "modal": "MODAL_API_KEY",
    "friendliai": "FRIENDLI_API_KEY",
    "kluster": "KLUSTER_API_KEY",
    # Audio
    "elevenlabs": "ELEVENLABS_API_KEY",
    "deepgram": "DEEPGRAM_API_KEY",
    "assemblyai": "ASSEMBLYAI_API_KEY",
    "playht": "PLAYHT_API_KEY",
    "resemble": "RESEMBLE_API_KEY",
    "google_speech": "GOOGLE_APPLICATION_CREDENTIALS",
    "aws_polly": "AWS_ACCESS_KEY_ID",
    "azure_speech": "AZURE_SPEECH_KEY",
    # Image/Video
    "stability": "STABILITY_API_KEY",
    "black_forest_labs": "BFL_API_KEY",
    "flux": "BFL_API_KEY",
    "runway": "RUNWAY_API_KEY",
    "pika": "PIKA_API_KEY",
    "leonardo": "LEONARDO_API_KEY",
    "fal": "FAL_KEY",
    "luma": "LUMA_API_KEY",
    "kling": "KLING_API_KEY",
    "midjourney": "MIDJOURNEY_API_KEY",
    # Search / embeddings
    "tavily": "TAVILY_API_KEY",
    "serper": "SERPER_API_KEY",
    "exa": "EXA_API_KEY",
    "bing": "BING_API_KEY",
    "brave": "BRAVE_API_KEY",
    "you": "YOU_API_KEY",
    "voyage": "VOYAGE_API_KEY",
    "jina": "JINA_API_KEY",
    "nomic": "NOMIC_API_KEY",
}


class ConfigManager:
    """Layered key resolution: explicit arg > env var > encrypted file."""

    def __init__(
        self,
        config_file: Optional[Path] = None,
        key_file: Optional[Path] = None,
        password: Optional[str] = None,
    ):
        self.config_file = Path(config_file or DEFAULT_CONFIG_FILE)
        self.key_file = Path(key_file or DEFAULT_KEY_FILE)
        self.password = password
        self._cache: dict[str, str] = {}
        self._loaded = False

    # ---------- Encryption ---------- #
    def _get_or_create_master_key(self) -> bytes:
        if not HAS_CRYPTO:
            raise RuntimeError("Install 'cryptography' to use encrypted config.")
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        if self.key_file.exists():
            return self.key_file.read_bytes()
        key = Fernet.generate_key()
        self.key_file.write_bytes(key)
        try:
            os.chmod(self.key_file, 0o600)
        except Exception:
            pass
        return key

    def _fernet(self) -> "Fernet":
        return Fernet(self._get_or_create_master_key())

    # ---------- Load / save ---------- #
    def load(self) -> dict[str, str]:
        if self._loaded:
            return self._cache
        if self.config_file.exists() and HAS_CRYPTO:
            try:
                raw = self.config_file.read_bytes()
                data = self._fernet().decrypt(raw)
                self._cache = json.loads(data.decode())
            except Exception:
                self._cache = {}
        self._loaded = True
        return self._cache

    def save(self) -> None:
        if not HAS_CRYPTO:
            raise RuntimeError("Install 'cryptography' to save encrypted config.")
        self.config_file.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps(self._cache).encode()
        enc = self._fernet().encrypt(data)
        self.config_file.write_bytes(enc)
        try:
            os.chmod(self.config_file, 0o600)
        except Exception:
            pass

    # ---------- Get / set ---------- #
    def get(self, provider: str, explicit: Optional[str] = None) -> Optional[str]:
        if explicit:
            return explicit
        # env vars
        env_name = ENV_VAR_MAP.get(provider.lower())
        if env_name and os.getenv(env_name):
            return os.getenv(env_name)
        # generic naming convention (e.g. OPENAI_API_KEY)
        generic = f"{provider.upper()}_API_KEY"
        if os.getenv(generic):
            return os.getenv(generic)
        # encrypted file
        self.load()
        return self._cache.get(provider.lower())

    def set(self, provider: str, api_key: str) -> None:
        """Set the key(s) for a provider. Accepts a single key or a list
        (comma/newline separated, or a JSON list string)."""
        self.load()
        # Keep as-is (caller decides if this replaces or not via add_key).
        self._cache[provider.lower()] = api_key
        self.save()

    def add_key(self, provider: str, api_key: str) -> int:
        """Append a key for a provider, returning the new total key count.

        If no key exists yet, this is equivalent to ``set``. If one or more
        keys already exist, the new key is appended (deduplicated)."""
        from eazzu.providers.router import _split_keys  # local import avoids cycle at import time
        self.load()
        prov = provider.lower()
        existing = _split_keys(self._cache.get(prov, ""))
        api_key = (api_key or "").strip().strip("\"'")
        if not api_key:
            return len(existing)
        if api_key in existing:
            return len(existing)
        existing.append(api_key)
        self._cache[prov] = ",".join(existing)
        self.save()
        return len(existing)

    def remove_key(self, provider: str, api_key_or_index) -> list[str]:
        """Remove a key (by value or 1-based index). Returns the remaining keys."""
        from eazzu.providers.router import _split_keys
        self.load()
        prov = provider.lower()
        existing = _split_keys(self._cache.get(prov, ""))
        if not existing:
            return []
        try:
            idx = int(api_key_or_index) - 1
            if 0 <= idx < len(existing):
                existing.pop(idx)
        except (TypeError, ValueError):
            val = (api_key_or_index or "").strip().strip("\"'")
            existing = [k for k in existing if k != val]
        if existing:
            self._cache[prov] = ",".join(existing)
        else:
            self._cache.pop(prov, None)
        self.save()
        return existing

    def list_keys(self, provider: str) -> list[str]:
        """Return all keys stored for a provider (from env + encrypted)."""
        from eazzu.providers.router import _split_keys
        keys: list[str] = []
        env_name = ENV_VAR_MAP.get(provider.lower())
        for candidate_env in (env_name, f"{provider.upper()}_API_KEY"):
            if candidate_env and os.environ.get(candidate_env):
                keys.extend(_split_keys(os.environ[candidate_env]))
        self.load()
        v = self._cache.get(provider.lower())
        if v:
            keys.extend(_split_keys(v))
        seen = set()
        out = []
        for k in keys:
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    def delete(self, provider: str) -> None:
        self.load()
        self._cache.pop(provider.lower(), None)
        self.save()

    def list_stored(self) -> list[str]:
        self.load()
        return sorted(self._cache.keys())
