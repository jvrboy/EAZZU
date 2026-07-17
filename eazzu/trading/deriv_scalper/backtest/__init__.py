"""
Backtesting Module
Historical testing engine for the trading bot
"""

from .engine import BacktestEngine, BacktestResult
from .data_generator import SyntheticDataGenerator, HistoricalDataLoader

__all__ = [
    'BacktestEngine',
    'BacktestResult',
    'SyntheticDataGenerator',
    'HistoricalDataLoader'
]
