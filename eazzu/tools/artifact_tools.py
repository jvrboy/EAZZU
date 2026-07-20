"""Artifacts creator — generate, manage, and export project artifacts.

An artifact is any structured output the agent creates: code files, documents,
data files, configurations, HTML pages, scripts, etc. This module provides:

  * ``create_artifact`` — create a named artifact with type and content
  * ``get_artifact`` — retrieve an artifact by ID
  * ``list_artifacts`` — list all artifacts
  * ``export_artifact`` — write an artifact to a file on disk
  * ``export_all`` — export all artifacts to a directory
  * ``create_html`` — create an HTML page artifact
  * ``create_markdown`` — create a Markdown document artifact
  * ``create_json_artifact`` — create a JSON data artifact
  * ``create_python_script`` — create a Python script artifact
  * ``create_config`` — create a configuration file artifact

Artifacts are persisted in working memory and can be exported to disk.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Optional

from eazzu.agent.memory import WorkingMemory


def create_artifact(name: str, artifact_type: str, content: str, memory_path: Optional[str] = None) -> dict:
    """Create a named artifact in persistent memory."""
    mem = WorkingMemory(path=memory_path)
    return mem.add_artifact(name, artifact_type, content)


def get_artifact(artifact_id: str, memory_path: Optional[str] = None) -> dict:
    """Retrieve an artifact by ID."""
    mem = WorkingMemory(path=memory_path)
    return mem.get_artifact(artifact_id)


def list_artifacts(memory_path: Optional[str] = None) -> dict:
    """List all artifacts (metadata only — no content)."""
    mem = WorkingMemory(path=memory_path)
    return mem.list_artifacts()


def export_artifact(artifact_id: str, output_path: str, memory_path: Optional[str] = None) -> dict:
    """Export an artifact to a file on disk."""
    mem = WorkingMemory(path=memory_path)
    artifact = mem.get_artifact(artifact_id)
    if "error" in artifact:
        return artifact
    p = Path(output_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(artifact["content"], encoding="utf-8")
    return {"exported": True, "path": str(p), "size": len(artifact["content"]), "artifact_id": artifact_id}


def export_all(output_dir: str, memory_path: Optional[str] = None) -> dict:
    """Export all artifacts to a directory. Returns list of exported files."""
    mem = WorkingMemory(path=memory_path)
    listing = mem.list_artifacts()
    if "error" in listing or listing["count"] == 0:
        return {"exported": [], "count": 0}
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    exported = []
    for meta in listing["artifacts"]:
        artifact = mem.get_artifact(meta["id"])
        safe_name = meta["name"].replace(" ", "_").replace("/", "_")
        ext = _ext_for_type(meta["type"])
        filename = f"{safe_name}{ext}"
        filepath = out / filename
        filepath.write_text(artifact["content"], encoding="utf-8")
        exported.append({"id": meta["id"], "name": meta["name"], "path": str(filepath), "size": len(artifact["content"])})
    return {"exported": exported, "count": len(exported), "directory": str(out)}


def _ext_for_type(artifact_type: str) -> str:
    ext_map = {
        "html": ".html", "markdown": ".md", "json": ".json", "python": ".py",
        "javascript": ".js", "typescript": ".ts", "shell": ".sh", "yaml": ".yaml",
        "config": ".json", "text": ".txt", "csv": ".csv", "sql": ".sql",
        "css": ".css", "xml": ".xml",
    }
    return ext_map.get(artifact_type.lower(), ".txt")


def create_html(title: str, body: str, memory_path: Optional[str] = None) -> dict:
    """Create a complete HTML page artifact."""
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 800px; margin: 2rem auto; padding: 1rem; line-height: 1.6; }}
        h1 {{ color: #1a1a2e; }}
        pre {{ background: #f4f4f4; padding: 1rem; border-radius: 8px; overflow-x: auto; }}
        code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 4px; }}
    </style>
</head>
<body>
{body}
</body>
</html>"""
    return create_artifact(title, "html", html, memory_path)


