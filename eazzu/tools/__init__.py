"""Tool registry — every entry becomes a callable the agent can dispatch.

Adding a new tool = append a dict to :data:`REGISTRY` with keys
``name``, ``description``, ``params`` (docs only, for the model), and
``run`` (any callable returning a JSON-serialisable result).
"""
from __future__ import annotations

from eazzu.tools import shell, files, net_tools, trade_tools, dev_tools, research_tools
from eazzu.tools import advanced_tools, agent_tools, alert_dispatcher, expanded_tools

REGISTRY: list[dict] = [
    *shell.TOOLS,
    *files.TOOLS,
    *net_tools.TOOLS,
    *trade_tools.TOOLS,
    *dev_tools.TOOLS,
    *research_tools.TOOLS,
    *advanced_tools.TOOLS,
    *agent_tools.TOOLS,
    *alert_dispatcher.TOOLS,
    *expanded_tools.TOOLS,
]

__all__ = ["REGISTRY"]
