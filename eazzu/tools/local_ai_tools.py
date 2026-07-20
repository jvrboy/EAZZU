"""Local AI model runner tools.

Pure-Python helpers that model local LLM/SLM workflows: model download,
quantization, routing, RAG, fine-tuning, LoRA, embeddings, STT/TTS, vision,
benchmarks, and more. Each tool returns a structured dict.
"""

from __future__ import annotations

import math

def _model_size_gb(params_b: float, quant: str) -> float:
    return params_b * {"fp16": 2, "q8": 1, "q4": 0.5, "q3": 0.375, "q2": 0.25}.get(quant, 2)

def _vram_needed(size_gb: float, context: int) -> float:
    return round(size_gb + context * 0.000002, 2)

def _estimate_tps(params_b: float, quant: str) -> float:
    base = 80.0 / max(params_b, 0.5)
    mult = {"fp16": 1.0, "q8": 1.3, "q4": 1.8, "q3": 2.0, "q2": 2.2}.get(quant, 1.0)
    return round(base * mult, 1)

def _embedding_dim(model: str) -> int:
    return {"nomic-embed": 768, "bge-small": 384, "bge-base": 768, "bge-large": 1024,
            "minilm": 384, "e5-base": 768}.get(model, 768)

def _prompt_profiles() -> list[dict]:
    return [{"name": "concise", "max_tokens": 256, "temperature": 0.3},
            {"name": "creative", "max_tokens": 1024, "temperature": 0.9},
            {"name": "coding", "max_tokens": 2048, "temperature": 0.1},
            {"name": "chat", "max_tokens": 512, "temperature": 0.7}]

def _benchmark_tasks() -> list[dict]:
    return [{"name": "mmlu", "type": "knowledge"}, {"name": "human_eval", "type": "coding"},
            {"name": "gsm8k", "type": "math"}, {"name": "mt_bench", "type": "chat"}]

def _api_formats() -> list[str]:
    return ["openai", "anthropic", "ollama", "llama_cpp", "custom"]

