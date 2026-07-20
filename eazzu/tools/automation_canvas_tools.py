"""Visual node-based automation canvas tools.

Pure-Python toolkit for building, connecting, scheduling, and managing
node-based automation workflows. Each tool returns a dict with a ``status``
key (``"ok"`` or ``"error"``) plus tool-specific payload data.
"""
from __future__ import annotations
import json, re, time, uuid
from typing import Any

_CANVASES: dict[str, dict] = {}
_TEMPLATES: dict[str, dict] = {}
_VAULT: dict[str, dict] = {}
_HISTORY: list[dict] = []
_BUS: dict[str, list[dict]] = {}
_MARKET: dict[str, dict] = {}
_IDEM: dict[str, dict] = {}
_QUEUES: dict[str, list[dict]] = {}
_APPROVALS: dict[str, dict] = {}
_VERSIONS: dict[str, list[dict]] = {}

def _now() -> float: return time.time()
def _uid(p="id") -> str: return f"{p}_{uuid.uuid4().hex[:12]}"
def _ok(**kw): return {"status": "ok", **kw}
def _err(m, **kw): return {"status": "error", "error": m, **kw}
def _cam(c): return _CANVASES.get(c)
def _node(cid, nid):
    c = _cam(cid); return next((n for n in c["nodes"] if n["id"] == nid), None) if c else None
def _ntype(t): return t in {"trigger", "action", "condition", "transform"}
def _cron(e):
    m = re.match(r"every\s+(\d+)\s*(second|minute|hour|day)s?", e.strip())
    if m: return {"interval": int(m[1]), "unit": m[2]}
    p = e.split(); return dict(zip(["minute","hour","day_of_month","month","day_of_week"], p)) if len(p)==5 else {"raw": e}
def _diff(v1, v2):
    n1, n2 = {n["id"]: n for n in v1.get("nodes", [])}, {n["id"]: n for n in v2.get("nodes", [])}
    return {"added": [n for n in n2 if n not in n1], "removed": [n for n in n1 if n not in n2], "changed": [n for n in n1 if n in n2 and n1[n] != n2[n]]}
def _cost(nc, ec, runs=1): return round((nc*0.001 + ec*0.0005)*runs, 4)

def _canvas_create(a):
    cid = _uid("canvas"); c = {"id": cid, "name": a.get("name","Untitled"), "nodes": a.get("nodes",[]), "edges": [], "created": _now(), "version": 1}
    _CANVASES[cid] = c; _VERSIONS.setdefault(cid, []).append({"version": 1, "snapshot": json.loads(json.dumps(c))})
    return _ok(canvas_id=cid, name=c["name"], node_count=len(c["nodes"]))

def _canvas_add_node(a):
    c = _cam(a.get("canvas_id",""))
    if not c: return _err("canvas not found")
    nt = a.get("type","action")
    if not _ntype(nt): return _err(f"invalid node type: {nt}")
    n = {"id": a.get("node_id", _uid("node")), "type": nt, "label": a.get("label", nt), "config": a.get("config",{}), "position": a.get("position",{"x":0,"y":0})}
    c["nodes"].append(n); c["version"] += 1; return _ok(node_id=n["id"], version=c["version"])

def _canvas_connect_nodes(a):
    c = _cam(a.get("canvas_id",""))
    if not c: return _err("canvas not found")
    s, d = a.get("source",""), a.get("target","")
    if not _node(a["canvas_id"], s) or not _node(a["canvas_id"], d): return _err("source or target node missing")
    e = {"id": _uid("edge"), "source": s, "target": d, "label": a.get("label","")}; c["edges"].append(e); return _ok(edge_id=e["id"])

def _canvas_conditional_branch(a):
    c = _cam(a.get("canvas_id",""))
    if not c: return _err("canvas not found")
    bt = a.get("branch_type","if")
    n = {"id": _uid("branch"), "type": "condition", "label": a.get("label", bt), "config": {"branch_type": bt, "condition": a.get("condition",""), "cases": a.get("cases",[]), "loop": a.get("loop",{})}, "preview": f"[{bt}] {a.get('condition','')}"}
    c["nodes"].append(n); return _ok(node_id=n["id"], preview=n["preview"])

def _canvas_data_merge(a):
    merged: dict[str, Any] = {}
    for s in a.get("sources", []): merged.update(s if isinstance(s, dict) else {})
    for tgt, src in a.get("schema_mapping", {}).items():
        val: Any = merged
        for p in src.split("."): val = val.get(p, {}) if isinstance(val, dict) else None
        merged[tgt] = val
    return _ok(merged=merged, source_count=len(a.get("sources",[])))


