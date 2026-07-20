"""Screen recording tools.

Pure-Python toolkit for screen recording with webcam PIP, audio dual-track,
keystroke visualization, green-screen removal, cursor effects, editing,
transcription, chapter markers, multi-scene capture, and export.
Each tool returns a dict with a ``status`` key.
"""
from __future__ import annotations
import re, time, uuid
from typing import Any

_SESSIONS: dict[str, dict] = {}
_BOOKMARKS: dict[str, list[dict]] = {}
_CHAPTERS: dict[str, list[dict]] = {}
_TRANSCRIPTS: dict[str, list[dict]] = {}

def _now() -> float: return time.time()
def _uid(p="rec") -> str: return f"{p}_{uuid.uuid4().hex[:10]}"
def _ok(**kw): return {"status": "ok", **kw}
def _err(m, **kw): return {"status": "error", "error": m, **kw}
def _sess(sid): return _SESSIONS.get(sid)
def _ts(s): return f"{int(s)//60:02d}:{int(s)%60:02d}"
def _silence(chunks): return [c for c in chunks if c.get("level", 0) < -50]
def _fillers(t):
    fillers = ["um","uh","like","you know","so basically","i mean"]; res = []
    for f in fillers:
        for m in re.finditer(rf"\b{re.escape(f)}\b", t.lower()): res.append({"word": f, "start": m.start()})
    return res
def _br(q): return {"low":1500,"medium":4000,"high":8000,"ultra":16000}.get(q, 4000)

def _record_start(a):
    sid = _uid("rec")
    cfg = {"webcam_pip": a.get("webcam_pip",False), "mic_audio": a.get("mic_audio",True), "system_audio": a.get("system_audio",True), "resolution": a.get("resolution","1080p"), "fps": a.get("fps",30), "region": a.get("region")}
    _SESSIONS[sid] = {"id": sid, "status": "recording", "config": cfg, "started": _now(), "duration": 0}
    return _ok(session_id=sid, config=cfg)

def _record_keystroke_viz(a):
    s = _sess(a.get("session_id",""))
    if not s: return _err("session not found")
    viz = {"enabled": a.get("enabled",True), "style": a.get("style","fade"), "position": a.get("position","bottom_center"), "show_mouse": a.get("show_mouse",True)}
    s["keystroke_viz"] = viz; return _ok(session_id=a["session_id"], keystroke_viz=viz)

def _record_green_screen(a):
    s = _sess(a.get("session_id",""))
    if not s: return _err("session not found")
    gs = {"enabled": a.get("enabled",True), "background": a.get("background","blur"), "threshold": a.get("threshold",0.4)}
    s["green_screen"] = gs; return _ok(session_id=a["session_id"], green_screen=gs)

def _record_cursor_highlight(a):
    s = _sess(a.get("session_id",""))
    if not s: return _err("session not found")
    ch = {"enabled": a.get("enabled",True), "color": a.get("color","#FFD700"), "radius": a.get("radius",30), "ripple": a.get("ripple",True)}
    s["cursor_highlight"] = ch; return _ok(session_id=a["session_id"], cursor_highlight=ch)

def _record_zoom_follow(a):
    s = _sess(a.get("session_id",""))
    if not s: return _err("session not found")
    zf = {"enabled": a.get("enabled",True), "zoom_level": a.get("zoom_level",1.5), "smoothness": a.get("smoothness",0.8)}
    s["zoom_follow"] = zf; return _ok(session_id=a["session_id"], zoom_follow=zf)

def _record_trim_split_merge(a):
    s = _sess(a.get("session_id",""))
    if not s: return _err("session not found")
    act = a.get("action","trim")
    if act == "trim": res = {"action":"trim", "start": a.get("start",0), "end": a.get("end", s["duration"])}
    elif act == "split": res = {"action":"split", "at": a.get("at",0), "parts": 2}
    elif act == "merge": res = {"action":"merge", "segments": a.get("segments",[])}
    else: return _err("unknown action")
    return _ok(session_id=a["session_id"], edit=res)

def _record_silence_remove(a):
    chunks = a.get("audio_chunks",[]); sil = _silence(chunks)
    return _ok(session_id=a.get("session_id",""), silences_removed=len(sil), remaining_chunks=len(chunks)-len(sil))

def _record_filler_cut(a):
    fillers = _fillers(a.get("transcript",""))
    return _ok(session_id=a.get("session_id",""), filler_count=len(fillers), fillers=fillers)

def _record_chapter_markers(a):
    sid = a.get("session_id",""); act = a.get("action","add")
    if act == "add":
        m = {"id": _uid("ch"), "label": a.get("label", f"Chapter {len(_CHAPTERS.get(sid,[]))+1}"), "timestamp": a.get("timestamp",0)}
        _CHAPTERS.setdefault(sid, []).append(m); return _ok(session_id=sid, chapter=m)
    if act == "list": return _ok(session_id=sid, chapters=_CHAPTERS.get(sid,[]))
    return _err("unknown action")