TOOLS: list[dict] = [
    {"name": "local_ai_download", "description": "Download a model from a registry with progress tracking.",
     "params": {"model": "str", "registry": "str", "quant": "str"},
     "run": lambda a: {"model": a.get("model", "llama3-8b"), "registry": a.get("registry", "huggingface"),
                      "quant": a.get("quant", "q4"), "size_gb": _model_size_gb(8, a.get("quant", "q4")), "status": "queued"}},

    {"name": "local_ai_quantize", "description": "Quantize a model to reduce memory footprint.",
     "params": {"model": "str", "source_quant": "str", "target_quant": "str", "params_b": "float"},
     "run": lambda a: {"model": a.get("model", "llama3-8b"), "from": a.get("source_quant", "fp16"),
                      "to": a.get("target_quant", "q4"),
                      "original_size_gb": _model_size_gb(a.get("params_b", 8), a.get("source_quant", "fp16")),
                      "quantized_size_gb": _model_size_gb(a.get("params_b", 8), a.get("target_quant", "q4")),
                      "compression_ratio": round(_model_size_gb(a.get("params_b", 8), a.get("source_quant", "fp16"))
                      / max(_model_size_gb(a.get("params_b", 8), a.get("target_quant", "q4")), 0.01), 2)}},

    {"name": "local_ai_dashboard", "description": "Return a dashboard summary of local model status and resources.",
     "params": {"models": "list[dict]", "gpu_vram_gb": "float"},
     "run": lambda a: {"models_loaded": len(a.get("models", [])),
                      "total_vram_used_gb": sum(m.get("size_gb", 0) for m in a.get("models", [])),
                      "gpu_vram_total_gb": a.get("gpu_vram_gb", 24),
                      "available_vram_gb": a.get("gpu_vram_gb", 24) - sum(m.get("size_gb", 0) for m in a.get("models", [])),
                      "status": "healthy"}},

    {"name": "local_ai_routing", "description": "Route a prompt to the best local model based on task type and VRAM.",
     "params": {"prompt": "str", "task": "str", "available_models": "list[dict]", "vram_gb": "float"},
     "run": lambda a: {"selected": min(a.get("available_models", [{"name": "default", "size_gb": 4}]),
                       key=lambda m: m.get("size_gb", 4)), "task": a.get("task", "chat"),
                      "reason": "best fit for available VRAM"}},

    {"name": "local_ai_offline", "description": "Configure offline mode settings for fully local inference.",
     "params": {"enabled": "bool", "cache_dir": "str", "models": "list[str]"},
     "run": lambda a: {"offline": a.get("enabled", True), "cache_dir": a.get("cache_dir", "~/.local-ai/models"),
                      "cached_models": a.get("models", []), "network_required": False}},

    {"name": "local_ai_rag", "description": "Set up a local RAG pipeline with embeddings and vector store.",
     "params": {"documents": "list[str]", "embedding_model": "str", "chunk_size": "int", "top_k": "int"},
     "run": lambda a: {"embedding_model": a.get("embedding_model", "nomic-embed"),
                      "embedding_dim": _embedding_dim(a.get("embedding_model", "nomic-embed")),
                      "chunk_count": len(a.get("documents", [])) * (1000 // max(a.get("chunk_size", 512), 1)),
                      "chunk_size": a.get("chunk_size", 512), "top_k": a.get("top_k", 4), "vector_store": "chroma"}},

    {"name": "local_ai_prompt_profiles", "description": "List or select a prompt profile for generation settings.",
     "params": {"profile": "str", "custom": "dict"},
     "run": lambda a: {"profiles": _prompt_profiles(),
                      "selected": next((p for p in _prompt_profiles() if p["name"] == a.get("profile", "chat")),
                                       _prompt_profiles()[3]),
                      "overrides": a.get("custom", {})}},

    {"name": "local_ai_finetune", "description": "Plan a local fine-tuning run with dataset and hyperparameters.",
     "params": {"model": "str", "dataset": "str", "epochs": "int", "lr": "float", "method": "str"},
     "run": lambda a: {"model": a.get("model", "llama3-8b"), "dataset": a.get("dataset", "custom.jsonl"),
                      "epochs": a.get("epochs", 3), "learning_rate": a.get("lr", 2e-5),
                      "method": a.get("method", "lora"), "estimated_time_hours": a.get("epochs", 3) * 2}},

    {"name": "local_ai_lora", "description": "Configure LoRA adapter settings for efficient fine-tuning.",
     "params": {"model": "str", "rank": "int", "alpha": "int", "target_modules": "list[str]"},
     "run": lambda a: {"model": a.get("model", "llama3-8b"), "rank": a.get("rank", 16), "alpha": a.get("alpha", 32),
                      "target_modules": a.get("target_modules", ["q_proj", "v_proj"]),
                      "trainable_params_pct": round(a.get("rank", 16) / 1000 * 100, 2),
                      "adapter_size_mb": a.get("rank", 16) * 8}},

    {"name": "local_ai_prompt_library", "description": "Manage a local library of saved prompts with tags.",
     "params": {"action": "str", "prompts": "list[dict]", "tag": "str"},
     "run": lambda a: {"action": a.get("action", "list"),
                      "prompts": [p for p in a.get("prompts", []) if a.get("tag", "") in p.get("tags", [])]
                      if a.get("tag") else a.get("prompts", []),
                      "count": len(a.get("prompts", []))}},

    {"name": "local_ai_api_endpoint", "description": "Configure a local OpenAI-compatible API endpoint.",
     "params": {"port": "int", "model": "str", "format": "str", "cors": "bool"},
     "run": lambda a: {"port": a.get("port", 8080), "model": a.get("model", "llama3-8b"),
                      "format": a.get("format", "openai"), "supported_formats": _api_formats(),
                      "cors": a.get("cors", True), "endpoint": f"http://localhost:{a.get('port', 8080)}/v1"}},

    {"name": "local_ai_memory", "description": "Manage conversation memory and context window for local models.",
     "params": {"messages": "list[dict]", "max_context": "int", "strategy": "str"},
     "run": lambda a: {"strategy": a.get("strategy", "sliding_window"), "max_context": a.get("max_context", 4096),
                      "current_tokens": sum(len(m.get("content", "").split()) for m in a.get("messages", [])),
                      "messages_retained": len(a.get("messages", [])),
                      "truncated": sum(len(m.get("content", "").split()) for m in a.get("messages", [])) > a.get("max_context", 4096)}},

    {"name": "local_ai_embeddings", "description": "Generate embeddings for a list of texts using a local model.",
     "params": {"texts": "list[str]", "model": "str", "batch_size": "int"},
     "run": lambda a: {"model": a.get("model", "nomic-embed"), "dim": _embedding_dim(a.get("model", "nomic-embed")),
                      "count": len(a.get("texts", [])),
                      "batches": math.ceil(len(a.get("texts", [])) / max(a.get("batch_size", 32), 1)),
                      "vectors": [[0.0] * _embedding_dim(a.get("model", "nomic-embed"))] * len(a.get("texts", []))}},

    {"name": "local_ai_stt_tts", "description": "Configure local speech-to-text and text-to-speech pipelines.",
     "params": {"stt_model": "str", "tts_model": "str", "language": "str", "sample_rate": "int"},
     "run": lambda a: {"stt": {"model": a.get("stt_model", "whisper-base"), "language": a.get("language", "en")},
                      "tts": {"model": a.get("tts_model", "piper"), "sample_rate": a.get("sample_rate", 22050)},
                      "realtime": True}},

    {"name": "local_ai_vision", "description": "Configure a local vision-language model for image understanding.",
     "params": {"model": "str", "max_image_size": "int", "task": "str"},
     "run": lambda a: {"model": a.get("model", "llava-1.5"), "task": a.get("task", "caption"),
                      "max_image_size": a.get("max_image_size", 1024),
                      "supports": ["caption", "vqa", "ocr", "detection"]}},

    {"name": "local_ai_batch", "description": "Run batch inference over a list of prompts.",
     "params": {"prompts": "list[str]", "model": "str", "batch_size": "int", "max_tokens": "int"},
     "run": lambda a: {"model": a.get("model", "llama3-8b"), "total_prompts": len(a.get("prompts", [])),
                      "batches": math.ceil(len(a.get("prompts", [])) / max(a.get("batch_size", 8), 1)),
                      "estimated_tokens": len(a.get("prompts", [])) * a.get("max_tokens", 512), "status": "queued"}},

    {"name": "local_ai_context_summarize", "description": "Summarize conversation context to fit within a target token budget.",
     "params": {"messages": "list[dict]", "target_tokens": "int", "strategy": "str"},
     "run": lambda a: {"original_tokens": sum(len(m.get("content", "").split()) for m in a.get("messages", [])),
                      "target_tokens": a.get("target_tokens", 1024), "strategy": a.get("strategy", "rolling_summary"),
                      "summary": "Compressed context summary.",
                      "compression_ratio": round(max(sum(len(m.get("content", "").split())
                      for m in a.get("messages", [])), 1) / a.get("target_tokens", 1024), 2)}},

    {"name": "local_ai_benchmark", "description": "Benchmark a local model across standard tasks.",
     "params": {"model": "str", "tasks": "list[str]", "quant": "str"},
     "run": lambda a: {"model": a.get("model", "llama3-8b"), "quant": a.get("quant", "q4"),
                      "tasks": [t for t in _benchmark_tasks() if t["name"] in a.get("tasks", [b["name"] for b in _benchmark_tasks()])]
                      or _benchmark_tasks(),
                      "tokens_per_second": _estimate_tps(8, a.get("quant", "q4"))}},

    {"name": "local_ai_model_card", "description": "Generate a model card with metadata, capabilities, and requirements.",
     "params": {"model": "str", "params_b": "float", "quant": "str", "context": "int", "license": "str"},
     "run": lambda a: {"model": a.get("model", "llama3-8b"), "parameters_b": a.get("params_b", 8),
                      "quantization": a.get("quant", "q4"), "size_gb": _model_size_gb(a.get("params_b", 8), a.get("quant", "q4")),
                      "vram_required_gb": _vram_needed(_model_size_gb(a.get("params_b", 8), a.get("quant", "q4")), a.get("context", 4096)),
                      "context_window": a.get("context", 4096), "license": a.get("license", "apache-2.0"),
                      "tokens_per_second": _estimate_tps(a.get("params_b", 8), a.get("quant", "q4"))}},

    {"name": "local_ai_update_check", "description": "Check for model updates or new versions available.",
     "params": {"models": "list[dict]", "registry": "str"},
     "run": lambda a: {"updates_available": [{"model": m.get("name", "unknown"),
                      "current": m.get("version", "1.0"), "latest": "2.0"} for m in a.get("models", [])],
                      "registry": a.get("registry", "huggingface"), "auto_update": False}},
]