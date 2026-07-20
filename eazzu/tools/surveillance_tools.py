"""Camera, video surveillance & streaming tools.

Pure-Python toolkit for multi-camera dashboards, motion detection, object
filtering, face/plate recognition, storage, streaming, PTZ, alerts, and more.
Each tool returns a dict with a ``status`` key (``"ok"`` or ``"error"``).
"""
from __future__ import annotations
import time, uuid
from typing import Any

_CAMERAS: dict[str, dict] = {}
_DASHBOARDS: dict[str, dict] = {}
_EVENTS: list[dict] = []
_USERS: dict[str, dict] = {}
_ALERTS: dict[str, dict] = {}
_TIMELAPSES: dict[str, dict] = {}
_FACE_LISTS: dict[str, dict] = {}
_PLATE_LOG: list[dict] = {}
_ACCESS_ROLES: dict[str, list[str]] = {}

def _now() -> float: return time.time()
def _uid(p="id") -> str: return f"{p}_{uuid.uuid4().hex[:10]}"
def _ok(**kw): return {"status": "ok", **kw}
def _err(m, **kw): return {"status": "error", "error": m, **kw}
def _cam(cid): return _CAMERAS.get(cid)
def _ev(cam_id, etype, meta=None):
    e = {"id": _uid("ev"), "camera_id": cam_id, "type": etype, "ts": _now(), "meta": meta or {}}
    _EVENTS.append(e); return e
def _bwq(bw): return "4K" if bw>=10000 else "1080p" if bw>=5000 else "720p" if bw>=2500 else "480p" if bw>=1000 else "360p"
def _ret(rule): return {"7d":7,"30d":30,"90d":90,"1y":365,"forever":99999}.get(rule, 30)

def _surveillance_dashboard(a):
    did = _uid("dash"); cam_ids = a.get("camera_ids",[])
    _DASHBOARDS[did] = {"id": did, "name": a.get("name","Dashboard"), "cameras": cam_ids, "layout": a.get("layout","grid"), "created": _now()}
    return _ok(dashboard_id=did, camera_count=len(cam_ids))

def _surveillance_motion_zones(a):
    c = _cam(a.get("camera_id",""))
    if not c: return _err("camera not found")
    zones = a.get("zones",[])
    for z in zones: z.setdefault("sensitivity", 50)
    c["motion_zones"] = zones; return _ok(camera_id=a["camera_id"], zones=zones)

def _surveillance_object_filter(a):
    c = _cam(a.get("camera_id","")); objs = a.get("objects",["person","vehicle","animal","package"])
    if c: c["object_filter"] = objs
    return _ok(camera_id=a.get("camera_id",""), filters=objs)

def _surveillance_face_recognition(a):
    lid = _uid("face"); lt = a.get("list_type","allow")
    _FACE_LISTS[lid] = {"id": lid, "type": lt, "name": a.get("name",f"{lt}_list"), "faces": a.get("faces",[])}
    return _ok(list_id=lid, type=lt, face_count=len(a.get("faces",[])))

def _surveillance_plate_reader(a):
    cid = a.get("camera_id",""); plate = a.get("plate","")
    e = {"id": _uid("plate"), "camera_id": cid, "plate": plate, "ts": _now(), "confidence": a.get("confidence",0.95)}
    _PLATE_LOG.append(e); _ev(cid, "plate_read", {"plate": plate})
    return _ok(log_id=e["id"], plate=plate)

def _surveillance_intercom(a):
    s = {"id": _uid("ic"), "camera_id": a.get("camera_id",""), "action": a.get("action","start"), "two_way": True, "ts": _now()}
    return _ok(session_id=s["id"], action=s["action"])

def _surveillance_timeline(a):
    cid = a.get("camera_id",""); lim = a.get("limit",50)
    evs = [e for e in _EVENTS if e["camera_id"]==cid] if cid else _EVENTS
    markers = [{"id": e["id"], "ts": e["ts"], "type": e["type"]} for e in evs[-lim:]]
    return _ok(markers=markers, count=len(markers))

def _surveillance_storage(a):
    cid = a.get("camera_id","")
    pol = {"camera_id": cid, "mode": a.get("mode","hybrid"), "retention_days": _ret(a.get("retention","30d")), "cloud": a.get("cloud",True), "local": a.get("local",True)}
    c = _cam(cid)
    if c: c["storage"] = pol
    return _ok(policy=pol)

def _surveillance_streaming(a):
    cid = a.get("camera_id",""); bw = a.get("bandwidth_kbps",5000); q = _bwq(bw)
    c = _cam(cid)
    if c: c["streaming"] = {"quality": q, "bandwidth_kbps": bw}
    return _ok(camera_id=cid, quality=q, bandwidth_kbps=bw)

