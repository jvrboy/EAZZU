"""Export & delivery tools: multi-format encoding, platform presets, HDR, codec control, watermarking, and publishing."""

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


_FORMAT_SPECS: dict[str, dict] = {
    "mp4": {"container": "mp4", "video": "h264", "audio": "aac"},
    "mov": {"container": "mov", "video": "prores", "audio": "pcm"},
    "webm": {"container": "webm", "video": "vp9", "audio": "opus"},
    "gif": {"container": "gif", "video": "gif", "audio": None},
    "heic": {"container": "heic", "video": "hevc", "audio": None},
    "png": {"container": "png", "video": "png", "audio": None},
    "webp": {"container": "webp", "video": "webp", "audio": None},
    "avif": {"container": "avif", "video": "av1", "audio": None},
}

_PLATFORM_PRESETS: dict[str, dict] = {
    "instagram_reel": {"container": "mp4", "video_codec": "h264", "resolution": (1080, 1920),
                      "fps": 30, "max_bitrate_mbps": 3.5, "audio_codec": "aac",
                      "audio_bitrate_kbps": 128, "max_duration_s": 90, "aspect": "9:16"},
    "tiktok": {"container": "mp4", "video_codec": "h264", "resolution": (1080, 1920),
               "fps": 30, "max_bitrate_mbps": 4.0, "audio_codec": "aac",
               "audio_bitrate_kbps": 128, "max_duration_s": 600, "aspect": "9:16"},
    "youtube_shorts": {"container": "mp4", "video_codec": "h264", "resolution": (1080, 1920),
                      "fps": 60, "max_bitrate_mbps": 8.0, "audio_codec": "aac",
                      "audio_bitrate_kbps": 192, "max_duration_s": 60, "aspect": "9:16"},
    "linkedin": {"container": "mp4", "video_codec": "h264", "resolution": (1280, 720),
                 "fps": 30, "max_bitrate_mbps": 5.0, "audio_codec": "aac",
                 "audio_bitrate_kbps": 128, "max_duration_s": 600, "aspect": "16:9"},
    "x": {"container": "mp4", "video_codec": "h264", "resolution": (1280, 720),
          "fps": 30, "max_bitrate_mbps": 5.0, "audio_codec": "aac",
          "audio_bitrate_kbps": 128, "max_duration_s": 140, "aspect": "16:9"},
}

_CODEC_PROFILES: dict[str, dict] = {
    "h264": {"profile": "high", "pixel_format": "yuv420p", "crf": 18},
    "h265": {"profile": "main", "pixel_format": "yuv420p", "crf": 20},
    "prores": {"profile": "422", "pixel_format": "yuv422p10le", "bitrate_mode": "cbr"},
    "av1": {"profile": "main", "pixel_format": "yuv420p", "crf": 24, "cpu_used": 4},
}

_HDR_STANDARDS: dict[str, dict] = {
    "rec2020": {"color_primaries": "bt2020", "transfer": "smpte2084", "matrix": "bt2020nc",
                "max_nits": 1000, "pixel_format": "yuv420p10le"},
    "dolby_vision": {"color_primaries": "bt2020", "transfer": "dolby_vision", "matrix": "bt2020nc",
                     "max_nits": 4000, "pixel_format": "yuv420p12le", "metadata": "xml sidecar"},
    "hdr10": {"color_primaries": "bt2020", "transfer": "smpte2084", "matrix": "bt2020nc",
              "max_nits": 1000, "pixel_format": "yuv420p10le"},
}

_STORAGE_TARGETS: dict[str, dict] = {
    "s3": {"protocol": "s3", "needs_credentials": True},
    "gcs": {"protocol": "gs", "needs_credentials": True},
    "azure": {"protocol": "abfs", "needs_credentials": True},
    "dropbox": {"protocol": "dropbox", "needs_credentials": True},
    "google_drive": {"protocol": "gdrive", "needs_credentials": True},
}

_SOCIAL_TARGETS: dict[str, dict] = {
    "youtube": {"api": "youtube_data_v3", "needs_oauth": True},
    "tiktok": {"api": "tiktok_content_posting", "needs_oauth": True},
    "instagram": {"api": "instagram_graph", "needs_oauth": True},
    "x": {"api": "x_api_v2", "needs_oauth": True},
    "linkedin": {"api": "linkedin_share", "needs_oauth": True},
}


def _bitrate_estimate(resolution: tuple[int, int], fps: int, quality: str) -> float:
    """Estimate a target bitrate (Mbps) from resolution, fps, and quality label."""
    w, h = resolution
    base = w * h * fps / 1_000_000
    factors = {"low": 0.05, "medium": 0.08, "high": 0.12, "lossless": 0.20}
    return round(base * factors.get(quality, 0.10), 2)


