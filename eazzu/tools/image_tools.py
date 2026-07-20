"""Advanced image tools — analysis, generation, transformation, color, metadata.

Pure stdlib. Works with raw pixel arrays (list of [r,g,b] or [r,g,b,a]) or
decodes common formats via the stdlib `imghdr` + struct when possible. All
functions return JSON-serialisable dicts.
"""
from __future__ import annotations

import base64
import colorsys
import hashlib
import io
import math
import struct
from typing import Any, Dict, List, Optional, Tuple


def _error(code: str, exc: Exception) -> Dict[str, Any]:
    return {"error": code, "message": str(exc)}


# ─── Color analysis ─────────────────────────────────────────────────────


def analyze_colors(pixels: List[List[int]]) -> Dict[str, Any]:
    """Analyze the color palette of an image (list of [r,g,b] pixels).

    Returns dominant colors, brightness, saturation, warmth, and a histogram.
    """
    if not pixels:
        return {"error": "no_pixels"}
    hist: Dict[str, int] = {}
    h_sum = s_sum = v_sum = 0.0
    warm = cool = 0
    for px in pixels:
        r, g, b = px[0], px[1], px[2]
        key = f"#{r:02x}{g:02x}{b:02x}"
        hist[key] = hist.get(key, 0) + 1
        h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
        h_sum += h
        s_sum += s
        v_sum += v
        if h < 0.5 or h > 0.9:
            warm += 1
        else:
            cool += 1
    n = len(pixels)
    dominant = sorted(hist.items(), key=lambda x: -x[1])[:10]
    return {
        "pixel_count": n,
        "unique_colors": len(hist),
        "dominant_colors": [{"hex": c, "count": cnt, "ratio": round(cnt / n, 4)} for c, cnt in dominant],
        "avg_brightness": round(v_sum / n, 4),
        "avg_saturation": round(s_sum / n, 4),
        "avg_hue": round(h_sum / n, 4),
        "warm_cool_ratio": {"warm": warm, "cool": cool, "warm_ratio": round(warm / n, 4)},
    }


def extract_palette(pixels: List[List[int]], k: int = 8) -> Dict[str, Any]:
    """Extract a k-color palette using simple frequency bucketing (pseudo-k-means)."""
    if not pixels:
        return {"error": "no_pixels"}
    hist: Dict[Tuple[int, int, int], int] = {}
    for px in pixels:
        r, g, b = px[0] // 32 * 32, px[1] // 32 * 32, px[2] // 32 * 32
        hist[(r, g, b)] = hist.get((r, g, b), 0) + 1
    top = sorted(hist.items(), key=lambda x: -x[1])[:k]
    return {
        "palette": [
            {"hex": f"#{r:02x}{g:02x}{b:02x}", "weight": cnt} for (r, g, b), cnt in top
        ]
    }


def color_distance(c1: List[int], c2: List[int]) -> Dict[str, Any]:
    """Compute Euclidean and weighted (sRGB-aware) distance between two RGB colors."""
    r1, g1, b1 = c1[:3]
    r2, g2, b2 = c2[:3]
    euclid = math.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)
    rmean = (r1 + r2) / 2
    weighted = math.sqrt((2 + rmean / 256) * (r1 - r2) ** 2 + 4 * (g1 - g2) ** 2 + (2 + (255 - rmean) / 256) * (b1 - b2) ** 2)
    return {"euclidean": round(euclid, 2), "weighted": round(weighted, 2), "max": 441.67}


def rgb_to_hsl(rgb: List[int]) -> Dict[str, Any]:
    """Convert RGB to HSL."""
    h, l, s = colorsys.rgb_to_hls(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)
    return {"h": round(h * 360), "s": round(s * 100), "l": round(l * 100)}


def hsl_to_rgb(h: int, s: int, l: int) -> Dict[str, Any]:
    """Convert HSL (0-360, 0-100, 0-100) to RGB."""
    r, g, b = colorsys.hls_to_rgb(h / 360, l / 100, s / 100)
    return {"r": round(r * 255), "g": round(g * 255), "b": round(b * 255),
            "hex": f"#{round(r*255):02x}{round(g*255):02x}{round(b*255):02x}"}


