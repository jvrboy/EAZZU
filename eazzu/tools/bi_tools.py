"""Business intelligence & data visualization tools.

Build dashboards, KPIs, charts (as SVG), and natural-language Q&A over
in-memory datasets. Pure-Python SVG generation — no browser required.
"""
from __future__ import annotations

import math as _math
import statistics as _stats

_CHART_TYPES = {"bar", "column", "line", "area", "pie", "doughnut", "scatter", "radar", "funnel", "gauge", "treemap", "waterfall"}


def _is_num(v):
    try:
        float(v)
        return True
    except (TypeError, ValueError):
        return False


def _svg_header(w, h):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" style="font-family:system-ui,sans-serif;font-size:12px">'


def _bar_chart(data, x, y, w=600, h=400, horizontal=False):
    if not data:
        return _svg_header(w, h) + "<text>No data</text></svg>"
    max_val = max(float(d[y]) for d in data) or 1
    margin, n = 60, len(data)
    plot_w, plot_h = w - 2 * margin, h - 2 * margin
    bar_size = (plot_h if horizontal else plot_w) / n * 0.7
    gap = (plot_h if horizontal else plot_w) / n * 0.3
    parts = [_svg_header(w, h), f'<rect width="{w}" height="{h}" fill="#ffffff"/>']
    for i, d in enumerate(data):
        val = float(d[y])
        length = (val / max_val) * (plot_w if horizontal else plot_h)
        if horizontal:
            yp = margin + i * (bar_size + gap)
            parts.append(f'<rect x="{margin}" y="{yp}" width="{length}" height="{bar_size}" fill="#0ea5e9"/>')
            parts.append(f'<text x="{margin-5}" y="{yp+bar_size/2}" text-anchor="end">{d[x]}</text>')
        else:
            xp = margin + i * (bar_size + gap)
            parts.append(f'<rect x="{xp}" y="{margin+plot_h-length}" width="{bar_size}" height="{length}" fill="#0ea5e9"/>')
            parts.append(f'<text x="{xp+bar_size/2}" y="{margin+plot_h+15}" text-anchor="middle">{d[x]}</text>')
    parts.append(f'<line x1="{margin}" y1="{margin+plot_h}" x2="{margin+plot_w}" y2="{margin+plot_h}" stroke="#cbd5e1"/>')
    return "\n".join(parts) + "</svg>"


def _line_chart(data, x, y, w=600, h=400, area=False):
    if not data:
        return _svg_header(w, h) + "<text>No data</text></svg>"
    margin = 60
    plot_w, plot_h = w - 2 * margin, h - 2 * margin
    vals = [float(d[y]) for d in data]
    max_val, min_val = max(vals), min(vals)
    rng = (max_val - min_val) or 1
    n = len(data)
    pts = []
    for i, d in enumerate(data):
        px = margin + (i / max(n - 1, 1)) * plot_w
        py = margin + plot_h - ((float(d[y]) - min_val) / rng) * plot_h
        pts.append((px, py))
    parts = [_svg_header(w, h), f'<rect width="{w}" height="{h}" fill="#ffffff"/>']
    path = "M " + " L ".join(f"{p[0]:.1f} {p[1]:.1f}" for p in pts)
    if area:
        parts.append(f'<path d="{path} L {margin+plot_w} {margin+plot_h} L {margin} {margin+plot_h} Z" fill="#0ea5e9" opacity="0.2"/>')
    parts.append(f'<path d="{path}" stroke="#0ea5e9" stroke-width="2" fill="none"/>')
    for i, (px, py) in enumerate(pts):
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="3" fill="#0369a1"/>')
        parts.append(f'<text x="{px:.1f}" y="{margin+plot_h+15}" text-anchor="middle">{data[i][x]}</text>')
    return "\n".join(parts) + "</svg>"


