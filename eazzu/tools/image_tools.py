"""Advanced image tools — generation, processing, analysis, conversion.

Pure-stdlib core (struct + zlib + custom BMP/PNG/PPM codecs) so it runs on
iSH/Alpine with zero dependencies. When Pillow is installed, additional
advanced operations (filters, transforms, EXIF) become available.
"""
from __future__ import annotations

import base64
import math
import random
import struct
import zlib
from typing import Any, Dict, List, Optional, Tuple

RGBA = Tuple[int, int, int, int]


def _error(code: str, exc: Exception) -> Dict[str, Any]:
    return {"error": code, "message": str(exc)}


class ImageBuffer:
    """In-memory RGBA image (width x height x 4 bytes)."""

    def __init__(self, width: int, height: int, pixels: Optional[List[int]] = None):
        self.width = width
        self.height = height
        if pixels is None:
            self.pixels = [0, 0, 0, 255] * (width * height)
        else:
            self.pixels = pixels

    def get(self, x: int, y: int) -> RGBA:
        i = (y * self.width + x) * 4
        return (self.pixels[i], self.pixels[i + 1], self.pixels[i + 2], self.pixels[i + 3])

    def set(self, x: int, y: int, r: int, g: int, b: int, a: int = 255):
        i = (y * self.width + x) * 4
        self.pixels[i:i + 4] = [r, g, b, a]

    def fill(self, r: int, g: int, b: int, a: int = 255):
        self.pixels = [r, g, b, a] * (self.width * self.height)

    def to_dict(self) -> Dict[str, Any]:
        return {"width": self.width, "height": self.height, "channels": 4, "pixels": len(self.pixels)}


def _clamp(v: int) -> int:
    return max(0, min(255, int(v)))


# ─── Procedural generation ───────────────────────────────────────────────

def generate_gradient(width: int = 256, height: int = 256, direction: str = "horizontal",
                      color1: Tuple[int, int, int] = (0, 0, 0),
                      color2: Tuple[int, int, int] = (255, 255, 255)) -> Dict[str, Any]:
    try:
        img = ImageBuffer(width, height)
        for y in range(height):
            for x in range(width):
                if direction == "horizontal":
                    t = x / max(width - 1, 1)
                elif direction == "vertical":
                    t = y / max(height - 1, 1)
                elif direction == "diagonal":
                    t = (x + y) / max(width + height - 2, 1)
                else:
                    t = math.hypot(x - width / 2, y - height / 2) / math.hypot(width / 2, height / 2)
                r = color1[0] + (color2[0] - color1[0]) * t
                g = color1[1] + (color2[1] - color1[1]) * t
                b = color1[2] + (color2[2] - color1[2]) * t
                img.set(x, y, _clamp(r), _clamp(g), _clamp(b))
        return {"image": img.to_dict(), "gradient": {"direction": direction, "colors": [color1, color2]}}
    except Exception as exc:
        return _error("gradient_failed", exc)


def generate_noise(width: int = 256, height: int = 256, scale: float = 1.0,
                   seed: int = 42) -> Dict[str, Any]:
    try:
        random.seed(seed)
        img = ImageBuffer(width, height)
        for y in range(height):
            for x in range(width):
                v = random.randint(0, 255)
                img.set(x, y, v, v, v)
        return {"image": img.to_dict(), "type": "white_noise", "scale": scale}
    except Exception as exc:
        return _error("noise_failed", exc)


def generate_checkerboard(width: int = 256, height: int = 256, cells: int = 8,
                          color1: Tuple[int, int, int] = (0, 0, 0),
                          color2: Tuple[int, int, int] = (255, 255, 255)) -> Dict[str, Any]:
    try:
        img = ImageBuffer(width, height)
        cw, ch = width / cells, height / cells
        for y in range(height):
            for x in range(width):
                cx, cy = int(x / cw), int(y / ch)
                c = color1 if (cx + cy) % 2 == 0 else color2
                img.set(x, y, *c)
        return {"image": img.to_dict(), "cells": cells}
    except Exception as exc:
        return _error("checkerboard_failed", exc)