def complement_color(rgb: List[int]) -> Dict[str, Any]:
    """Return the complementary, analogous, and triadic colors for a given RGB."""
    h, l, s = colorsys.rgb_to_hls(rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)
    def _hls_to_hex(hh, ll, ss):
        r, g, b = colorsys.hls_to_rgb(hh, ll, ss)
        return f"#{round(r*255):02x}{round(g*255):02x}{round(b*255):02x}"
    return {
        "original": f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}",
        "complement": _hls_to_hex((h + 0.5) % 1, l, s),
        "analogous": [_hls_to_hex((h + 1/12) % 1, l, s), _hls_to_hex((h - 1/12) % 1, l, s)],
        "triadic": [_hls_to_hex((h + 1/3) % 1, l, s), _hls_to_hex((h + 2/3) % 1, l, s)],
        "split_complement": [_hls_to_hex((h + 0.5 + 1/12) % 1, l, s), _hls_to_hex((h + 0.5 - 1/12) % 1, l, s)],
    }


# ─── Image statistics ──────────────────────────────────────────────────


def image_stats(pixels: List[List[int]], width: int = 0, height: int = 0) -> Dict[str, Any]:
    """Compute brightness, contrast, entropy, and channel statistics."""
    if not pixels:
        return {"error": "no_pixels"}
    n = len(pixels)
    grays = [0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2] for p in pixels]
    mean = sum(grays) / n
    variance = sum((g - mean) ** 2 for g in grays) / n
    std = math.sqrt(variance)
    hist = [0] * 256
    for g in grays:
        hist[min(255, max(0, int(g)))] += 1
    entropy = 0.0
    for cnt in hist:
        if cnt > 0:
            p = cnt / n
            entropy -= p * math.log2(p)
    return {
        "pixel_count": n,
        "dimensions": {"width": width, "height": height} if width and height else None,
        "brightness": round(mean, 2),
        "contrast": round(std, 2),
        "entropy": round(entropy, 4),
        "r_mean": round(sum(p[0] for p in pixels) / n, 2),
        "g_mean": round(sum(p[1] for p in pixels) / n, 2),
        "b_mean": round(sum(p[2] for p in pixels) / n, 2),
        "r_std": round(math.sqrt(sum((p[0] - mean) ** 2 for p in pixels) / n), 2),
        "g_std": round(math.sqrt(sum((p[1] - mean) ** 2 for p in pixels) / n), 2),
        "b_std": round(math.sqrt(sum((p[2] - mean) ** 2 for p in pixels) / n), 2),
    }


def image_hash(pixels: List[List[int]]) -> Dict[str, Any]:
    """Compute a perceptual average hash (aHash) and a content hash for an image."""
    if not pixels:
        return {"error": "no_pixels"}
    grays = [int(0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2]) for p in pixels]
    mean = sum(grays) / len(grays)
    bits = [1 if g > mean else 0 for g in grays]
    ahash = 0
    for b in bits:
        ahash = (ahash << 1) | b
    content = hashlib.md5(str(grays[:1000]).encode()).hexdigest()
    return {"ahash": hex(ahash), "content_hash": content, "mean_gray": round(mean, 2)}


# ─── Image transformations ──────────────────────────────────────────────


def adjust_brightness(pixels: List[List[int]], factor: float = 1.2) -> Dict[str, Any]:
    """Adjust brightness of all pixels by a multiplicative factor."""
    result = []
    for p in pixels:
        r = min(255, max(0, int(p[0] * factor)))
        g = min(255, max(0, int(p[1] * factor)))
        b = min(255, max(0, int(p[2] * factor)))
        result.append([r, g, b] + p[3:] if len(p) > 3 else [r, g, b])
    return {"pixel_count": len(result), "factor": factor, "pixels": result[:1000]}


