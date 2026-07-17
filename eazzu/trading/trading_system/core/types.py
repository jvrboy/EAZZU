"""
Core Data Types
===============
Type definitions used across the trading system.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum
import numpy as np


class Direction(Enum):
    """Market direction."""
    BULLISH = 1
    BEARISH = -1
    NEUTRAL = 0
    STRONG_BULLISH = 2
    STRONG_BEARISH = -2


class SignalStrength(Enum):
    """Signal strength levels."""
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    VERY_STRONG = 4
    EXTREME = 5


@dataclass
class OHLCV:
    """OHLCV candle data."""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    
    def to_array(self) -> np.ndarray:
        return np.array([self.open, self.high, self.low, self.close, self.volume])
    
    @property
    def body(self) -> float:
        return abs(self.close - self.open)
    
    @property
    def range(self) -> float:
        return self.high - self.low
    
    @property
    def is_bullish(self) -> bool:
        return self.close > self.open
    
    @property
    def is_bearish(self) -> bool:
        return self.close < self.open


@dataclass
class MarketData:
    """Complete market data for an asset."""
    symbol: str
    asset_class: str
    timeframe: str
    candles: List[OHLCV]
    current_price: float = 0.0
    bid: float = 0.0
    ask: float = 0.0
    spread: float = 0.0
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def closes(self) -> np.ndarray:
        return np.array([c.close for c in self.candles])
    
    @property
    def highs(self) -> np.ndarray:
        return np.array([c.high for c in self.candles])
    
    @property
    def lows(self) -> np.ndarray:
        return np.array([c.low for c in self.candles])
    
    @property
    def opens(self) -> np.ndarray:
        return np.array([c.open for c in self.candles])
    
    @property
    def volumes(self) -> np.ndarray:
        return np.array([c.volume for c in self.candles])
    
    @property
    def latest_candle(self) -> Optional[OHLCV]:
        return self.candles[-1] if self.candles else None


@dataclass
class TechnicalIndicators:
    """Container for all technical indicators."""
    sma_20: float = 0.0
    sma_50: float = 0.0
    sma_200: float = 0.0
    ema_12: float = 0.0
    ema_26: float = 0.0
    ema_50: float = 0.0
    ema_200: float = 0.0
    rsi_14: float = 50.0
    rsi_6: float = 50.0
    macd_line: float = 0.0
    macd_signal: float = 0.0
    macd_histogram: float = 0.0
    bb_upper: float = 0.0
    bb_middle: float = 0.0
    bb_lower: float = 0.0
    bb_width: float = 0.0
    bb_position: float = 0.5
    atr_14: float = 0.0
    atr_7: float = 0.0
    stochastic_k: float = 50.0
    stochastic_d: float = 50.0
    adx: float = 0.0
    adx_plus_di: float = 0.0
    adx_minus_di: float = 0.0
    obv: float = 0.0
    vwma: float = 0.0
    cci_20: float = 0.0
    williams_r: float = -50.0
    momentum_10: float = 0.0
    roc_12: float = 0.0
    mfi_14: float = 50.0
    psar: float = 0.0
    psar_trend: str = "neutral"
    ichimoku_tenkan: float = 0.0
    ichimoku_kijun: float = 0.0
    ichimoku_senkou_a: float = 0.0
    ichimoku_senkou_b: float = 0.0
    ichimoku_chikou: float = 0.0
    fib_236: float = 0.0
    fib_382: float = 0.0
    fib_500: float = 0.0
    fib_618: float = 0.0
    fib_786: float = 0.0
    pivot_point: float = 0.0
    pivot_r1: float = 0.0
    pivot_r2: float = 0.0
    pivot_r3: float = 0.0
    pivot_s1: float = 0.0
    pivot_s2: float = 0.0
    pivot_s3: float = 0.0
    volume_sma: float = 0.0
    volume_ratio: float = 1.0
    trend_strength: float = 0.0
    volatility: float = 0.0


@dataclass
class AgentVote:
    """Vote from a single agent."""
    agent_name: str
    agent_type: str
    direction: Direction
    confidence: float
    reasoning: str = ""
    indicators_used: List[str] = field(default_factory=list)
    weight: float = 1.0


@dataclass
class CouncilDecision:
    """Final decision from the council."""
    timestamp: datetime
    symbol: str
    timeframe: str
    direction: Direction
    confidence: float
    consensus_ratio: float
    votes: List[AgentVote]
    strategy: str = ""
    risk_level: str = "medium"


@dataclass
class TradingSignal:
    """Complete trading signal."""
    id: str
    timestamp: datetime
    symbol: str
    asset_class: str
    timeframe: str
    signal_type: str  # BUY, SELL, STRONG_BUY, STRONG_SELL
    direction: Direction
    entry_price: float
    stop_loss: float
    take_profit: float
    confidence: float
    strength: SignalStrength
    risk_reward_ratio: float
    expected_pips: float
    timeframe_minutes: int
    indicators: Dict[str, Any] = field(default_factory=dict)
    agent_votes: List[AgentVote] = field(default_factory=list)
    council_decision: Optional[CouncilDecision] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    expiry: Optional[datetime] = None
    status: str = "active"  # active, expired, triggered, cancelled
    
    @property
    def is_active(self) -> bool:
        if self.expiry:
            return datetime.now() < self.expiry and self.status == "active"
        return self.status == "active"


@dataclass
class BacktestResult:
    """Backtest performance results."""
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_return: float = 0.0
    max_drawdown: float = 0.0
    sharpe_ratio: float = 0.0
    avg_trade: float = 0.0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    avg_holding_time: float = 0.0
    expectancy: float = 0.0
    calmar_ratio: float = 0.0
    sortino_ratio: float = 0.0


@dataclass
class MarketRegime:
    """Detected market regime."""
    regime: str  # trending_up, trending_down, ranging, volatile, breakout
    confidence: float
    volatility_regime: str  # low, normal, high, extreme
    trend_strength: float
    cycle_position: str  # early, mid, late, reversal
    support_levels: List[float] = field(default_factory=list)
    resistance_levels: List[float] = field(default_factory=list)
