"""Document authoring & word processing tools.

Pure-Python text/Markdown authoring helpers — no external binary
dependencies, so they work on iSH/Alpine. Covers formatting, styles,
templates, TOC/footnote generation, word count/readability, and export.
"""
from __future__ import annotations

import re
import string
from collections import Counter
from pathlib import Path

_STYLE_PRESETS = {
    "default": {"font": "Calibri", "size": 11, "line_spacing": 1.15},
    "manuscript": {"font": "Times New Roman", "size": 12, "line_spacing": 2.0},
    "compact": {"font": "Arial", "size": 10, "line_spacing": 1.0},
    "technical": {"font": "Cambria", "size": 11, "line_spacing": 1.25},
}

_TEMPLATES = {
    "resume": "# {name}\n{contact}\n\n## Experience\n- {role} @ {company}\n\n## Skills\n- \n",
    "letter": "{date}\n\n{recipient}\n\nDear {recipient_name},\n\n{body}\n\nSincerely,\n{name}\n",
    "report": "# {title}\n\n**Author:** {author}\n**Date:** {date}\n\n## Executive Summary\n\n## Findings\n\n## Recommendations\n",
    "invoice": "INVOICE #{number}\nDate: {date}\nBilled to: {client}\n\n| Item | Qty | Price | Total |\n|------|-----|-------|-------|\n| {item} | {qty} | ${price} | ${total} |\n\n**Total Due:** ${total}\n",
    "newsletter": "# {title} — {date}\n\n## Lead Story\n\n## Updates\n\n## Events\n",
    "brochure": "# {title}\n\n## About\n\n## Features\n- \n\n## Contact\n",
}

_ALIGNMENTS = {"left": "<div style='text-align:left'>", "center": "<div style='text-align:center'>", "right": "<div style='text-align:right'>", "justify": "<div style='text-align:justify'>"}

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "at", "is", "are",
    "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "for", "with", "as", "by", "this", "that", "it", "its", "from", "he", "she", "they",
    "we", "you", "i", "not", "no", "so", "if", "then", "than", "about",
}


def _word_count(text: str) -> dict:
    words = re.findall(r"\b[\w'-]+\b", text, flags=re.UNICODE)
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    syllables = sum(_syllables(w) for w in words)
    return {
        "words": len(words),
        "characters": len(text),
        "characters_no_spaces": len(text.replace(" ", "")),
        "sentences": len(sentences),
        "paragraphs": len([p for p in text.split("\n\n") if p.strip()]),
        "lines": text.count("\n") + 1,
        "syllables": syllables,
        "avg_words_per_sentence": round(len(words) / max(len(sentences), 1), 2),
    }


def _syllables(word: str) -> int:
    word = re.sub(r"[^a-zA-Z]", "", word.lower())
    if not word:
        return 0
    return max(len(re.findall(r"[aeiouy]+", word)), 1)


def _readability(text: str) -> dict:
    stats = _word_count(text)
    words, sentences, syllables = stats["words"], max(stats["sentences"], 1), max(stats["syllables"], 1)
    flesch = 206.835 - 1.015 * (words / sentences) - 84.6 * (syllables / words)
    grade = 0.39 * (words / sentences) + 11.8 * (syllables / words) - 15.59
    return {
        "flesch_reading_ease": round(flesch, 2),
        "flesch_kincaid_grade": round(max(grade, 0), 2),
        "reading_time_minutes": round(words / 200, 2),
        "speaking_time_minutes": round(words / 130, 2),
    }


def _format_text(text: str, fmt: str) -> str:
    if fmt == "uppercase":
        return text.upper()
    if fmt == "lowercase":
        return text.lower()
    if fmt == "title":
        return string.capwords(text)
    if fmt == "sentence":
        return text[:1].upper() + text[1:].lower() if text else text
    if fmt == "smallcaps":
        return "".join(chr(ord(c) - 32) if "a" <= c <= "z" else c for c in text)
    if fmt == "superscript":
        sup = "⁰¹²³⁴⁵⁶⁷⁸⁹"
        return "".join(sup[int(c)] if c.isdigit() else c for c in text)
    if fmt == "subscript":
        sub = "₀₁₂₃₄₅₆₇₈₉"
        return "".join(sub[int(c)] if c.isdigit() else c for c in text)
    return text


def _build_toc(markdown: str, max_level: int = 3) -> str:
    lines = []
    for line in markdown.splitlines():
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            level = len(m.group(1))
            if level <= max_level:
                title = m.group(2).strip()
                anchor = re.sub(r"[^\w\s-]", "", title).strip().lower().replace(" ", "-")
                lines.append(f"{'  ' * (level - 1)}- [{title}](#{anchor})")
    return "\n".join(lines)


def _footnote_block(body: str, footnotes: list[str]) -> str:
    if not footnotes:
        return body
    block = "\n\n---\n### Footnotes\n\n"
    for i, fn in enumerate(footnotes, 1):
        body = re.sub(r"\[\^" + str(i) + r"\]", f"[^{i}]", body)
        block += f"[^{i}]: {fn}\n"
    return body + block


