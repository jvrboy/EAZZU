"""Diagramming & visual modeling tools.

Generate Mermaid diagrams (flowcharts, sequence, ERD, Gantt, mind maps,
state, class) and Graphviz DOT from structured input. No external
runtime required — outputs text the agent can embed in Markdown.
"""
from __future__ import annotations


def _mermaid_flowchart(nodes, edges, direction="TD"):
    lines = [f"flowchart {direction}"]
    for n in nodes:
        shape = n.get("shape", "rect")
        label = n.get("label", n["id"])
        if shape == "round":
            lines.append(f"  {n['id']}({label})")
        elif shape == "diamond":
            lines.append(f"  {n['id']}{{{label}}}")
        elif shape == "circle":
            lines.append(f"  {n['id']}(( {label} ))")
        elif shape == "stadium":
            lines.append(f"  {n['id']}([{label}])")
        else:
            lines.append(f"  {n['id']}[{label}]")
    for e in edges:
        label = e.get("label", "")
        arrow = f"-->{label}" if label else "-->"
        lines.append(f"  {e['from']} {arrow} {e['to']}")
    return "\n".join(lines)


def _mermaid_sequence(actors, messages):
    lines = ["sequenceDiagram"]
    for a in actors:
        lines.append(f"  participant {a}")
    for m in messages:
        arrow = "->>" if m.get("type", "sync") == "sync" else "-->>"
        lines.append(f"  {m['from']} {arrow} {m['to']}: {m['text']}")
    return "\n".join(lines)


def _mermaid_erd(entities, relations):
    lines = ["erDiagram"]
    for e in entities:
        lines.append(f"  {e['name']} {{")
        for f in e.get("fields", []):
            pk = "PK" if f.get("pk") else ("FK" if f.get("fk") else "")
            lines.append(f"    {f.get('type','string')} {f['name']} {pk}")
        lines.append("  }")
    for r in relations:
        lines.append(f"  {r['from']} {r.get('card','||--||')} {r['to']} : {r.get('label','')}")
    return "\n".join(lines)


def _mermaid_gantt(tasks):
    lines = ["gantt", "  title Project Schedule", "  dateFormat YYYY-MM-DD"]
    for t in tasks:
        lines.append(f"  section {t.get('section','Tasks')}")
        lines.append(f"  {t['name']} :{t.get('id','')} {t.get('start','')} {t.get('duration','1d')}")
    return "\n".join(lines)


def _mermaid_mindmap(central, branches):
    lines = ["mindmap", f"  root(({central}))"]

    def render(node, depth):
        for b in node:
            lines.append(f"{'  ' * (depth + 1)}{b['text']}")
            if b.get("children"):
                render(b["children"], depth + 1)

    render(branches, 1)
    return "\n".join(lines)


def _mermaid_state(states, transitions):
    lines = ["stateDiagram-v2"]
    for s in states:
        if s.get("initial"):
            lines.append(f"  [*] --> {s['id']}")
        if s.get("final"):
            lines.append(f"  {s['id']} --> [*]")
    for t in transitions:
        lines.append(f"  {t['from']} --> {t['to']}: {t.get('label','')}")
    return "\n".join(lines)


def _mermaid_class(classes):
    lines = ["classDiagram"]
    for c in classes:
        lines.append(f"  class {c['name']}")
        for m in c.get("methods", []):
            lines.append(f"    +{m}")
        for attr in c.get("attributes", []):
            lines.append(f"    +{attr}")
        if c.get("extends"):
            lines.append(f"  {c['extends']} <|-- {c['name']}")
    return "\n".join(lines)


def _graphviz_dot(nodes, edges):
    lines = ["digraph G {"]
    for n in nodes:
        attrs = []
        if n.get("label"):
            attrs.append(f'label="{n["label"]}"')
        if n.get("shape"):
            attrs.append(f'shape={n["shape"]}')
        attr_str = f" [{', '.join(attrs)}]" if attrs else ""
        lines.append(f'  "{n["id"]}"{attr_str};')
    for e in edges:
        attrs = [f'label="{e["label"]}"'] if e.get("label") else []
        attr_str = f" [{', '.join(attrs)}]" if attrs else ""
        lines.append(f'  "{e["from"]}" -> "{e["to"]}"{attr_str};')
    lines.append("}")
    return "\n".join(lines)