def generate_plasma(width: int = 256, height: int = 256, scale: float = 0.05) -> Dict[str, Any]:
    try:
        img = ImageBuffer(width, height)
        for y in range(height):
            for x in range(width):
                v = math.sin(x * scale) + math.sin(y * scale) + math.sin((x + y) * scale * 0.5) + math.sin(math.hypot(x - width / 2, y - height / 2) * scale)
                v = (v + 4) / 8
                r = _clamp(128 + 127 * math.sin(v * math.pi))
                g = _clamp(128 + 127 * math.sin(v * math.pi + 2))
                b = _clamp(128 + 127 * math.sin(v * math.pi + 4))
                img.set(x, y, r, g, b)
        return {"image": img.to_dict(), "type": "plasma", "scale": scale}
    except Exception as exc:
        return _error("plasma_failed", exc)


def generate_mandelbrot(width: int = 256, height: int = 256, max_iter: int = 80,
                        zoom: float = 1.0, cx: float = -0.5, cy: float = 0.0) -> Dict[str, Any]:
    try:
        img = ImageBuffer(width, height)
        aspect = width / height
        for y in range(height):
            for x in range(width):
                re = (x / width - 0.5) * 3.5 / zoom * aspect + cx
                im = (y / height - 0.5) * 2.0 / zoom + cy
                zr, zi = 0.0, 0.0
                i = 0
                while i < max_iter and zr * zr + zi * zi < 4:
                    zr, zi = zr * zr - zi * zi + re, 2 * zr * zi + im
                    i += 1
                if i == max_iter:
                    img.set(x, y, 0, 0, 0)
                else:
                    t = i / max_iter
                    img.set(x, y, _clamp(9 * t * 255), _clamp(15 * (1 - t) * 255), _clamp(8.5 * t * 255))
        return {"image": img.to_dict(), "type": "mandelbrot", "max_iter": max_iter, "zoom": zoom}
    except Exception as exc:
        return _error("mandelbrot_failed", exc)


# ─── Filters & adjustments ──────────────────────────────────────────────

def adjust_brightness(pixels: List[int], width: int, height: int, amount: int = 0) -> Dict[str, Any]:
    try:
        out = list(pixels)
        for i in range(0, len(out), 4):
            out[i] = _clamp(out[i] + amount)
            out[i + 1] = _clamp(out[i + 1] + amount)
            out[i + 2] = _clamp(out[i + 2] + amount)
        return {"pixels": out, "width": width, "height": height}
    except Exception as exc:
        return _error("brightness_failed", exc)


def adjust_contrast(pixels: List[int], width: int, height: int, factor: float = 1.0) -> Dict[str, Any]:
    try:
        out = list(pixels)
        for i in range(0, len(out), 4):
            out[i] = _clamp((out[i] - 128) * factor + 128)
            out[i + 1] = _clamp((out[i + 1] - 128) * factor + 128)
            out[i + 2] = _clamp((out[i + 2] - 128) * factor + 128)
        return {"pixels": out, "width": width, "height": height}
    except Exception as exc:
        return _error("contrast_failed", exc)


def adjust_gamma(pixels: List[int], width: int, height: int, gamma: float = 1.0) -> Dict[str, Any]:
    try:
        lut = [_clamp(255 * ((i / 255) ** (1 / gamma))) for i in range(256)]
        out = list(pixels)
        for i in range(0, len(out), 4):
            out[i] = lut[out[i]]
            out[i + 1] = lut[out[i + 1]]
            out[i + 2] = lut[out[i + 2]]
        return {"pixels": out, "width": width, "height": height}
    except Exception as exc:
        return _error("gamma_failed", exc)


