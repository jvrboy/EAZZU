"""Creative and compositional tools: layer system, masking, blend-if, vector shapes, text/typography, stickers/GIFs, transitions, split screen, chroma key, duotone, vignette, grain engine.

Pure-Python configuration generators. No external deps.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Layer system
# ---------------------------------------------------------------------------

_LAYER_TYPES = ["normal", "adjustment", "smart_object", "group", "clipping_mask"]


def _layer_config(ltype: str, name: str, visible: bool, opacity: float) -> dict:
    ltype = ltype if ltype in _LAYER_TYPES else "normal"
    return {
        "type": ltype,
        "name": name,
        "visible": bool(visible),
        "opacity": max(0.0, min(1.0, opacity)),
    }


# ---------------------------------------------------------------------------
# Masking
# ---------------------------------------------------------------------------

_MASK_TYPES = ["brush", "gradient", "radial", "luminosity", "ai_subject"]


def _mask_config(mtype: str, animated: bool, feather: float) -> dict:
    mtype = mtype if mtype in _MASK_TYPES else "brush"
    return {"type": mtype, "animated": bool(animated), "feather": max(0.0, min(1.0, feather))}


# ---------------------------------------------------------------------------
# Blend-if
# ---------------------------------------------------------------------------

_BLEND_IF_RANGES = ["tonal", "color"]


def _blend_if_config(range_type: str, channel: str, lower: int, upper: int) -> dict:
    range_type = range_type if range_type in _BLEND_IF_RANGES else "tonal"
    return {
        "range": range_type,
        "channel": channel,
        "lower_bound": max(0, min(255, lower)),
        "upper_bound": max(0, min(255, upper)),
    }


# ---------------------------------------------------------------------------
# Vector shapes
# ---------------------------------------------------------------------------

_SHAPE_TYPES = ["rectangle", "ellipse", "polygon", "line", "custom_path", "custom_mask"]


def _vector_config(shape: str, points: list, fill: str, stroke: float) -> dict:
    shape = shape if shape in _SHAPE_TYPES else "rectangle"
    return {"shape": shape, "points": points, "fill": fill, "stroke_width": stroke}


# ---------------------------------------------------------------------------
# Text / typography
# ---------------------------------------------------------------------------

_TEXT_EFFECTS = ["kinetic", "variable_font", "curve_along_path", "3d", "text_behind_subject"]


def _text_config(text: str, effect: str, font: str, size: int) -> dict:
    effect = effect if effect in _TEXT_EFFECTS else "kinetic"
    return {"text": text, "effect": effect, "font": font, "size": size}


# ---------------------------------------------------------------------------
# Stickers / GIFs
# ---------------------------------------------------------------------------

def _sticker_config(name: str, duration: float, loop: bool) -> dict:
    return {"sticker": name, "duration": duration, "loop": bool(loop)}


# ---------------------------------------------------------------------------
# Transitions
# ---------------------------------------------------------------------------

_TRANSITIONS = [
    "cross_dissolve", "whip_pan", "zoom_blur", "morph_cut",
    "luma_fade", "glitch", "3d_flip",
]


def _transition_config(ttype: str, duration: float) -> dict:
    ttype = ttype if ttype in _TRANSITIONS else "cross_dissolve"
    return {"type": ttype, "duration": max(0.0, duration)}


# ---------------------------------------------------------------------------
# Split screen
# ---------------------------------------------------------------------------

_SPLIT_LAYOUTS = ["grid_2x2", "grid_3x3", "pip", "side_by_side", "multi_cam_sync"]


def _split_config(layout: str, clips: list) -> dict:
    layout = layout if layout in _SPLIT_LAYOUTS else "side_by_side"
    return {"layout": layout, "clips": clips}


# ---------------------------------------------------------------------------
# Chroma key
# ---------------------------------------------------------------------------

def _chroma_config(key_color: str, spill: float, edge_soft: float) -> dict:
    return {
        "key_color": key_color,
        "spill_suppression": max(0.0, min(1.0, spill)),
        "edge_softening": max(0.0, min(1.0, edge_soft)),
    }


# ---------------------------------------------------------------------------
# Duotone
# ---------------------------------------------------------------------------

_DUOTONE_MODES = ["duotone", "tritone", "gradient_map"]


def _duotone_config(mode: str, colors: list) -> dict:
    mode = mode if mode in _DUOTONE_MODES else "duotone"
    return {"mode": mode, "colors": colors}


# ---------------------------------------------------------------------------
# Vignette
# ---------------------------------------------------------------------------

def _vignette_config(amount: float, feather: float, center_offset: tuple) -> dict:
    return {
        "amount": max(-1.0, min(1.0, amount)),
        "feather": max(0.0, min(1.0, feather)),
        "center_offset": center_offset,
    }


# ---------------------------------------------------------------------------
# Grain engine
# ---------------------------------------------------------------------------

def _grain_config(size: float, roughness: float, per_channel: bool) -> dict:
    return {
        "size": max(0.0, min(1.0, size)),
        "roughness": max(0.0, min(1.0, roughness)),
        "per_channel": bool(per_channel),
    }


# ===========================================================================
# TOOLS
# ===========================================================================

TOOLS: list[dict] = [
    {
        "name": "creative_layer_system",
        "description": "Unlimited layers, groups, adjustment layers, smart objects, and clipping masks.",
        "params": {"type": "str", "name": "str", "visible": "bool", "opacity": "float"},
        "run": lambda a: {"layer": _layer_config(a.get("type", "normal"), a.get("name", "Layer"), bool(a.get("visible", True)), float(a.get("opacity", 1.0)))},
    },
    {
        "name": "creative_masking",
        "description": "Brush, gradient, radial, luminosity, or AI subject masks with animation support.",
        "params": {"type": "str", "animated": "bool", "feather": "float"},
        "run": lambda a: {"mask": _mask_config(a.get("type", "brush"), bool(a.get("animated", False)), float(a.get("feather", 0.0)))},
    },
    {
        "name": "creative_blend_if",
        "description": "Range masks by tonal or color range with per-channel control.",
        "params": {"range": "str", "channel": "str", "lower": "int", "upper": "int"},
        "run": lambda a: {"blend_if": _blend_if_config(a.get("range", "tonal"), a.get("channel", "rgb"), int(a.get("lower", 0)), int(a.get("upper", 255)))},
    },
    {
        "name": "creative_vector_shapes",
        "description": "Draw shapes, paths, or custom masks.",
        "params": {"shape": "str", "points": "list", "fill": "str", "stroke": "float"},
        "run": lambda a: {"vector": _vector_config(a.get("shape", "rectangle"), a.get("points", []), a.get("fill", "#ffffff"), float(a.get("stroke", 0.0)))},
    },
    {
        "name": "creative_text_typography",
        "description": "Kinetic text, variable fonts, curve-along-path, 3D text, text-behind-subject.",
        "params": {"text": "str", "effect": "str", "font": "str", "size": "int"},
        "run": lambda a: {"text": _text_config(a.get("text", ""), a.get("effect", "kinetic"), a.get("font", "Inter"), int(a.get("size", 48)))},
    },
    {
        "name": "creative_stickers_gifs",
        "description": "Animated overlay stickers and GIFs from a library.",
        "params": {"name": "str", "duration": "float", "loop": "bool"},
        "run": lambda a: {"sticker": _sticker_config(a.get("name", "emoji"), float(a.get("duration", 2.0)), bool(a.get("loop", True)))},
    },
    {
        "name": "creative_transitions",
        "description": "Cross-dissolve, whip pan, zoom blur, morph cut, luma fade, glitch, 3D flip.",
        "params": {"type": "str", "duration": "float"},
        "run": lambda a: {"transition": _transition_config(a.get("type", "cross_dissolve"), float(a.get("duration", 0.5)))},
    },
    {
        "name": "creative_split_screen",
        "description": "Grid layouts, picture-in-picture, and multi-cam sync.",
        "params": {"layout": "str", "clips": "list"},
        "run": lambda a: {"split": _split_config(a.get("layout", "side_by_side"), a.get("clips", []))},
    },
    {
        "name": "creative_chroma_key",
        "description": "Green screen keying with spill suppression and edge softening.",
        "params": {"key_color": "str", "spill": "float", "edge_soft": "float"},
        "run": lambda a: {"chroma": _chroma_config(a.get("key_color", "#00ff00"), float(a.get("spill", 0.5)), float(a.get("edge_soft", 0.3)))},
    },
    {
        "name": "creative_duotone",
        "description": "Duotone, tritone, and gradient map color grading.",
        "params": {"mode": "str", "colors": "list"},
        "run": lambda a: {"duotone": _duotone_config(a.get("mode", "duotone"), a.get("colors", ["#1a1a2e", "#e94560"]))},
    },
    {
        "name": "creative_vignette",
        "description": "Radial darken or lighten with feather and center offset.",
        "params": {"amount": "float", "feather": "float", "center_offset": "tuple"},
        "run": lambda a: {"vignette": _vignette_config(float(a.get("amount", -0.5)), float(a.get("feather", 0.5)), a.get("center_offset", (0, 0)))},
    },
    {
        "name": "creative_grain_engine",
        "description": "Analog film grain with per-channel, size, and roughness controls.",
        "params": {"size": "float", "roughness": "float", "per_channel": "bool"},
        "run": lambda a: {"grain": _grain_config(float(a.get("size", 0.5)), float(a.get("roughness", 0.5)), bool(a.get("per_channel", False)))},
    },
]