def _swimlane(lanes, steps):
    lines = ["flowchart TD"]
    for lane in lanes:
        lines.append(f"  subgraph {lane.replace(' ','_')}")
        for s in [s for s in steps if s.get("lane") == lane]:
            lines.append(f"    {s['id']}[{s['label']}]")
        lines.append("  end")
    for s in steps:
        for nxt in s.get("next", []):
            lines.append(f"  {s['id']} --> {nxt}")
    return "\n".join(lines)


def _fishbone(categories):
    lines = ["flowchart TD", "  effect((Effect))"]
    for c in categories:
        lines.append(f"  {c['name']}[{c['name']}]")
        lines.append(f"  {c['name']} --> effect")
        for cause in c.get("causes", []):
            cid = cause.replace(" ", "_")
            lines.append(f"  {cid}[{cause}]")
            lines.append(f"  {cid} --> {c['name']}")
    return "\n".join(lines)


TOOLS: list[dict] = [
    {
        "name": "diagram_flowchart",
        "description": "Generate a Mermaid flowchart from nodes (id, label, shape) and edges (from, to, label).",
        "params": {"nodes": "list", "edges": "list", "direction": "string"},
        "run": lambda a: {"mermaid": _mermaid_flowchart(a.get("nodes", []), a.get("edges", []), a.get("direction", "TD"))},
    },
    {
        "name": "diagram_sequence",
        "description": "Generate a Mermaid sequence diagram from actors and messages (from, to, text, type).",
        "params": {"actors": "list", "messages": "list"},
        "run": lambda a: {"mermaid": _mermaid_sequence(a.get("actors", []), a.get("messages", []))},
    },
    {
        "name": "diagram_erd",
        "description": "Generate a Mermaid ER diagram from entities (name, fields[{name,type,pk,fk}]) and relations (from, to, card, label).",
        "params": {"entities": "list", "relations": "list"},
        "run": lambda a: {"mermaid": _mermaid_erd(a.get("entities", []), a.get("relations", []))},
    },
    {
        "name": "diagram_gantt",
        "description": "Generate a Mermaid Gantt chart from tasks (section, name, id, start, duration).",
        "params": {"tasks": "list"},
        "run": lambda a: {"mermaid": _mermaid_gantt(a.get("tasks", []))},
    },
    {
        "name": "diagram_mindmap",
        "description": "Generate a Mermaid mind map from a central topic and nested branches (text, children).",
        "params": {"central": "string", "branches": "list"},
        "run": lambda a: {"mermaid": _mermaid_mindmap(a.get("central", ""), a.get("branches", []))},
    },
    {
        "name": "diagram_state",
        "description": "Generate a Mermaid state diagram from states (id, initial, final) and transitions (from, to, label).",
        "params": {"states": "list", "transitions": "list"},
        "run": lambda a: {"mermaid": _mermaid_state(a.get("states", []), a.get("transitions", []))},
    },
    {
        "name": "diagram_class",
        "description": "Generate a Mermaid class diagram from classes (name, attributes, methods, extends).",
        "params": {"classes": "list"},
        "run": lambda a: {"mermaid": _mermaid_class(a.get("classes", []))},
    },
    {
        "name": "diagram_graphviz",
        "description": "Generate Graphviz DOT source from nodes and edges (for rendering with graphviz).",
        "params": {"nodes": "list", "edges": "list"},
        "run": lambda a: {"dot": _graphviz_dot(a.get("nodes", []), a.get("edges", []))},
    },
    {
        "name": "diagram_swimlane",
        "description": "Generate a cross-functional swimlane flowchart from lanes and steps (lane, id, label, next).",
        "params": {"lanes": "list", "steps": "list"},
        "run": lambda a: {"mermaid": _swimlane(a.get("lanes", []), a.get("steps", []))},
    },
    {
        "name": "diagram_fishbone",
        "description": "Generate an Ishikawa/fishbone diagram from categories (name, causes).",
        "params": {"categories": "list"},
        "run": lambda a: {"mermaid": _fishbone(a.get("categories", []))},
    },
]
