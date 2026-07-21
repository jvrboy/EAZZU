"""Agent core — a portable ReAct-style loop with pluggable tools.

Design goals
------------
* Provider-agnostic. Uses :class:`eazzu.providers.Connector`, so any of the 80+
  registered providers (OpenAI, Anthropic, Groq, Ollama, DeepSeek, xAI, …) can
  drive the agent — the user brings their own API keys.
* Works even on strict text-only models (no native function calling required).
  Tools are surfaced through a JSON protocol in the system prompt; the agent
  parses ```tool``` fenced blocks and dispatches to :mod:`eazzu.tools`.
* Streaming-friendly. When the caller passes ``on_token``, tokens are streamed
  live; otherwise we fall back to a single blocking call.
* Deterministic tool contract — every tool returns a JSON-serialisable dict so
  the transcript stays reproducible and audit-friendly.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Optional

from eazzu.providers import Connector
import eazzu.providers.providers  # noqa: F401 — side-effect: register all providers

# Regex that finds ```tool\n{...}\n``` blocks the LLM emits to call a tool.
_TOOL_RE = re.compile(r"```tool\s*(\{.*?\})\s*```", re.DOTALL)


@dataclass
class AgentMessage:
    role: str
    content: str

    def to_dict(self) -> dict:
        return {"role": self.role, "content": self.content}


@dataclass
class AgentTurn:
    prompt: str
    reply: str
    tool_calls: list[dict] = field(default_factory=list)
    latency_ms: float = 0.0
    cost_usd: float = 0.0


def _default_system_prompt(tool_catalog: list[dict]) -> str:
    tool_lines = []
    for t in tool_catalog:
        params = ", ".join(f"{k}: {v}" for k, v in t.get("params", {}).items()) or "—"
        tool_lines.append(f"- **{t['name']}** — {t['description']} · params: {params}")
    tools_block = "\n".join(tool_lines) if tool_lines else "(no tools available)"
    return f"""You are EAZZU, an agentic assistant that can call local tools.

## Tools you can use
{tools_block}

## How to call a tool
Emit a fenced block **exactly** like this — nothing else on those lines:

```tool
{{"name": "<tool_name>", "args": {{ "<arg>": "<value>" }} }}
```

Rules:
1. You may call **at most one** tool per response.
2. After a tool result comes back, decide whether to call another tool or
   answer the user directly in plain prose.
