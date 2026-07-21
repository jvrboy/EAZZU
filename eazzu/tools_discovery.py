"""``eazzu tools`` — discoverability commands for the 400+ tool registry.

Sub-commands
------------
* ``tools list``     list all tools (optionally filter ``--query`` / ``--group``)
* ``tools count``    print total tool count and per-group breakdown
* ``tools info``     print a single tool's description, parameters, and example
* ``tools groups``   list the source-module groups and their counts

The registry is imported lazily so ``eazzu --help`` stays snappy.
"""
from __future__ import annotations

import fnmatch
import json
from typing import Any, Iterable

from eazzu.cli_ui import colorize, C, table


def _registry() -> list[dict[str, Any]]:
    from eazzu.tools import REGISTRY  # noqa: WPS433 — lazy
    return list(REGISTRY)


# --- grouping: map tool name back to its source module by scanning __init__ --
_GROUPS_ORDER: list[str] = []
_GROUPS_MAP: dict[str, str] = {}


def _build_group_map() -> None:
    """Lazily build a tool -> source-module mapping by inspecting eazzu.tools."""
    if _GROUPS_MAP:
        return
    import importlib
    import eazzu.tools as _t
    from eazzu import tools as tools_pkg
    # Iterate attributes in order they appear in tools/__init__.py exports.
    for attr in dir(tools_pkg):
        if attr.startswith("_"):
            continue
        mod_name = f"eazzu.tools.{attr}"
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            continue
        toollist = getattr(mod, "TOOLS", None)
        if not isinstance(toollist, list):
            continue
        label = attr
        if label not in _GROUPS_ORDER:
            _GROUPS_ORDER.append(label)
        for t in toollist:
            if isinstance(t, dict) and "name" in t:
                # First group to claim the name wins (preserves import order).
                _GROUPS_MAP.setdefault(t["name"], label)


def _group_of(tool: dict[str, Any]) -> str:
    _build_group_map()
    return _GROUPS_MAP.get(tool["name"], "uncategorized")


# ---------------------------------------------------------------- commands #
def cmd_list(
    query: str | None = None,
    group: str | None = None,
    as_json: bool = False,
) -> int:
    tools = _registry()
    if query:
        q = query.lower()
        tools = [
            t for t in tools
            if q in t["name"].lower() or q in (t.get("description") or "").lower()
        ]
    if group:
        tools = [t for t in tools if fnmatch.fnmatch(_group_of(t), group)]

    if as_json:
        print(json.dumps([
            {"name": t["name"], "description": t.get("description", ""), "group": _group_of(t)}
            for t in tools
        ], indent=2))
        return 0

    if not tools:
        print("(no tools match)")
        return 1

    rows = [
        [t["name"], _group_of(t), (t.get("description") or "")[:55]]
        for t in tools
    ]
    print(table(["Tool", "Group", "Description"], rows))
    print(f"\n{len(tools)} tool(s) shown")
    return 0


def cmd_count() -> int:
    tools = _registry()
    _build_group_map()
    counts: dict[str, int] = {}
    for t in tools:
        g = _group_of(t)
        counts[g] = counts.get(g, 0) + 1
    rows = [[g, str(counts[g])] for g in sorted(counts, key=lambda x: -counts[x])]
    rows.append([colorize("TOTAL", C.BOLD), colorize(str(len(tools)), C.BOLD)])
    print(table(["Group", "Tools"], rows))
    return 0


def cmd_info(name: str) -> int:
    tools = {t["name"]: t for t in _registry()}
    if name not in tools:
        # Fuzzy: prefix match
        matches = [n for n in tools if n.startswith(name) or name in n]
        if len(matches) == 1:
            name = matches[0]
        else:
            print(f"no tool named {name!r}")
            if matches:
                print("did you mean:", ", ".join(sorted(matches)[:10]))
            return 1
    t = tools[name]
    print(colorize(t["name"], C.BOLD + C.CYAN))
    print(f"  group      : {_group_of(t)}")
    print(f"  description: {t.get('description', '')}")
    params = t.get("params") or {}
    if params:
        print("  parameters :")
        for pname, pspec in params.items():
            if isinstance(pspec, dict):
                req = "required" if pspec.get("required") else "optional"
                typ = pspec.get("type", "any")
                default = pspec.get("default", None)
                desc = pspec.get("description", "")
                dflt = f" (default: {default!r})" if default is not None else ""
                print(f"    - {pname} ({typ}, {req}){dflt}: {desc}")
            else:
                print(f"    - {pname}: {pspec}")
    example = t.get("example")
    if example:
        print(f"  example    : {example}")
    return 0


def cmd_groups() -> int:
    _build_group_map()
    from eazzu.tools import REGISTRY
    counts: dict[str, int] = {}
    for t in REGISTRY:
        g = _group_of(t)
        counts[g] = counts.get(g, 0) + 1
    for g in sorted(counts, key=lambda x: -counts[x]):
        print(f"  {counts[g]:4d}  {g}")
    return 0


__all__ = ["cmd_list", "cmd_count", "cmd_info", "cmd_groups"]
