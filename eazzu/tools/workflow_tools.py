"""Workflow automation & RPA tools.

Declarative workflow engine: triggers, steps, conditions, approvals,
loops, and retries. Runs entirely in Python — no external runtime needed.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_STORE_PATH = Path.home() / ".eazzu" / "workflows.json"
_TRIGGERS = {"manual", "schedule", "event", "webhook", "button", "record_change"}


def _load():
    if _STORE_PATH.exists():
        try:
            return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"flows": {}, "runs": []}
    return {"flows": {}, "runs": []}


def _save(store):
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def _create_flow(name, trigger, steps):
    store = _load()
    flow = {"name": name, "trigger": trigger if trigger in _TRIGGERS else "manual", "steps": steps, "created": time.strftime("%Y-%m-%dT%H:%M:%S")}
    store["flows"][name] = flow
    _save(store)
    return flow


def _eval_condition(condition, context):
    if not condition:
        return True
    try:
        return bool(eval(condition, {"__builtins__": {}}, context))
    except Exception:
        return False


def _run_step(step, context):
    stype = step.get("type", "action")
    if stype == "condition":
        met = _eval_condition(step.get("if", ""), context)
        return {"step": step.get("name"), "branch": "true" if met else "false", "result": "condition met" if met else "condition not met"}
    if stype == "approval":
        approver = step.get("approver", "auto")
        return {"step": step.get("name"), "type": "approval", "approver": approver, "approved": approver == "auto"}
    if stype == "delay":
        secs = int(step.get("seconds", 0))
        if secs:
            time.sleep(min(secs, 5))
        return {"step": step.get("name"), "type": "delay", "seconds": secs}
    if stype == "loop":
        items = step.get("items", [])
        results = []
        for item in items:
            ctx = {**context, "item": item}
            for sub in step.get("steps", []):
                results.append(_run_step(sub, ctx))
        return {"step": step.get("name"), "type": "loop", "iterations": len(items), "results": results}
    if stype == "set":
        var = step.get("var", "")
        context[var] = step.get("value")
        return {"step": step.get("name"), "type": "set", "var": var, "value": step.get("value")}
    return {"step": step.get("name"), "type": "action", "action": step.get("action", ""), "params": step.get("params", {})}


def _run_flow(name, context=None, max_steps=100):
    store = _load()
    flow = store.get("flows", {}).get(name)
    if not flow:
        return {"error": "flow not found"}
    ctx = context or {}
    results = []
    for step in flow.get("steps", [])[:max_steps]:
        attempt, max_retry = 0, int(step.get("retries", 0))
        while True:
            try:
                res = _run_step(step, ctx)
                results.append(res)
                break
            except Exception as e:
                attempt += 1
                if attempt > max_retry:
                    results.append({"step": step.get("name"), "error": str(e), "failed": True})
                    break
                time.sleep(0.1 * attempt)
    run = {"flow": name, "started": time.strftime("%Y-%m-%dT%H:%M:%S"), "steps": results, "context": ctx}
    store["runs"].append(run)
    _save(store)
    return run


def _list_flows():
    store = _load()
    return {"flows": {n: {"trigger": f["trigger"], "steps": len(f["steps"])} for n, f in store["flows"].items()}}


def _run_history(limit=20):
    store = _load()
    return {"runs": store.get("runs", [])[-limit:]}


def _approval_flow(name, step_name, approved, comments=""):
    store = _load()
    flow = store.get("flows", {}).get(name, {})
    for step in flow.get("steps", []):
        if step.get("name") == step_name:
            step["pending_approval"] = False
            step["approved"] = approved
            step["comments"] = comments
            _save(store)
            return {"step": step_name, "approved": approved}
    return {"error": "step not found"}


TOOLS: list[dict] = [
    {
        "name": "workflow_create",
        "description": "Create a workflow flow with a trigger (manual, schedule, event, webhook, button, record_change) and ordered steps.",
        "params": {"name": "string", "trigger": "string", "steps": "list"},
        "run": lambda a: _create_flow(a.get("name", ""), a.get("trigger", "manual"), a.get("steps", [])),
    },
    {
        "name": "workflow_run",
        "description": "Execute a workflow by name with an optional context dict. Steps can be action, condition (if), approval, delay, loop (items+steps), or set (var+value).",
        "params": {"name": "string", "context": "object", "max_steps": "int"},
        "run": lambda a: _run_flow(a.get("name", ""), a.get("context", {}), int(a.get("max_steps", 100))),
    },
    {
        "name": "workflow_list",
        "description": "List all saved workflows with their triggers and step counts.",
        "params": {},
        "run": lambda a: _list_flows(),
    },
    {
        "name": "workflow_history",
        "description": "Get recent workflow run history (last N runs).",
        "params": {"limit": "int"},
        "run": lambda a: _run_history(int(a.get("limit", 20))),
    },
    {
        "name": "workflow_approve",
        "description": "Approve or reject a pending approval step in a workflow.",
        "params": {"name": "string", "step_name": "string", "approved": "bool", "comments": "string"},
        "run": lambda a: _approval_flow(a.get("name", ""), a.get("step_name", ""), bool(a.get("approved", False)), a.get("comments", "")),
    },
]
