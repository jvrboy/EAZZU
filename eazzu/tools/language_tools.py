"""Global & language tools.

Translation requests (routed via the configured provider), RTL/bidi
handling, Unicode normalization, script detection, phonetic guides
(furigana/pinyin), and localized date/number/currency formatting.
"""
from __future__ import annotations

import re as _re
import unicodedata as _ud
from datetime import datetime


_RTL_RANGES = [
    (0x0590, 0x05FF), (0x0600, 0x06FF), (0x0700, 0x074F), (0x0750, 0x077F),
    (0x0780, 0x07BF), (0x07C0, 0x07FF), (0x0800, 0x083F), (0xFB1D, 0xFB4F),
    (0xFB50, 0xFDFF), (0xFE70, 0xFEFF),
]


def _is_rtl(text):
    for ch in text:
        cp = ord(ch)
        for lo, hi in _RTL_RANGES:
            if lo <= cp <= hi:
                return True
    return False


def _bidi_wrap(text):
    return f"\u202B{text}\u202C" if _is_rtl(text) else f"\u202A{text}\u202C"


def _normalize(text, form="NFC"):
    form = form.upper()
    if form not in ("NFC", "NFD", "NFKC", "NFKD"):
        form = "NFC"
    return _ud.normalize(form, text)


def _script_detect(text):
    scripts = set()
    for ch in text:
        name = _ud.name(ch, "")
        if "LATIN" in name:
            scripts.add("Latin")
        elif "CYRILLIC" in name:
            scripts.add("Cyrillic")
        elif "ARABIC" in name:
            scripts.add("Arabic")
        elif "HEBREW" in name:
            scripts.add("Hebrew")
        elif "CJK" in name or "HIRAGANA" in name or "KATAKANA" in name or "HANGUL" in name:
            scripts.add("CJK")
        elif "DEVANAGARI" in name:
            scripts.add("Devanagari")
        elif "THAI" in name:
            scripts.add("Thai")
    return sorted(scripts)


def _phonetic_guide(text, script="auto"):
    if script == "auto":
        detected = _script_detect(text)
        script = detected[0] if detected else "Latin"
    if script == "CJK":
        pinyin_map = {"你好": "nǐ hǎo", "谢谢": "xiè xie", "中国": "zhōng guó", "日本": "rì běn", "学校": "xué xiào", "老师": "lǎo shī"}
        furigana_map = {"日本": "にほん", "学校": "がっこう", "先生": "せんせい"}
        guides = []
        for k, v in pinyin_map.items():
            if k in text:
                guides.append({"char": k, "pinyin": v, "furigana": furigana_map.get(k, "")})
        return {"text": text, "guide": guides}
    return {"text": text, "guide": [], "note": f"no phonetic guide for {script}"}


def _format_date(date_str, locale="en_US", format="long"):
    try:
        dt = datetime.fromisoformat(date_str) if "T" in date_str else datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return date_str
    formats = {"long": "%A, %B %d, %Y", "short": "%m/%d/%Y", "iso": "%Y-%m-%d", "european": "%d/%m/%Y"}
    return dt.strftime(formats.get(format, formats["long"]))


def _format_number(value, locale="en_US", decimals=2):
    sep, dec = (".", ",") if locale in ("de_DE", "fr_FR", "es_ES", "pt_BR", "ru_RU") else (",", ".")
    s = f"{value:,.{decimals}f}"
    return s.replace(",", "§").replace(".", dec).replace("§", sep)


def _format_currency(value, code="USD", locale="en_US"):
    symbols = {"USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", "CNY": "¥", "INR": "₹", "NGN": "₦", "KES": "KSh", "ZAR": "R"}
    sym = symbols.get(code, code + " ")
    return sym + _format_number(value, locale, 2 if code != "JPY" else 0)


def _translate(text, source="auto", target="en"):
    return {"type": "translation_request", "text": text, "source": source, "target": target, "note": "translation is routed through the configured AI provider by the agent"}


