"""Tool registry — every entry becomes a callable the agent can dispatch."""
from __future__ import annotations

from eazzu.tools import shell, files, net_tools, trade_tools, dev_tools, research_tools
from eazzu.tools import advanced_tools, agent_tools, alert_dispatcher, expanded_tools
from eazzu.tools import music_tools, web_tools, deriv_tools, image_tools
from eazzu.tools import advanced_music_tools
from eazzu.tools import mcp_tools, code_tools, artifact_tools, research_tools_v2
from eazzu.tools import memory_tools
from eazzu.tools import docs_tools, data_tools, slides_tools, notes_tools
from eazzu.tools import tasks_tools, projects_tools, diagram_tools, workflow_tools
from eazzu.tools import bi_tools, search_tools, language_tools, accessibility_tools
from eazzu.tools import media_edit_tools, media_ai_tools, media_creative_tools, media_pro_tools
from eazzu.tools import media_audio_tools, media_export_tools, media_smart_tools, media_nextgen_tools
from eazzu.tools import automation_canvas_tools, surveillance_tools, screenshot_tools, screen_record_tools
from eazzu.tools import daw_tools, three_d_tools, ai_coding_tools, local_ai_tools
from eazzu.tools import crosscut_tools, pipeline_tools, pipeline_extra_tools
from eazzu.tools import provider_registry_tools, extra_tools
from eazzu.tools import computer_tools, app_builder_tools, self_updater_tools, platform_tools

REGISTRY: list[dict] = [
    *shell.TOOLS,
    *files.TOOLS,
    *net_tools.TOOLS,
    *trade_tools.TOOLS,
    *dev_tools.TOOLS,
    *research_tools.TOOLS,
    *computer_tools.TOOLS,
    *app_builder_tools.TOOLS,
    *self_updater_tools.TOOLS,
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
    *docs_tools.TOOLS,
    *data_tools.TOOLS,
    *slides_tools.TOOLS,
    *notes_tools.TOOLS,
    *tasks_tools.TOOLS,
    *projects_tools.TOOLS,
    *diagram_tools.TOOLS,
    *workflow_tools.TOOLS,
    *bi_tools.TOOLS,
    *search_tools.TOOLS,
    *language_tools.TOOLS,
    *accessibility_tools.TOOLS,
    *media_edit_tools.TOOLS,
    *media_ai_tools.TOOLS,
    *media_creative_tools.TOOLS,
    *media_pro_tools.TOOLS,
    *media_audio_tools.TOOLS,
    *media_export_tools.TOOLS,
    *media_smart_tools.TOOLS,
    *media_nextgen_tools.TOOLS,
    *automation_canvas_tools.TOOLS,
    *surveillance_tools.TOOLS,
    *screenshot_tools.TOOLS,
    *screen_record_tools.TOOLS,
    *daw_tools.TOOLS,
    *three_d_tools.TOOLS,
    *ai_coding_tools.TOOLS,
    *local_ai_tools.TOOLS,
    *crosscut_tools.TOOLS,
    *pipeline_tools.TOOLS,
    *pipeline_extra_tools.TOOLS,
    *provider_registry_tools.TOOLS,
    *extra_tools.TOOLS,
    *platform_tools.TOOLS,
]

__all__ = ["REGISTRY"]