def _canvas_webhook_listener(a):
    cid = a.get("canvas_id",""); path = a.get("path", f"/hook/{cid}")
    l = {"id": _uid("hook"), "path": path, "method": a.get("method","POST"), "log": [], "replay_buffer": []}
    c = _cam(cid)
    if c: c.setdefault("webhooks", []).append(l)
    return _ok(webhook_id=l["id"], path=path)

def _canvas_scheduler(a):
    cid = a.get("canvas_id",""); sch = a.get("schedule","every 5 minutes"); parsed = _cron(sch)
    s = {"id": _uid("sched"), "schedule": sch, "parsed": parsed, "timezone": a.get("timezone","UTC"), "enabled": a.get("enabled", True)}
    c = _cam(cid)
    if c: c.setdefault("schedulers", []).append(s)
    return _ok(scheduler_id=s["id"], parsed=parsed)

def _canvas_error_handler(a):
    cid = a.get("canvas_id","")
    h = {"id": _uid("eh"), "retry": a.get("retry",{"max":3,"backoff":"exponential"}), "fallback": a.get("fallback",{}), "escalation": a.get("escalation",{"notify":[]})}
    c = _cam(cid)
    if c: c.setdefault("error_handlers", []).append(h)
    return _ok(handler_id=h["id"])

def _canvas_sub_workflow(a):
    cid = a.get("canvas_id",""); sid = a.get("sub_workflow_id", _uid("sub"))
    s = {"id": sid, "name": a.get("name","SubWorkflow"), "inputs": a.get("inputs",[]), "outputs": a.get("outputs",[]), "reusable": a.get("reusable", True)}
    c = _cam(cid)
    if c: c.setdefault("sub_workflows", []).append(s)
    return _ok(sub_workflow_id=sid)

def _canvas_env_manager(a):
    act, key = a.get("action","set"), a.get("key","")
    if act == "set": _VAULT[key] = {"value": a.get("value",""), "secret": a.get("secret", False), "created": _now()}; return _ok(key=key, stored=True)
    if act == "get":
        e = _VAULT.get(key)
        return _ok(key=key, value=e["value"] if e and not e["secret"] else "***") if e else _err("key not found")
    if act == "list": return _ok(keys=list(_VAULT.keys()))
    return _err("unknown action")

def _canvas_version_control(a):
    c = _cam(a.get("canvas_id",""))
    if not c: return _err("canvas not found")
    act = a.get("action","snapshot")
    if act == "snapshot":
        _VERSIONS.setdefault(c["id"], []).append({"version": c["version"], "snapshot": json.loads(json.dumps(c))})
        return _ok(version=c["version"])
    if act == "rollback":
        snap = next((s for s in _VERSIONS.get(c["id"],[]) if s["version"]==a.get("target_version")), None)
        if not snap: return _err("version not found")
        _CANVASES[c["id"]] = json.loads(json.dumps(snap["snapshot"])); return _ok(rolled_back_to=a["target_version"])
    if act == "diff":
        h = _VERSIONS.get(c["id"], [])
        s1 = next((s for s in h if s["version"]==a.get("from_version")), None)
        s2 = next((s for s in h if s["version"]==a.get("to_version", c["version"])), None)
        if not s1 or not s2: return _err("version not found")
        return _ok(diff=_diff(s1["snapshot"], s2["snapshot"]))
    return _err("unknown action")

def _canvas_approval_step(a):
    aid = _uid("approval")
    _APPROVALS[aid] = {"id": aid, "canvas_id": a.get("canvas_id",""), "approver": a.get("approver",""), "status": "pending", "timeout": a.get("timeout",3600), "created": _now()}
    return _ok(approval_id=aid, status="pending")

def _canvas_rate_limiter(a):
    cid = a.get("canvas_id","")
    rl = {"id": _uid("rl"), "max_requests": a.get("max_requests",100), "window": a.get("window",60), "strategy": a.get("strategy","token_bucket")}
    c = _cam(cid)
    if c: c.setdefault("rate_limiters", []).append(rl)
    return _ok(rate_limiter_id=rl["id"])

def _canvas_queue(a):
    qid = a.get("queue_id", _uid("queue")); act = a.get("action","enqueue")
    _QUEUES.setdefault(qid, [])
    if act == "enqueue":
        item = {"id": _uid("msg"), "payload": a.get("payload",{}), "priority": a.get("priority",5), "attempts": 0}
        _QUEUES[qid].append(item); _QUEUES[qid].sort(key=lambda m: m["priority"], reverse=True)
        return _ok(queue_id=qid, message_id=item["id"])
    if act == "dequeue":
        return _ok(queue_id=qid, message=_QUEUES[qid].pop(0) if _QUEUES[qid] else None)
    if act == "dead_letter":
        dlq = f"{qid}_dlq"; _QUEUES.setdefault(dlq, []).append(a.get("message",{})); return _ok(dead_letter_queue=dlq)
    return _err("unknown action")