def _pie_chart(data, label, value, w=400, h=400, doughnut=False):
    if not data:
        return _svg_header(w, h) + "<text>No data</text></svg>"
    total = sum(float(d[value]) for d in data) or 1
    cx, cy, r = w / 2, h / 2, min(w, h) / 2 - 40
    colors = ["#0ea5e9", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#f97316"]
    parts = [_svg_header(w, h), f'<rect width="{w}" height="{h}" fill="#ffffff"/>']
    angle = -90
    for i, d in enumerate(data):
        frac = float(d[value]) / total
        sweep = frac * 360
        end = angle + sweep
        rad_s, rad_e = _math.radians(angle), _math.radians(end)
        x1, y1 = cx + r * _math.cos(rad_s), cy + r * _math.sin(rad_s)
        x2, y2 = cx + r * _math.cos(rad_e), cy + r * _math.sin(rad_e)
        large = 1 if sweep > 180 else 0
        if doughnut:
            ri = r * 0.5
            xi1, yi1 = cx + ri * _math.cos(rad_s), cy + ri * _math.sin(rad_s)
            xi2, yi2 = cx + ri * _math.cos(rad_e), cy + ri * _math.sin(rad_e)
            parts.append(f'<path d="M {x1:.1f} {y1:.1f} A {r} {r} 0 {large} 1 {x2:.1f} {y2:.1f} L {xi2:.1f} {yi2:.1f} A {ri} {ri} 0 {large} 0 {xi1:.1f} {yi1:.1f} Z" fill="{colors[i % len(colors)]}"/>')
        else:
            parts.append(f'<path d="M {cx} {cy} L {x1:.1f} {y1:.1f} A {r} {r} 0 {large} 1 {x2:.1f} {y2:.1f} Z" fill="{colors[i % len(colors)]}"/>')
        mid = _math.radians((angle + end) / 2)
        parts.append(f'<text x="{cx+(r*0.6)*_math.cos(mid):.1f}" y="{cy+(r*0.6)*_math.sin(mid):.1f}" text-anchor="middle" fill="white">{d[label]}</text>')
        angle = end
    return "\n".join(parts) + "</svg>"


def _scatter_chart(data, x, y, w=600, h=400):
    margin = 60
    plot_w, plot_h = w - 2 * margin, h - 2 * margin
    xs = [float(d[x]) for d in data]
    ys = [float(d[y]) for d in data]
    if not xs:
        return _svg_header(w, h) + "<text>No data</text></svg>"
    x_min, x_max, y_min, y_max = min(xs), max(xs), min(ys), max(ys)
    x_rng = (x_max - x_min) or 1
    y_rng = (y_max - y_min) or 1
    parts = [_svg_header(w, h), f'<rect width="{w}" height="{h}" fill="#ffffff"/>']
    for d in data:
        px = margin + ((float(d[x]) - x_min) / x_rng) * plot_w
        py = margin + plot_h - ((float(d[y]) - y_min) / y_rng) * plot_h
        parts.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4" fill="#0ea5e9"/>')
    parts.append(f'<line x1="{margin}" y1="{margin+plot_h}" x2="{margin+plot_w}" y2="{margin+plot_h}" stroke="#cbd5e1"/>')
    parts.append(f'<line x1="{margin}" y1="{margin}" x2="{margin}" y2="{margin+plot_h}" stroke="#cbd5e1"/>')
    return "\n".join(parts) + "</svg>"


def _gauge_chart(value, max_val=100, label="KPI", w=300, h=200):
    cx, cy, r = w / 2, h * 0.8, min(w, h) * 0.4
    frac = max(0, min(1, value / max_val if max_val else 0))
    rad = _math.radians(-180 + frac * 180)
    x, y = cx + r * _math.cos(rad), cy + r * _math.sin(rad)
    color = "#10b981" if frac > 0.66 else "#f59e0b" if frac > 0.33 else "#ef4444"
    parts = [_svg_header(w, h), f'<rect width="{w}" height="{h}" fill="#ffffff"/>']
    parts.append(f'<path d="M {cx-r} {cy} A {r} {r} 0 0 1 {cx+r} {cy}" stroke="#e2e8f0" stroke-width="20" fill="none"/>')
    parts.append(f'<path d="M {cx-r} {cy} A {r} {r} 0 0 1 {x:.1f} {y:.1f}" stroke="{color}" stroke-width="20" fill="none"/>')
    parts.append(f'<text x="{cx}" y="{cy-10}" text-anchor="middle" font-size="24">{value:.1f}</text>')
    parts.append(f'<text x="{cx}" y="{cy+20}" text-anchor="middle">{label}</text>')
    return "\n".join(parts) + "</svg>"


def _funnel_chart(data, label, value, w=400, h=400):
    if not data:
        return _svg_header(w, h) + "<text>No data</text></svg>"
    max_val = max(float(d[value]) for d in data) or 1
    n = len(data)
    section_h = h / n
    parts = [_svg_header(w, h), f'<rect width="{w}" height="{h}" fill="#ffffff"/>']
    colors = ["#0ea5e9", "#38bdf8", "#7dd3fc", "#bae6fd", "#e0f2fe"]
    for i, d in enumerate(data):
        bw = (float(d[value]) / max_val) * w
        x = (w - bw) / 2
        parts.append(f'<rect x="{x:.1f}" y="{i*section_h:.1f}" width="{bw:.1f}" height="{section_h-4:.1f}" fill="{colors[i % len(colors)]}"/>')
        parts.append(f'<text x="{w/2:.1f}" y="{i*section_h+section_h/2:.1f}" text-anchor="middle" fill="white">{d[label]}: {d[value]}</text>')
    return "\n".join(parts) + "</svg>"


def _kpi_card(label, value, target=None, unit=""):
    pct = (value / target * 100) if target else None
    status = "on track" if target and value >= target else "below target" if target else "n/a"
    return {"label": label, "value": value, "unit": unit, "target": target, "percent_of_target": round(pct, 1) if pct else None, "status": status}


def _dashboard(title, kpis, charts):
    return {
        "title": title, "kpis": kpis, "charts": charts,
        "layout": [{"x": 0, "y": 0, "w": 12, "h": 2, "type": "kpi"}] * len(kpis) + [{"x": i % 2 * 6, "y": 2 + i // 2 * 4, "w": 6, "h": 4, "type": "chart"} for i in range(len(charts))],
    }


def _nlq(question, dataset):
    q = question.lower()
    if not dataset:
        return {"answer": "No data available."}
    cols = list(dataset[0].keys())
    if "how many" in q or "count" in q:
        return {"answer": f"There are {len(dataset)} records.", "count": len(dataset)}
    for c in cols:
        if c in q:
            vals = [float(d[c]) for d in dataset if _is_num(d[c])]
            if "sum" in q or "total" in q:
                return {"answer": f"Sum of {c}: {sum(vals):.2f}", "sum": sum(vals)}
            if "average" in q or "mean" in q:
                return {"answer": f"Average of {c}: {_stats.mean(vals):.2f}", "mean": _stats.mean(vals)}
            if "max" in q or "highest" in q:
                return {"answer": f"Max of {c}: {max(vals)}", "max": max(vals)}
            if "min" in q or "lowest" in q:
                return {"answer": f"Min of {c}: {min(vals)}", "min": min(vals)}
    return {"answer": f"Columns: {', '.join(cols)}. Ask about count, sum, average, max, or min of any column."}


def _render_chart(a):
    ctype, data = a.get("type", "bar"), a.get("data", [])
    w, h = int(a.get("width", 600)), int(a.get("height", 400))
    if ctype == "bar":
        return {"svg": _bar_chart(data, a.get("x", ""), a.get("y", ""), w, h, horizontal=True)}
    if ctype == "column":
        return {"svg": _bar_chart(data, a.get("x", ""), a.get("y", ""), w, h, horizontal=False)}
    if ctype == "line":
        return {"svg": _line_chart(data, a.get("x", ""), a.get("y", ""), w, h, area=False)}
    if ctype == "area":
        return {"svg": _line_chart(data, a.get("x", ""), a.get("y", ""), w, h, area=True)}
    if ctype in ("pie", "doughnut"):
        return {"svg": _pie_chart(data, a.get("label", ""), a.get("value", ""), w, h, doughnut=(ctype == "doughnut"))}
    if ctype == "scatter":
        return {"svg": _scatter_chart(data, a.get("x", ""), a.get("y", ""), w, h)}
    if ctype == "gauge":
        return {"svg": _gauge_chart(float(a.get("value", 0)), float(a.get("max", 100)), a.get("label", "KPI"), w, h)}
    if ctype == "funnel":
        return {"svg": _funnel_chart(data, a.get("label", ""), a.get("value", ""), w, h)}
    return {"error": f"unsupported chart type: {ctype}"}


TOOLS: list[dict] = [
    {
        "name": "bi_chart",
        "description": "Generate an SVG chart (bar, column, line, area, pie, doughnut, scatter, gauge, funnel) from a list-of-dicts.",
        "params": {"type": "string", "data": "list", "x": "string", "y": "string", "label": "string", "value": "string", "width": "int", "height": "int"},
        "run": lambda a: _render_chart(a),
    },
    {
        "name": "bi_kpi",
        "description": "Build a KPI card with label, value, target, percent-of-target, and status.",
        "params": {"label": "string", "value": "number", "target": "number", "unit": "string"},
        "run": lambda a: _kpi_card(a.get("label", ""), float(a.get("value", 0)), float(a["target"]) if a.get("target") else None, a.get("unit", "")),
    },
    {
        "name": "bi_dashboard",
        "description": "Assemble a dashboard from KPI cards and chart definitions with a grid layout.",
        "params": {"title": "string", "kpis": "list", "charts": "list"},
        "run": lambda a: _dashboard(a.get("title", "Dashboard"), a.get("kpis", []), a.get("charts", [])),
    },
    {
        "name": "bi_nlq",
        "description": "Natural-language Q&A over a dataset: ask about count, sum, average, max, or min of any column.",
        "params": {"question": "string", "dataset": "list"},
        "run": lambda a: _nlq(a.get("question", ""), a.get("dataset", [])),
    },
    {
        "name": "bi_chart_types",
        "description": "List all supported chart types.",
        "params": {},
        "run": lambda a: {"types": sorted(_CHART_TYPES)},
    },
]
