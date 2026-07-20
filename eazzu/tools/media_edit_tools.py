"""Image and video editing tools: crop, filters, adjustments, effects, matting, trim, warp, merge, blend, opacity, object removal, texture overlays.

Pure-Python implementations operating on in-memory frame dicts. No external deps.
"""

from __future__ import annotations

import math
from typing import Any

# ---------------------------------------------------------------------------
# Aspect-ratio presets
# ---------------------------------------------------------------------------

_ASPECT_PRESETS = {
    "9:16": (9, 16),
    "16:9": (16, 9),
    "1:1": (1, 1),
    "4:5": (4, 5),
}


def _resolve_aspect(preset: str | None, freeform: tuple[int, int] | None) -> tuple[int, int]:
    if freeform:
        return freeform
    if preset in _ASPECT_PRESETS:
        return _ASPECT_PRESETS[preset]
    return (1, 1)


def _compute_crop_box(width: int, height: int, aspect: tuple[int, int]) -> dict:
    aw, ah = aspect
    target = aw / ah
    current = width / height
    if current > target:
        new_h = height
        new_w = int(round(height * target))
    else:
        new_w = width
        new_h = int(round(width / target))
    x = (width - new_w) // 2
    y = (height - new_h) // 2
    return {"x": x, "y": y, "w": new_w, "h": new_h}


# ---------------------------------------------------------------------------
# Filter preset packs (stackable)
# ---------------------------------------------------------------------------

_FILTER_PRESETS: dict[str, dict[str, float]] = {
    "cinematic": {"contrast": 1.15, "saturation": 0.9, "temperature": -0.05, "highlights": 0.9, "shadows": 1.1},
    "vintage": {"saturation": 0.7, "contrast": 0.9, "temperature": 0.15, "vignette": 0.3},
    "film": {"grain": 0.2, "contrast": 1.05, "saturation": 0.95, "highlights": 0.95},
    "moody": {"contrast": 1.2, "saturation": 0.8, "shadows": 0.85, "temperature": -0.1},
    "vibrant": {"saturation": 1.3, "vibrance": 1.2, "contrast": 1.1},
}


def _apply_filter_params(params: dict, intensity: float) -> dict:
    out: dict[str, float] = {}
    for k, v in params.items():
        out[k] = 1.0 + (v - 1.0) * intensity
    return out


def _stack_filters(presets: list[str], intensity: float) -> dict:
    merged: dict[str, float] = {}
    for name in presets:
        p = _FILTER_PRESETS.get(name, {})
        for k, v in p.items():
            merged[k] = merged.get(k, 1.0) * (1.0 + (v - 1.0) * intensity)
    return merged


# ---------------------------------------------------------------------------
# Adjustment parameters
# ---------------------------------------------------------------------------

_ADJUST_KEYS = [
    "exposure", "contrast", "highlights", "shadows", "whites", "blacks",
    "temperature", "tint", "vibrance", "saturation", "clarity", "dehaze",
    "sharpness", "noise_reduction",
]


def _normalize_adjustments(raw: dict) -> dict:
    out: dict[str, float] = {}
    for k in _ADJUST_KEYS:
        out[k] = float(raw.get(k, 1.0))
    return out


# ---------------------------------------------------------------------------
# Effects
# ---------------------------------------------------------------------------

_EFFECTS = [
    "glow", "bloom", "chromatic_aberration", "film_grain", "light_leaks",
    "glitch", "vhs", "prism", "tilt_shift", "motion_blur", "radial_blur",
]


def _effect_config(effect: str, amount: float) -> dict:
    return {"effect": effect, "amount": max(0.0, min(1.0, amount))}


# ---------------------------------------------------------------------------
# Matting / background
# ---------------------------------------------------------------------------

_BG_MODES = ["image", "video", "color", "gradient", "blurred", "ai_scene"]


def _matte_config(edge_refine: float, feather: float, export_alpha: bool) -> dict:
    return {
        "edge_refinement": max(0.0, min(1.0, edge_refine)),
        "feather": max(0.0, min(1.0, feather)),
        "transparent_png": bool(export_alpha),
    }


