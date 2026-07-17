"""
Deriv Scalper Bot - Core Module
Core trading functionality for 24/7 perpetual scalping
"""

from .deriv_client import DerivClient, ConnectionState
from .trader import Trader, TradeResult, TradeDirection
from .bot import ScalperBot
from .logger import TradingLogger, get_logger

__all__ = [
    'DerivClient',
    'ConnectionState',
    'Trader',
    'TradeResult',
    'TradeDirection',
    'ScalperBot',
    'TradingLogger',
    'get_logger'
]
