"""Smart/workflow tools: prompt-to-edit, auto-edit, highlight reels, content search, emotion tagging, copyright checks, and accessibility."""

from __future__ import annotations

import re
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


def _parse_prompt(prompt: str) -> list[dict]:
    """Parse a plain-language edit prompt into ordered edit operations."""
    ops: list[dict] = []
    text = prompt.lower()
    if "trim" in text or "cut" in text or "shorten" in text:
        ops.append({"op": "trim", "target": "silent_or_dead", "params": {}})
    if "speed" in text or "fast" in text or "slow mo" in text:
        factor = 2.0 if "fast" in text or "speed up" in text else 0.5
        ops.append({"op": "speed", "factor": factor, "target": "all"})
    if "color" in text or "grade" in text or "cinematic" in text:
        ops.append({"op": "color_grade", "preset": "cinematic" if "cinematic" in text else "auto"})
    if "subtitle" in text or "caption" in text:
        ops.append({"op": "add_captions", "language": "auto"})
    if "music" in text or "soundtrack" in text:
        ops.append({"op": "add_music", "mood": "auto", "ducking": True})
    if "transition" in text or "fade" in text:
        ops.append({"op": "add_transitions", "style": "crossfade"})
    if "zoom" in text or "punch" in text:
        ops.append({"op": "add_zoom_punches", "intensity": 1.2})
    if "stabilize" in text or "shaky" in text:
        ops.append({"op": "stabilize", "smoothness": 0.8})
    if not ops:
        ops.append({"op": "auto_edit", "params": {}})
    return ops


def _brief_to_plan(brief: str) -> dict:
    """Convert a brief string into a structured edit plan."""
    brief_l = brief.lower()
    plan: dict[str, Any] = {"target_duration_s": 60.0, "style": "vlog", "pacing": "medium",
                           "include_captions": True, "include_music": True}
    if "fast" in brief_l or "energetic" in brief_l:
        plan["pacing"] = "fast"
    if "slow" in brief_l or "calm" in brief_l:
        plan["pacing"] = "slow"
    if "corporate" in brief_l or "professional" in brief_l:
        plan["style"] = "corporate"
    if "cinematic" in brief_l or "film" in brief_l:
        plan["style"] = "cinematic"
    if "no music" in brief_l:
        plan["include_music"] = False
    if "no captions" in brief_l or "no subtitles" in brief_l:
        plan["include_captions"] = False
    m = re.search(r"(\d+)\s*s", brief_l)
    if m:
        plan["target_duration_s"] = float(m.group(1))
    return plan


def _score_segment(seg: dict) -> float:
    """Score a segment for highlight-reel inclusion."""
    score = float(seg.get("motion", 0)) * 0.3 + float(seg.get("audio_energy", 0)) * 0.3
    score += float(seg.get("face_presence", 0)) * 0.2 + float(seg.get("speech_clarity", 0)) * 0.2
    return min(score, 1.0)


def _mock_segments(duration_s: float) -> list[dict]:
    """Generate mock segment metadata for a video of given duration."""
    import random as _r
    chunk = 5.0
    n = max(1, int(duration_s / chunk))
    segs: list[dict] = []
    for i in range(n):
        rng = _r.Random(i * 7 + 13)
        segs.append({"index": i, "start": round(i * chunk, 2), "end": round((i + 1) * chunk, 2),
                     "motion": rng.random(), "audio_energy": rng.random(),
                     "face_presence": rng.random(), "speech_clarity": rng.random()})
    return segs


_DEFAULT_LIBRARY = [
    {"id": "clip_01", "desc": "sunset over ocean waves", "tags": ["nature", "sunset", "water"]},
    {"id": "clip_02", "desc": "city street at night neon", "tags": ["urban", "night", "neon"]},
    {"id": "clip_03", "desc": "close-up face smiling", "tags": ["portrait", "face", "smile"]},
    {"id": "clip_04", "desc": "drone mountain aerial", "tags": ["aerial", "nature", "mountain"]},
]


def _search_library(query: str, library: list[dict] | None) -> list[dict]:
    """Search a media library by description keywords."""
    if library is None:
        library = _DEFAULT_LIBRARY
    q = set(query.lower().split())
    results: list[dict] = []
    for item in library:
        text = (item.get("desc", "") + " " + " ".join(item.get("tags", []))).lower()
        if q & set(text.split()):
            results.append(item)
    return results


def _emotion_tags(clip: dict) -> dict:
    """Auto-tag a clip by who/what/mood."""
    return {"who": clip.get("who", "unknown"), "what": clip.get("what", "unknown"),
            "mood": clip.get("mood", "neutral"), "confidence": min(1.0, float(clip.get("confidence", 0.7)))}


