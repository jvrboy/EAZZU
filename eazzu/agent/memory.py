"""Persistent working memory for the agentic loop.

Stores agent state, conversation history, task progress, and scratchpad
data in a JSON file on disk. This allows the agent to:

  * Resume conversations across CLI sessions
  * Track multi-step task progress
  * Remember facts, decisions, and intermediate results
  * Maintain a persistent scratchpad for long-running workflows

No external dependencies — uses stdlib json + os.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Optional


def _default_path() -> Path:
    return Path(os.environ.get("EAZZU_MEMORY_PATH", Path.home() / ".eazzu" / "memory.json"))


class WorkingMemory:
    """Persistent JSON-backed working memory."""

    def __init__(self, path: Optional[str] = None) -> None:
        self.path = Path(path) if path else _default_path()
        self._data: dict = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "facts": {},
            "history": [],
            "tasks": [],
            "scratchpad": "",
            "artifacts": [],
        }

    def _save(self) -> None:
        self._data["updated"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(self._data, indent=2, default=str), encoding="utf-8")

    def set_fact(self, key: str, value: Any) -> dict:
        self._data["facts"][key] = value
        self._save()
        return {"key": key, "value": value}

    def get_fact(self, key: str) -> dict:
        return {"key": key, "value": self._data["facts"].get(key)}

    def list_facts(self) -> dict:
        return {"facts": self._data["facts"], "count": len(self._data["facts"])}

    def delete_fact(self, key: str) -> dict:
        removed = self._data["facts"].pop(key, None)
        self._save()
        return {"key": key, "deleted": removed is not None}

    def add_message(self, role: str, content: str) -> dict:
        msg = {"role": role, "content": content, "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
        self._data["history"].append(msg)
        if len(self._data["history"]) > 1000:
            self._data["history"] = self._data["history"][-500:]
        self._save()
        return msg

    def get_history(self, limit: int = 50) -> dict:
        msgs = self._data["history"][-limit:]
        return {"messages": msgs, "count": len(msgs), "total": len(self._data["history"])}

    def clear_history(self) -> dict:
        count = len(self._data["history"])
        self._data["history"] = []
        self._save()
        return {"cleared": count}

    def add_task(self, description: str, steps: Optional[list[str]] = None) -> dict:
        task = {
            "id": f"task_{len(self._data['tasks']) + 1}",
            "description": description,
            "status": "pending",
            "steps": [{"desc": s, "done": False} for s in (steps or [])],
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self._data["tasks"].append(task)
        self._save()
        return task

    def update_task(self, task_id: str, status: Optional[str] = None, step_idx: Optional[int] = None) -> dict:
        for t in self._data["tasks"]:
            if t["id"] == task_id:
                if status:
                    t["status"] = status
                if step_idx is not None and 0 <= step_idx < len(t["steps"]):
                    t["steps"][step_idx]["done"] = True
                self._save()
                return t
        return {"error": f"task '{task_id}' not found"}

    def list_tasks(self, status: Optional[str] = None) -> dict:
        tasks = self._data["tasks"]
        if status:
            tasks = [t for t in tasks if t["status"] == status]
        return {"tasks": tasks, "count": len(tasks)}

    def task_progress(self, task_id: str) -> dict:
        for t in self._data["tasks"]:
            if t["id"] == task_id:
                done = sum(1 for s in t["steps"] if s["done"])
                total = len(t["steps"])
                return {"task_id": task_id, "completed_steps": done, "total_steps": total, "progress": f"{done}/{total}", "all_done": done == total and total > 0}
        return {"error": f"task '{task_id}' not found"}

    def set_scratchpad(self, text: str) -> dict:
        self._data["scratchpad"] = text
        self._save()
        return {"length": len(text)}

    def get_scratchpad(self) -> dict:
        return {"scratchpad": self._data["scratchpad"], "length": len(self._data["scratchpad"])}

    def append_scratchpad(self, text: str) -> dict:
        self._data["scratchpad"] = (self._data["scratchpad"] or "") + text + "\n"
        self._save()
        return {"length": len(self._data["scratchpad"])}

    def add_artifact(self, name: str, artifact_type: str, content: str) -> dict:
        artifact = {
            "id": f"art_{len(self._data['artifacts']) + 1}",
            "name": name,
            "type": artifact_type,
            "content": content,
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        self._data["artifacts"].append(artifact)
        self._save()
        return artifact

    def list_artifacts(self) -> dict:
        return {"artifacts": [{"id": a["id"], "name": a["name"], "type": a["type"], "ts": a["ts"]} for a in self._data["artifacts"]], "count": len(self._data["artifacts"])}

    def get_artifact(self, artifact_id: str) -> dict:
        for a in self._data["artifacts"]:
            if a["id"] == artifact_id:
                return a
        return {"error": f"artifact '{artifact_id}' not found"}

    def snapshot(self) -> dict:
        return {
            "facts": len(self._data["facts"]),
            "history": len(self._data["history"]),
            "tasks": len(self._data["tasks"]),
            "artifacts": len(self._data["artifacts"]),
            "scratchpad_len": len(self._data["scratchpad"]),
            "created": self._data.get("created"),
            "updated": self._data.get("updated"),
        }

    def reset(self) -> dict:
        self._data = {
            "created": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "updated": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "facts": {},
            "history": [],
            "tasks": [],
            "scratchpad": "",
            "artifacts": [],
        }
        self._save()
        return {"reset": True}
