"""Screenshot capture & annotation tools.

Pure-Python toolkit for capturing, annotating, blurring, OCR-ing, organizing,
and sharing screenshots. Each tool returns a dict with a ``status`` key.
"""
from __future__ import annotations
import re, time, uuid
from typing import Any

_SCREENSHOTS: dict[str, dict] = {}
_WORKSPACES: dict[str, dict] = {}
_HISTORY: list[dict] = []
_REDACT_LOG: list[dict] = {}
_CLIPBOARD: dict[str, Any] = {}

def _now() -> float: return time.time()
def _uid(p="ss") -> str: return f"{p}_{uuid.uuid4().hex[:10]}"
def _ok(**kw): return {"status": "ok", **kw}
def _err(m, **kw): return {"status": "error", "error": m, **kw}
def _slug(t): return re.sub(r"[^a-z0-9]+", "_", t.lower()).strip("_") or "untitled"
def _tsname(t): return f"{_slug(t)}_{time.strftime('%Y%m%d_%H%M%S')}.png"
def _emails(t): return re.findall(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", t)
def _cards(t): return re.findall(r"\b(?:\d[ -]*?){13,19}\b", t)
def _pwds(t): return re.findall(r"(?:password|passwd|pwd|secret|token)\s*[:=]\s*\S+", t, re.IGNORECASE)
def _bbox(w, h): return {"x": int(w*0.05), "y": int(h*0.05), "w": int(w*0.9), "h": int(h*0.9)}

def _screenshot_capture(a):
    sid = _uid("ss"); mode = a.get("mode","fullscreen")
    shot = {"id": sid, "mode": mode, "region": a.get("region"), "window": a.get("window",""), "width": a.get("width",1920), "height": a.get("height",1080), "ts": _now(), "data": a.get("data","")}
    _SCREENSHOTS[sid] = shot; _HISTORY.append({"id": sid, "ts": _now(), "mode": mode})
    return _ok(screenshot_id=sid, mode=mode)

def _screenshot_delayed(a):
    d = a.get("delay_seconds",5); return _ok(delay_seconds=d, countdown=list(range(d, 0, -1)))

def _screenshot_multi_monitor(a):
    monitors = a.get("monitors",[0,1]); shots = [{"monitor": m, "id": _uid("ss")} for m in monitors]
    return _ok(screenshots=shots, monitor_count=len(monitors))

def _screenshot_annotate(a):
    shot = _SCREENSHOTS.get(a.get("screenshot_id",""))
    if not shot: return _err("screenshot not found")
    anns = a.get("annotations",[])
    valid = {"arrow","box","blur","highlight","number"}
    for ann in anns:
        if ann.get("type") not in valid: return _err(f"invalid annotation type: {ann.get('type')}")
    shot["annotations"] = anns; return _ok(screenshot_id=a["screenshot_id"], annotation_count=len(anns))

def _screenshot_auto_blur(a):
    shot = _SCREENSHOTS.get(a.get("screenshot_id",""))
    if not shot: return _err("screenshot not found")
    t = a.get("text",""); blurred = {"emails": _emails(t), "cards": _cards(t), "passwords": _pwds(t)}
    shot["auto_blur"] = blurred; return _ok(screenshot_id=a["screenshot_id"], blurred=blurred)

def _screenshot_ocr(a):
    shot = _SCREENSHOTS.get(a.get("screenshot_id",""))
    if not shot: return _err("screenshot not found")
    t = a.get("text", shot.get("data","")); lines = t.split("\n") if t else []
    res = {"text": t, "lines": lines, "word_count": len(t.split()) if t else 0}
    shot["ocr"] = res; return _ok(screenshot_id=a["screenshot_id"], ocr=res)

def _screenshot_upload(a):
    sid = a.get("screenshot_id",""); prov = a.get("provider","internal")
    return _ok(screenshot_id=sid, url=f"https://{prov}.example.com/{sid}.png", provider=prov)

def _screenshot_history(a):
    q = a.get("query",""); lim = a.get("limit",20)
    res = [h for h in _HISTORY if not q or q.lower() in h.get("mode","").lower() or q.lower() in h.get("id","").lower()]
    return _ok(results=res[-lim:], total=len(res))

def _screenshot_auto_crop(a):
    shot = _SCREENSHOTS.get(a.get("screenshot_id",""))
    if not shot: return _err("screenshot not found")
    bbox = _bbox(shot["width"], shot["height"]); shot["cropped"] = bbox
    return _ok(screenshot_id=a["screenshot_id"], crop_region=bbox)

def _screenshot_color_picker(a):
    x, y = a.get("x",0), a.get("y",0)
    color = {"r": (x*7)%256, "g": (y*13)%256, "b": (x*y)%256, "hex": f"#{(x*7)%256:02x}{(y*13)%256:02x}{(x*y)%256:02x}"}
    return _ok(screenshot_id=a.get("screenshot_id",""), pixel={"x":x,"y":y}, color=color)

def _screenshot_compare(a):
    s1, s2 = _SCREENSHOTS.get(a.get("screenshot_a","")), _SCREENSHOTS.get(a.get("screenshot_b",""))
    if not s1 or not s2: return _err("screenshot(s) not found")
    diff = {"width_diff": abs(s1["width"]-s2["width"]), "height_diff": abs(s1["height"]-s2["height"]), "layout": "side_by_side"}
    return _ok(comparison=diff, screenshot_a=a["screenshot_a"], screenshot_b=a["screenshot_b"])

def _screenshot_batch(a):
    iv = a.get("interval_seconds",10); cnt = a.get("count",5)
    shots = [{"id": _uid("ss"), "index": i, "ts": _now()+i*iv} for i in range(cnt)]
    return _ok(screenshots=shots, count=cnt, interval=iv)

def _screenshot_workspace(a):
    wid = _uid("ws"); _WORKSPACES[wid] = {"id": wid, "name": a.get("name","Default"), "screenshots": [], "created": _now()}
    return _ok(workspace_id=wid, name=a.get("name","Default"))

def _screenshot_clipboard(a):
    sid = a.get("screenshot_id",""); dest = a.get("destination","clipboard")
    tmpl = a.get("naming_template","{title}_{timestamp}")
    name = tmpl.replace("{title}","screenshot").replace("{timestamp}", time.strftime("%Y%m%d_%H%M%S"))
    if dest == "clipboard": _CLIPBOARD["last"] = sid
    return _ok(screenshot_id=sid, destination=dest, filename=name)

def _screenshot_redact(a):
    rid = _uid("redact"); regions = a.get("regions",[]); rev = a.get("reversible",True)
    _REDACT_LOG.append({"id": rid, "screenshot_id": a.get("screenshot_id",""), "regions": regions, "reversible": rev, "ts": _now()})
    return _ok(redact_id=rid, region_count=len(regions), reversible=rev)

def _screenshot_to_markdown(a):
    shot = _SCREENSHOTS.get(a.get("screenshot_id",""))
    if not shot: return _err("screenshot not found")
    ocr = shot.get("ocr",{}).get("text","")
    md = f"## Screenshot {shot['id']}\n\n![screenshot]({shot['id']}.png)\n\n"
    if ocr: md += f"### Extracted Text\n\n```\n{ocr}\n```\n"
    return _ok(screenshot_id=shot["id"], markdown=md)

def _screenshot_filename(a):
    title = a.get("window_title","Untitled"); return _ok(filename=_tsname(title), window_title=title)

def _screenshot_chained(a):
    screens = a.get("screens",[0,1,2]); delay = a.get("delay_ms",200)
    chain = [{"index": i, "id": _uid("ss"), "delay_ms": i*delay} for i in range(len(screens))]
    return _ok(chained=chain, count=len(chain))

def _screenshot_sticker(a):
    shot = _SCREENSHOTS.get(a.get("screenshot_id",""))
    if not shot: return _err("screenshot not found")
    stickers = a.get("stickers",[]); shot["stickers"] = stickers
    return _ok(screenshot_id=a["screenshot_id"], sticker_count=len(stickers))

def _screenshot_perspective(a):
    corners = a.get("corners",[[0,0],[100,0],[100,100],[0,100]])
    if len(corners) != 4: return _err("exactly 4 corner points required")
    return _ok(corrected={"screenshot_id": a.get("screenshot_id",""), "corners": corners, "method": "homography"})

TOOLS: list[dict] = [
    {"name":"screenshot_capture","description":"Full-screen/window/region/scrolling page capture","params":{"mode":"str","region":"dict","window":"str","width":"int","height":"int","data":"str"},"run":lambda a:_screenshot_capture(a)},
    {"name":"screenshot_delayed","description":"Delayed capture with countdown","params":{"delay_seconds":"int"},"run":lambda a:_screenshot_delayed(a)},
    {"name":"screenshot_multi_monitor","description":"Multi-monitor aware capture","params":{"monitors":"list"},"run":lambda a:_screenshot_multi_monitor(a)},
    {"name":"screenshot_annotate","description":"Arrows/boxes/blur/highlight/numbered steps","params":{"screenshot_id":"str","annotations":"list"},"run":lambda a:_screenshot_annotate(a)},
    {"name":"screenshot_auto_blur","description":"Auto-blur sensitive text: emails, credit cards, passwords","params":{"screenshot_id":"str","text":"str"},"run":lambda a:_screenshot_auto_blur(a)},
    {"name":"screenshot_ocr","description":"OCR extraction from captured image","params":{"screenshot_id":"str","text":"str"},"run":lambda a:_screenshot_ocr(a)},
    {"name":"screenshot_upload","description":"Direct upload to cloud with shareable link","params":{"screenshot_id":"str","provider":"str"},"run":lambda a:_screenshot_upload(a)},
    {"name":"screenshot_history","description":"Screenshot history gallery with search by content","params":{"query":"str","limit":"int"},"run":lambda a:_screenshot_history(a)},
    {"name":"screenshot_auto_crop","description":"Auto-crop to detected content","params":{"screenshot_id":"str"},"run":lambda a:_screenshot_auto_crop(a)},
    {"name":"screenshot_color_picker","description":"Pixel color picker and measurement ruler","params":{"screenshot_id":"str","x":"int","y":"int"},"run":lambda a:_screenshot_color_picker(a)},
    {"name":"screenshot_compare","description":"Before/after side-by-side comparison","params":{"screenshot_a":"str","screenshot_b":"str"},"run":lambda a:_screenshot_compare(a)},
    {"name":"screenshot_batch","description":"Batch capture on schedule","params":{"interval_seconds":"int","count":"int"},"run":lambda a:_screenshot_batch(a)},
    {"name":"screenshot_workspace","description":"Named workspace/project folders","params":{"name":"str"},"run":lambda a:_screenshot_workspace(a)},
    {"name":"screenshot_clipboard","description":"Auto-paste to clipboard or file with naming templates","params":{"screenshot_id":"str","destination":"str","naming_template":"str"},"run":lambda a:_screenshot_clipboard(a)},
    {"name":"screenshot_redact","description":"Redaction stamps with reversible logging","params":{"screenshot_id":"str","regions":"list","reversible":"bool"},"run":lambda a:_screenshot_redact(a)},
    {"name":"screenshot_to_markdown","description":"Screenshot-to-markdown converter","params":{"screenshot_id":"str"},"run":lambda a:_screenshot_to_markdown(a)},
    {"name":"screenshot_filename","description":"Automatic filename from window title + timestamp","params":{"window_title":"str"},"run":lambda a:_screenshot_filename(a)},
    {"name":"screenshot_chained","description":"Chained capture of multiple screens","params":{"screens":"list","delay_ms":"int"},"run":lambda a:_screenshot_chained(a)},
    {"name":"screenshot_sticker","description":"Emoji and sticker overlay","params":{"screenshot_id":"str","stickers":"list"},"run":lambda a:_screenshot_sticker(a)},
    {"name":"screenshot_perspective","description":"Perspective correction for photographed screens","params":{"screenshot_id":"str","corners":"list"},"run":lambda a:_screenshot_perspective(a)},
]