"""EAZZU — Unified agentic developer + trading + AI toolkit.

Combines 25+ tools (Deriv/Forex bots, dev-toolkits, VPN/network utilities,
LLM/GGUF runners, deep-research pipelines, media utilities) behind a single
CLI (`eazzu`) and an agentic chat loop that can invoke every subsystem as a
tool. Bring-your-own API keys — nothing is hardcoded.

Public entry points:
    eazzu.Agent            — the agentic chat + tool-use loop
    eazzu.get_connector    — a Connector (80+ AI providers) with keys loaded
    eazzu.tools.REGISTRY   — the tool catalogue exposed to the agent

CLI:
    $ eazzu --help
    $ eazzu chat              # interactive agentic chat
    $ eazzu keys set openai sk-...
    $ eazzu trade backtest --symbol R_75
    $ eazzu dev analyze ./src
    $ eazzu deep-research "topic"
"""
from __future__ import annotations

__version__ = "1.0.0"
__all__ = ["Agent", "get_connector", "tools"]


def get_connector(enable_cache: bool = False, enable_tracking: bool = True):
    """Return a fully wired :class:`Connector` with all providers registered."""
    # Local imports so a broken provider file cannot poison ``import eazzu``.
    from eazzu.providers import Connector  # noqa: WPS433
    import eazzu.providers.providers  # noqa: F401 — side-effect: register all
    return Connector(enable_cache=enable_cache, enable_tracking=enable_tracking)


def __getattr__(name: str):
    # Lazy attribute access — avoids importing heavy submodules on `import eazzu`.
    if name == "Agent":
        from eazzu.agent.core import Agent  # noqa: WPS433
        return Agent
    if name == "tools":
        from eazzu import tools as _t  # noqa: WPS433
        return _t
    raise AttributeError(f"module 'eazzu' has no attribute {name!r}")