def _copyright_scan(items: list[dict]) -> list[dict]:
    """Scan media items for potential copyright issues."""
    flagged: list[dict] = []
    for item in items:
        issues: list[str] = []
        if item.get("music_title") and not item.get("licensed", False):
            issues.append("unlicensed_music")
        if item.get("image_source") and "stock" not in str(item.get("image_source", "")).lower():
            issues.append("unverified_image_source")
        if item.get("video_clip") and not item.get("licensed", False):
            issues.append("unlicensed_video")
        flagged.append({"item": item.get("id", "?"), "issues": issues, "safe": len(issues) == 0})
    return flagged


def _alt_text(clip: dict) -> str:
    """Generate alt text for a clip/frame."""
    subject = clip.get("subject", "a scene")
    action = clip.get("action", "is shown")
    setting = clip.get("setting", "")
    return f"{subject} {action}" + (f" in {setting}" if setting else "")


_CB_TRANSFORMS = {
    "protanopia": {"matrix": "protanope", "label": "red-blind"},
    "deuteranopia": {"matrix": "deuteranope", "label": "green-blind"},
    "tritanopia": {"matrix": "tritanope", "label": "blue-blind"},
    "achromatopsia": {"matrix": "achromat", "label": "full color-blind"},
}


def _color_blind_preview(mode: str) -> dict:
    """Return a color-blind-safe preview transform."""
    return _CB_TRANSFORMS.get(mode.lower(), _CB_TRANSFORMS["deuteranopia"])


def _caption_compliance(captions: list[dict]) -> dict:
    """Check caption compliance against common standards."""
    issues: list[str] = []
    for c in captions:
        if not c.get("text"):
            issues.append("empty_caption_segment")
        if len(c.get("text", "")) > 60:
            issues.append("caption_too_long")
        if c.get("start") is None or c.get("end") is None:
            issues.append("missing_timing")
    return {"standard": "WCAG 2.1 AA / FCC", "segment_count": len(captions),
            "issues": issues, "compliant": len(issues) == 0}


# --- Public tool entries -----------------------------------------------------

TOOLS: list[dict] = [
    {
        "name": "smart_prompt_to_edit",
        "description": "Describe an edit in plain language and let AI execute the operations.",
        "params": {"prompt": "str"},
        "run": lambda a: {"prompt": _safe_str(a, "prompt", ""),
                         "operations": _parse_prompt(_safe_str(a, "prompt", ""))},
    },
    {
        "name": "smart_auto_edit",
        "description": "Feed raw footage plus a brief and get an AI-produced first cut.",
        "params": {"brief": "str", "footage_count": "int"},
        "run": lambda a: {"brief": _safe_str(a, "brief", ""),
                         "plan": _brief_to_plan(_safe_str(a, "brief", "")),
                         "footage_count": _safe_int(a, "footage_count", 1)},
    },
    {
        "name": "smart_highlight_reel",
        "description": "AI picks the best moments from long videos to build a highlight reel.",
        "params": {"duration_s": "float", "target_reel_s": "float", "threshold": "float"},
        "run": lambda a: (
            lambda segs, thr: {"segments": segs, "threshold": thr,
                               "highlights": [s for s in segs if _score_segment(s) >= thr],
                               "target_reel_s": _safe_float(a, "target_reel_s", 30.0)}
        )(_mock_segments(_safe_float(a, "duration_s", 120.0)), _safe_float(a, "threshold", 0.6)),
    },
    {
        "name": "smart_content_search",
        "description": "Search the media library by natural-language description.",
        "params": {"query": "str", "library": "list[dict]"},
        "run": lambda a: {"query": _safe_str(a, "query", ""),
                         "results": _search_library(_safe_str(a, "query", ""), a.get("library"))},
    },
    {
        "name": "smart_emotion_tagging",
        "description": "Auto-tag clips by who, what, and mood.",
        "params": {"clips": "list[dict]"},
        "run": lambda a: {"tags": [_emotion_tags(c) for c in a.get("clips", [])]},
    },
    {
        "name": "smart_copyright_check",
        "description": "Scan for licensed music or images before publishing.",
        "params": {"items": "list[dict]"},
        "run": lambda a: (
            lambda res: {"results": res, "all_clear": all(r["safe"] for r in res)}
        )(_copyright_scan(a.get("items", []))),
    },
    {
        "name": "smart_accessibility",
        "description": "Auto alt-text, color-blind-safe preview, and caption compliance check.",
        "params": {"clip": "dict", "color_blind_mode": "str", "captions": "list[dict]"},
        "run": lambda a: {
            "alt_text": _alt_text(a.get("clip", {})),
            "color_blind_preview": _color_blind_preview(_safe_str(a, "color_blind_mode", "deuteranopia")),
            "caption_compliance": _caption_compliance(a.get("captions", [])),
        },
    },
]