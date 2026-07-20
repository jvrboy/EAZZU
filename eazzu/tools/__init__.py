"""Tool registry — every entry becomes a callable the agent can dispatch."""
from __future__ import annotations

from eazzu.tools import shell, files, net_tools, trade_tools, dev_tools, research_tools
from eazzu.tools import advanced_tools, agent_tools, alert_dispatcher, expanded_tools
from eazzu.tools import music_tools, web_tools, deriv_tools, image_tools

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
    *music_tools.TOOLS,
    *web_tools.TOOLS,
    *deriv_tools.TOOLS,
    *image_tools.TOOLS,
]

__all__ = ["REGISTRY"]
