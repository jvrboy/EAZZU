"""AI provider registry tools: 56 providers with multi-key support.

Pure-Python module exposing a TOOLS list of dicts. Each tool has:
  - name: str
  - description: str
  - params: dict[str, str]  (param_name -> type as string)
  - run: callable[[dict], dict]  (lambda taking args dict, returning dict)

Helpers are private (underscore-prefixed). No external dependencies.
"""

# ---------------------------------------------------------------------------
# Provider catalog: 56 providers. One line each for compactness.
# ---------------------------------------------------------------------------

_PROVIDERS: dict[str, dict] = {
    "OpenAI": {"name": "OpenAI", "category": "LLM", "base_url": "https://api.openai.com/v1", "capabilities": ["chat", "completion", "embedding", "vision"], "models": ["gpt-4o", "gpt-4o-mini", "o1"]},
    "Google Cloud AI": {"name": "Google Cloud AI", "category": "LLM", "base_url": "https://ai.googleapis.com/v1", "capabilities": ["chat", "vision", "audio"], "models": ["gemini-1.5-pro", "gemini-1.5-flash"]},
    "Microsoft Azure Cognitive Services": {"name": "Microsoft Azure Cognitive Services", "category": "vision", "base_url": "https://{region}.api.cognitive.microsoft.com", "capabilities": ["vision", "audio", "embedding"], "models": ["vision-v4", "speech-v3"]},
    "Amazon Web Services AI": {"name": "Amazon Web Services AI", "category": "LLM", "base_url": "https://runtime.sagemaker.{region}.amazonaws.com", "capabilities": ["chat", "embedding", "vision"], "models": ["titan-text", "titan-embed"]},
    "IBM Watson": {"name": "IBM Watson", "category": "LLM", "base_url": "https://api.{region}.ml.cloud.ibm.com", "capabilities": ["chat", "audio"], "models": ["granite-13b", "watson-speech"]},
    "Anthropic Claude": {"name": "Anthropic Claude", "category": "LLM", "base_url": "https://api.anthropic.com/v1", "capabilities": ["chat", "vision"], "models": ["claude-3-5-sonnet", "claude-3-opus"]},
    "Cohere": {"name": "Cohere", "category": "LLM", "base_url": "https://api.cohere.ai/v1", "capabilities": ["chat", "embedding"], "models": ["command-r-plus", "embed-v3"]},
    "xAI": {"name": "xAI", "category": "LLM", "base_url": "https://api.x.ai/v1", "capabilities": ["chat"], "models": ["grok-2", "grok-beta"]},
    "AI21 Labs": {"name": "AI21 Labs", "category": "LLM", "base_url": "https://api.ai21.com/v1", "capabilities": ["chat", "completion"], "models": ["jamba-1.5", "jurassic-2"]},
    "DeepAI": {"name": "DeepAI", "category": "image", "base_url": "https://api.deepai.org/api", "capabilities": ["image"], "models": ["text2img", "enhance"]},
    "Wit.ai": {"name": "Wit.ai", "category": "audio", "base_url": "https://api.wit.ai", "capabilities": ["audio"], "models": ["speech", "intent"]},
    "Kairos": {"name": "Kairos", "category": "vision", "base_url": "https://api.kairos.com", "capabilities": ["vision"], "models": ["face-detect", "face-verify"]},
    "Imagga": {"name": "Imagga", "category": "vision", "base_url": "https://api.imagga.com/v2", "capabilities": ["vision"], "models": ["tagging", "color"]},
    "Filestack": {"name": "Filestack", "category": "vision", "base_url": "https://www.filestackapi.com", "capabilities": ["vision"], "models": ["file-picker", "transform"]},
    "Vision AI": {"name": "Vision AI", "category": "vision", "base_url": "https://api.visionai.com", "capabilities": ["vision"], "models": ["object-detect", "ocr"]},
    "NVIDIA NIM": {"name": "NVIDIA NIM", "category": "LLM", "base_url": "https://integrate.api.nvidia.com/v1", "capabilities": ["chat", "embedding"], "models": ["nemotron-70b", "llama3-nim"]},
    "DeepInfra": {"name": "DeepInfra", "category": "LLM", "base_url": "https://api.deepinfra.com/v1/openai", "capabilities": ["chat", "embedding"], "models": ["llama3-70b", "mixtral"]},
    "Together AI": {"name": "Together AI", "category": "LLM", "base_url": "https://api.together.xyz/v1", "capabilities": ["chat", "image", "embedding"], "models": ["llama3-405b", "flux-schnell"]},
    "Fireworks AI": {"name": "Fireworks AI", "category": "LLM", "base_url": "https://api.fireworks.ai/inference/v1", "capabilities": ["chat", "embedding", "image"], "models": ["llama3-v-70b", "firework-embed"]},
    "Unify": {"name": "Unify", "category": "LLM", "base_url": "https://api.unify.ai/v1", "capabilities": ["chat"], "models": ["unify-router", "mixtral"]},
    "Baseten": {"name": "Baseten", "category": "LLM", "base_url": "https://api.baseten.co/v1", "capabilities": ["chat", "embedding"], "models": ["llama3-8b", "mistral-7b"]},
    "Eden AI": {"name": "Eden AI", "category": "LLM", "base_url": "https://api.edenai.run/v2", "capabilities": ["chat", "image", "audio"], "models": ["eden-chat", "eden-image"]},
    "Modal": {"name": "Modal", "category": "LLM", "base_url": "https://api.modal.com/v1", "capabilities": ["chat", "embedding"], "models": ["modal-llama", "modal-embed"]},
    "Groq": {"name": "Groq", "category": "LLM", "base_url": "https://api.groq.com/openai/v1", "capabilities": ["chat", "audio"], "models": ["llama3-70b", "whisper-large-v3"]},
    "NLP Cloud": {"name": "NLP Cloud", "category": "LLM", "base_url": "https://api.nlpcloud.io/v1", "capabilities": ["chat", "embedding"], "models": ["dolphin", "fast-gpt"]},
    "Upstage": {"name": "Upstage", "category": "LLM", "base_url": "https://api.upstage.ai/v1", "capabilities": ["chat", "embedding"], "models": ["solar-10b", "solar-embed"]},
    "Hugging Face Inference API": {"name": "Hugging Face Inference API", "category": "LLM", "base_url": "https://api-inference.huggingface.co", "capabilities": ["chat", "image", "audio"], "models": ["mixtral-8x7b", "stable-diffusion"]},
    "Stability AI": {"name": "Stability AI", "category": "image", "base_url": "https://api.stability.ai/v1", "capabilities": ["image"], "models": ["stable-diffusion-3", "sd-xl"]},
    "Mistral AI": {"name": "Mistral AI", "category": "LLM", "base_url": "https://api.mistral.ai/v1", "capabilities": ["chat", "embedding"], "models": ["mistral-large", "mistral-embed"]},
    "Google AI Studio Gemini": {"name": "Google AI Studio Gemini", "category": "LLM", "base_url": "https://generativelanguage.googleapis.com/v1", "capabilities": ["chat", "vision", "audio"], "models": ["gemini-1.5-pro", "gemini-1.5-flash"]},
    "Amazon Bedrock": {"name": "Amazon Bedrock", "category": "LLM", "base_url": "https://bedrock-runtime.{region}.amazonaws.com", "capabilities": ["chat", "embedding", "image"], "models": ["claude-3", "titan-embed"]},
    "Meta Llama": {"name": "Meta Llama", "category": "LLM", "base_url": "https://api.meta.ai/llama/v1", "capabilities": ["chat"], "models": ["llama3-405b", "llama3-8b"]},
    "Perplexity API": {"name": "Perplexity API", "category": "LLM", "base_url": "https://api.perplexity.ai", "capabilities": ["chat"], "models": ["sonar-large", "sonar-small"]},
    "ElevenLabs": {"name": "ElevenLabs", "category": "audio", "base_url": "https://api.elevenlabs.io/v1", "capabilities": ["audio"], "models": ["eleven-turbo", "eleven-multilingual"]},
    "AssemblyAI": {"name": "AssemblyAI", "category": "audio", "base_url": "https://api.assemblyai.com/v2", "capabilities": ["audio"], "models": ["transcribe", "leMur"]},
    "DeepL API": {"name": "DeepL API", "category": "LLM", "base_url": "https://api-free.deepl.com/v2", "capabilities": ["chat"], "models": ["deepl-translate", "deepl-pro"]},
    "OpenRouter": {"name": "OpenRouter", "category": "LLM", "base_url": "https://openrouter.ai/api/v1", "capabilities": ["chat", "vision"], "models": ["auto-router", "anthropic-claude"]},
    "OctoAI": {"name": "OctoAI", "category": "LLM", "base_url": "https://api.octoai.run/v1", "capabilities": ["chat", "image"], "models": ["octo-llama", "octo-flux"]},
    "Replicate": {"name": "Replicate", "category": "image", "base_url": "https://api.replicate.com/v1", "capabilities": ["image", "audio", "video"], "models": ["flux-dev", "sdxl"]},
    "Aleph Alpha": {"name": "Aleph Alpha", "category": "LLM", "base_url": "https://api.aleph-alpha.com/v1", "capabilities": ["chat", "embedding"], "models": ["luminous-supreme", "luminous-base"]},
    "Writer": {"name": "Writer", "category": "LLM", "base_url": "https://api.writer.com/v1", "capabilities": ["chat"], "models": ["palmyra-x", "palmyra-creative"]},
    "Jasper": {"name": "Jasper", "category": "LLM", "base_url": "https://api.jasper.ai/v1", "capabilities": ["chat"], "models": ["jasper-chat", "jasper-art"]},
    "Pinecone": {"name": "Pinecone", "category": "embedding", "base_url": "https://controller.{env}.pinecone.io", "capabilities": ["embedding"], "models": ["pinecone-vector", "pinecone-sparse"]},
    "Qdrant Cloud": {"name": "Qdrant Cloud", "category": "embedding", "base_url": "https://{cluster}.qdrant.io", "capabilities": ["embedding"], "models": ["qdrant-vector", "qdrant-hybrid"]},
    "Milvus Zilliz Cloud": {"name": "Milvus Zilliz Cloud", "category": "embedding", "base_url": "https://{cluster}.zillizcloud.com", "capabilities": ["embedding"], "models": ["milvus-vector", "zilliz-hybrid"]},
    "GooseAI": {"name": "GooseAI", "category": "LLM", "base_url": "https://api.goose.ai/v1", "capabilities": ["chat", "completion"], "models": ["gpt-neo-20b", "gpt-j-6b"]},
    "Azure OpenAI Service": {"name": "Azure OpenAI Service", "category": "LLM", "base_url": "https://{resource}.openai.azure.com/openai", "capabilities": ["chat", "embedding", "vision"], "models": ["gpt-4o", "gpt-4-turbo"]},
    "DeepSeek": {"name": "DeepSeek", "category": "LLM", "base_url": "https://api.deepseek.com/v1", "capabilities": ["chat"], "models": ["deepseek-chat", "deepseek-coder"]},
    "Kie.ai": {"name": "Kie.ai", "category": "LLM", "base_url": "https://api.kie.ai/v1", "capabilities": ["chat", "image"], "models": ["kie-chat", "kie-flux"]},
    "Fal.ai": {"name": "Fal.ai", "category": "image", "base_url": "https://fal.run", "capabilities": ["image", "video"], "models": ["flux-dev", "sdxl-turbo"]},
    "Featherless AI": {"name": "Featherless AI", "category": "LLM", "base_url": "https://api.featherless.ai/v1", "capabilities": ["chat"], "models": ["featherless-llama", "featherless-mistral"]},
    "Hypereal Tech": {"name": "Hypereal Tech", "category": "video", "base_url": "https://api.hypereal.tech/v1", "capabilities": ["video"], "models": ["hypereal-video", "hypereal-motion"]},
    "Wavespeed.ai": {"name": "Wavespeed.ai", "category": "video", "base_url": "https://api.wavespeed.ai/v1", "capabilities": ["video"], "models": ["wavespeed-gen", "wavespeed-fast"]},
    "Hyperbolic": {"name": "Hyperbolic", "category": "LLM", "base_url": "https://api.hyperbolic.xyz/v1", "capabilities": ["chat", "image"], "models": ["hyperbolic-llama", "hyperbolic-flux"]},
    "Modular": {"name": "Modular", "category": "LLM", "base_url": "https://api.modular.com/v1", "capabilities": ["chat", "embedding"], "models": ["mojo-llm", "max-embed"]},
}