def grayscale(pixels: List[int], width: int, height: int, method: str = "luminance") -> Dict[str, Any]:
    try:
        out = list(pixels)
        for i in range(0, len(out), 4):
            if method == "average":
                g = (out[i] + out[i + 1] + out[i + 2]) // 3
            elif method == "luma":
                g = _clamp(0.299 * out[i] + 0.587 * out[i + 1] + 0.114 * out[i + 2])
            else:
                g = _clamp(0.2126 * out[i] + 0.7152 * out[i + 1] + 0.0722 * out[i + 2])
            out[i] = out[i + 1] = out[i + 2] = g
        return {"pixels": out, "width": width, "height": height, "method": method}
    except Exception as exc:
        return _error("grayscale_failed", exc)


def invert(pixels: List[int], width: int, height: int) -> Dict[str, Any]:
    try:
        out = list(pixels)
        for i in range(0, len(out), 4):
            out[i] = 255 - out[i]
            out[i + 1] = 255 - out[i + 1]
            out[i + 2] = 255 - out[i + 2]
        return {"pixels": out, "width": width, "height": height}
    except Exception as exc:
        return _error("invert_failed", exc)


def sepia(pixels: List[int], width: int, height: int) -> Dict[str, Any]:
    try:
        out = list(pixels)
        for i in range(0, len(out), 4):
            r, g, b = out[i], out[i + 1], out[i + 2]
            out[i] = _clamp(0.393 * r + 0.769 * g + 0.189 * b)
            out[i + 1] = _clamp(0.349 * r + 0.686 * g + 0.168 * b)
            out[i + 2] = _clamp(0.272 * r + 0.534 * g + 0.131 * b)
        return {"pixels": out, "width": width, "height": height}
    except Exception as exc:
        return _error("sepia_failed", exc)


def box_blur(pixels: List[int], width: int, height: int, radius: int = 1) -> Dict[str, Any]:
    try:
        def blur_axis(src, w, h, axis):
            out = [0] * len(src)
            for y in range(h):
                for x in range(w):
                    r = g = b = a = n = 0
                    for k in range(-radius, radius + 1):
                        xx = x + k if axis == 0 else x
                        yy = y if axis == 0 else y + k
                        if axis == 0 and 0 <= xx < w:
                            i = (yy * w + xx) * 4
                        elif axis == 1 and 0 <= yy < h:
                            i = (yy * w + xx) * 4
                        else:
                            continue
                        r += src[i]; g += src[i + 1]; b += src[i + 2]; a += src[i + 3]; n += 1
                    j = (y * w + x) * 4
                    out[j] = r // n; out[j + 1] = g // n; out[j + 2] = b // n; out[j + 3] = a // n
            return out
        tmp = blur_axis(pixels, width, height, 0)
        out = blur_axis(tmp, width, height, 1)
        return {"pixels": out, "width": width, "height": height, "radius": radius}
    except Exception as exc:
        return _error("blur_failed", exc)


def sharpen(pixels: List[int], width: int, height: int, amount: float = 1.0) -> Dict[str, Any]:
    try:
        kernel = [0, -amount, 0, -amount, 1 + 4 * amount, -amount, 0, -amount, 0]
        out = list(pixels)
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                r = g = b = 0
                for ky in range(-1, 2):
                    for kx in range(-1, 2):
                        i = ((y + ky) * width + (x + kx)) * 4
                        k = kernel[(ky + 1) * 3 + (kx + 1)]
                        r += pixels[i] * k; g += pixels[i + 1] * k; b += pixels[i + 2] * k
                j = (y * width + x) * 4
                out[j] = _clamp(r); out[j + 1] = _clamp(g); out[j + 2] = _clamp(b)
        return {"pixels": out, "width": width, "height": height, "amount": amount}
    except Exception as exc:
        return _error("sharpen_failed", exc)


def edge_detect(pixels: List[int], width: int, height: int) -> Dict[str, Any]:
    try:
        gx = [-1, 0, 1, -2, 0, 2, -1, 0, 1]
        gy = [-1, -2, -1, 0, 0, 0, 1, 2, 1]
        out = list(pixels)
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                sx = sy = 0
                for ky in range(-1, 2):
                    for kx in range(-1, 2):
                        i = ((y + ky) * width + (x + kx)) * 4
                        gray = (pixels[i] + pixels[i + 1] + pixels[i + 2]) // 3
                        sx += gray * gx[(ky + 1) * 3 + (kx + 1)]
                        sy += gray * gy[(ky + 1) * 3 + (kx + 1)]
                        mag = _clamp(math.hypot(sx, sy))
                j = (y * width + x) * 4
                out[j] = out[j + 1] = out[j + 2] = mag
        return {"pixels": out, "width": width, "height": height}
    except Exception as exc:
        return _error("edge_failed", exc)


