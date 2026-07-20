"""Audio tools for video editing: ducking, noise removal, voice enhancement, mixing, music generation, and SFX library."""

from __future__ import annotations

import math
import random
from typing import Any


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp a value to the [lo, hi] range."""
    return max(lo, min(hi, value))


def _db_to_gain(db: float) -> float:
    """Convert decibels to a linear gain factor."""
    return 10.0 ** (db / 20.0)


def _safe_str(a: dict, key: str, default: str = "") -> str:
    """Return a cleaned string param or a default."""
    return str(a.get(key, default)).strip() or default


def _safe_float(a: dict, key: str, default: float) -> float:
    """Return a float param or a default, tolerating bad input."""
    try:
        return float(a.get(key, default))
    except (TypeError, ValueError):
        return default


def _duck_plan(voice_segments: list[dict], reduction_db: float, fade_ms: int) -> list[dict]:
    """Build a music ducking envelope from voice segments."""
    envelope: list[dict] = []
    for seg in voice_segments:
        start = float(seg.get("start", 0.0))
        end = float(seg.get("end", start + 1.0))
        envelope.append({"t": start, "gain": _db_to_gain(-reduction_db), "type": "duck"})
        envelope.append({"t": end, "gain": 1.0, "type": "restore"})
        envelope.append({"t": max(0.0, start - fade_ms / 1000.0), "gain": _db_to_gain(-reduction_db), "type": "fade_in"})
        envelope.append({"t": end + fade_ms / 1000.0, "gain": 1.0, "type": "fade_out"})
    envelope.sort(key=lambda p: p["t"])
    return envelope


_NOISE_PROFILES = {
    "hum": {"freq": 60.0, "harmonics": 3, "q": 30, "reduction_db": -18},
    "hiss": {"freq": 8000.0, "harmonics": 0, "q": 0.7, "reduction_db": -12},
    "wind": {"freq": 200.0, "harmonics": 0, "q": 0.5, "reduction_db": -15},
    "chatter": {"freq": 1200.0, "harmonics": 0, "q": 1.2, "reduction_db": -10},
}


def _noise_profile(noise_types: list[str]) -> dict:
    """Return a synthetic noise profile for the given noise categories."""
    merged: dict[str, Any] = {"bands": [], "overall_db": 0.0}
    for n in noise_types:
        p = _NOISE_PROFILES.get(n.lower())
        if not p:
            continue
        merged["bands"].append({"type": n, **p})
        merged["overall_db"] += p["reduction_db"]
    merged["overall_db"] = _clamp(merged["overall_db"], -40.0, 0.0)
    return merged


def _eq_band(freq: float, gain_db: float, q: float = 1.0) -> dict:
    """Describe a single EQ band."""
    return {"freq": round(freq, 1), "gain_db": round(gain_db, 2), "q": round(q, 3)}


def _compressor(threshold_db: float, ratio: float, attack_ms: float, release_ms: float) -> dict:
    """Return a compressor config dict."""
    return {"threshold_db": threshold_db, "ratio": f"{ratio:.1f}:1", "attack_ms": attack_ms,
            "release_ms": release_ms, "makeup_db": round(max(0.0, -threshold_db) * 0.25, 2)}


_REVERB_PRESETS = {
    "small_room": {"decay_ms": 400, "predelay_ms": 12, "wet": 0.18},
    "hall": {"decay_ms": 2400, "predelay_ms": 40, "wet": 0.30},
    "plate": {"decay_ms": 1800, "predelay_ms": 8, "wet": 0.25},
    "studio": {"decay_ms": 900, "predelay_ms": 20, "wet": 0.15},
}

_MOOD_SCALES = {
    "happy": [0, 4, 7, 12, 16, 19], "sad": [0, 3, 7, 12, 15, 19],
    "epic": [0, 7, 12, 19, 24, 31], "calm": [0, 5, 7, 12, 17, 19],
    "tense": [0, 1, 6, 7, 13, 18], "upbeat": [0, 4, 7, 11, 14, 18],
}


def _reverb_ir(room: str) -> dict:
    """Return a synthetic reverb impulse-response description."""
    return _REVERB_PRESETS.get(room, _REVERB_PRESETS["studio"])


def _generate_notes(mood: str, duration_s: float, tempo_bpm: int) -> list[dict]:
    """Generate a simple note sequence for a mood/duration."""
    scale = _MOOD_SCALES.get(mood.lower(), _MOOD_SCALES["happy"])
    beat = 60.0 / tempo_bpm
    total_beats = int(duration_s / beat)
    rng = random.Random(hash(mood) & 0xFFFF)
    notes: list[dict] = []
    t = 0.0
    for i in range(total_beats):
        interval = scale[i % len(scale)]
        dur = beat * rng.choice([0.5, 1.0, 1.0, 2.0])
        notes.append({"start": round(t, 3), "duration": round(dur, 3),
                      "semitone": interval, "velocity": rng.randint(60, 100)})
        t += dur
    return notes


_SFX_CATALOG = [
    {"id": "sfx_whoosh_01", "name": "Whoosh Fast", "tags": ["transition", "swoosh"], "duration_s": 0.8},
    {"id": "sfx_impact_01", "name": "Cinematic Impact", "tags": ["impact", "boom"], "duration_s": 1.2},
    {"id": "sfx_pop_01", "name": "Pop", "tags": ["ui", "pop", "click"], "duration_s": 0.15},
    {"id": "sfx_rain_01", "name": "Rain Ambience", "tags": ["ambient", "weather"], "duration_s": 10.0},
    {"id": "sfx_typing_01", "name": "Keyboard Typing", "tags": ["office", "typing"], "duration_s": 3.0},
    {"id": "sfx_laugh_01", "name": "Crowd Laugh", "tags": ["crowd", "laugh", "people"], "duration_s": 2.5},
    {"id": "sfx_door_01", "name": "Door Close", "tags": ["door", "thud"], "duration_s": 0.6},
    {"id": "sfx_bell_01", "name": "Notification Bell", "tags": ["ui", "bell", "alert"], "duration_s": 0.9},
]


def _search_sfx(query: str) -> list[dict]:
    """Search the built-in SFX catalog by name or tags."""
    q = query.lower()
    return [s for s in _SFX_CATALOG
            if q == "" or q in s["name"].lower() or any(q in t.lower() for t in s["tags"])]


def _sync_suggestions(sfx: dict, clip_duration: float) -> list[dict]:
    """Suggest placement points for an SFX within a clip."""
    dur = sfx["duration_s"]
    if dur >= clip_duration:
        return [{"at": 0.0, "reason": "full-length overlay"}]
    return [
        {"at": 0.0, "reason": "intro hit"},
        {"at": round(clip_duration / 2 - dur / 2, 3), "reason": "midpoint accent"},
        {"at": round(clip_duration - dur, 3), "reason": "outro stinger"},
    ]


# --- Public tool entries -----------------------------------------------------

TOOLS: list[dict] = [
    {
        "name": "audio_ducking",
        "description": "Automatically lower music bed under voiceover segments and restore it between them.",
        "params": {"voice_segments": "list[dict]", "reduction_db": "float", "fade_ms": "int"},
        "run": lambda a: {
            "ducking": _duck_plan(a.get("voice_segments", []),
                                  _safe_float(a, "reduction_db", 12.0),
                                  int(_safe_float(a, "fade_ms", 150))),
            "reduction_db": _safe_float(a, "reduction_db", 12.0),
            "fade_ms": int(_safe_float(a, "fade_ms", 150)),
        },
    },
    {
        "name": "audio_noise_removal",
        "description": "Remove hum, hiss, wind, or background chatter from an audio track.",
        "params": {"noise_types": "list[str]", "strength": "float"},
        "run": lambda a: {
            "profile": _noise_profile(a.get("noise_types", ["hiss"])),
            "strength": _clamp(_safe_float(a, "strength", 0.8)),
            "output_gain_db": 3.0,
        },
    },
    {
        "name": "audio_voice_enhance",
        "description": "Turn phone or field recordings into studio-quality voice with EQ, de-ess, and repair.",
        "params": {"source": "str", "target_tone": "str", "deess": "bool"},
        "run": lambda a: {
            "eq": [_eq_band(80, -6, 0.7), _eq_band(300, -2, 1.0),
                   _eq_band(3500, 3, 0.9), _eq_band(8000, 2, 0.8)],
            "deess": bool(a.get("deess", True)),
            "deess_freq": 6800,
            "compressor": _compressor(-24, 3.0, 8, 120),
            "reverb": _reverb_ir("studio"),
            "target_tone": _safe_str(a, "target_tone", "warm"),
        },
    },
    {
        "name": "audio_mixer",
        "description": "Full mixing suite: parametric EQ, compressor, and reverb across multiple stems.",
        "params": {"stems": "list[str]", "room": "str", "master_lufs": "float"},
        "run": lambda a: {
            "stems": [{"name": s, "eq": [_eq_band(100, -3, 1.0), _eq_band(4000, 2, 0.9)],
                       "compressor": _compressor(-18, 2.5, 10, 100)}
                      for s in a.get("stems", ["voice", "music", "sfx"])],
            "reverb": _reverb_ir(_safe_str(a, "room", "studio")),
            "master_lufs": _safe_float(a, "master_lufs", -14.0),
            "limiter_ceiling_db": -1.0,
        },
    },
    {
        "name": "audio_music_generation",
        "description": "Compose royalty-free music tracks matching a mood and target duration.",
        "params": {"mood": "str", "duration_s": "float", "tempo_bpm": "int"},
        "run": lambda a: {
            "mood": _safe_str(a, "mood", "happy"),
            "duration_s": _safe_float(a, "duration_s", 30.0),
            "tempo_bpm": int(_safe_float(a, "tempo_bpm", 120)),
            "notes": _generate_notes(_safe_str(a, "mood", "happy"),
                                     _safe_float(a, "duration_s", 30.0),
                                     int(_safe_float(a, "tempo_bpm", 120))),
            "license": "royalty-free / CC0",
        },
    },
    {
        "name": "audio_sfx_library",
        "description": "Search a built-in sound-effects library and get auto-sync placement suggestions.",
        "params": {"query": "str", "clip_duration": "float"},
        "run": lambda a: {
            "query": _safe_str(a, "query", ""),
            "results": [{**sfx, "suggestions": _sync_suggestions(sfx, _safe_float(a, "clip_duration", 10.0))}
                        for sfx in _search_sfx(_safe_str(a, "query", ""))],
        },
    },
]