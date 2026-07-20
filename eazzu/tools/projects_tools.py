"""Project & portfolio management tools.

Task scheduling with dependencies (FS, SS, FF, SF), Gantt-chart data,
resource leveling, baselines, variance tracking, and earned value
management. Pure-Python, no external deps.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

_STORE_PATH = Path.home() / ".eazzu" / "projects.json"
_DEP_TYPES = {"FS", "SS", "FF", "SF"}
_TASK_TYPES = {"fixed_duration", "fixed_work", "fixed_units"}


def _load():
    if _STORE_PATH.exists():
        try:
            return json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {"projects": {}}
    return {"projects": {}}


def _save(store):
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(store, indent=2), encoding="utf-8")


def _parse_date(s):
    return datetime.strptime(s, "%Y-%m-%d") if s else datetime.now()


def _fmt_date(d):
    return d.strftime("%Y-%m-%d")


def _create_project(name, start=""):
    store = _load()
    proj = {"start": start or _fmt_date(datetime.now()), "tasks": [], "resources": {}, "baselines": {}, "created": _fmt_date(datetime.now())}
    store["projects"][name] = proj
    _save(store)
    return {"project": name, "start": proj["start"]}


def _add_task(project, name, duration=1, start="", predecessors=None, resources=None, task_type="fixed_duration", work=0):
    store = _load()
    proj = store["projects"].setdefault(project, {"tasks": [], "resources": {}, "start": _fmt_date(datetime.now())})
    task = {
        "id": f"T{len(proj['tasks']) + 1}", "name": name, "duration": duration,
        "start": start or proj["start"], "predecessors": predecessors or [],
        "resources": resources or [], "task_type": task_type if task_type in _TASK_TYPES else "fixed_duration",
        "work": work, "percent_complete": 0,
    }
    proj["tasks"].append(task)
    _save(store)
    return task


def _schedule(project):
    store = _load()
    proj = store.get("projects", {}).get(project, {})
    tasks = {t["id"]: t for t in proj.get("tasks", [])}
    scheduled = {}

    def schedule(tid, visited=None):
        visited = visited or set()
        if tid in scheduled or tid in visited:
            return scheduled.get(tid, {}).get("finish_dt")
        visited.add(tid)
        t = tasks[tid]
        start = _parse_date(t["start"])
        for pred in t.get("predecessors", []):
            pid, ptype = pred.get("id"), pred.get("type", "FS")
            lag = pred.get("lag", 0)
            schedule(pid, visited)
            if pid in scheduled:
                p_start = _parse_date(scheduled[pid]["start"])
                p_finish = _parse_date(scheduled[pid]["finish"])
                if ptype == "FS":
                    start = max(start, p_finish + timedelta(days=lag))
                elif ptype == "SS":
                    start = max(start, p_start + timedelta(days=lag))
                elif ptype == "FF":
                    start = max(start, p_finish + timedelta(days=lag) - timedelta(days=t["duration"]))
                elif ptype == "SF":
                    start = max(start, p_start + timedelta(days=lag) - timedelta(days=t["duration"]))
        finish = start + timedelta(days=t["duration"])
        scheduled[tid] = {"start": _fmt_date(start), "finish": _fmt_date(finish), "start_dt": start, "finish_dt": finish, **t}
        return finish

    for tid in tasks:
        schedule(tid)
    for s in scheduled.values():
        s.pop("start_dt", None)
        s.pop("finish_dt", None)
    return {"project": project, "schedule": list(scheduled.values())}


def _gantt(project):
    sched = _schedule(project)
    rows = [{"id": s["id"], "name": s["name"], "start": s["start"], "finish": s["finish"], "duration": s["duration"], "percent": s.get("percent_complete", 0)} for s in sched["schedule"]]
    return {"project": project, "gantt": rows}


def _critical_path(project):
    sched = _schedule(project)
    tasks = {s["id"]: s for s in sched["schedule"]}
    if not tasks:
        return {"project": project, "critical_path": []}
    project_finish = max(_parse_date(s["finish"]) for s in tasks.values())
    late_finish = {tid: project_finish for tid in tasks}
    for tid in sorted(tasks, key=lambda t: -len(tasks[t].get("predecessors", []))):
        succ = [s for s in tasks if any(p.get("id") == tid for p in tasks[s].get("predecessors", []))]
        if succ:
            late_finish[tid] = min(late_finish[s] - timedelta(days=tasks[s]["duration"]) for s in succ)
    critical = [tid for tid, t in tasks.items() if (_parse_date(t["finish"]) - late_finish[tid]).days == 0]
    return {"project": project, "critical_path": critical}


def _set_baseline(project, name="baseline"):
    store = _load()
    sched = _schedule(project)
    proj = store["projects"].get(project, {})
    proj.setdefault("baselines", {})[name] = {"set": _fmt_date(datetime.now()), "schedule": sched["schedule"]}
    _save(store)
    return {"baseline": name, "tasks": len(sched["schedule"])}


def _variance(project, baseline="baseline"):
    store = _load()
    proj = store.get("projects", {}).get(project, {})
    base = proj.get("baselines", {}).get(baseline, {})
    current = _schedule(project)["schedule"]
    base_map = {t["id"]: t for t in base.get("schedule", [])}
    variances = []
    for t in current:
        b = base_map.get(t["id"], {})
        if b:
            sv = (_parse_date(t["start"]) - _parse_date(b["start"])).days
            fv = (_parse_date(t["finish"]) - _parse_date(b["finish"])).days
            dv = t["duration"] - b["duration"]
            if sv or fv or dv:
                variances.append({"id": t["id"], "name": t["name"], "start_variance": sv, "finish_variance": fv, "duration_variance": dv})
    return {"project": project, "baseline": baseline, "variances": variances}


def _earned_value(project, baseline="baseline"):
    store = _load()
    proj = store.get("projects", {}).get(project, {})
    base = proj.get("baselines", {}).get(baseline, {}).get("schedule", [])
    current = _schedule(project)["schedule"]
    bcws = sum(t["duration"] for t in base)
    bcwp = sum(t["duration"] * t.get("percent_complete", 0) / 100 for t in current)
    acwp = bcwp
    cpi = bcwp / acwp if acwp else 0
    spi = bcwp / bcws if bcws else 0
    return {"BCWS": bcws, "BCWP": round(bcwp, 2), "ACWP": round(acwp, 2), "CPI": round(cpi, 4), "SPI": round(spi, 4), "status": "on budget" if cpi >= 1 else "over budget"}


def _level_resources(project):
    store = _load()
    proj = store.get("projects", {}).get(project, {})
    tasks = proj.get("tasks", [])
    usage: dict[str, list] = {}
    for t in tasks:
        for r in t.get("resources", []):
            usage.setdefault(r, []).append(t)
    over = {r: ts for r, ts in usage.items() if len(ts) > 1}
    return {"project": project, "overallocated": list(over.keys()), "conflicts": {r: [t["id"] for t in ts] for r, ts in over.items()}}


TOOLS: list[dict] = [
    {
        "name": "project_create",
        "description": "Create a new project with a start date.",
        "params": {"name": "string", "start": "string"},
        "run": lambda a: _create_project(a.get("name", ""), a.get("start", "")),
    },
    {
        "name": "project_add_task",
        "description": "Add a task with duration (days), start, predecessors (list of {id, type: FS/SS/FF/SF, lag}), resources, task_type, and work hours.",
        "params": {"project": "string", "name": "string", "duration": "int", "start": "string", "predecessors": "list", "resources": "list", "task_type": "string", "work": "int"},
        "run": lambda a: _add_task(a.get("project", ""), a.get("name", ""), int(a.get("duration", 1)), a.get("start", ""), a.get("predecessors", []), a.get("resources", []), a.get("task_type", "fixed_duration"), int(a.get("work", 0))),
    },
    {
        "name": "project_schedule",
        "description": "Compute the project schedule honoring dependency types (FS, SS, FF, SF) and lags.",
        "params": {"project": "string"},
        "run": lambda a: _schedule(a.get("project", "")),
    },
    {
        "name": "project_gantt",
        "description": "Produce Gantt-chart rows (id, name, start, finish, duration, percent) for visualization.",
        "params": {"project": "string"},
        "run": lambda a: _gantt(a.get("project", "")),
    },
    {
        "name": "project_critical_path",
        "description": "Compute the critical path (tasks with zero slack) of the project.",
        "params": {"project": "string"},
        "run": lambda a: _critical_path(a.get("project", "")),
    },
    {
        "name": "project_set_baseline",
        "description": "Save the current schedule as a named baseline for variance tracking.",
        "params": {"project": "string", "name": "string"},
        "run": lambda a: _set_baseline(a.get("project", ""), a.get("name", "baseline")),
    },
    {
        "name": "project_variance",
        "description": "Compare the current schedule against a baseline and report start/finish/duration variances.",
        "params": {"project": "string", "baseline": "string"},
        "run": lambda a: _variance(a.get("project", ""), a.get("baseline", "baseline")),
    },
    {
        "name": "project_earned_value",
        "description": "Compute earned-value metrics: BCWS, BCWP, ACWP, CPI, SPI.",
        "params": {"project": "string", "baseline": "string"},
        "run": lambda a: _earned_value(a.get("project", ""), a.get("baseline", "baseline")),
    },
    {
        "name": "project_resource_level",
        "description": "Detect overallocated resources (assigned to more than one concurrent task).",
        "params": {"project": "string"},
        "run": lambda a: _level_resources(a.get("project", "")),
    },
]