def adjust_contrast(pixels: List[List[int]], factor: float = 1.5) -> Dict[str, Any]:
    """Adjust contrast of all pixels (factor > 1 increases, < 1 decreases)."""
    n = len(pixels)
    if n == 0:
        return {"error": "no_pixels"}
    mean_r = sum(p[0] for p in pixels) / n
    mean_g = sum(p[1] for p in pixels) / n
    mean_b = sum(p[2] for p in pixels) / n
    result = []
    for p in pixels:
        r = min(255, max(0, int((p[0] - mean_r) * factor + mean_r)))
        g = min(255, max(0, int((p[1] - mean_g) * factor + mean_g)))
        b = min(255, max(0, int((p[2] - mean_b) * factor + mean_b)))
        result.append([r, g, b] + p[3:] if len(p) > 3 else [r, g, b])
    return {"pixel_count": len(result), "factor": factor, "pixels": result[:1000]}


def grayscale(pixels: List[List[int]]) -> Dict[str, Any]:
    """Convert pixels to grayscale (luminance weighting)."""
    result = []
    for p in pixels:
        g = int(0.299 * p[0] + 0.587 * p[1] + 0.114 * p[2])
        result.append([g, g, g])
    return {"pixel_count": len(result), "pixels": result[:1000]}


def invert(pixels: List[List[int]]) -> Dict[str, Any]:
    """Invert all pixel colors."""
    result = []
    for p in pixels:
        r, g, b = 255 - p[0], 255 - p[1], 255 - p[2]
        result.append([r, g, b])
    return {"pixel_count": len(result), "pixels": result[:1000]}


def sepia(pixels: List[List[int]]) -> Dict[str, Any]:
    """Apply a sepia tone filter."""
    result = []
    for p in pixels:
        r, g, b = p[0], p[1], p[2]
        sr = min(255, int(0.393 * r + 0.769 * g + 0.189 * b))
        sg = min(255, int(0.349 * r + 0.686 * g + 0.168 * b))
        sb = min(255, int(0.272 * r + 0.534 * g + 0.131 * b))
        result.append([sr, sg, sb])
    return {"pixel_count": len(result), "pixels": result[:1000]}


def apply_tint(pixels: List[List[int]], tint: List[int], strength: float = 0.3) -> Dict[str, Any]:
    """Apply a color tint to all pixels with a given strength (0-1)."""
    tr, tg, tb = tint[:3]
    result = []
    for p in pixels:
        r = int(p[0] * (1 - strength) + tr * strength)
        g = int(p[1] * (1 - strength) + tg * strength)
        b = int(p[2] * (1 - strength) + tb * strength)
        result.append([r, g, b])
    return {"pixel_count": len(result), "tint": tint, "strength": strength, "pixels": result[:1000]}


# ─── Pattern / generative ───────────────────────────────────────────────


def generate_gradient(width: int = 100, height: int = 100, c1: Optional[List[int]] = None,
                      c2: Optional[List[int]] = None, direction: str = "horizontal") -> Dict[str, Any]:
    """Generate a linear gradient image as a pixel array."""
    c1 = c1 or [0, 0, 0]
    c2 = c2 or [255, 255, 255]
    pixels = []
    for y in range(height):
        for x in range(width):
            if direction == "horizontal":
                t = x / max(1, width - 1)
            elif direction == "vertical":
                t = y / max(1, height - 1)
            else:
                t = (x + y) / max(1, width + height - 2)
            r = int(c1[0] * (1 - t) + c2[0] * t)
            g = int(c1[1] * (1 - t) + c2[1] * t)
            b = int(c1[2] * (1 - t) + c2[2] * t)
            pixels.append([r, g, b])
    return {"width": width, "height": height, "direction": direction, "pixel_count": len(pixels),
            "pixels": pixels[:2000]}