def _watermark_layout(position: str, wm_w: int, wm_h: int, frame_w: int, frame_h: int, margin: int = 24) -> dict:
    """Compute pixel coordinates for a watermark position."""
    positions = {
        "top_left": (margin, margin),
        "top_right": (frame_w - wm_w - margin, margin),
        "bottom_left": (margin, frame_h - wm_h - margin),
        "bottom_right": (frame_w - wm_w - margin, frame_h - wm_h - margin),
        "center": ((frame_w - wm_w) // 2, (frame_h - wm_h) // 2),
    }
    x, y = positions.get(position, positions["bottom_right"])
    return {"x": x, "y": y, "w": wm_w, "h": wm_h, "position": position}


# --- Public tool entries -----------------------------------------------------

TOOLS: list[dict] = [
    {
        "name": "export_multi_format",
        "description": "Export a timeline to one or more of: MP4, MOV, WebM, GIF, HEIC, PNG, WebP, AVIF.",
        "params": {"formats": "list[str]", "resolution": "str", "quality": "str"},
        "run": lambda a: {
            "outputs": [{"format": fmt, "spec": _FORMAT_SPECS.get(fmt, _FORMAT_SPECS["mp4"]),
                         "bitrate_mbps": _bitrate_estimate((1920, 1080), 30, _safe_str(a, "quality", "high"))}
                        for fmt in a.get("formats", ["mp4"]) if fmt in _FORMAT_SPECS],
            "resolution": _safe_str(a, "resolution", "1920x1080"),
        },
    },
    {
        "name": "export_platform_presets",
        "description": "Export with correct specs for Instagram Reel, TikTok, YouTube Shorts, LinkedIn, or X.",
        "params": {"platform": "str", "quality": "str"},
        "run": lambda a: (
            lambda p: {
                "platform": p,
                "preset": _PLATFORM_PRESETS.get(p, _PLATFORM_PRESETS["instagram_reel"]),
                "estimated_bitrate_mbps": _bitrate_estimate(
                    _PLATFORM_PRESETS.get(p, _PLATFORM_PRESETS["instagram_reel"])["resolution"],
                    _PLATFORM_PRESETS.get(p, _PLATFORM_PRESETS["instagram_reel"])["fps"],
                    _safe_str(a, "quality", "high")),
            })(_safe_str(a, "platform", "instagram_reel")),
    },
    {
        "name": "export_hdr",
        "description": "Export HDR video using Rec.2020, HDR10, or Dolby Vision standards.",
        "params": {"standard": "str", "max_nits": "int", "codec": "str"},
        "run": lambda a: {
            "standard": _safe_str(a, "standard", "rec2020"),
            "hdr": _HDR_STANDARDS.get(_safe_str(a, "standard", "rec2020"), _HDR_STANDARDS["rec2020"]),
            "codec": _safe_str(a, "codec", "h265"),
            "tone_map_sdr_fallback": True,
        },
    },
    {
        "name": "export_bitrate_codec",
        "description": "Control codec and bitrate: H.264, H.265, ProRes, or AV1 with quality settings.",
        "params": {"codec": "str", "crf": "int", "bitrate_mbps": "float", "pixel_format": "str"},
        "run": lambda a: {
            "codec": _safe_str(a, "codec", "h264"),
            "profile": _CODEC_PROFILES.get(_safe_str(a, "codec", "h264"), _CODEC_PROFILES["h264"]),
            "crf": _safe_int(a, "crf", 18),
            "bitrate_mbps": _safe_float(a, "bitrate_mbps", 8.0),
            "override_pixel_format": _safe_str(a, "pixel_format", ""),
        },
    },
    {
        "name": "export_watermark",
        "description": "Add a logo watermark or animated intro/outro pack to exported video.",
        "params": {"logo_path": "str", "position": "str", "opacity": "float", "intro_pack": "str", "outro_pack": "str"},
        "run": lambda a: {
            "logo": _safe_str(a, "logo_path", ""),
            "layout": _watermark_layout(_safe_str(a, "position", "bottom_right"), 200, 80, 1920, 1080),
            "opacity": max(0.0, min(1.0, _safe_float(a, "opacity", 0.8))),
            "intro_pack": _safe_str(a, "intro_pack", ""),
            "outro_pack": _safe_str(a, "outro_pack", ""),
        },
    },
    {
        "name": "export_publish",
        "description": "One-click publish exported video to social channels or cloud storage targets.",
        "params": {"targets": "list[str]", "title": "str", "description": "str", "visibility": "str"},
        "run": lambda a: {
            "targets": a.get("targets", []),
            "title": _safe_str(a, "title", "Untitled"),
            "description": _safe_str(a, "description", ""),
            "visibility": _safe_str(a, "visibility", "public"),
            "resolved": [{"target": t, **_SOCIAL_TARGETS.get(t, _STORAGE_TARGETS.get(t, {"unknown": True}))}
                         for t in a.get("targets", [])],
        },
    },
]