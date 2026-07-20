"""Memory and loop agent tools — expose persistent memory and agentic loop.

These tools let the agent (and CLI user) interact with the persistent working
memory and launch autonomous task loops.
"""
from __future__ import annotations

from typing import Optional

from eazzu.agent.memory import WorkingMemory
from eazzu.agent.loop import run_loop


TOOLS: list[dict] = [
    # ---- Memory: facts ---- #
    {
        "name": "memory_set_fact",
        "description": "Store a key-value fact in persistent working memory (survives across sessions)",
        "params": {"key": "string", "value": "string"},
        "run": lambda args: WorkingMemory().set_fact(args.get("key", ""), args.get("value", "")),
    },
    {
        "name": "memory_get_fact",
        "description": "Retrieve a stored fact from working memory by key",
        "params": {"key": "string"},
        "run": lambda args: WorkingMemory().get_fact(args.get("key", "")),
    },
    {
        "name": "memory_list_facts",
        "description": "List all stored facts in working memory",
        "params": {},
        "run": lambda args: WorkingMemory().list_facts(),
    },
    {
        "name": "memory_delete_fact",
        "description": "Delete a fact from working memory",
        "params": {"key": "string"},
        "run": lambda args: WorkingMemory().delete_fact(args.get("key", "")),
    },
    # ---- Memory: history ---- #
    {
        "name": "memory_get_history",
        "description": "Get conversation history from working memory",
        "params": {"limit": "int"},
        "run": lambda args: WorkingMemory().get_history(int(args.get("limit", 50))),
    },
    {
        "name": "memory_clear_history",
        "description": "Clear conversation history in working memory",
        "params": {},
        "run": lambda args: WorkingMemory().clear_history(),
    },
    # ---- Memory: tasks ---- #
    {
        "name": "memory_add_task",
        "description": "Add a task to the persistent task tracker",
        "params": {"description": "string", "steps": "list"},
        "run": lambda args: WorkingMemory().add_task(args.get("description", ""), args.get("steps", [])),
    },
    {
        "name": "memory_update_task",
        "description": "Update a task's status or mark a step as done",
        "params": {"task_id": "string", "status": "string", "step_idx": "int"},
        "run": lambda args: WorkingMemory().update_task(args.get("task_id", ""), args.get("status"), args.get("step_idx")),
    },
    {
        "name": "memory_list_tasks",
        "description": "List tasks in the persistent task tracker (optionally filter by status)",
        "params": {"status": "string"},
        "run": lambda args: WorkingMemory().list_tasks(args.get("status")),
    },
    {
        "name": "memory_task_progress",
        "description": "Check progress of a specific task",
        "params": {"task_id": "string"},
        "run": lambda args: WorkingMemory().task_progress(args.get("task_id", "")),
    },
    # ---- Memory: scratchpad ---- #
    {
        "name": "memory_set_scratchpad",
        "description": "Set the persistent scratchpad text",
        "params": {"text": "string"},
        "run": lambda args: WorkingMemory().set_scratchpad(args.get("text", "")),
    },
    {
        "name": "memory_get_scratchpad",
        "description": "Get the current scratchpad text",
        "params": {},
        "run": lambda args: WorkingMemory().get_scratchpad(),
    },
    {
        "name": "memory_append_scratchpad",
        "description": "Append text to the persistent scratchpad",
        "params": {"text": "string"},
        "run": lambda args: WorkingMemory().append_scratchpad(args.get("text", "")),
    },
    # ---- Memory: snapshot ---- #
    {
        "name": "memory_snapshot",
        "description": "Get a summary of the current working memory state",
        "params": {},
        "run": lambda args: WorkingMemory().snapshot(),
    },
    {
        "name": "memory_reset",
        "description": "Reset all working memory (facts, history, tasks, scratchpad, artifacts)",
        "params": {},
        "run": lambda args: WorkingMemory().reset(),
    },
    # ---- Agentic loop ---- #
    {
        "name": "run_agentic_loop",
        "description": "Run an autonomous agentic loop that executes a task until complete or max iterations. The agent plans, executes steps using tools, and checks completion.",
        "params": {"task": "string", "max_iterations": "int", "provider": "string", "model": "string"},
        "run": lambda args: run_loop(
            args.get("task", ""),
            provider=args.get("provider", "openai"),
            model=args.get("model"),
            max_iterations=int(args.get("max_iterations", 20)),
        ),
    },
]