def create_markdown(title: str, body: str, memory_path: Optional[str] = None) -> dict:
    """Create a Markdown document artifact."""
    content = f"# {title}\n\n{body}"
    return create_artifact(title, "markdown", content, memory_path)


def create_json_artifact(name: str, data: dict, memory_path: Optional[str] = None) -> dict:
    """Create a JSON data artifact."""
    return create_artifact(name, "json", json.dumps(data, indent=2, default=str), memory_path)


def create_python_script(name: str, code: str, memory_path: Optional[str] = None) -> dict:
    """Create a Python script artifact."""
    return create_artifact(name, "python", code, memory_path)


def create_config(name: str, config: dict, format: str = "json", memory_path: Optional[str] = None) -> dict:
    """Create a configuration file artifact."""
    if format == "yaml":
        lines = []
        def _yaml(obj, indent=0):
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, (dict, list)):
                        lines.append(f"{'  ' * indent}{k}:")
                        _yaml(v, indent + 1)
                    else:
                        lines.append(f"{'  ' * indent}{k}: {v}")
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, (dict, list)):
                        lines.append(f"{'  ' * indent}-")
                        _yaml(item, indent + 1)
                    else:
                        lines.append(f"{'  ' * indent}- {item}")
        _yaml(config)
        content = "\n".join(lines)
    else:
        content = json.dumps(config, indent=2, default=str)
    return create_artifact(name, format, content, memory_path)


TOOLS: list[dict] = [
    {
        "name": "create_artifact",
        "description": "Create a named artifact (code, document, config, etc.) in persistent memory",
        "params": {"name": "string", "type": "string", "content": "string"},
        "run": lambda args: create_artifact(args.get("name", ""), args.get("type", "text"), args.get("content", "")),
    },
    {
        "name": "get_artifact",
        "description": "Retrieve an artifact by its ID",
        "params": {"id": "string"},
        "run": lambda args: get_artifact(args.get("id", "")),
    },
    {
        "name": "list_artifacts",
        "description": "List all stored artifacts (metadata only)",
        "params": {},
        "run": lambda args: list_artifacts(),
    },
    {
        "name": "export_artifact",
        "description": "Export an artifact to a file on disk",
        "params": {"id": "string", "path": "string"},
        "run": lambda args: export_artifact(args.get("id", ""), args.get("path", "")),
    },
    {
        "name": "export_all_artifacts",
        "description": "Export all artifacts to a directory",
        "params": {"directory": "string"},
        "run": lambda args: export_all(args.get("directory", "./artifacts")),
    },
    {
        "name": "create_html_page",
        "description": "Create a complete HTML page artifact with title and body content",
        "params": {"title": "string", "body": "string"},
        "run": lambda args: create_html(args.get("title", ""), args.get("body", "")),
    },
    {
        "name": "create_markdown_doc",
        "description": "Create a Markdown document artifact",
        "params": {"title": "string", "body": "string"},
        "run": lambda args: create_markdown(args.get("title", ""), args.get("body", "")),
    },
    {
        "name": "create_json_data",
        "description": "Create a JSON data artifact from a dict/list",
        "params": {"name": "string", "data": "object"},
        "run": lambda args: create_json_artifact(args.get("name", ""), args.get("data", {})),
    },
    {
        "name": "create_python_script",
        "description": "Create a Python script artifact",
        "params": {"name": "string", "code": "string"},
        "run": lambda args: create_python_script(args.get("name", ""), args.get("code", "")),
    },
    {
        "name": "create_config_file",
        "description": "Create a configuration file artifact (JSON or YAML)",
        "params": {"name": "string", "config": "object", "format": "string"},
        "run": lambda args: create_config(args.get("name", ""), args.get("config", {}), args.get("format", "json")),
    },
]
