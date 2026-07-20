"""Precision and pro tools: curves/levels, scopes, match frame, node compositing, proxy workflow, batch processing, presets/templates, version history, collaboration, cloud render.

Pure-Python configuration generators. No external deps.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Curves / levels
# ---------------------------------------------------------------------------

_CURVE_CHANNELS = ["rgb", "red", "green", "blue", "luminance"]


def _curves_config(channel: str, points: list) -> dict:
    channel = channel if channel in _CURVE_CHANNELS else "rgb"
    return {"channel": channel, "points": points}


def _levels_config(channel: str, black: int, white: int, gamma: float) -> dict:
    channel = channel if channel in _CURVE_CHANNELS else "rgb"
    return {
        "channel": channel,
        "black_point": max(0, min(255, black)),
        "white_point": max(0, min(255, white)),
        "gamma": max(0.1, min(10.0, gamma)),
    }


# ---------------------------------------------------------------------------
# Scopes
# ---------------------------------------------------------------------------

_SCOPE_TYPES = ["waveform", "vectorscope", "rgb_parade", "histogram", "broadcast_safe"]


def _scope_config(scope: str, broadcast_safe: bool) -> dict:
    scope = scope if scope in _SCOPE_TYPES else "waveform"
    return {"scope": scope, "broadcast_safe_monitoring": bool(broadcast_safe)}


# ---------------------------------------------------------------------------
# Match frame
# ---------------------------------------------------------------------------

_MATCH_ATTRS = ["exposure", "color", "white_balance", "contrast"]


def _match_config(source: dict, target: dict, attributes: list) -> dict:
    attributes = [a for a in attributes if a in _MATCH_ATTRS] or _MATCH_ATTRS
    return {"source": source, "target": target, "match_attributes": attributes}


# ---------------------------------------------------------------------------
# Node compositing
# ---------------------------------------------------------------------------

def _node_config(nodes: list, connections: list) -> dict:
    return {"nodes": nodes, "connections": connections}


# ---------------------------------------------------------------------------
# Proxy workflow
# ---------------------------------------------------------------------------

_PROXY_QUALITY = ["quarter", "half", "full"]


def _proxy_config(quality: str, auto_toggle: bool) -> dict:
    quality = quality if quality in _PROXY_QUALITY else "half"
    return {"quality": quality, "auto_toggle": bool(auto_toggle)}


# ---------------------------------------------------------------------------
# Batch processing
# ---------------------------------------------------------------------------

def _batch_config(stack: list, sources: list, parallel: int) -> dict:
    return {
        "edit_stack": stack,
        "sources": sources,
        "parallel_workers": max(1, min(32, parallel)),
    }


# ---------------------------------------------------------------------------
# Presets / templates
# ---------------------------------------------------------------------------

_PRESET_TYPES = ["edit_recipe", "lut", "effect_stack"]


def _preset_config(name: str, ptype: str, data: dict) -> dict:
    ptype = ptype if ptype in _PRESET_TYPES else "edit_recipe"
    return {"name": name, "type": ptype, "data": data, "action": "save"}


def _preset_import_config(source: str) -> dict:
    return {"source": source, "action": "import"}


# ---------------------------------------------------------------------------
# Version history
# ---------------------------------------------------------------------------

def _version_config(action: str, label: str, branch: str) -> dict:
    action = action if action in ["save", "branch", "revert", "compare"] else "save"
    return {"action": action, "label": label, "branch": branch}


# ---------------------------------------------------------------------------
# Collaboration
# ---------------------------------------------------------------------------

def _collab_config(users: list, comments: list, mode: str) -> dict:
    mode = mode if mode in ["realtime", "async"] else "realtime"
    return {"users": users, "comments": comments, "mode": mode}


# ---------------------------------------------------------------------------
# Cloud render
# ---------------------------------------------------------------------------

_RENDER_FORMATS = ["mp4", "mov", "prores", "webm", "png_sequence"]


def _cloud_render_config(format: str, resolution: str, priority: str) -> dict:
    format = format if format in _RENDER_FORMATS else "mp4"
    priority = priority if priority in ["low", "normal", "high"] else "normal"
    return {"format": format, "resolution": resolution, "priority": priority}


# ===========================================================================
# TOOLS
# ===========================================================================

TOOLS: list[dict] = [
    {
        "name": "pro_curves_levels",
        "description": "Per-channel tone curves and levels with histogram scope.",
        "params": {"channel": "str", "points": "list", "black": "int", "white": "int", "gamma": "float"},
        "run": lambda a: {
            "curves": _curves_config(a.get("channel", "rgb"), a.get("points", [(0, 0), (255, 255)])),
            "levels": _levels_config(a.get("channel", "rgb"), int(a.get("black", 0)), int(a.get("white", 255)), float(a.get("gamma", 1.0))),
        },
    },
    {
        "name": "pro_scopes",
        "description": "Waveform, vectorscope, RGB parade, and broadcast-safe monitoring.",
        "params": {"scope": "str", "broadcast_safe": "bool"},
        "run": lambda a: {"scope": _scope_config(a.get("scope", "waveform"), bool(a.get("broadcast_safe", False)))},
    },
    {
        "name": "pro_match_frame",
        "description": "Snap two clips to identical exposure and color.",
        "params": {"source": "dict", "target": "dict", "attributes": "list"},
        "run": lambda a: {"match": _match_config(a.get("source", {}), a.get("target", {}), a.get("attributes", _MATCH_ATTRS))},
    },
    {
        "name": "pro_node_compositing",
        "description": "Non-destructive graph-based effects chaining.",
        "params": {"nodes": "list", "connections": "list"},
        "run": lambda a: {"graph": _node_config(a.get("nodes", []), a.get("connections", []))},
    },
    {
        "name": "pro_proxy_workflow",
        "description": "Edit with low-res proxies and export at full resolution.",
        "params": {"quality": "str", "auto_toggle": "bool"},
        "run": lambda a: {"proxy": _proxy_config(a.get("quality", "half"), bool(a.get("auto_toggle", True)))},
    },
    {
        "name": "pro_batch_processing",
        "description": "Apply an edit stack to hundreds of images or clips.",
        "params": {"stack": "list", "sources": "list", "parallel": "int"},
        "run": lambda a: {"batch": _batch_config(a.get("stack", []), a.get("sources", []), int(a.get("parallel", 4)))},
    },
    {
        "name": "pro_presets_templates",
        "description": "Save, share, and import edit recipes, LUTs, and effect stacks.",
        "params": {"name": "str", "type": "str", "data": "dict", "import_source": "str"},
        "run": lambda a: (
            {"preset": _preset_import_config(a.get("import_source", ""))}
            if a.get("import_source")
            else {"preset": _preset_config(a.get("name", "Untitled"), a.get("type", "edit_recipe"), a.get("data", {}))}
        ),
    },
    {
        "name": "pro_version_history",
        "description": "Non-destructive branching version history.",
        "params": {"action": "str", "label": "str", "branch": "str"},
        "run": lambda a: {"version": _version_config(a.get("action", "save"), a.get("label", "v1"), a.get("branch", "main"))},
    },
    {
        "name": "pro_collaboration",
        "description": "Real-time multi-user editing with comments pinned to the timeline.",
        "params": {"users": "list", "comments": "list", "mode": "str"},
        "run": lambda a: {"collab": _collab_config(a.get("users", []), a.get("comments", []), a.get("mode", "realtime"))},
    },
    {
        "name": "pro_cloud_render",
        "description": "Offload heavy exports to cloud rendering.",
        "params": {"format": "str", "resolution": "str", "priority": "str"},
        "run": lambda a: {"render": _cloud_render_config(a.get("format", "mp4"), a.get("resolution", "1080p"), a.get("priority", "normal"))},
    },
]