def generate_checkerboard(width: int = 64, height: int = 64, cell: int = 8,
                          c1: Optional[List[int]] = None, c2: Optional[List[int]] = None) -> Dict[str, Any]:
    """Generate a checkerboard pattern."""
    c1 = c1 or [255, 255, 255]
    c2 = c2 or [0, 0, 0]
    pixels = []
    for y in range(height):
        for x in range(width):
            cx, cy = x // cell, y // cell
            color = c1 if (cx + cy) % 2 == 0 else c2
            pixels.append(list(color))
    return {"width": width, "height": height, "cell_size": cell, "pixel_count": len(pixels),
            "pixels": pixels[:2000]}


def generate_noise(width: int = 64, height: int = 64, seed: int = 0) -> Dict[str, Any]:
    """Generate random noise as a pixel array (deterministic with seed)."""
    import random
    rng = random.Random(seed)
    pixels = [[rng.randint(0, 255), rng.randint(0, 255), rng.randint(0, 255)]
              for _ in range(width * height)]
    return {"width": width, "height": height, "seed": seed, "pixel_count": len(pixels),
            "pixels": pixels[:2000]}


def generate_mandelbrot(width: int = 100, height: int = 100, max_iter: int = 50) -> Dict[str, Any]:
    """Generate a Mandelbrot set fractal as a pixel array."""
    pixels = []
    for y in range(height):
        for x in range(width):
            cx = (x - width / 2) * 4 / width - 0.5
            cy = (y - height / 2) * 4 / height
            zx, zy = 0.0, 0.0
            i = 0
            while zx * zx + zy * zy < 4 and i < max_iter:
                zx, zy = zx * zx - zy * zy + cx, 2 * zx * zy + cy
                i += 1
            if i == max_iter:
                pixels.append([0, 0, 0])
            else:
                t = i / max_iter
                pixels.append([int(9 * t * 255), int(2 * (1 - t) * t * 255), int((1 - t) * 255)])
    return {"width": width, "height": height, "max_iter": max_iter, "pixel_count": len(pixels),
            "pixels": pixels[:2000]}


# ─── Metadata / encoding ────────────────────────────────────────────────


def image_metadata(width: int, height: int, format: str = "png", channels: int = 3,
                   has_alpha: bool = False, color_depth: int = 8) -> Dict[str, Any]:
    """Compute image metadata and estimated file sizes."""
    bpp = channels * color_depth
    raw_size = width * height * (channels + (1 if has_alpha else 0))
    return {
        "width": width, "height": height, "format": format,
        "channels": channels, "has_alpha": has_alpha, "color_depth": color_depth,
        "bits_per_pixel": bpp,
        "megapixels": round(width * height / 1e6, 2),
        "aspect_ratio": round(width / height, 4) if height else None,
        "raw_size_bytes": raw_size,
        "raw_size_kb": round(raw_size / 1024, 1),
        "estimated_png_kb": round(raw_size * 0.5 / 1024, 1),
        "estimated_jpeg_kb": round(raw_size * 0.15 / 1024, 1),
    }


def base64_encode_image(data: bytes) -> Dict[str, Any]:
    """Base64-encode raw image bytes and return a data URI."""
    encoded = base64.b64encode(data).decode("ascii")
    return {"base64": encoded[:5000], "size_bytes": len(data), "data_uri": f"data:image/png;base64,{encoded}"}