def _surveillance_night_vision(a):
    cid = a.get("camera_id",""); ir = a.get("ir_sensitivity",60); auto = a.get("auto_toggle",True)
    c = _cam(cid)
    if c: c["night_vision"] = {"ir_sensitivity": ir, "auto": auto}
    return _ok(camera_id=cid, ir_sensitivity=ir, auto=auto)

def _surveillance_ptz(a):
    cid = a.get("camera_id",""); presets = a.get("presets",[]); patrol = a.get("patrol_path",[])
    c = _cam(cid)
    if c: c["ptz"] = {"presets": presets, "patrol": patrol}
    return _ok(camera_id=cid, presets=len(presets), patrol_points=len(patrol))

def _surveillance_snapshot(a):
    cid = a.get("camera_id",""); burst = a.get("burst_count",3); interval = a.get("interval_ms",500)
    shots = [{"id": _uid("snap"), "index": i, "ts": _now()} for i in range(burst)]
    _ev(cid, "snapshot_burst", {"count": burst})
    return _ok(camera_id=cid, snapshots=shots, interval_ms=interval)

def _surveillance_privacy_mask(a):
    cid = a.get("camera_id",""); regions = a.get("regions",[])
    c = _cam(cid)
    if c: c["privacy_masks"] = regions
    return _ok(camera_id=cid, masked_regions=len(regions))

def _surveillance_alerts(a):
    aid = _uid("alert"); ch = a.get("channels",["push"]); qh = a.get("quiet_hours",{"start":"22:00","end":"07:00"})
    _ALERTS[aid] = {"id": aid, "channels": ch, "quiet_hours": qh, "rules": a.get("rules",[])}
    return _ok(alert_id=aid, channels=ch)

def _surveillance_timelapse(a):
    cid = a.get("camera_id",""); tid = _uid("tl")
    _TIMELAPSES[tid] = {"id": tid, "camera_id": cid, "interval": a.get("interval",60), "duration": a.get("duration",86400), "status": "processing"}
    return _ok(timelapse_id=tid, status="processing")

def _surveillance_access(a):
    uid = a.get("user_id", _uid("user")); role = a.get("role","viewer")
    _USERS[uid] = {"id": uid, "role": role, "name": a.get("name","User")}
    _ACCESS_ROLES[uid] = a.get("permissions",["view"])
    return _ok(user_id=uid, role=role)

def _surveillance_relay(a):
    cid = a.get("camera_id",""); proto = a.get("protocol","rtsp"); enc = a.get("encrypted",True)
    r = {"id": _uid("relay"), "camera_id": cid, "protocol": proto, "encrypted": enc, "url": a.get("url", f"{proto}://relay/{cid}")}
    return _ok(relay=r)

def _surveillance_ai_summary(a):
    cid = a.get("camera_id",""); evs = [e for e in _EVENTS if e["camera_id"]==cid]
    types: dict[str,int] = {}
    for e in evs: types[e["type"]] = types.get(e["type"], 0) + 1
    summary = f"Detected {len(evs)} events on camera {cid}. " + (", ".join(f"{k}: {v}" for k,v in types.items()) or "No activity.")
    return _ok(camera_id=cid, summary=summary, event_count=len(evs))

def _surveillance_anomaly(a):
    cid = a.get("camera_id",""); at = a.get("anomaly_type","loitering"); th = a.get("threshold_seconds",300)
    cfg = {"camera_id": cid, "type": at, "threshold": th, "unusual_hours": a.get("unusual_hours",{"start":"00:00","end":"06:00"})}
    c = _cam(cid)
    if c: c.setdefault("anomaly", []).append(cfg)
    return _ok(anomaly=cfg)

def _surveillance_health(a):
    c = _cam(a.get("camera_id",""))
    if not c: return _err("camera not found")
    h = {"signal": a.get("signal",85), "uptime_pct": a.get("uptime",99.5), "storage_pct": a.get("storage",42), "temperature": a.get("temp",35)}
    c["health"] = h; return _ok(camera_id=a["camera_id"], health=h)

def _surveillance_cross_track(a):
    oid = a.get("object_id", _uid("obj")); cams = a.get("camera_ids",[])
    track = {"object_id": oid, "cameras": cams, "points": [{"camera": c, "ts": _now()} for c in cams]}
    return _ok(track=track)

def _surveillance_outdoor(a):
    cid = a.get("camera_id",""); ab = a.get("auto_brightness",True); wp = a.get("weatherproof",True)
    c = _cam(cid)
    if c: c["outdoor"] = {"auto_brightness": ab, "weatherproof": wp, "ip_rating": a.get("ip_rating","IP66")}
    return _ok(camera_id=cid, outdoor_mode=True)