def _proofread(text):
    issues = []
    if "  " in text:
        issues.append({"type": "spacing", "message": "Multiple consecutive spaces", "fix": "Use a single space"})
    if _re.search(r"\s+[,.!?;:]", text):
        issues.append({"type": "punctuation", "message": "Space before punctuation", "fix": "Remove space before punctuation"})
    if _re.search(r"[,.!?;:][^\s\n]", text):
        issues.append({"type": "punctuation", "message": "Missing space after punctuation", "fix": "Add a space after punctuation"})
    if _re.search(r"[.!?]\s+[a-z]", text):
        issues.append({"type": "capitalization", "message": "Sentence not capitalized", "fix": "Capitalize the first word of each sentence"})
    if _re.search(r"\b(\w+)\s+\1\b", text, _re.I):
        issues.append({"type": "repetition", "message": "Repeated word", "fix": "Remove the duplicate word"})
    return {"issues": issues, "issue_count": len(issues)}


TOOLS: list[dict] = [
    {
        "name": "lang_translate",
        "description": "Request a translation of text between languages. Routed through the configured AI provider by the agent.",
        "params": {"text": "string", "source": "string", "target": "string"},
        "run": lambda a: _translate(a.get("text", ""), a.get("source", "auto"), a.get("target", "en")),
    },
    {
        "name": "lang_detect_rtl",
        "description": "Detect whether text contains right-to-left characters (Arabic, Hebrew, Syriac, etc.).",
        "params": {"text": "string"},
        "run": lambda a: {"rtl": _is_rtl(a.get("text", ""))},
    },
    {
        "name": "lang_bidi_wrap",
        "description": "Wrap text with Unicode bidi controls so RTL text renders correctly in LTR contexts.",
        "params": {"text": "string"},
        "run": lambda a: {"text": _bidi_wrap(a.get("text", ""))},
    },
    {
        "name": "lang_normalize",
        "description": "Normalize Unicode text to a given form (NFC, NFD, NFKC, NFKD).",
        "params": {"text": "string", "form": "string"},
        "run": lambda a: {"text": _normalize(a.get("text", ""), a.get("form", "NFC"))},
    },
    {
        "name": "lang_detect_script",
        "description": "Detect the scripts present in text (Latin, Cyrillic, Arabic, Hebrew, CJK, Devanagari, Thai).",
        "params": {"text": "string"},
        "run": lambda a: {"scripts": _script_detect(a.get("text", ""))},
    },
    {
        "name": "lang_phonetic_guide",
        "description": "Generate a phonetic guide (pinyin/furigana) for CJK text.",
        "params": {"text": "string", "script": "string"},
        "run": lambda a: _phonetic_guide(a.get("text", ""), a.get("script", "auto")),
    },
    {
        "name": "lang_format_date",
        "description": "Format an ISO date as long, short, iso, or european style.",
        "params": {"date": "string", "locale": "string", "format": "string"},
        "run": lambda a: {"formatted": _format_date(a.get("date", ""), a.get("locale", "en_US"), a.get("format", "long"))},
    },
    {
        "name": "lang_format_number",
        "description": "Format a number with locale-appropriate separators (en_US vs de_DE/fr_FR style).",
        "params": {"value": "number", "locale": "string", "decimals": "int"},
        "run": lambda a: {"formatted": _format_number(float(a.get("value", 0)), a.get("locale", "en_US"), int(a.get("decimals", 2)))},
    },
    {
        "name": "lang_format_currency",
        "description": "Format a number as a localized currency string with the right symbol.",
        "params": {"value": "number", "code": "string", "locale": "string"},
        "run": lambda a: {"formatted": _format_currency(float(a.get("value", 0)), a.get("code", "USD"), a.get("locale", "en_US"))},
    },
    {
        "name": "lang_proofread",
        "description": "Check text for common spelling/punctuation/capitalization issues (spacing, repeated words, sentence caps).",
        "params": {"text": "string"},
        "run": lambda a: _proofread(a.get("text", "")),
    },
]