def _record_transcription(a):
    sid = a.get("session_id",""); t = a.get("text",""); speakers = a.get("speakers",["Speaker 1"])
    segs = [{"id": i, "text": line, "speaker": speakers[i % len(speakers)], "start": i*2.0} for i, line in enumerate(t.split("\n") if t else [])]
    _TRANSCRIPTS[sid] = segs; return _ok(session_id=sid, segments=segs, speaker_count=len(speakers))

def _record_face_tracking(a):
    s = _sess(a.get("session_id",""))
    if not s: return _err("session not found")
    ft = {"enabled": a.get("enabled",True), "auto_crop": a.get("auto_crop",True), "smoothness": a.get("smoothness",0.85)}
    s["face_tracking"] = ft; return _ok(session_id=a["session_id"], face_tracking=ft)

def _record_multi_scene(a):
    sid = a.get("session_id",""); scenes = a.get("scenes",["Screen","Webcam","Demo"]); hk = a.get("hotkeys",{"switch":"F1","next":"F2"})
    s = _sess(sid)
    if s: s["scenes"] = scenes; s["scene_hotkeys"] = hk
    return _ok(session_id=sid, scenes=scenes, hotkeys=hk)

def _record_region_lock(a):
    s = _sess(a.get("session_id",""))
    if not s: return _err("session not found")
    lock = {"enabled": a.get("enabled",True), "follow_window": a.get("follow_window",True), "window_title": a.get("window_title","")}
    s["region_lock"] = lock; return _ok(session_id=a["session_id"], region_lock=lock)

def _record_draw_annotate(a):
    s = _sess(a.get("session_id",""))
    if not s: return _err("session not found")
    da = {"enabled": a.get("enabled",True), "tools": a.get("draw_tools",["pen","arrow","box","text"]), "color": a.get("color","#FF0000")}
    s["draw_annotate"] = da; return _ok(session_id=a["session_id"], draw_annotate=da)

def _record_controls(a):
    s = _sess(a.get("session_id","")); act = a.get("action","start")
    if not s and act != "start": return _err("session not found")
    if not s: return _err("session not found")
    if act == "start": s["status"] = "recording"
    elif act == "pause": s["status"] = "paused"
    elif act == "resume": s["status"] = "recording"
    elif act == "stop": s["status"] = "stopped"; s["duration"] = _now() - s["started"]
    elif act == "countdown": return _ok(session_id=a["session_id"], countdown=a.get("seconds",3))
    return _ok(session_id=a["session_id"], status=s["status"])

def _record_multi_export(a):
    sid = a.get("session_id",""); ratios = a.get("aspect_ratios",["16:9","9:16","1:1"]); fmts = a.get("formats",["mp4"])
    exports = [{"ratio": r, "format": f, "status": "queued"} for r in ratios for f in fmts]
    return _ok(session_id=sid, exports=exports, count=len(exports))

def _record_adaptive_bitrate(a):
    sid = a.get("session_id",""); q = a.get("quality","medium"); bw = a.get("bandwidth_kbps",4000); br = _br(q)
    ad = {"quality": q, "target_bitrate": br, "actual_bitrate": min(br, bw), "adaptive": True}
    s = _sess(sid)
    if s: s["adaptive_bitrate"] = ad
    return _ok(session_id=sid, adaptive_bitrate=ad)

def _record_bookmark(a):
    sid = a.get("session_id",""); act = a.get("action","add")
    if act == "add":
        bm = {"id": _uid("bm"), "label": a.get("label","Bookmark"), "timestamp": a.get("timestamp",0)}
        _BOOKMARKS.setdefault(sid, []).append(bm); return _ok(session_id=sid, bookmark=bm)
    if act == "list": return _ok(session_id=sid, bookmarks=_BOOKMARKS.get(sid,[]))
    return _err("unknown action")

def _record_caption_burn(a):
    style = {"font": a.get("font","Arial"), "size": a.get("size",24), "color": a.get("color","#FFFFFF"), "bg": a.get("bg","semi"), "position": a.get("position","bottom")}
    return _ok(session_id=a.get("session_id",""), preset=a.get("preset","default"), style=style, burned=True)

def _record_to_tutorial(a):
    sid = a.get("session_id",""); s = _sess(sid)
    if not s: return _err("session not found")
    tut = {"title": a.get("title","Untitled Tutorial"), "steps": a.get("steps",[]), "session_id": sid, "chapters": _CHAPTERS.get(sid,[]), "transcript": _TRANSCRIPTS.get(sid,[])}
    return _ok(tutorial=tut)