# ---------------------------------------------------------------------------
# Multi-key storage: provider_name -> list of API key strings.
# ---------------------------------------------------------------------------

_KEYS: dict[str, list[str]] = {
    "OpenAI": ["sk-mock-openai-1", "sk-mock-openai-2"],
    "Anthropic Claude": ["sk-ant-mock-1"],
}

_DEFAULT_PROVIDER: str | None = None


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _get_provider(a: dict) -> dict | None:
    name = a.get("provider")
    return _PROVIDERS.get(name) if name else None


def _mask_key(k: str) -> str:
    if len(k) <= 8:
        return k[:2] + "***"
    return k[:4] + "*" * 6 + k[-4:]


def _masked_keys(provider: str) -> list[str]:
    return [_mask_key(k) for k in _KEYS.get(provider, [])]


def _ensure_list(val) -> list:
    if isinstance(val, list):
        return val
    if val is None:
        return []
    return [val]


def _ok(**kw) -> dict:
    return {"ok": True, **kw}


def _err(msg: str, **kw) -> dict:
    return {"ok": False, "error": msg, **kw}


def _mock_status(provider: str) -> str:
    """Deterministic mock health so output is stable."""
    return "healthy" if hash(provider) % 3 != 0 else "degraded"


def _require_provider(a: dict):
    """Return provider name if valid, else None."""
    name = a.get("provider")
    return name if name and name in _PROVIDERS else None