def detect_format(data: bytes) -> Dict[str, Any]:
    """Detect image format from raw bytes magic numbers."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return {"format": "png", "mime": "image/png"}
    if data.startswith(b"\xff\xd8\xff"):
        return {"format": "jpeg", "mime": "image/jpeg"}
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return {"format": "gif", "mime": "image/gif"}
    if data[:6] in (b"BM",):
        return {"format": "bmp", "mime": "image/bmp"}
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return {"format": "webp", "mime": "image/webp"}
    return {"format": "unknown", "mime": None}


TOOLS = [
    {"name": "analyze_colors", "description": "Analyze the color palette of an image (list of [r,g,b] pixels): dominant colors, brightness, saturation, warmth.",
     "params": {"pixels": "array[array[int]]"}, "run": analyze_colors},
    {"name": "extract_palette", "description": "Extract a k-color palette from an image using frequency bucketing.",
     "params": {"pixels": "array[array[int]]", "k": "int"}, "run": extract_palette},
    {"name": "color_distance", "description": "Compute Euclidean and weighted sRGB distance between two RGB colors.",
     "params": {"c1": "array[int]", "c2": "array[int]"}, "run": color_distance},
    {"name": "rgb_to_hsl", "description": "Convert an RGB color to HSL.",
     "params": {"rgb": "array[int]"}, "run": rgb_to_hsl},
    {"name": "hsl_to_rgb", "description": "Convert HSL (0-360, 0-100, 0-100) to RGB.",
     "params": {"h": "int", "s": "int", "l": "int"}, "run": hsl_to_rgb},
    {"name": "complement_color", "description": "Return complementary, analogous, triadic, and split-complement colors for an RGB color.",
     "params": {"rgb": "array[int]"}, "run": complement_color},
    {"name": "image_stats", "description": "Compute brightness, contrast, entropy, and per-channel statistics for an image.",
     "params": {"pixels": "array[array[int]]", "width": "int", "height": "int"}, "run": image_stats},
    {"name": "image_hash", "description": "Compute a perceptual average hash (aHash) and content hash for an image.",
     "params": {"pixels": "array[array[int]]"}, "run": image_hash},
    {"name": "adjust_brightness", "description": "Adjust brightness of all pixels by a multiplicative factor.",
     "params": {"pixels": "array[array[int]]", "factor": "float"}, "run": adjust_brightness},
    {"name": "adjust_contrast", "description": "Adjust contrast of all pixels (factor > 1 increases, < 1 decreases).",
     "params": {"pixels": "array[array[int]]", "factor": "float"}, "run": adjust_contrast},
    {"name": "grayscale", "description": "Convert pixels to grayscale using luminance weighting.",
     "params": {"pixels": "array[array[int]]"}, "run": grayscale},
    {"name": "invert", "description": "Invert all pixel colors (negative effect).",
     "params": {"pixels": "array[array[int]]"}, "run": invert},
    {"name": "sepia", "description": "Apply a sepia tone filter to pixels.",
     "params": {"pixels": "array[array[int]]"}, "run": sepia},
    {"name": "apply_tint", "description": "Apply a color tint to all pixels with a given strength (0-1).",
     "params": {"pixels": "array[array[int]]", "tint": "array[int]", "strength": "float"}, "run": apply_tint},
    {"name": "generate_gradient", "description": "Generate a linear gradient image (horizontal, vertical, or diagonal).",
     "params": {"width": "int", "height": "int", "c1": "array[int]", "c2": "array[int]", "direction": "string"},
     "run": generate_gradient},
    {"name": "generate_checkerboard", "description": "Generate a checkerboard pattern image.",
     "params": {"width": "int", "height": "int", "cell": "int", "c1": "array[int]", "c2": "array[int]"},
     "run": generate_checkerboard},
    {"name": "generate_noise", "description": "Generate random noise as a pixel array (deterministic with seed).",
     "params": {"width": "int", "height": "int", "seed": "int"}, "run": generate_noise},
    {"name": "generate_mandelbrot", "description": "Generate a Mandelbrot set fractal as a pixel array.",
     "params": {"width": "int", "height": "int", "max_iter": "int"}, "run": generate_mandelbrot},
    {"name": "image_metadata", "description": "Compute image metadata and estimated file sizes from dimensions and format.",
     "params": {"width": "int", "height": "int", "format": "string", "channels": "int", "has_alpha": "bool", "color_depth": "int"},
     "run": image_metadata},
    {"name": "base64_encode_image", "description": "Base64-encode raw image bytes and return a data URI.",
     "params": {"data": "bytes"}, "run": base64_encode_image},
    {"name": "detect_format", "description": "Detect image format from raw bytes magic numbers (PNG, JPEG, GIF, BMP, WEBP).",
     "params": {"data": "bytes"}, "run": detect_format},
]