3. If the user's request needs no tool, just reply normally.
4. Always be concise, technical, and give copy-pasteable commands or code.
"""


class Agent:
    """A minimal, provider-agnostic tool-using agent.

    Parameters
    ----------
    provider:
        Name of a registered provider (e.g. ``"openai"``, ``"anthropic"``,
        ``"groq"``, ``"deepseek"``, ``"ollama"``). The API key is read from the
        connector's :class:`ConfigManager` — set it via ``eazzu keys set``.
    model:
        Optional model override. Falls back to the provider's default.
    connector:
        Reuse an existing :class:`Connector`; otherwise a fresh one is built.
    tools:
        Iterable of ``{name, description, params, run(args) -> Any}`` dicts.
        Defaults to :data:`eazzu.tools.REGISTRY`.
    max_steps:
        Safety cap on tool-calling loops per user turn (default 6).
    """

    def __init__(
        self,
        provider: str = "auto",
        model: Optional[str] = None,
        connector: Optional[Connector] = None,
        tools: Optional[Iterable[dict]] = None,
        system_prompt: Optional[str] = None,
        max_steps: int = 6,
        router_strategy: str = "random",
    ) -> None:
        self.provider = provider  # "auto" -> use ProviderRouter
        self.model = model
        self.connector = connector or Connector()
        self.router = None
        if str(provider).lower() == "auto":
            from eazzu.providers.router import ProviderRouter  # noqa: WPS433
            self.router = ProviderRouter(
                connector=self.connector,
                config=getattr(self.connector, "config", None),
                strategy=router_strategy,
            )
            if not self.router.endpoints:
                import sys
                print(
                    "[eazzu] router found no configured LLM keys — "
                    "set keys via `eazzu keys add <provider> <key>` or env vars; "
                    "falling back to single-provider mode.",
                    file=sys.stderr,
                )
                self.provider = "openai"
                self.router = None
        # Deferred tool import prevents circular imports at package load time.
        if tools is None:
            from eazzu.tools import REGISTRY  # noqa: WPS433
            tools = REGISTRY
        self.tools: list[dict] = list(tools)
        self.max_steps = max_steps
        catalog = [
            {"name": t["name"], "description": t["description"], "params": t.get("params", {})}
            for t in self.tools
        ]
        self.system_prompt = system_prompt or _default_system_prompt(catalog)
        self.history: list[AgentMessage] = [AgentMessage("system", self.system_prompt)]
        self.last_route: Optional[dict] = None  # populated after each LLM call

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def reset(self) -> None:
        self.history = [AgentMessage("system", self.system_prompt)]

    def ask(
        self,
        user_input: str,
        on_token: Optional[Callable[[str], None]] = None,
        on_tool: Optional[Callable[[str, dict, Any], None]] = None,
    ) -> AgentTurn:
        """Run one full user-turn — may loop through several tool calls."""
        self.history.append(AgentMessage("user", user_input))
        start = time.time()
        cost_total = 0.0
        tool_calls: list[dict] = []

        for _ in range(self.max_steps):
            reply, cost = self._call_llm(on_token)
            cost_total += cost
            call = self._extract_tool_call(reply)

            if call is None:
                # Plain assistant answer — we're done.
                self.history.append(AgentMessage("assistant", reply))
                return AgentTurn(
                    prompt=user_input,
                    reply=reply,
                    tool_calls=tool_calls,
                    latency_ms=(time.time() - start) * 1000,
                    cost_usd=cost_total,
                )

            # Assistant wants to call a tool.
            self.history.append(AgentMessage("assistant", reply))
            tool_name = call.get("name", "")
            tool_args = call.get("args", {}) or {}
            result = self._run_tool(tool_name, tool_args)
            tool_calls.append({"name": tool_name, "args": tool_args, "result": result})
            if on_tool:
                on_tool(tool_name, tool_args, result)
            # Feed the tool output back in as a user-role message (works even
            # on providers without a native ``tool`` role).
            self.history.append(
                AgentMessage(
                    "user",
                    f"TOOL_RESULT for `{tool_name}`:\n```json\n{json.dumps(result, default=str)[:8000]}\n```",
                )
            )

        # Fell off the loop — max steps hit.
        final = "⚠️  Reached max tool-call depth. Try a narrower question."
        self.history.append(AgentMessage("assistant", final))
        return AgentTurn(
            prompt=user_input,
            reply=final,
            tool_calls=tool_calls,
            latency_ms=(time.time() - start) * 1000,
            cost_usd=cost_total,
        )

    # ------------------------------------------------------------------ #
    # Internal
    # ------------------------------------------------------------------ #
    def _call_llm(self, on_token: Optional[Callable[[str], None]]) -> tuple[str, float]:
        messages = [m.to_dict() for m in self.history]

        # ---- Auto router path: transparent multi-provider failover ----
        if self.router is not None:
            def _on_failover(err: dict):
                # Non-fatal notice in streaming/callbacks when a key burns mid-turn.
                note = f"\n[failover: {err.get('endpoint')} → next provider ({err.get('error', '')[:60]})]\n"
                if on_token:
                    try:
                        on_token(note)
                    except Exception:
                        pass

            if on_token:
                try:
                    buf: list[str] = []
                    for chunk in self.router.stream(messages, model=self.model, on_failover=_on_failover):
                        buf.append(chunk)
                        on_token(chunk)
                    return "".join(buf), 0.0
                except Exception as e:
                    # Streaming failed across all endpoints — try blocking chat as last resort.
                    pass
            res = self.router.chat(messages, model=self.model, on_failover=_on_failover)
            self.last_route = {
                "provider": res.provider,
                "endpoint": res.endpoint_label,
                "attempts": res.attempts,
                "errors": len(res.errors),
                "latency_ms": getattr(res.response, "latency_ms", 0),
            }
            return res.response.content, float(getattr(res.response, "cost_usd", 0.0) or 0.0)

        # ---- Single-provider legacy path ----
        if on_token:
            buf = []
            try:
                for chunk in self.connector.stream(
                    self.provider, messages, model=self.model
                ):
                    buf.append(chunk)
                    on_token(chunk)
                return "".join(buf), 0.0
            except Exception:
                # Fall through to blocking call if streaming isn't supported.
                pass
        resp = self.connector.chat(self.provider, messages, model=self.model)
        return resp.content, float(getattr(resp, "cost_usd", 0.0) or 0.0)

    @staticmethod
    def _extract_tool_call(text: str) -> Optional[dict]:
        m = _TOOL_RE.search(text or "")
        if not m:
            return None
        try:
            return json.loads(m.group(1))
        except json.JSONDecodeError:
            return None

    def _run_tool(self, name: str, args: dict) -> Any:
        for t in self.tools:
            if t["name"] == name:
                try:
                    return t["run"](**args)
                except TypeError as e:
                    return {"error": f"bad_arguments: {e}"}
                except Exception as e:  # pragma: no cover — surfaced to LLM
                    return {"error": f"{type(e).__name__}: {e}"}
        return {"error": f"unknown_tool: {name}"}