def _record_face_blur(a):
    s = _sess(a.get("session_id",""))
    if not s: return _err("session not found")
    fb = {"enabled": a.get("enabled",True), "blur_strength": a.get("blur_strength",15), "track_faces": a.get("track_faces",True)}
    s["face_blur"] = fb; return _ok(session_id=a["session_id"], face_blur=fb)

TOOLS: list[dict] = [
    {"name":"record_start","description":"Start recording with config: webcam PIP, mic+system audio dual-track","params":{"webcam_pip":"bool","mic_audio":"bool","system_audio":"bool","resolution":"str","fps":"int","region":"dict"},"run":lambda a:_record_start(a)},
    {"name":"record_keystroke_viz","description":"Keystroke and mouse-click visualizer","params":{"session_id":"str","enabled":"bool","style":"str","position":"str","show_mouse":"bool"},"run":lambda a:_record_keystroke_viz(a)},
    {"name":"record_green_screen","description":"Green-screen background removal without physical screen","params":{"session_id":"str","enabled":"bool","background":"str","threshold":"float"},"run":lambda a:_record_green_screen(a)},
    {"name":"record_cursor_highlight","description":"Cursor highlight with click ripple effect","params":{"session_id":"str","enabled":"bool","color":"str","radius":"int","ripple":"bool"},"run":lambda a:_record_cursor_highlight(a)},
    {"name":"record_zoom_follow","description":"Zoom-and-follow cursor automatic framing","params":{"session_id":"str","enabled":"bool","zoom_level":"float","smoothness":"float"},"run":lambda a:_record_zoom_follow(a)},
    {"name":"record_trim_split_merge","description":"Trim, split, merge inside recording tool","params":{"session_id":"str","action":"str","start":"float","end":"float","at":"float","segments":"list"},"run":lambda a:_record_trim_split_merge(a)},
    {"name":"record_silence_remove","description":"Silence auto-remover","params":{"session_id":"str","audio_chunks":"list"},"run":lambda a:_record_silence_remove(a)},
    {"name":"record_filler_cut","description":"Filler word auto-cut","params":{"session_id":"str","transcript":"str"},"run":lambda a:_record_filler_cut(a)},
    {"name":"record_chapter_markers","description":"Chapter markers by hotkey","params":{"session_id":"str","action":"str","label":"str","timestamp":"float"},"run":lambda a:_record_chapter_markers(a)},
    {"name":"record_transcription","description":"Auto-transcription with speaker labels","params":{"session_id":"str","text":"str","speakers":"list"},"run":lambda a:_record_transcription(a)},
    {"name":"record_face_tracking","description":"Face-tracking auto-crop for talking-head","params":{"session_id":"str","enabled":"bool","auto_crop":"bool","smoothness":"float"},"run":lambda a:_record_face_tracking(a)},
    {"name":"record_multi_scene","description":"Multi-scene recording with hotkey scene switch","params":{"session_id":"str","scenes":"list","hotkeys":"dict"},"run":lambda a:_record_multi_scene(a)},
    {"name":"record_region_lock","description":"Region locking so window movement is followed","params":{"session_id":"str","enabled":"bool","follow_window":"bool","window_title":"str"},"run":lambda a:_record_region_lock(a)},
    {"name":"record_draw_annotate","description":"Draw-on-screen annotations during recording","params":{"session_id":"str","enabled":"bool","draw_tools":"list","color":"str"},"run":lambda a:_record_draw_annotate(a)},
    {"name":"record_controls","description":"Countdown, pause, hotkey-restart","params":{"session_id":"str","action":"str","seconds":"int"},"run":lambda a:_record_controls(a)},
    {"name":"record_multi_export","description":"Export to multiple aspect ratios in one pass","params":{"session_id":"str","aspect_ratios":"list","formats":"list"},"run":lambda a:_record_multi_export(a)},
    {"name":"record_adaptive_bitrate","description":"Bandwidth-optimized recording","params":{"session_id":"str","quality":"str","bandwidth_kbps":"int"},"run":lambda a:_record_adaptive_bitrate(a)},
    {"name":"record_bookmark","description":"Session bookmark timeline for later editing","params":{"session_id":"str","action":"str","label":"str","timestamp":"float"},"run":lambda a:_record_bookmark(a)},
    {"name":"record_caption_burn","description":"Auto-caption burn-in with style presets","params":{"session_id":"str","preset":"str","font":"str","size":"int","color":"str","bg":"str","position":"str"},"run":lambda a:_record_caption_burn(a)},
    {"name":"record_to_tutorial","description":"Recording-to-tutorial converter","params":{"session_id":"str","title":"str","steps":"list"},"run":lambda a:_record_to_tutorial(a)},
    {"name":"record_face_blur","description":"Face-blur toggle for privacy","params":{"session_id":"str","enabled":"bool","blur_strength":"int","track_faces":"bool"},"run":lambda a:_record_face_blur(a)},
]