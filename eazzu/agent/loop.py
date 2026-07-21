"""Agentic loop — autonomous task execution until completion.

The loop:
  1. Takes a task description from the user
  2. Plans steps (using the LLM)
  3. Executes each step (calling tools as needed)
  4. Checks if the task is complete (LLM judges)
  5. Repeats until done or max iterations reached

Uses persistent working memory to track progress across iterations and
sessions. Works with any provider via the Connector.
"""
from __future__ import annotations

import json
import time
from typing import Optional

from eazzu.agent.core import Agent
from eazzu.agent.memory import WorkingMemory


_LOOP_SYSTEM = """You are an autonomous task executor. Given a task, you must:
1. Break it into concrete steps
2. Execute each step by calling tools
3. After each step, assess progress
4. When all steps are done, output <<<TASK_COMPLETE>>>
5. If stuck after 3 attempts on a step, output <<<TASK_BLOCKED>>>

Always be concrete and action-oriented. Use tools to do real work, not just
describe what you would do. After each tool call, briefly note the result and
what you'll do next."""

_COMPLETE = "<<<TASK_COMPLETE>>>"
_BLOCKED = "<<<TASK_BLOCKED>>>"


def run_loop(
    task: str,
    *,
    provider: str = "auto",
    model: Optional[str] = None,
    max_iterations: int = 20,
    memory_path: Optional[str] = None,
    on_step: Optional[callable] = None,
    router_strategy: str = "random",
) -> dict:
    """Run the autonomous agentic loop until the task is complete or max iterations."""
    agent = Agent(provider=provider, model=model, router_strategy=router_strategy)
    memory = WorkingMemory(path=memory_path)
    task_record = memory.add_task(task)
    task_id = task_record["id"]

    steps = []
    status = "max_reached"
    current_prompt = f"Task: {task}\n\nBreak this into steps and execute them one at a time. Start by listing the steps, then work through each."

    for i in range(max_iterations):
        iteration = i + 1
        step_start = time.time()

        context = f"\n\n[Iteration {iteration}/{max_iterations} | Task ID: {task_id} | Progress: {memory.task_progress(task_id).get('progress', '0/0')}]"
        turn = agent.ask(current_prompt + context)
        reply = turn.reply or ""
        memory.add_message("assistant", reply)
        memory.append_scratchpad(f"\n--- Iteration {iteration} ---\n{reply}\n")

        step_result = {
            "iteration": iteration,
            "reply": reply[:2000],
            "tool_calls": turn.tool_calls,
            "latency_ms": turn.latency_ms,
            "elapsed_s": time.time() - step_start,
            "elapsed": time.time() - step_start,
        }
        if getattr(agent, "last_route", None):
            step_result["route"] = dict(agent.last_route)
        steps.append(step_result)
        if on_step:
            on_step(step_result)

        if _COMPLETE in reply:
            status = "complete"
            memory.update_task(task_id, status="complete")
            break
        if _BLOCKED in reply:
            status = "blocked"
            memory.update_task(task_id, status="blocked")
            break

        current_prompt = f"Continue working on the task. Here's what you did last:\n\n{reply[:1500]}\n\nWhat's your next step? Execute it now."

    snapshot = memory.snapshot()
    return {
        "task": task,
        "task_id": task_id,
        "iterations": len(steps),
        "status": status,
        "steps": steps,
        "memory": snapshot,
    }