def _background_config(mode: str, **extra: Any) -> dict:
    mode = mode if mode in _BG_MODES else "color"
    cfg: dict[str, Any] = {"mode": mode}
    cfg.update(extra)
    return cfg


# ---------------------------------------------------------------------------
# Trim helpers
# ---------------------------------------------------------------------------

_TRIM_MODES = ["frame_accurate", "ripple", "slip", "slide", "silence_autocut"]


def _trim_config(mode: str, start: int, end: int, fps: float = 30.0) -> dict:
    mode = mode if mode in _TRIM_MODES else "frame_accurate"
    return {"mode": mode, "start_frame": start, "end_frame": end, "fps": fps}


# ---------------------------------------------------------------------------
# Manipulation
# ---------------------------------------------------------------------------

_MANIP_TYPES = ["warp", "liquify", "perspective", "lens_distortion", "mesh_transform", "puppet_warp"]


def _manip_config(mtype: str, strength: float) -> dict:
    mtype = mtype if mtype in _MANIP_TYPES else "warp"
    return {"type": mtype, "strength": max(0.0, min(1.0, strength))}


# ---------------------------------------------------------------------------
# Merge helpers
# ---------------------------------------------------------------------------

_MERGE_MODES = ["concat", "panorama", "hdr_bracket", "photo_stack"]


# ---------------------------------------------------------------------------
# Blend modes
# ---------------------------------------------------------------------------

_BLEND_MODES = [
    "normal", "multiply", "screen", "overlay", "darken", "lighten",
    "color_dodge", "color_burn", "linear_burn", "linear_dodge", "vivid_light",
    "linear_light", "pin_light", "hard_mix", "difference", "exclusion",
    "subtract", "divide", "hue", "saturation", "color", "luminosity",
    "soft_light", "hard_light", "dissolve", "pass_through", "add", "glow",
    "erased",
]


def _blend_config(mode: str, opacity: float, mask: dict | None = None) -> dict:
    mode = mode if mode in _BLEND_MODES else "normal"
    cfg = {"mode": mode, "opacity": max(0.0, min(1.0, opacity))}
    if mask:
        cfg["mask"] = mask
    return cfg


# ---------------------------------------------------------------------------
# Texture overlays
# ---------------------------------------------------------------------------

_TEXTURES = ["grain", "paper", "canvas", "fabric", "dust", "bokeh"]


def _texture_config(name: str, blend: str, opacity: float, scale: float = 1.0) -> dict:
    name = name if name in _TEXTURES else "grain"
    blend = blend if blend in _BLEND_MODES else "overlay"
    return {"texture": name, "blend": blend, "opacity": opacity, "scale": scale}


# ===========================================================================
# TOOLS
# ===========================================================================

