"""EAZZU — Unified agentic developer + trading + AI + MCP toolkit.

Combines 90+ tools (Deriv/Forex bots, dev-toolkits, VPN/network utilities,
LLM/GGUF runners, deep-research pipelines, media utilities, MCP servers,
code runner, artifacts, Telegram bot, plus a full productivity suite:
document authoring, spreadsheets & analytics, presentations, notes,
tasks, project management, diagramming, workflow automation, BI,
search, language, and accessibility) behind a single CLI (`eazzu`) and
an agentic chat loop that can invoke every subsystem as a tool.
Bring-your-own API keys — nothing is hardcoded.

Public entry points:
    eazzu.Agent            — the agentic chat + tool-use loop
    eazzu.get_connector    — a Connector (80+ AI providers) with keys loaded
    eazzu.tools.REGISTRY   — the tool catalogue exposed to the agent
    eazzu.mcp              — MCP client framework (HuggingFace, TradingView, MT5)
    eazzu.bot              — Telegram bot interface

CLI:
    $ eazzu --help
    $ eazzu chat              # interactive agentic chat
    $ eazzu loop "task"       # autonomous loop until task complete
    $ eazzu mcp list          # list MCP servers
    $ eazzu code eval "..."   # run Python code
    $ eazzu telegram          # start Telegram bot
"""
from __future__ import annotations

__version__ = "1.5.0"
__all__ = ["Agent", "get_connector", "tools"]


def get_connector(enable_cache: bool = False, enable_tracking: bool = True):
    """Return a fully wired :class:`Connector` with all providers registered."""
    from eazzu.providers import Connector  # noqa: WPS433
    import eazzu.providers.providers  # noqa: F401 — side-effect: register all
    return Connector(enable_cache=enable_cache, enable_tracking=enable_tracking)


def __getattr__(name: str):
    if name == "Agent":
        from eazzu.agent.core import Agent  # noqa: WPS433
        return Agent
    if name == "tools":
        from eazzu import tools as _t  # noqa: WPS433
        return _t
    raise AttributeError(f"module 'eazzu' has no attribute {name!r}")
