"""Bot subpackage — external bot interfaces for EAZZU."""
from eazzu.bot.telegram import run_bot, get_me, send_message

__all__ = ["run_bot", "get_me", "send_message"]