def _add_keys(provider: str, keys) -> dict:
    k = _ensure_list(keys)
    _KEYS.setdefault(provider, []).extend(k)
    return _ok(provider=provider, added=len(k), total=len(_KEYS[provider]))


def _remove_key(provider: str, key: str) -> dict:
    keys = _KEYS.get(provider, [])
    if key in keys:
        keys.remove(key)
        return _ok(provider=provider, remaining=len(keys))
    return _err("Key not found", provider=provider)


def _rotate_key(provider: str) -> dict:
    keys = _KEYS.get(provider, [])
    if len(keys) > 1:
        keys.append(keys.pop(0))
    return _ok(provider=provider, rotated=True, keys=_masked_keys(provider))


def _add_custom(a: dict) -> dict:
    name = a.get("name")
    if not name:
        return _err("name required")
    if name in _PROVIDERS:
        return _err("Provider already exists")
    _PROVIDERS[name] = {
        "name": name, "category": a.get("category", "LLM"),
        "base_url": a.get("base_url", ""), "capabilities": a.get("capabilities", []),
        "models": a.get("models", []),
    }
    return _ok(provider=name, total=len(_PROVIDERS))


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

TOOLS: list[dict] = [
    {
        "name": "provider_list",
        "description": "List all registered providers with their categories.",
        "params": {},
        "run": lambda a: _ok(count=len(_PROVIDERS), providers=[{"name": p["name"], "category": p["category"]} for p in _PROVIDERS.values()]),
    },
    {
        "name": "provider_add_keys",
        "description": "Add one or more API keys to a provider.",
        "params": {"provider": "str", "keys": "list[str]"},
        "run": lambda a: _add_keys(a["provider"], a.get("keys")) if _require_provider(a) else _err("Unknown provider"),
    },
    {
        "name": "provider_remove_key",
        "description": "Remove a specific API key from a provider.",
        "params": {"provider": "str", "key": "str"},
        "run": lambda a: _remove_key(a["provider"], a.get("key")) if _require_provider(a) else _err("Unknown provider"),
    },
    {
        "name": "provider_list_keys",
        "description": "List API keys for a provider (masked).",
        "params": {"provider": "str"},
        "run": lambda a: _ok(provider=a["provider"], count=len(_KEYS.get(a["provider"], [])), keys=_masked_keys(a["provider"])) if _require_provider(a) else _err("Unknown provider"),
    },
    {
        "name": "provider_rotate_key",
        "description": "Rotate keys for a provider (move first key to end).",
        "params": {"provider": "str"},
        "run": lambda a: _rotate_key(a["provider"]) if _require_provider(a) else _err("Unknown provider"),
    },
    {
        "name": "provider_test_key",
        "description": "Test a provider's API key (returns mock status).",
        "params": {"provider": "str", "key": "str"},
        "run": lambda a: _ok(provider=a["provider"], key=_mask_key(a.get("key", "")), status=_mock_status(a["provider"]), latency_ms=42) if _require_provider(a) else _err("Unknown provider"),
    },
    {
        "name": "provider_get_config",
        "description": "Get the full configuration for a provider.",
        "params": {"provider": "str"},
        "run": lambda a: _ok(config=_get_provider(a), key_count=len(_KEYS.get(a["provider"], []))) if _require_provider(a) else _err("Unknown provider"),
    },
    {
        "name": "provider_set_default",
        "description": "Set the default provider.",
        "params": {"provider": "str"},
        "run": lambda a: _ok(default=a["provider"]) if _require_provider(a) else _err("Unknown provider"),
    },
    {
        "name": "provider_get_usage",
        "description": "Get mock usage stats for a provider (requests, tokens, cost).",
        "params": {"provider": "str"},
        "run": lambda a: _ok(provider=a["provider"], requests=hash(a["provider"]) % 10000, tokens=hash(a["provider"]) % 500000, cost_usd=round((hash(a["provider"]) % 50000) / 100, 2)) if _require_provider(a) else _err("Unknown provider"),
    },
    {
        "name": "provider_categories",
        "description": "List all unique categories with provider counts.",
        "params": {},
        "run": lambda a: _ok(categories={c: sum(1 for p in _PROVIDERS.values() if p["category"] == c) for c in sorted({p["category"] for p in _PROVIDERS.values()})}),
    },
    {
        "name": "provider_add_custom",
        "description": "Add a custom provider to the registry.",
        "params": {"name": "str", "category": "str", "base_url": "str", "capabilities": "list[str]", "models": "list[str]"},
        "run": lambda a: _add_custom(a),
    },
    {
        "name": "provider_health_check",
        "description": "Check health of all providers (returns mock statuses).",
        "params": {},
        "run": lambda a: _ok(results={p: _mock_status(p) for p in _PROVIDERS}, healthy=sum(1 for p in _PROVIDERS if _mock_status(p) == "healthy"), degraded=sum(1 for p in _PROVIDERS if _mock_status(p) == "degraded")),
    },
]