TOOLS: list[dict] = [
    {"name":"surveillance_dashboard","description":"Multi-camera unified dashboard with live grid view","params":{"name":"str","camera_ids":"list","layout":"str"},"run":lambda a:_surveillance_dashboard(a)},
    {"name":"surveillance_motion_zones","description":"Motion detection zones with sensitivity sliders","params":{"camera_id":"str","zones":"list"},"run":lambda a:_surveillance_motion_zones(a)},
    {"name":"surveillance_object_filter","description":"Object recognition: person/vehicle/animal/package","params":{"camera_id":"str","objects":"list"},"run":lambda a:_surveillance_object_filter(a)},
    {"name":"surveillance_face_recognition","description":"Facial recognition allow-list and deny-list","params":{"list_type":"str","name":"str","faces":"list"},"run":lambda a:_surveillance_face_recognition(a)},
    {"name":"surveillance_plate_reader","description":"License plate reader with automatic logging","params":{"camera_id":"str","plate":"str","confidence":"float"},"run":lambda a:_surveillance_plate_reader(a)},
    {"name":"surveillance_intercom","description":"Two-way audio intercom overlay","params":{"camera_id":"str","action":"str"},"run":lambda a:_surveillance_intercom(a)},
    {"name":"surveillance_timeline","description":"Timeline scrubber with event markers","params":{"camera_id":"str","limit":"int"},"run":lambda a:_surveillance_timeline(a)},
    {"name":"surveillance_storage","description":"Cloud + local hybrid storage with retention rules","params":{"camera_id":"str","mode":"str","retention":"str","cloud":"bool","local":"bool"},"run":lambda a:_surveillance_storage(a)},
    {"name":"surveillance_streaming","description":"Bandwidth-adaptive streaming quality","params":{"camera_id":"str","bandwidth_kbps":"int"},"run":lambda a:_surveillance_streaming(a)},
    {"name":"surveillance_night_vision","description":"Night vision auto-toggle with IR sensitivity","params":{"camera_id":"str","ir_sensitivity":"int","auto_toggle":"bool"},"run":lambda a:_surveillance_night_vision(a)},
    {"name":"surveillance_ptz","description":"Pan/tilt/zoom preset positions and patrol paths","params":{"camera_id":"str","presets":"list","patrol_path":"list"},"run":lambda a:_surveillance_ptz(a)},
    {"name":"surveillance_snapshot","description":"Snapshot burst mode on motion trigger","params":{"camera_id":"str","burst_count":"int","interval_ms":"int"},"run":lambda a:_surveillance_snapshot(a)},
    {"name":"surveillance_privacy_mask","description":"Privacy masking regions","params":{"camera_id":"str","regions":"list"},"run":lambda a:_surveillance_privacy_mask(a)},
    {"name":"surveillance_alerts","description":"Push/email/SMS alert routing with quiet hours","params":{"channels":"list","quiet_hours":"dict","rules":"list"},"run":lambda a:_surveillance_alerts(a)},
    {"name":"surveillance_timelapse","description":"Timelapse generator from continuous recording","params":{"camera_id":"str","interval":"int","duration":"int"},"run":lambda a:_surveillance_timelapse(a)},
    {"name":"surveillance_access","description":"Multi-user access with role-based permissions","params":{"user_id":"str","role":"str","name":"str","permissions":"list"},"run":lambda a:_surveillance_access(a)},
    {"name":"surveillance_relay","description":"Encrypted RTSP/ONVIF stream relay","params":{"camera_id":"str","protocol":"str","encrypted":"bool","url":"str"},"run":lambda a:_surveillance_relay(a)},
    {"name":"surveillance_ai_summary","description":"AI-generated event summaries","params":{"camera_id":"str"},"run":lambda a:_surveillance_ai_summary(a)},
    {"name":"surveillance_anomaly","description":"Anomaly detection: loitering, unusual hours","params":{"camera_id":"str","anomaly_type":"str","threshold_seconds":"int","unusual_hours":"dict"},"run":lambda a:_surveillance_anomaly(a)},
    {"name":"surveillance_health","description":"Camera health monitor: signal, uptime, storage","params":{"camera_id":"str","signal":"int","uptime":"float","storage":"int","temp":"int"},"run":lambda a:_surveillance_health(a)},
    {"name":"surveillance_cross_track","description":"Cross-camera object tracking","params":{"object_id":"str","camera_ids":"list"},"run":lambda a:_surveillance_cross_track(a)},
    {"name":"surveillance_outdoor","description":"Weatherproof outdoor mode with auto-brightness","params":{"camera_id":"str","auto_brightness":"bool","weatherproof":"bool","ip_rating":"str"},"run":lambda a:_surveillance_outdoor(a)},
]