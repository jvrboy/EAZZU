"""Next-gen/experimental tools: 3D reconstruction, avatars, AR preview, interactive video, multimodal reference, semantic timeline, auto storyboard, and style lock."""

from __future__ import annotations

import math
from typing import Any


def _safe_str(a: dict, key: str, default: str = "") -> str:
    """Return a cleaned string param or a default."""
    return str(a.get(key, default)).strip() or default


def _safe_float(a: dict, key: str, default: float) -> float:
    """Return a float param or a default, tolerating bad input."""
    try:
        return float(a.get(key, default))
    except (TypeError, ValueError):
        return default


def _safe_int(a: dict, key: str, default: int) -> int:
    """Return an int param or a default."""
    try:
        return int(a.get(key, default))
    except (TypeError, ValueError):
        return default


def _safe_bool(a: dict, key: str, default: bool) -> bool:
    """Return a bool param or a default."""
    return bool(a.get(key, default))


def _reconstruct_config(method: str, frames: int) -> dict:
    """Return a 3D reconstruction config for NeRF or Gaussian Splatting."""
    if method.lower() == "nerf":
        return {
            "method": "NeRF",
            "iterations": 30000,
            "samples_per_ray": 64,
            "resolution": (1920, 1080),
            "frames_used": frames,
            "output": "volumetric_scene",
        }
    return {
        "method": "Gaussian Splatting",
        "iterations": 20000,
        "splats": 500_000,
        "resolution": (1920, 1080),
        "frames_used": frames,
        "output": "point_cloud_splat",
    }


def _avatar_phonemes(text: str) -> list[dict]:
    """Map text to a simplified viseme/phoneme sequence for lip-sync."""
    visemes = {
        "a": "open", "e": "wide", "i": "narrow", "o": "round", "u": "pucker",
        "m": "closed", "b": "closed", "p": "closed", "f": "teeth_lower",
        "v": "teeth_lower", "s": "narrow", "t": "tongue_up", "n": "tongue_up",
    }
    seq: list[dict] = []
    for i, ch in enumerate(text.lower()):
        if ch in visemes:
            seq.append({"t": round(i * 0.08, 3), "viseme": visemes[ch], "char": ch})
    return seq


def _ar_anchor(surface: str) -> dict:
    """Return AR anchor/placement config for a surface type."""
    surfaces = {
        "floor": {"plane": "horizontal", "alignment": "y", "scale": 1.0},
        "wall": {"plane": "vertical", "alignment": "z", "scale": 1.0},
        "table": {"plane": "horizontal", "alignment": "y", "scale": 0.5},
        "floating": {"plane": "none", "alignment": "free", "scale": 1.0},
    }
    return surfaces.get(surface.lower(), surfaces["floating"])


def _hotspot_template(hotspot_type: str) -> dict:
    """Return a hotspot template for interactive video."""
    types = {
        "link": {"action": "open_url", "style": "pill"},
        "info": {"action": "show_overlay", "style": "card"},
        "branch": {"action": "jump_to_chapter", "style": "button"},
        "product": {"action": "show_product_card", "style": "tag"},
        "quiz": {"action": "show_question", "style": "panel"},
    }
    return types.get(hotspot_type.lower(), types["info"])


def _reference_weights(modalities: list[str]) -> dict:
    """Compute weighting for multimodal reference inputs."""
    weights: dict[str, float] = {}
    for m in modalities:
        m_l = m.lower()
        if "text" in m_l:
            weights["text"] = 0.3
        elif "image" in m_l:
            weights["image"] = 0.3
        elif "audio" in m_l:
            weights["audio"] = 0.2
        elif "video" in m_l:
            weights["video"] = 0.2
    total = sum(weights.values()) or 1.0
    return {k: round(v / total, 3) for k, v in weights.items()}


def _semantic_groups(timeline: list[dict]) -> list[dict]:
    """Group timeline clips by scene/speaker/topic."""
    groups: dict[str, list[dict]] = {}
    for clip in timeline:
        key = clip.get("scene", clip.get("speaker", clip.get("topic", "ungrouped")))
        groups.setdefault(str(key), []).append(clip)
    return [{"group": k, "clips": v} for k, v in groups.items()]


def _shot_list(script: str, shots_per_scene: int) -> list[dict]:
    """Convert a script into a shot-by-shot storyboard list."""
    scenes = [s.strip() for s in script.split("\n") if s.strip()]
    boards: list[dict] = []
    shot_types = ["wide", "medium", "close-up", "over-the-shoulder", "insert", "aerial"]
    for si, scene in enumerate(scenes):
        for j in range(shots_per_scene):
            boards.append({
                "scene": si + 1,
                "shot": j + 1,
                "description": scene[:120],
                "shot_type": shot_types[j % len(shot_types)],
                "duration_s": 4.0,
            })
    return boards


