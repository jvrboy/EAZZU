"""Task, to-do & lightweight planning tools.

Personal task lists with due dates, reminders, recurring tasks, subtasks,
priorities, and shared team plans. Persists to a JSON store on disk.
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_STORE_PATH = Path.home() / ".eazzu" / "tasks.json"
_PRIORITY = {"low": 1, "medium": 2, "high": 3, "critical": 4}
_RECURRENCE = {"none", "daily", "weekly", "monthly", "yearly"}


def _load() -> dict:
    if _STORE_PATH.exists():
        try:
            return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"lists": {}, "plans": {}}
    return {"lists": {}, "plans": {}}


def _save(store):
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _today():
    return time.strftime("%Y-%m-%d")


def _add_task(list_name, title, due="", priority="medium", recurrence="none", notes="", subtasks=None):
    store = _load()
    lst = store["lists"].setdefault(list_name, {"tasks": []})
    task = {
        "id": f"t{len(lst['tasks']) + 1}", "title": title, "due": due,
        "priority": priority, "recurrence": recurrence if recurrence in _RECURRENCE else "none",
        "notes": notes, "subtasks": [{"id": f"{len(lst['tasks'])+1}.{i+1}", "title": s, "done": False} for i, s in enumerate(subtasks or [])],
        "done": False, "created": _now(), "completed": None,
    }
    lst["tasks"].append(task)
    _save(store)
    return task


def _recurring_next(task):
    offsets = {"daily": 86400, "weekly": 7 * 86400, "monthly": 30 * 86400, "yearly": 365 * 86400}
    if task["recurrence"] in offsets:
        task["due"] = time.strftime("%Y-%m-%d", time.localtime(time.time() + offsets[task["recurrence"]]))
    task["done"] = False
    task["completed"] = None


def _complete_task(list_name, task_id):
    store = _load()
    for t in store["lists"].get(list_name, {}).get("tasks", []):
        if t["id"] == task_id:
            t["done"] = True
            t["completed"] = _now()
            if t["recurrence"] != "none":
                _recurring_next(t)
            _save(store)
            return {"completed": True, "task": t}
    return {"completed": False, "error": "task not found"}


def _my_day():
    store = _load()
    today = _today()
    tasks = []
    for lst_name, lst in store["lists"].items():
        for t in lst["tasks"]:
            if not t["done"] and (t["due"] == today or t["priority"] in ("high", "critical")):
                tasks.append({"list": lst_name, **t})
    tasks.sort(key=lambda t: _PRIORITY.get(t["priority"], 2), reverse=True)
    return {"date": today, "tasks": tasks}


def _list_tasks(list_name="", status=""):
    store = _load()
    out = {}
    lists = [list_name] if list_name else list(store["lists"].keys())
    for name in lists:
        tasks = store["lists"].get(name, {}).get("tasks", [])
        if status == "open":
            tasks = [t for t in tasks if not t["done"]]
        elif status == "done":
            tasks = [t for t in tasks if t["done"]]
        out[name] = tasks
    return out


def _add_subtask(list_name, task_id, title):
    store = _load()
    for t in store["lists"].get(list_name, {}).get("tasks", []):
        if t["id"] == task_id:
            sub = {"id": f"{task_id}.{len(t['subtasks'])+1}", "title": title, "done": False}
            t["subtasks"].append(sub)
            _save(store)
            return {"subtask": sub}
    return {"error": "task not found"}


def _complete_subtask(list_name, task_id, subtask_id):
    store = _load()
    for t in store["lists"].get(list_name, {}).get("tasks", []):
        if t["id"] == task_id:
            for s in t["subtasks"]:
                if s["id"] == subtask_id:
                    s["done"] = True
                    _save(store)
                    return {"subtask": s}
    return {"error": "subtask not found"}


def _create_plan(name, buckets=None):
    store = _load()
    plan = {"buckets": {b: [] for b in (buckets or ["To Do", "Doing", "Done"])}, "created": _now()}
    store["plans"][name] = plan
    _save(store)
    return {"plan": name, "buckets": list(plan["buckets"].keys())}


def _add_plan_task(plan, bucket, title, priority="medium", assignee=""):
    store = _load()
    p = store["plans"].setdefault(plan, {"buckets": {"To Do": [], "Doing": [], "Done": []}, "created": _now()})
    b = p["buckets"].setdefault(bucket, [])
    task = {"id": f"{plan}-{len(b)+1}", "title": title, "priority": priority, "assignee": assignee, "done": bucket == "Done"}
    b.append(task)
    _save(store)
    return task


def _move_plan_task(plan, task_id, to_bucket):
    store = _load()
    p = store.get("plans", {}).get(plan, {})
    found = None
    for bucket, tasks in p.get("buckets", {}).items():
        for t in tasks:
            if t["id"] == task_id:
                found = t
                tasks.remove(t)
                break
        if found:
            break
    if found:
        p["buckets"].setdefault(to_bucket, []).append(found)
        found["done"] = to_bucket.lower() == "done"
        _save(store)
        return {"moved": True, "task": found, "bucket": to_bucket}
    return {"moved": False, "error": "task not found"}


TOOLS: list[dict] = [
    {
        "name": "task_add",
        "description": "Add a task to a list with due date, priority (low/medium/high/critical), recurrence (none/daily/weekly/monthly/yearly), notes, and subtasks.",
        "params": {"list": "string", "title": "string", "due": "string", "priority": "string", "recurrence": "string", "notes": "string", "subtasks": "list"},
        "run": lambda a: _add_task(a.get("list", "My Tasks"), a.get("title", ""), a.get("due", ""), a.get("priority", "medium"), a.get("recurrence", "none"), a.get("notes", ""), a.get("subtasks", [])),
    },
    {
        "name": "task_complete",
        "description": "Mark a task as done; recurring tasks auto-roll to the next due date.",
        "params": {"list": "string", "task_id": "string"},
        "run": lambda a: _complete_task(a.get("list", ""), a.get("task_id", "")),
    },
    {
        "name": "task_my_day",
        "description": "Get a curated My Day list: tasks due today plus high/critical priority open tasks.",
        "params": {},
        "run": lambda a: _my_day(),
    },
    {
        "name": "task_list",
        "description": "List tasks in a list (or all lists), optionally filtered by status (open/done).",
        "params": {"list": "string", "status": "string"},
        "run": lambda a: _list_tasks(a.get("list", ""), a.get("status", "")),
    },
    {
        "name": "task_add_subtask",
        "description": "Add a subtask to an existing task.",
        "params": {"list": "string", "task_id": "string", "title": "string"},
        "run": lambda a: _add_subtask(a.get("list", ""), a.get("task_id", ""), a.get("title", "")),
    },
    {
        "name": "task_complete_subtask",
        "description": "Mark a subtask as done.",
        "params": {"list": "string", "task_id": "string", "subtask_id": "string"},
        "run": lambda a: _complete_subtask(a.get("list", ""), a.get("task_id", ""), a.get("subtask_id", "")),
    },
    {
        "name": "plan_create",
        "description": "Create a team plan with Kanban buckets (default: To Do, Doing, Done).",
        "params": {"name": "string", "buckets": "list"},
        "run": lambda a: _create_plan(a.get("name", ""), a.get("buckets", [])),
    },
    {
        "name": "plan_add_task",
        "description": "Add a task to a plan bucket with priority and optional assignee.",
        "params": {"plan": "string", "bucket": "string", "title": "string", "priority": "string", "assignee": "string"},
        "run": lambda a: _add_plan_task(a.get("plan", ""), a.get("bucket", "To Do"), a.get("title", ""), a.get("priority", "medium"), a.get("assignee", "")),
    },
    {
        "name": "plan_move_task",
        "description": "Move a task between buckets in a plan (Kanban board move).",
        "params": {"plan": "string", "task_id": "string", "to_bucket": "string"},
        "run": lambda a: _move_plan_task(a.get("plan", ""), a.get("task_id", ""), a.get("to_bucket", "")),
    },
]
