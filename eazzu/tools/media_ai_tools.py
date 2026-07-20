"""AI-powered media tools: generative fill/replace, text-to-image/video, image-to-video, face retouch/swap, rotoscoping, auto-reframe, motion tracking, speech-to-text, voiceover, lip sync, silence/scene/beat detection, Ken Burns, depth map, relight, sky replace, weather effects, time remap, frame interpolation, stabilization, deflicker.

Pure-Python configuration generators. No external deps.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Generative
# ---------------------------------------------------------------------------

_CAMERA_MOVES = ["dolly", "pan", "zoom", "orbit", "static"]


def _gen_fill_config(direction: str, size: dict) -> dict:
    return {"direction": direction, "size": size}


def _gen_replace_config(mask: dict, prompt: str) -> dict:
    return {"mask": mask, "prompt": prompt}


def _t2i_config(prompt: str, style: str, aspect: str, count: int) -> dict:
    return {
        "prompt": prompt,
        "style": style,
        "aspect": aspect,
        "count": max(1, min(8, count)),
    }


def _t2v_config(prompt: str, duration: float, fps: int, resolution: str) -> dict:
    return {
        "prompt": prompt,
        "duration": max(0.5, duration),
        "fps": fps,
        "resolution": resolution,
    }


def _i2v_config(camera: str, duration: float) -> dict:
    camera = camera if camera in _CAMERA_MOVES else "static"
    return {"camera_move": camera, "duration": max(0.5, duration)}


# ---------------------------------------------------------------------------
# Face
# ---------------------------------------------------------------------------

_FACE_RETOUCH_OPS = ["skin_smoothing", "blemish_removal", "eye_brighten", "teeth_whiten", "jawline"]


def _face_retouch_config(ops: list, natural: bool) -> dict:
    return {
        "operations": [o for o in ops if o in _FACE_RETOUCH_OPS],
        "natural_look": bool(natural),
    }


def _face_swap_config(source: dict, target: dict, preserve_identity: bool) -> dict:
    return {
        "source": source,
        "target": target,
        "preserve_identity": bool(preserve_identity),
    }


# ---------------------------------------------------------------------------
# Masking / tracking / reframe
# ---------------------------------------------------------------------------

def _rotoscope_config(subject: str, track: bool) -> dict:
    return {"subject": subject, "track_across_frames": bool(track)}


def _auto_reframe_config(target_aspect: str, tracking: bool) -> dict:
    return {"target_aspect": target_aspect, "subject_tracking": bool(tracking)}


def _motion_tracking_config(track_type: str, attach: dict) -> dict:
    track_type = track_type if track_type in ["point", "planar"] else "point"
    return {"type": track_type, "attach": attach}


# ---------------------------------------------------------------------------
# Audio / speech
# ---------------------------------------------------------------------------

_CAPTION_STYLES = ["minimal", "bold", "karaoke", "boxed", "outline"]


def _speech_to_text_config(lang: str, style: str, karaoke: bool) -> dict:
    style = style if style in _CAPTION_STYLES else "minimal"
    return {"language": lang, "style": style, "karaoke_highlight": bool(karaoke)}


def _voiceover_config(voice: str, lang: str, clone: bool) -> dict:
    return {"voice": voice, "language": lang, "voice_clone": bool(clone)}


def _lip_sync_config(audio: dict, quality: str) -> dict:
    return {"audio": audio, "quality": quality}


def _silence_detect_config(remove_pauses: bool, remove_fillers: bool, threshold: float) -> dict:
    return {
        "remove_pauses": bool(remove_pauses),
        "remove_fillers": bool(remove_fillers),
        "threshold_db": threshold,
    }


# ---------------------------------------------------------------------------
# Editing intelligence
# ---------------------------------------------------------------------------

def _scene_detect_config(threshold: float, min_duration: float) -> dict:
    return {"threshold": threshold, "min_duration": min_duration}


def _beat_sync_config(bpm: int, cut_on: str) -> dict:
    cut_on = cut_on if cut_on in ["beat", "downbeat", "bar"] else "beat"
    return {"bpm": bpm, "cut_on": cut_on}


def _ken_burns_config(zoom: float, pan: str) -> dict:
    return {"zoom": zoom, "pan_direction": pan}


def _depth_config(quality: str, parallax: float) -> dict:
    return {"quality": quality, "parallax_strength": parallax}


def _relight_config(direction: str, intensity: float, color: str) -> dict:
    return {"direction": direction, "intensity": intensity, "color": color}


def _sky_replace_config(sky: str, adjust_reflection: bool, color_match: bool) -> dict:
    return {"sky": sky, "adjust_reflection": bool(adjust_reflection), "color_match": bool(color_match)}


# ---------------------------------------------------------------------------
# Weather / time / interpolation / stabilize / deflicker
# ---------------------------------------------------------------------------

_WEATHER = ["rain", "snow", "fog", "sun_rays", "lens_flares"]


def _weather_config(effect: str, intensity: float) -> dict:
    effect = effect if effect in _WEATHER else "rain"
    return {"effect": effect, "intensity": intensity}


_TIME_REMAP_MODES = ["speed_ramp", "slow_mo", "reverse", "freeze_frame", "optical_flow"]


def _time_remap_config(mode: str, speed: float) -> dict:
    mode = mode if mode in _TIME_REMAP_MODES else "speed_ramp"
    return {"mode": mode, "speed": speed}


def _frame_interpolate_config(target_fps: int, method: str) -> dict:
    return {"target_fps": target_fps, "method": method}


def _stabilize_config(smoothness: float, correct_rs: bool) -> dict:
    return {"smoothness": smoothness, "rolling_shutter_correction": bool(correct_rs)}


def _deflicker_config(strength: float, temporal_window: int) -> dict:
    return {"strength": strength, "temporal_window": temporal_window}


# ===========================================================================
# TOOLS
# ===========================================================================

TOOLS: list[dict] = [
    {
        "name": "ai_generative_fill",
        "description": "Outpaint or extend canvas in a given direction with AI-generated content.",
        "params": {"direction": "str", "size": "dict"},
        "run": lambda a: {"fill": _gen_fill_config(a.get("direction", "right"), a.get("size", {"w": 256, "h": 256}))},
    },
    {
        "name": "ai_generative_replace",
        "description": "Highlight an area and describe a replacement; AI fills it in.",
        "params": {"mask": "dict", "prompt": "str"},
        "run": lambda a: {"replace": _gen_replace_config(a.get("mask", {}), a.get("prompt", ""))},
    },
    {
        "name": "ai_text_to_image",
        "description": "Generate images from a text prompt with style and aspect options.",
        "params": {"prompt": "str", "style": "str", "aspect": "str", "count": "int"},
        "run": lambda a: {"generation": _t2i_config(a.get("prompt", ""), a.get("style", "photorealistic"), a.get("aspect", "1:1"), int(a.get("count", 1)))},
    },
    {
        "name": "ai_text_to_video",
        "description": "Generate a video clip from a text prompt.",
        "params": {"prompt": "str", "duration": "float", "fps": "int", "resolution": "str"},
        "run": lambda a: {"generation": _t2v_config(a.get("prompt", ""), float(a.get("duration", 3.0)), int(a.get("fps", 30)), a.get("resolution", "1080p"))},
    },
    {
        "name": "ai_image_to_video",
        "description": "Animate a still image with camera moves: dolly, pan, zoom, orbit.",
        "params": {"camera": "str", "duration": "float"},
        "run": lambda a: {"animation": _i2v_config(a.get("camera", "static"), float(a.get("duration", 3.0)))},
    },
    {
        "name": "ai_face_retouch",
        "description": "Skin smoothing, blemish removal, eye brighten, teeth whiten, jawline with natural-look toggle.",
        "params": {"operations": "list", "natural": "bool"},
        "run": lambda a: {"retouch": _face_retouch_config(a.get("operations", []), bool(a.get("natural", True)))},
    },
    {
        "name": "ai_face_swap",
        "description": "Swap faces while preserving identity across edits.",
        "params": {"source": "dict", "target": "dict", "preserve_identity": "bool"},
        "run": lambda a: {"swap": _face_swap_config(a.get("source", {}), a.get("target", {}), bool(a.get("preserve_identity", True)))},
    },
    {
        "name": "ai_rotoscoping",
        "description": "Automatically mask moving subjects across frames.",
        "params": {"subject": "str", "track": "bool"},
        "run": lambda a: {"mask": _rotoscope_config(a.get("subject", "person"), bool(a.get("track", True)))},
    },
    {
        "name": "ai_auto_reframe",
        "description": "Convert 16:9 to 9:16 or 1:1 with subject tracking.",
        "params": {"target_aspect": "str", "tracking": "bool"},
        "run": lambda a: {"reframe": _auto_reframe_config(a.get("target_aspect", "9:16"), bool(a.get("tracking", True)))},
    },
    {
        "name": "ai_motion_tracking",
        "description": "Attach text or effects to a moving object via point or planar tracking.",
        "params": {"type": "str", "attach": "dict"},
        "run": lambda a: {"tracking": _motion_tracking_config(a.get("type", "point"), a.get("attach", {}))},
    },
    {
        "name": "ai_speech_to_text",
        "description": "Auto subtitles with caption styles, multi-language, and karaoke highlight.",
        "params": {"language": "str", "style": "str", "karaoke": "bool"},
        "run": lambda a: {"captions": _speech_to_text_config(a.get("language", "en"), a.get("style", "minimal"), bool(a.get("karaoke", False)))},
    },
    {
        "name": "ai_voiceover",
        "description": "Text-to-speech in multiple voices/languages with optional voice cloning.",
        "params": {"voice": "str", "language": "str", "clone": "bool"},
        "run": lambda a: {"voiceover": _voiceover_config(a.get("voice", "narrator"), a.get("language", "en"), bool(a.get("clone", False)))},
    },
    {
        "name": "ai_lip_sync",
        "description": "Match mouth movement to audio track.",
        "params": {"audio": "dict", "quality": "str"},
        "run": lambda a: {"lip_sync": _lip_sync_config(a.get("audio", {}), a.get("quality", "high"))},
    },
    {
        "name": "ai_silence_detect",
        "description": "Remove pauses and filler words from audio/video.",
        "params": {"remove_pauses": "bool", "remove_fillers": "bool", "threshold": "float"},
        "run": lambda a: {"silence": _silence_detect_config(bool(a.get("remove_pauses", True)), bool(a.get("remove_fillers", True)), float(a.get("threshold", -40.0)))},
    },
    {
        "name": "ai_scene_detect",
        "description": "Split footage into individual shots.",
        "params": {"threshold": "float", "min_duration": "float"},
        "run": lambda a: {"scenes": _scene_detect_config(float(a.get("threshold", 0.5)), float(a.get("min_duration", 0.5)))},
    },
    {
        "name": "ai_beat_sync",
        "description": "Cut video to music beats.",
        "params": {"bpm": "int", "cut_on": "str"},
        "run": lambda a: {"beat_sync": _beat_sync_config(int(a.get("bpm", 120)), a.get("cut_on", "beat"))},
    },
    {
        "name": "ai_ken_burns",
        "description": "Content-aware pan and zoom for still images.",
        "params": {"zoom": "float", "pan": "str"},
        "run": lambda a: {"ken_burns": _ken_burns_config(float(a.get("zoom", 1.2)), a.get("pan", "center"))},
    },
    {
        "name": "ai_depth_map",
        "description": "Extract depth map and apply parallax motion.",
        "params": {"quality": "str", "parallax": "float"},
        "run": lambda a: {"depth": _depth_config(a.get("quality", "high"), float(a.get("parallax", 0.5)))},
    },
    {
        "name": "ai_relight",
        "description": "Change lighting direction, intensity, and color.",
        "params": {"direction": "str", "intensity": "float", "color": "str"},
        "run": lambda a: {"relight": _relight_config(a.get("direction", "left"), float(a.get("intensity", 0.8)), a.get("color", "#ffffff"))},
    },
    {
        "name": "ai_sky_replace",
        "description": "Swap skies with automatic reflection and color adjustment.",
        "params": {"sky": "str", "adjust_reflection": "bool", "color_match": "bool"},
        "run": lambda a: {"sky": _sky_replace_config(a.get("sky", "sunset"), bool(a.get("adjust_reflection", True)), bool(a.get("color_match", True)))},
    },
    {
        "name": "ai_weather_effects",
        "description": "Add rain, snow, fog, sun rays, or lens flares.",
        "params": {"effect": "str", "intensity": "float"},
        "run": lambda a: {"weather": _weather_config(a.get("effect", "rain"), float(a.get("intensity", 0.5)))},
    },
    {
        "name": "ai_time_remap",
        "description": "Speed ramps, slow-mo, reverse, freeze frame, optical flow.",
        "params": {"mode": "str", "speed": "float"},
        "run": lambda a: {"time_remap": _time_remap_config(a.get("mode", "speed_ramp"), float(a.get("speed", 1.0)))},
    },
    {
        "name": "ai_frame_interpolate",
        "description": "Interpolate frames from 24fps to 60/120fps.",
        "params": {"target_fps": "int", "method": "str"},
        "run": lambda a: {"interpolation": _frame_interpolate_config(int(a.get("target_fps", 60)), a.get("method", "optical_flow"))},
    },
    {
        "name": "ai_stabilize",
        "description": "Warp stabilizer with rolling-shutter correction.",
        "params": {"smoothness": "float", "correct_rs": "bool"},
        "run": lambda a: {"stabilize": _stabilize_config(float(a.get("smoothness", 0.5)), bool(a.get("correct_rs", False)))},
    },
    {
        "name": "ai_deflicker",
        "description": "Remove flicker from timelapses.",
        "params": {"strength": "float", "temporal_window": "int"},
        "run": lambda a: {"deflicker": _deflicker_config(float(a.get("strength", 0.5)), int(a.get("temporal_window", 5)))},
    },
]