def _style_palette(name: str) -> dict:
    """Return a shared visual-identity palette for style locking."""
    palettes = {
        "warm_cinema": {"primary": "#D4A24E", "secondary": "#2B2B2B", "accent": "#F5E6C8", "contrast": 0.7},
        "neon_noir": {"primary": "#FF2E63", "secondary": "#0D0D0D", "accent": "#08D9D6", "contrast": 0.9},
        "soft_pastel": {"primary": "#A8DADC", "secondary": "#F1FAEE", "accent": "#E63946", "contrast": 0.4},
        "mono_pro": {"primary": "#1D3557", "secondary": "#F1FAEE", "accent": "#457B9D", "contrast": 0.6},
    }
    return palettes.get(name.lower(), palettes["warm_cinema"])


def _style_lock_assets(palette: dict) -> list[dict]:
    """Return per-asset style-lock rules."""
    return [
        {"asset": "post_image", "palette": palette, "filter": "match_primary"},
        {"asset": "video_grade", "palette": palette, "lut": "auto_from_palette"},
        {"asset": "thumbnail", "palette": palette, "font": "brand_sans", "contrast": palette.get("contrast", 0.6)},
    ]


# --- Public tool entries -----------------------------------------------------

TOOLS: list[dict] = [
    {
        "name": "nextgen_3d_reconstruct",
        "description": "Reconstruct a video walkaround into an explorable 3D scene via NeRF or Gaussian Splatting.",
        "params": {"method": "str", "frames": "int"},
        "run": lambda a: {
            "method": _safe_str(a, "method", "gaussian_splatting"),
            "config": _reconstruct_config(_safe_str(a, "method", "gaussian_splatting"), _safe_int(a, "frames", 120)),
            "export_formats": ["glb", "ply", "splat"],
        },
    },
    {
        "name": "nextgen_avatar",
        "description": "Turn a photo into a talking animated avatar with lip-sync from text or audio.",
        "params": {"photo_id": "str", "speech_text": "str", "emotion": "str"},
        "run": lambda a: {
            "photo_id": _safe_str(a, "photo_id", ""),
            "emotion": _safe_str(a, "emotion", "neutral"),
            "phonemes": _avatar_phonemes(_safe_str(a, "speech_text", "")),
            "fps": 30,
            "output": "talking_avatar_video",
        },
    },
    {
        "name": "nextgen_ar_preview",
        "description": "Preview how an edit looks placed in real-world space via AR camera.",
        "params": {"surface": "str", "scale": "float", "lighting_match": "bool"},
        "run": lambda a: {
            "anchor": _ar_anchor(_safe_str(a, "surface", "floating")),
            "scale": _safe_float(a, "scale", 1.0),
            "lighting_match": _safe_bool(a, "lighting_match", True),
            "pass": "world_tracking",
        },
    },
    {
        "name": "nextgen_interactive_video",
        "description": "Add clickable hotspots and branching narratives to video.",
        "params": {"hotspots": "list[dict]", "chapters": "list[dict]"},
        "run": lambda a: {
            "hotspots": [
                {**h, **_hotspot_template(h.get("type", "info"))}
                for h in a.get("hotspots", [])
            ],
            "chapters": a.get("chapters", []),
            "branching": any(h.get("type") == "branch" for h in a.get("hotspots", [])),
        },
    },
    {
        "name": "nextgen_multimodal_reference",
        "description": "Combine text, image, audio, and video as guiding input for edits.",
        "params": {"modalities": "list[str]", "prompt": "str"},
        "run": lambda a: {
            "modalities": a.get("modalities", ["text"]),
            "weights": _reference_weights(a.get("modalities", ["text"])),
            "prompt": _safe_str(a, "prompt", ""),
            "fused_embedding": True,
        },
    },
    {
        "name": "nextgen_semantic_timeline",
        "description": "Organize the timeline by scenes, speakers, or topics.",
        "params": {"timeline": "list[dict]", "group_by": "str"},
        "run": lambda a: {
            "group_by": _safe_str(a, "group_by", "scene"),
            "groups": _semantic_groups(a.get("timeline", [])),
        },
    },
    {
        "name": "nextgen_auto_storyboard",
        "description": "Convert a script into a shot-by-shot visual storyboard.",
        "params": {"script": "str", "shots_per_scene": "int"},
        "run": lambda a: {
            "script": _safe_str(a, "script", ""),
            "shots_per_scene": _safe_int(a, "shots_per_scene", 4),
            "boards": _shot_list(_safe_str(a, "script", ""), _safe_int(a, "shots_per_scene", 4)),
        },
    },
    {
        "name": "nextgen_style_lock",
        "description": "Ensure post image, video, and thumbnail share one visual identity.",
        "params": {"palette_name": "str"},
        "run": lambda a: {
            "palette_name": _safe_str(a, "palette_name", "warm_cinema"),
            "palette": _style_palette(_safe_str(a, "palette_name", "warm_cinema")),
            "locked_assets": _style_lock_assets(_style_palette(_safe_str(a, "palette_name", "warm_cinema"))),
        },
    },
]