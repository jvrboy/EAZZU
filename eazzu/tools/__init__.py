"""Tool registry — every entry becomes a callable the agent can dispatch."""
from __future__ import annotations

from eazzu.tools import shell, files, net_tools, trade_tools, dev_tools, research_tools
from eazzu.tools import advanced_tools, agent_tools, alert_dispatcher, expanded_tools
from eazzu.tools import music_tools, web_tools, deriv_tools, image_tools
from eazzu.tools import advanced_music_tools
from eazzu.tools import mcp_tools, code_tools, artifact_tools, research_tools_v2
from eazzu.tools import memory_tools

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
    *advanced_music_tools.TOOLS,
    *mcp_tools.TOOLS,
    *code_tools.TOOLS,
    *artifact_tools.TOOLS,
    *research_tools_v2.TOOLS,
    *memory_tools.TOOLS,
]

__all__ = ["REGISTRY"]