def _canvas_batch_process(a):
    items = a.get("items",[]); par = a.get("parallel",4)
    return _ok(batch_id=_uid("batch"), total=len(items), parallel=par)

def _canvas_event_bus(a):
    act, topic = a.get("action","publish"), a.get("topic","")
    if act == "publish": _BUS.setdefault(topic, []).append({"message": a.get("message",{}), "ts": _now()}); return _ok(topic=topic, published=True)
    if act == "subscribe": _BUS.setdefault(topic, []); return _ok(topic=topic, subscribed=True)
    if act == "poll": return _ok(topic=topic, messages=_BUS.get(topic, [])[-a.get("limit",10):])
    return _err("unknown action")

def _canvas_marketplace(a):
    act = a.get("action","publish")
    if act == "publish":
        tid = _uid("tmpl"); _MARKET[tid] = {"id": tid, "name": a.get("name","Template"), "description": a.get("description",""), "category": a.get("category","general"), "canvas": a.get("canvas",{}), "downloads": 0}
        return _ok(template_id=tid)
    if act == "search":
        cat = a.get("category",""); return _ok(templates=[t for t in _MARKET.values() if not cat or t["category"]==cat])
    if act == "install":
        t = _MARKET.get(a.get("template_id",""))
        if not t: return _err("template not found")
        t["downloads"] += 1; return _ok(template=t)
    return _err("unknown action")

def _canvas_ai_suggest(a):
    desc = a.get("description","").lower()
    kw = {"trigger": ["when","on","every","schedule"], "condition": ["if","else","switch","case"], "transform": ["map","convert","format","transform"], "action": ["send","create","update","delete","post"]}
    sugg = [{"type": nt, "label": a.get("description","")[:40]} for nt, ws in kw.items() if any(w in desc for w in ws)]
    return _ok(suggestions=sugg or [{"type":"action","label":"generic action"}])

def _canvas_data_transform(a):
    data, fmt = a.get("data",{}), a.get("format","json")
    if fmt == "json": return _ok(output=json.dumps(data), format="json")
    if fmt == "xml":
        def _xml(d, r="root"): return "".join(f"<{k}>{_xml(v,k)}</{k}>" for k,v in d.items()) if isinstance(d,dict) else str(d)
        return _ok(output=_xml(data), format="xml")
    if fmt == "csv":
        if not isinstance(data, list) or not data: return _ok(output="", format="csv")
        cols = list(data[0].keys()); lines = [",".join(cols)] + [",".join(str(r.get(c,"")) for c in cols) for r in data]
        return _ok(output="\n".join(lines), format="csv")
    return _err("unsupported format")

def _canvas_idempotency(a):
    act, key = a.get("action","check"), a.get("key","")
    if act == "check":
        e = _IDEM.get(key); return _ok(key=key, duplicate=True, result=e.get("result")) if e else _ok(key=key, duplicate=False)
    if act == "store": _IDEM[key] = {"result": a.get("result"), "ts": _now()}; return _ok(key=key, stored=True)
    return _err("unknown action")

def _canvas_execution_history(a):
    act = a.get("action","log")
    if act == "log":
        e = {"id": _uid("exec"), "canvas_id": a.get("canvas_id",""), "status": a.get("status","completed"), "duration": a.get("duration",0), "ts": _now()}
        _HISTORY.append(e); return _ok(exec_id=e["id"])
    if act == "search":
        st, cid = a.get("filter_status"), a.get("filter_canvas")
        return _ok(results=[e for e in _HISTORY if (not st or e["status"]==st) and (not cid or e["canvas_id"]==cid)])
    return _err("unknown action")

def _canvas_cost_estimator(a):
    c = _cam(a.get("canvas_id",""))
    if not c: return _err("canvas not found")
    runs = a.get("runs",1); return _ok(estimated_cost=_cost(len(c["nodes"]), len(c["edges"]), runs), runs=runs)

def _canvas_to_api(a):
    c = _cam(a.get("canvas_id",""))
    if not c: return _err("canvas not found")
    return _ok(api={"endpoint": a.get("endpoint", f"/api/run/{c['id']}"), "method": a.get("method","POST"), "canvas_id": c["id"], "auth": a.get("auth","api_key")})

