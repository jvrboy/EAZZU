"""
GUI Module
Tkinter-based graphical user interface for the trading bot
"""

from .dashboard import TradingDashboard
from .widgets import (
    StatsPanel,
    TradeHistoryPanel,
    ChartPanel,
    ControlPanel,
    LogPanel
)

__all__ = [
    'TradingDashboard',
    'StatsPanel',
    'TradeHistoryPanel',
    'ChartPanel',
    'ControlPanel',
    'LogPanel'
]