TOOLS: list[dict] = [
    {
        "name": "media_crop",
        "description": "Crop media to aspect-ratio presets (9:16, 16:9, 1:1, 4:5), freeform, or multi-crop batch.",
        "params": {"preset": "str", "freeform": "tuple", "batch": "list", "width": "int", "height": "int"},
        "run": lambda a: {
            "crops": [
                _compute_crop_box(
                    a.get("width", 1920),
                    a.get("height", 1080),
                    _resolve_aspect(item.get("preset"), item.get("freeform")),
                )
                for item in a.get("batch", [{"preset": a.get("preset", "16:9")}])
            ],
        },
    },
    {
        "name": "media_filters",
        "description": "Apply stackable preset filter packs (cinematic/vintage/film/moody/vibrant) with intensity slider.",
        "params": {"presets": "list", "intensity": "float"},
        "run": lambda a: {
            "applied": _stack_filters(a.get("presets", ["cinematic"]), float(a.get("intensity", 1.0))),
        },
    },
    {
        "name": "media_adjust",
        "description": "Fine-tune exposure, contrast, highlights, shadows, whites, blacks, temperature, tint, vibrance, saturation, clarity, dehaze, sharpness, noise reduction.",
        "params": {k: "float" for k in _ADJUST_KEYS},
        "run": lambda a: {"adjustments": _normalize_adjustments(a)},
    },
    {
        "name": "media_effects",
        "description": "Apply creative effects: glow, bloom, chromatic aberration, film grain, light leaks, glitch, VHS, prism, tilt-shift, motion blur, radial blur.",
        "params": {"effects": "list", "amount": "float"},
        "run": lambda a: {
            "effects": [
                _effect_config(e, float(a.get("amount", 0.5)))
                for e in a.get("effects", ["glow"])
                if e in _EFFECTS
            ]
        },
    },
    {
        "name": "media_remove_background",
        "description": "AI matting with edge refinement and transparent PNG export.",
        "params": {"edge_refine": "float", "feather": "float", "export_alpha": "bool"},
        "run": lambda a: {"matte": _matte_config(
            float(a.get("edge_refine", 0.5)),
            float(a.get("feather", 0.2)),
            bool(a.get("export_alpha", True)),
        )},
    },
    {
        "name": "media_change_background",
        "description": "Replace background with image, video, color, gradient, blurred, or AI scene.",
        "params": {"mode": "str", "source": "str", "color": "str", "gradient": "list"},
        "run": lambda a: {"background": _background_config(
            a.get("mode", "color"),
            source=a.get("source"),
            color=a.get("color", "#000000"),
            gradient=a.get("gradient", []),
        )},
    },
    {
        "name": "media_trim",
        "description": "Frame-accurate trim, ripple trim, slip/slide, or silence auto-cut.",
        "params": {"mode": "str", "start": "int", "end": "int", "fps": "float"},
        "run": lambda a: {"trim": _trim_config(
            a.get("mode", "frame_accurate"),
            int(a.get("start", 0)),
            int(a.get("end", 0)),
            float(a.get("fps", 30.0)),
        )},
    },
    {
        "name": "media_manipulation",
        "description": "Warp, liquify, perspective, lens distortion, mesh transform, or puppet warp.",
        "params": {"type": "str", "strength": "float"},
        "run": lambda a: {"manipulation": _manip_config(a.get("type", "warp"), float(a.get("strength", 0.5)))},
    },
    {
        "name": "media_merge",
        "description": "Combine clips/images, panorama stitching, HDR bracket merge, or photo stacking.",
        "params": {"mode": "str", "sources": "list"},
        "run": lambda a: {
            "merge": {
                "mode": a.get("mode", "concat") if a.get("mode", "concat") in _MERGE_MODES else "concat",
                "sources": a.get("sources", []),
            }
        },
    },
    {
        "name": "media_blend",
        "description": "27+ blend modes with per-layer masks.",
        "params": {"mode": "str", "opacity": "float", "mask": "dict"},
        "run": lambda a: {"blend": _blend_config(
            a.get("mode", "normal"),
            float(a.get("opacity", 1.0)),
            a.get("mask"),
        )},
    },
    {
        "name": "media_opacity",
        "description": "Layer, fill, or animated opacity with feathered edges.",
        "params": {"opacity": "float", "feather": "float", "animated": "bool", "keyframes": "list"},
        "run": lambda a: {
            "opacity": {
                "value": max(0.0, min(1.0, float(a.get("opacity", 1.0)))),
                "feather": max(0.0, min(1.0, float(a.get("feather", 0.0)))),
                "animated": bool(a.get("animated", False)),
                "keyframes": a.get("keyframes", []),
            }
        },
    },
    {
        "name": "media_remove_objects",
        "description": "AI content-aware fill, magic eraser, and temporal tracking for video.",
        "params": {"regions": "list", "mode": "str", "temporal_track": "bool"},
        "run": lambda a: {
            "remove": {
                "regions": a.get("regions", []),
                "mode": a.get("mode", "content_aware"),
                "temporal_track": bool(a.get("temporal_track", False)),
            }
        },
    },
    {
        "name": "media_texture",
        "description": "Overlay grain, paper, canvas, fabric, dust, or bokeh textures with blend controls.",
        "params": {"texture": "str", "blend": "str", "opacity": "float", "scale": "float"},
        "run": lambda a: {"texture": _texture_config(
            a.get("texture", "grain"),
            a.get("blend", "overlay"),
            float(a.get("opacity", 0.5)),
            float(a.get("scale", 1.0)),
        )},
    },
]