TOOLS: list[dict] = [
    {"name":"canvas_create","description":"Create an automation canvas with nodes","params":{"name":"str","nodes":"list"},"run":lambda a:_canvas_create(a)},
    {"name":"canvas_add_node","description":"Add a trigger/action/condition/transform node","params":{"canvas_id":"str","type":"str","label":"str","config":"dict","position":"dict"},"run":lambda a:_canvas_add_node(a)},
    {"name":"canvas_connect_nodes","description":"Connect nodes with edges","params":{"canvas_id":"str","source":"str","target":"str","label":"str"},"run":lambda a:_canvas_connect_nodes(a)},
    {"name":"canvas_conditional_branch","description":"If/else, switch, loops with visual preview","params":{"canvas_id":"str","branch_type":"str","condition":"str","cases":"list","loop":"dict"},"run":lambda a:_canvas_conditional_branch(a)},
    {"name":"canvas_data_merge","description":"Multi-source data merging with schema mapping","params":{"sources":"list","schema_mapping":"dict"},"run":lambda a:_canvas_data_merge(a)},
    {"name":"canvas_webhook_listener","description":"Webhook listener with request logging and replay","params":{"canvas_id":"str","path":"str","method":"str"},"run":lambda a:_canvas_webhook_listener(a)},
    {"name":"canvas_scheduler","description":"Cron-like syntax + natural language scheduling","params":{"canvas_id":"str","schedule":"str","timezone":"str","enabled":"bool"},"run":lambda a:_canvas_scheduler(a)},
    {"name":"canvas_error_handler","description":"Retry, fallback, escalation paths","params":{"canvas_id":"str","retry":"dict","fallback":"dict","escalation":"dict"},"run":lambda a:_canvas_error_handler(a)},
    {"name":"canvas_sub_workflow","description":"Embed reusable logic blocks","params":{"canvas_id":"str","name":"str","inputs":"list","outputs":"list","reusable":"bool"},"run":lambda a:_canvas_sub_workflow(a)},
    {"name":"canvas_env_manager","description":"Environment variables with secrets vault","params":{"action":"str","key":"str","value":"str","secret":"bool"},"run":lambda a:_canvas_env_manager(a)},
    {"name":"canvas_version_control","description":"Version control with rollback and diff","params":{"canvas_id":"str","action":"str","target_version":"int","from_version":"int","to_version":"int"},"run":lambda a:_canvas_version_control(a)},
    {"name":"canvas_approval_step","description":"Human-in-the-loop approval mid-workflow","params":{"canvas_id":"str","approver":"str","timeout":"int"},"run":lambda a:_canvas_approval_step(a)},
    {"name":"canvas_rate_limiter","description":"Rate limiter and throttling node","params":{"canvas_id":"str","max_requests":"int","window":"int","strategy":"str"},"run":lambda a:_canvas_rate_limiter(a)},
    {"name":"canvas_queue","description":"Queue with priority levels and dead-letter handling","params":{"queue_id":"str","action":"str","payload":"dict","priority":"int","message":"dict"},"run":lambda a:_canvas_queue(a)},
    {"name":"canvas_batch_process","description":"Batch processing with parallel execution","params":{"canvas_id":"str","items":"list","parallel":"int"},"run":lambda a:_canvas_batch_process(a)},
    {"name":"canvas_event_bus","description":"Cross-workflow pub/sub","params":{"action":"str","topic":"str","message":"dict","limit":"int"},"run":lambda a:_canvas_event_bus(a)},
    {"name":"canvas_marketplace","description":"Workflow template marketplace","params":{"action":"str","name":"str","description":"str","category":"str","canvas":"dict","template_id":"str"},"run":lambda a:_canvas_marketplace(a)},
    {"name":"canvas_ai_suggest","description":"AI-assisted node suggestion","params":{"description":"str"},"run":lambda a:_canvas_ai_suggest(a)},
    {"name":"canvas_data_transform","description":"Visual JSON/XML/CSV mapping","params":{"data":"dict","format":"str"},"run":lambda a:_canvas_data_transform(a)},
    {"name":"canvas_idempotency","description":"Idempotency key manager","params":{"action":"str","key":"str","result":"dict"},"run":lambda a:_canvas_idempotency(a)},
    {"name":"canvas_execution_history","description":"Searchable logs and filters","params":{"action":"str","canvas_id":"str","status":"str","duration":"int","filter_status":"str","filter_canvas":"str"},"run":lambda a:_canvas_execution_history(a)},
    {"name":"canvas_cost_estimator","description":"Cost estimator per workflow run","params":{"canvas_id":"str","runs":"int"},"run":lambda a:_canvas_cost_estimator(a)},
    {"name":"canvas_to_api","description":"Turn any flow into a callable API endpoint","params":{"canvas_id":"str","endpoint":"str","method":"str","auth":"str"},"run":lambda a:_canvas_to_api(a)},
]