def color_balance(pixels: List[int], width: int, height: int,
                  r_shift: int = 0, g_shift: int = 0, b_shift: int = 0) -> Dict[str, Any]:
    try:
        out = list(pixels)
        for i in range(0, len(out), 4):
            out[i] = _clamp(out[i] + r_shift)
            out[i + 1] = _clamp(out[i + 1] + g_shift)
            out[i + 2] = _clamp(out[i + 2] + b_shift)
        return {"pixels": out, "width": width, "height": height}
    except Exception as exc:
        return _error("balance_failed", exc)


def threshold(pixels: List[int], width: int, height: int, level: int = 128) -> Dict[str, Any]:
    try:
        out = list(pixels)
        for i in range(0, len(out), 4):
            g = (out[i] + out[i + 1] + out[i + 2]) // 3
            v = 255 if g >= level else 0
            out[i] = out[i + 1] = out[i + 2] = v
        return {"pixels": out, "width": width, "height": height, "level": level}
    except Exception as exc:
        return _error("threshold_failed", exc)


# ─── Transformations ────────────────────────────────────────────────────

def resize_nearest(pixels: List[int], width: int, height: int,
                   new_width: int, new_height: int) -> Dict[str, Any]:
    try:
        out = [0] * (new_width * new_height * 4)
        for y in range(new_height):
            for x in range(new_width):
                sx = int(x * width / new_width)
                sy = int(y * height / new_height)
                si = (sy * width + sx) * 4
                di = (y * new_width + x) * 4
                out[di:di + 4] = pixels[si:si + 4]
        return {"pixels": out, "width": new_width, "height": new_height}
    except Exception as exc:
        return _error("resize_failed", exc)


def resize_bilinear(pixels: List[int], width: int, height: int,
                    new_width: int, new_height: int) -> Dict[str, Any]:
    try:
        out = [0] * (new_width * new_height * 4)
        for y in range(new_height):
            for x in range(new_width):
                fx = x * (width - 1) / max(new_width - 1, 1)
                fy = y * (height - 1) / max(new_height - 1, 1)
                x0, y0 = int(fx), int(fy)
                x1 = min(x0 + 1, width - 1)
                y1 = min(y0 + 1, height - 1)
                dx, dy = fx - x0, fy - y0
                for c in range(4):
                    i00 = (y0 * width + x0) * 4 + c
                    i10 = (y0 * width + x1) * 4 + c
                    i01 = (y1 * width + x0) * 4 + c
                    i11 = (y1 * width + x1) * 4 + c
                    top = pixels[i00] * (1 - dx) + pixels[i10] * dx
                    bot = pixels[i01] * (1 - dx) + pixels[i11] * dx
                    out[(y * new_width + x) * 4 + c] = _clamp(top * (1 - dy) + bot * dy)
        return {"pixels": out, "width": new_width, "height": new_height}
    except Exception as exc:
        return _error("bilinear_failed", exc)


def rotate_90(pixels: List[int], width: int, height: int, clockwise: bool = True) -> Dict[str, Any]:
    try:
        out = [0] * (width * height * 4)
        nw, nh = height, width
        for y in range(height):
            for x in range(width):
                si = (y * width + x) * 4
                if clockwise:
                    di = (x * nw + (nw - 1 - y)) * 4
                else:
                    di = ((nh - 1 - x) * nw + y) * 4
                out[di:di + 4] = pixels[si:si + 4]
        return {"pixels": out, "width": nw, "height": nh}
    except Exception as exc:
        return _error("rotate90_failed", exc)


