"""Accessibility tools.

Alt-text generation hints, color-contrast checking, reading-order
analysis, and structural checks for documents and HTML. Helps the
agent produce more accessible content.
"""
from __future__ import annotations

import re as _re


def _hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))


def _relative_luminance(rgb):
    def channel(c):
        cs = c / 255
        return cs / 12.92 if cs <= 0.03928 else ((cs + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def _contrast_ratio(fg, bg):
    try:
        l1 = _relative_luminance(_hex_to_rgb(fg))
        l2 = _relative_luminance(_hex_to_rgb(bg))
    except Exception as e:
        return {"error": f"invalid color: {e}"}
    ratio = (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)
    return {
        "fg": fg, "bg": bg, "ratio": round(ratio, 2),
        "wcag_aa_normal": ratio >= 4.5, "wcag_aa_large": ratio >= 3.0,
        "wcag_aaa_normal": ratio >= 7.0, "wcag_aaa_large": ratio >= 4.5,
    }


def _suggest_alt_text(image_desc, context=""):
    base = image_desc.strip() or "an image"
    suggestion = f"{base} — used in the context of {context}." if context else base
    return {
        "suggested_alt": suggestion,
        "tips": ["Keep under 125 characters.", "Describe the purpose, not just appearance.", "Skip 'image of' / 'picture of'.", "If decorative, mark with alt=\"\"."],
    }


def _reading_order(html):
    elements = [{"tag": m.group(1).lower(), "position": m.start()} for m in _re.finditer(r"<(h[1-6]|p|li|img|button|a|table|figure)[^>]*>", html, _re.I)]
    issues = []
    headings = [(i, e) for i, e in enumerate(elements) if e["tag"].startswith("h")]
    for i in range(1, len(headings)):
        prev_tag, curr_tag = headings[i - 1][1]["tag"], headings[i][1]["tag"]
        if int(curr_tag[1]) > int(prev_tag[1]) + 1:
            issues.append({"type": "heading_skip", "message": f"Heading jumps from {prev_tag} to {curr_tag}", "position": headings[i][1]["position"]})
    for m in _re.finditer(r"<img[^>]*>", html, _re.I):
        if "alt=" not in m.group(0).lower():
            issues.append({"type": "missing_alt", "message": "Image without alt text", "position": m.start()})
    return {"order": elements, "issues": issues}


def _check_keyboard(html):
    issues = []
    for m in _re.finditer(r"<(div|span)[^>]*onclick=[^>]*>", html, _re.I):
        if "tabindex" not in m.group(0).lower() and "role" not in m.group(0).lower():
            issues.append({"type": "keyboard_trap", "message": "Clickable element without tabindex/role", "position": m.start()})
    for m in _re.finditer(r'<a[^>]*href="#"[^>]*>([^<]*)</a>', html, _re.I):
        issues.append({"type": "empty_link", "message": f"Link with empty href: '{m.group(1).strip()}'", "position": m.start()})
    return {"issues": issues, "issue_count": len(issues)}


def _aria_labels(html):
    issues = []
    for m in _re.finditer(r"<input[^>]*>", html, _re.I):
        if "aria-label" not in m.group(0).lower() and "id=" not in m.group(0).lower():
            issues.append({"type": "missing_label", "message": "Input without aria-label or associated label", "position": m.start()})
    for m in _re.finditer(r"<button[^>]*>([^<]*)</button>", html, _re.I):
        if not m.group(1).strip() and "aria-label" not in m.group(0).lower():
            issues.append({"type": "empty_button", "message": "Button without text or aria-label", "position": m.start()})
    return {"issues": issues, "issue_count": len(issues)}


def _color_blind_sim(rgb, mode="protanopia"):
    matrices = {
        "protanopia": ((0.567, 0.433, 0), (0.558, 0.442, 0), (0, 0.242, 0.758)),
        "deuteranopia": ((0.625, 0.375, 0), (0.7, 0.3, 0), (0, 0.3, 0.7)),
        "tritanopia": ((0.95, 0.05, 0), (0, 0.433, 0.567), (0, 0.475, 0.525)),
    }
    m = matrices.get(mode, matrices["protanopia"])
    r, g, b = rgb
    nr = min(255, max(0, round(r * m[0][0] + g * m[0][1] + b * m[0][2])))
    ng = min(255, max(0, round(r * m[1][0] + g * m[1][1] + b * m[1][2])))
    nb = min(255, max(0, round(r * m[2][0] + g * m[2][1] + b * m[2][2])))
    return (nr, ng, nb)


TOOLS: list[dict] = [
    {
        "name": "a11y_contrast",
        "description": "Compute WCAG contrast ratio between two hex colors and check AA/AAA compliance for normal and large text.",
        "params": {"fg": "string", "bg": "string"},
        "run": lambda a: _contrast_ratio(a.get("fg", "#000000"), a.get("bg", "#ffffff")),
    },
    {
        "name": "a11y_suggest_alt",
        "description": "Generate a starting point for image alt text from a description and optional context.",
        "params": {"image_desc": "string", "context": "string"},
        "run": lambda a: _suggest_alt_text(a.get("image_desc", ""), a.get("context", "")),
    },
    {
        "name": "a11y_reading_order",
        "description": "Analyze HTML for reading-order issues: skipped heading levels and images without alt text.",
        "params": {"html": "string"},
        "run": lambda a: _reading_order(a.get("html", "")),
    },
    {
        "name": "a11y_keyboard_check",
        "description": "Check HTML for keyboard accessibility issues: clickable divs/spans without tabindex or role, and empty links.",
        "params": {"html": "string"},
        "run": lambda a: _check_keyboard(a.get("html", "")),
    },
    {
        "name": "a11y_aria_labels",
        "description": "Check HTML for missing ARIA labels on inputs and empty buttons.",
        "params": {"html": "string"},
        "run": lambda a: _aria_labels(a.get("html", "")),
    },
    {
        "name": "a11y_color_blind_sim",
        "description": "Simulate how an RGB color appears under protanopia, deuteranopia, or tritanopia.",
        "params": {"r": "int", "g": "int", "b": "int", "mode": "string"},
        "run": lambda a: {"rgb": _color_blind_sim((int(a.get("r", 0)), int(a.get("g", 0)), int(a.get("b", 0))), a.get("mode", "protanopia"))},
    },
]