def _strip_markdown(text: str) -> str:
    text = re.sub(r"!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    text = re.sub(r"[#*_`~>]", "", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def _export_text(text: str, fmt: str, path: str) -> dict:
    if not path:
        return {"error": "path required"}
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "md":
        p.write_text(text, encoding="utf-8")
    elif fmt == "txt":
        p.write_text(_strip_markdown(text), encoding="utf-8")
    elif fmt == "html":
        p.write_text("<!doctype html><html><body><pre style='white-space:pre-wrap'>" + text + "</pre></body></html>", encoding="utf-8")
    elif fmt == "pdf":
        try:
            from fpdf import FPDF  # type: ignore
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Helvetica", size=11)
            for line in _strip_markdown(text).splitlines():
                pdf.multi_cell(0, 6, line)
            pdf.output(str(p))
        except Exception as e:
            p.write_text(_strip_markdown(text), encoding="utf-8")
            return {"path": str(p), "fallback": "txt", "error": f"fpdf unavailable: {e}"}
    else:
        return {"error": f"unsupported format: {fmt}"}
    return {"path": str(p), "format": fmt, "bytes": p.stat().st_size}


def _word_frequency(text: str, top: int = 20) -> list[tuple[str, int]]:
    words = [w.lower() for w in re.findall(r"\b[\w'-]+\b", text) if w.lower() not in _STOPWORDS]
    return Counter(words).most_common(top)


TOOLS: list[dict] = [
    {"name": "doc_format_text", "description": "Apply text formatting: case transforms (uppercase, lowercase, title, sentence, smallcaps), or numeric superscript/subscript.", "params": {"text": "string", "format": "string"}, "run": lambda a: {"result": _format_text(a.get("text", ""), a.get("format", ""))}},
    {"name": "doc_apply_style", "description": "Apply a named style preset (default, manuscript, compact, technical) to a block of text.", "params": {"text": "string", "style": "string"}, "run": lambda a: {"style": a.get("style", "default"), "preset": _STYLE_PRESETS.get(a.get("style", "default"), _STYLE_PRESETS["default"]), "text": a.get("text", "")}},
    {"name": "doc_template", "description": "Render a built-in document template (resume, letter, report, invoice, newsletter, brochure) with provided fields.", "params": {"template": "string", "fields": "object"}, "run": lambda a: {"template": a.get("template", ""), "rendered": _TEMPLATES.get(a.get("template", ""), "Unknown template").format(**{k: v for k, v in a.get("fields", {}).items()})}},
    {"name": "doc_align_paragraph", "description": "Wrap a paragraph with an alignment directive (left, center, right, justify) for HTML export.", "params": {"text": "string", "alignment": "string"}, "run": lambda a: {"alignment": a.get("alignment", "left"), "html": _ALIGNMENTS.get(a.get("alignment", "left"), _ALIGNMENTS["left"]) + a.get("text", "") + "</div>"}},
    {"name": "doc_page_layout", "description": "Define page layout metadata (margins, orientation, size, columns) for a document section.", "params": {"margins": "string", "orientation": "string", "size": "string", "columns": "int"}, "run": lambda a: {"layout": {"margins": a.get("margins", "1in"), "orientation": a.get("orientation", "portrait"), "size": a.get("size", "letter"), "columns": int(a.get("columns", 1))}}},
    {"name": "doc_build_toc", "description": "Generate a Markdown table of contents from the headings in a Markdown document.", "params": {"markdown": "string", "max_level": "int"}, "run": lambda a: {"toc": _build_toc(a.get("markdown", ""), int(a.get("max_level", 3)))}},
    {"name": "doc_add_footnotes", "description": "Append a footnotes block to a Markdown document, replacing [^n] markers in the body.", "params": {"body": "string", "footnotes": "list"}, "run": lambda a: {"document": _footnote_block(a.get("body", ""), a.get("footnotes", []))}},
    {"name": "doc_word_count", "description": "Compute word count, characters, sentences, paragraphs, syllables, and average words per sentence.", "params": {"text": "string"}, "run": lambda a: _word_count(a.get("text", ""))},
    {"name": "doc_readability", "description": "Compute Flesch reading ease, Flesch-Kincaid grade level, reading time, and speaking time.", "params": {"text": "string"}, "run": lambda a: _readability(a.get("text", ""))},
    {"name": "doc_strip_markdown", "description": "Strip Markdown formatting to produce plain text.", "params": {"text": "string"}, "run": lambda a: {"text": _strip_markdown(a.get("text", ""))}},
    {"name": "doc_export", "description": "Export a document to md, txt, html, or pdf (pdf falls back to txt if fpdf is unavailable).", "params": {"text": "string", "format": "string", "path": "string"}, "run": lambda a: _export_text(a.get("text", ""), a.get("format", "md"), a.get("path", ""))},
    {"name": "doc_word_frequency", "description": "Compute the top-N most frequent words (case-insensitive, stopwords excluded).", "params": {"text": "string", "top": "int"}, "run": lambda a: {"frequencies": _word_frequency(a.get("text", ""), int(a.get("top", 20)))}},
]