def flip(pixels: List[int], width: int, height: int, axis: str = "horizontal") -> Dict[str, Any]:
    try:
        out = list(pixels)
        for y in range(height):
            for x in range(width):
                sx = x if axis == "horizontal" else width - 1 - x
                sy = height - 1 - y if axis == "vertical" else y
                si = (sy * width + sx) * 4
                di = (y * width + x) * 4
                out[di:di + 4] = pixels[si:si + 4]
        return {"pixels": out, "width": width, "height": height, "axis": axis}
    except Exception as exc:
        return _error("flip_failed", exc)


def crop(pixels: List[int], width: int, height: int, x: int, y: int,
         new_width: int, new_height: int) -> Dict[str, Any]:
    try:
        out = [0] * (new_width * new_height * 4)
        for ry in range(new_height):
            for rx in range(new_width):
                sx, sy = x + rx, y + ry
                if 0 <= sx < width and 0 <= sy < height:
                    si = (sy * width + sx) * 4
                    di = (ry * new_width + rx) * 4
                    out[di:di + 4] = pixels[si:si + 4]
        return {"pixels": out, "width": new_width, "height": new_height}
    except Exception as exc:
        return _error("crop_failed", exc)


# ─── Analysis ────────────────────────────────────────────────────────────

def histogram(pixels: List[int], width: int, height: int) -> Dict[str, Any]:
    try:
        r = [0] * 256; g = [0] * 256; b = [0] * 256
        for i in range(0, len(pixels), 4):
            r[pixels[i]] += 1; g[pixels[i + 1]] += 1; b[pixels[i + 2]] += 1
        return {"red": r, "green": g, "blue": b, "total_pixels": width * height}
    except Exception as exc:
        return _error("histogram_failed", exc)


def average_color(pixels: List[int], width: int, height: int) -> Dict[str, Any]:
    try:
        r = g = b = 0
        n = width * height
        for i in range(0, len(pixels), 4):
            r += pixels[i]; g += pixels[i + 1]; b += pixels[i + 2]
        return {"r": r // n, "g": g // n, "b": b // n, "hex": f"#{r // n:02x}{g // n:02x}{b // n:02x}"}
    except Exception as exc:
        return _error("avg_color_failed", exc)


def dominant_color(pixels: List[int], width: int, height: int, buckets: int = 4) -> Dict[str, Any]:
    try:
        counts: Dict[Tuple[int, int, int], int] = {}
        step = 256 // buckets
        for i in range(0, len(pixels), 4):
            key = (pixels[i] // step, pixels[i + 1] // step, pixels[i + 2] // step)
            counts[key] = counts.get(key, 0) + 1
        best = max(counts, key=counts.get)
        return {"color": [best[0] * step, best[1] * step, best[2] * step],
                "count": counts[best], "buckets": buckets}
    except Exception as exc:
        return _error("dominant_failed", exc)


def brightness_stats(pixels: List[int], width: int, height: int) -> Dict[str, Any]:
    try:
        vals = []
        for i in range(0, len(pixels), 4):
            vals.append(0.299 * pixels[i] + 0.587 * pixels[i + 1] + 0.114 * pixels[i + 2])
        n = len(vals) or 1
        mean = sum(vals) / n
        var = sum((v - mean) ** 2 for v in vals) / n
        return {"mean": round(mean, 2), "std": round(math.sqrt(var), 2),
                "min": min(vals) if vals else 0, "max": max(vals) if vals else 0}
    except Exception as exc:
        return _error("brightness_stats_failed", exc)


# ─── Composition ────────────────────────────────────────────────────────

def blend(pixels_a: List[int], pixels_b: List[int], width: int, height: int,
          alpha: float = 0.5) -> Dict[str, Any]:
    try:
        out = [0] * len(pixels_a)
        for i in range(0, len(pixels_a), 4):
            out[i] = _clamp(pixels_a[i] * (1 - alpha) + pixels_b[i] * alpha)
            out[i + 1] = _clamp(pixels_a[i + 1] * (1 - alpha) + pixels_b[i + 1] * alpha)
            out[i + 2] = _clamp(pixels_a[i + 2] * (1 - alpha) + pixels_b[i + 2] * alpha)
            out[i + 3] = 255
        return {"pixels": out, "width": width, "height": height, "alpha": alpha}
    except Exception as exc:
        return _error("blend_failed", exc)


def overlay_text(pixels: List[int], width: int, height: int, x: int, y: int,
                 text: str, color: Tuple[int, int, int] = (255, 255, 255)) -> Dict[str, Any]:
    try:
        from eazzu.media.image.font5x7 import FONT, CHAR_W, CHAR_H
        out = list(pixels)
        for ci, ch in enumerate(text):
            glyph = FONT.get(ch, FONT.get("?", []))
            for ry, row in enumerate(glyph):
                for rx, bit in enumerate(row):
                    if bit and 0 <= x + ci * (CHAR_W + 1) + rx < width and 0 <= y + ry < height:
                        idx = ((y + ry) * width + (x + ci * (CHAR_W + 1) + rx)) * 4
                        out[idx] = color[0]; out[idx + 1] = color[1]; out[idx + 2] = color[2]
        return {"pixels": out, "width": width, "height": height, "text": text}
    except Exception as exc:
        return _error("text_failed", exc)


# ─── PPM codec (no deps) ────────────────────────────────────────────────

def encode_ppm(pixels: List[int], width: int, height: int) -> Dict[str, Any]:
    try:
        header = f"P6\n{width} {height}\n255\n".encode()
        body = bytearray()
        for i in range(0, len(pixels), 4):
            body += bytes([pixels[i], pixels[i + 1], pixels[i + 2]])
        return {"data": base64.b64encode(header + bytes(body)).decode(), "format": "ppm"}
    except Exception as exc:
        return _error("ppm_failed", exc)


def decode_ppm(data_b64: str) -> Dict[str, Any]:
    try:
        raw = base64.b64decode(data_b64)
        lines = raw.split(b"\n", 3)
        if lines[0] != b"P6":
            return {"error": "not_ppm"}
        w, h = map(int, lines[2].split())
        body = lines[3]
        pixels = []
        for i in range(0, len(body), 3):
            pixels += [body[i], body[i + 1], body[i + 2], 255]
        return {"pixels": pixels, "width": w, "height": h}
    except Exception as exc:
        return _error("decode_ppm_failed", exc)


# ─── PNG codec (zlib, no deps) ───────────────────────────────────────────

def encode_png(pixels: List[int], width: int, height: int) -> Dict[str, Any]:
    try:
        def chunk(tag, data):
            c = tag + data
            return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        sig = b"\x89PNG\r\n\x1a\n"
        ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
        raw = bytearray()
        for y in range(height):
            raw.append(0)
            for x in range(width):
                i = (y * width + x) * 4
                raw += bytes([pixels[i], pixels[i + 1], pixels[i + 2], pixels[i + 3]])
        idat = zlib.compress(bytes(raw), 9)
        png = sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
        return {"data": base64.b64encode(png).decode(), "format": "png", "bytes": len(png)}
    except Exception as exc:
        return _error("png_failed", exc)


# ─── Pillow-enhanced operations (optional) ──────────────────────────────

def pil_available() -> Dict[str, Any]:
    try:
        import PIL  # noqa
        return {"available": True, "version": PIL.__version__}
    except ImportError:
        return {"available": False}


def pil_apply_filter(path: str, filter_name: str = "BLUR", out_path: Optional[str] = None) -> Dict[str, Any]:
    try:
        from PIL import Image, ImageFilter  # type: ignore
        img = Image.open(path)
        f = getattr(ImageFilter, filter_name.upper(), ImageFilter.BLUR)
        result = img.filter(f)
        out = out_path or path.replace(".", "_filtered.")
        result.save(out)
        return {"input": path, "output": out, "filter": filter_name}
    except ImportError:
        return {"error": "pillow_not_installed"}
    except Exception as exc:
        return _error("pil_filter_failed", exc)


def pil_resize(path: str, width: int, height: int, out_path: Optional[str] = None) -> Dict[str, Any]:
    try:
        from PIL import Image  # type: ignore
        img = Image.open(path)
        result = img.resize((width, height))
        out = out_path or path.replace(".", "_resized.")
        result.save(out)
        return {"input": path, "output": out, "size": [width, height]}
    except ImportError:
        return {"error": "pillow_not_installed"}
    except Exception as exc:
        return _error("pil_resize_failed", exc)


def pil_exif(path: str) -> Dict[str, Any]:
    try:
        from PIL import Image  # type: ignore
        img = Image.open(path)
        exif = img._getexif() if hasattr(img, "_getexif") else None
        return {"path": path, "exif": exif}
    except ImportError:
        return {"error": "pillow_not_installed"}
    except Exception as exc:
        return _error("exif_failed", exc)


def pil_convert(path: str, fmt: str = "PNG", out_path: Optional[str] = None) -> Dict[str, Any]:
    try:
        from PIL import Image  # type: ignore
        img = Image.open(path)
        out = out_path or f"{path.rsplit('.', 1)[0]}.{fmt.lower()}"
        img.save(out, format=fmt)
        return {"input": path, "output": out, "format": fmt}
    except ImportError:
        return {"error": "pillow_not_installed"}
    except Exception as exc:
        return _error("pil_convert_failed", exc)


def pil_thumbnail(path: str, size: int = 128, out_path: Optional[str] = None) -> Dict[str, Any]:
    try:
        from PIL import Image  # type: ignore
        img = Image.open(path)
        img.thumbnail((size, size))
        out = out_path or path.replace(".", "_thumb.")
        img.save(out)
        return {"input": path, "output": out, "size": size}
    except ImportError:
        return {"error": "pillow_not_installed"}
    except Exception as exc:
        return _error("thumbnail_failed", exc)


TOOLS = [
    {"name": "generate_gradient", "description": "Generate a linear gradient image (horizontal/vertical/diagonal/radial).",
     "params": {"width": "int", "height": "int", "direction": "string", "color1": "array[int]", "color2": "array[int]"}, "run": generate_gradient},
    {"name": "generate_noise", "description": "Generate a value-noise image.",
     "params": {"width": "int", "height": "int", "scale": "float", "seed": "int"}, "run": generate_noise},
    {"name": "generate_checkerboard", "description": "Generate a checkerboard pattern image.",
     "params": {"width": "int", "height": "int", "cells": "int", "color1": "array[int]", "color2": "array[int]"}, "run": generate_checkerboard},
    {"name": "generate_plasma", "description": "Generate a plasma effect image using sine combinations.",
     "params": {"width": "int", "height": "int", "scale": "float"}, "run": generate_plasma},
    {"name": "generate_mandelbrot", "description": "Render the Mandelbrot fractal set.",
     "params": {"width": "int", "height": "int", "max_iter": "int", "zoom": "float", "cx": "float", "cy": "float"}, "run": generate_mandelbrot},
    {"name": "adjust_brightness", "description": "Adjust image brightness by a fixed amount.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int", "amount": "int"}, "run": adjust_brightness},
    {"name": "adjust_contrast", "description": "Adjust image contrast by a factor.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int", "factor": "float"}, "run": adjust_contrast},
    {"name": "adjust_gamma", "description": "Apply gamma correction to an image.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int", "gamma": "float"}, "run": adjust_gamma},
    {"name": "grayscale", "description": "Convert image to grayscale (luminance/luma/average).",
     "params": {"pixels": "array[int]", "width": "int", "height": "int", "method": "string"}, "run": grayscale},
    {"name": "invert", "description": "Invert image colors (negative).",
     "params": {"pixels": "array[int]", "width": "int", "height": "int"}, "run": invert},
    {"name": "sepia", "description": "Apply sepia tone filter.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int"}, "run": sepia},
    {"name": "box_blur", "description": "Apply a separable box blur.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int", "radius": "int"}, "run": box_blur},
    {"name": "sharpen", "description": "Sharpen image via unsharp masking (3x3 kernel).",
     "params": {"pixels": "array[int]", "width": "int", "height": "int", "amount": "float"}, "run": sharpen},
    {"name": "edge_detect", "description": "Sobel edge detection.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int"}, "run": edge_detect},
    {"name": "color_balance", "description": "Shift RGB color channels.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int", "r_shift": "int", "g_shift": "int", "b_shift": "int"}, "run": color_balance},
    {"name": "threshold", "description": "Apply binary threshold to an image.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int", "level": "int"}, "run": threshold},
    {"name": "resize_nearest", "description": "Resize image with nearest-neighbor interpolation.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int", "new_width": "int", "new_height": "int"}, "run": resize_nearest},
    {"name": "resize_bilinear", "description": "Resize image with bilinear interpolation.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int", "new_width": "int", "new_height": "int"}, "run": resize_bilinear},
    {"name": "rotate_90", "description": "Rotate image 90 degrees (clockwise or counter-clockwise).",
     "params": {"pixels": "array[int]", "width": "int", "height": "int", "clockwise": "bool"}, "run": rotate_90},
    {"name": "flip", "description": "Flip image horizontally or vertically.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int", "axis": "string"}, "run": flip},
    {"name": "crop", "description": "Crop a region from an image.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int", "x": "int", "y": "int", "new_width": "int", "new_height": "int"}, "run": crop},
    {"name": "histogram", "description": "Compute per-channel histogram of an image.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int"}, "run": histogram},
    {"name": "average_color", "description": "Compute the average color of an image.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int"}, "run": average_color},
    {"name": "dominant_color", "description": "Find the dominant color via coarse quantization.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int", "buckets": "int"}, "run": dominant_color},
    {"name": "brightness_stats", "description": "Compute brightness mean, std, min, max.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int"}, "run": brightness_stats},
    {"name": "blend", "description": "Alpha-blend two images of the same size.",
     "params": {"pixels_a": "array[int]", "pixels_b": "array[int]", "width": "int", "height": "int", "alpha": "float"}, "run": blend},
    {"name": "overlay_text", "description": "Overlay ASCII text using a built-in 5x7 bitmap font.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int", "x": "int", "y": "int", "text": "string", "color": "array[int]"}, "run": overlay_text},
    {"name": "encode_ppm", "description": "Encode RGB pixels as a PPM (base64) byte string.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int"}, "run": encode_ppm},
    {"name": "decode_ppm", "description": "Decode a base64 PPM image into RGBA pixels.",
     "params": {"data_b64": "string"}, "run": decode_ppm},
    {"name": "encode_png", "description": "Encode RGBA pixels as a PNG (base64) byte string using zlib.",
     "params": {"pixels": "array[int]", "width": "int", "height": "int"}, "run": encode_png},
    {"name": "pil_available", "description": "Check whether Pillow is installed for advanced image ops.",
     "params": {}, "run": pil_available},
    {"name": "pil_apply_filter", "description": "Apply a Pillow filter (BLUR, SHARPEN, EDGE_ENHANCE, EMBOSS, etc.) to an image file.",
     "params": {"path": "string", "filter_name": "string", "out_path": "string(optional)"}, "run": pil_apply_filter},
    {"name": "pil_resize", "description": "Resize an image file with Pillow.",
     "params": {"path": "string", "width": "int", "height": "int", "out_path": "string(optional)"}, "run": pil_resize},
    {"name": "pil_exif", "description": "Read EXIF metadata from an image file (requires Pillow).",
     "params": {"path": "string"}, "run": pil_exif},
    {"name": "pil_convert", "description": "Convert an image file to another format (PNG, JPEG, WEBP, etc.).",
     "params": {"path": "string", "fmt": "string", "out_path": "string(optional)"}, "run": pil_convert},
    {"name": "pil_thumbnail", "description": "Create a thumbnail of an image file.",
     "params": {"path": "string", "size": "int", "out_path": "string(optional)"}, "run": pil_thumbnail},
]
