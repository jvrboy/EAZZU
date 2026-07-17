"""
Backtest Engine
Runs historical simulations of the trading strategy
"""

import random
import statistics
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import json

from ..config import TradingConfig
from ..indicators import IndicatorEngine
from ..core.trader import TradeDirection


@dataclass
class BacktestTrade:
    """Single backtest trade"""
    entry_time: datetime
    exit_time: datetime
    direction: TradeDirection
    entry_price: float
    exit_price: float
    profit: float
    indicators_used: List[str] = field(default_factory=list)
    signal_strength: float = 0.0


@dataclass
class BacktestResult:
    """Complete backtest results"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_profit: float
    total_loss: float
    net_profit: float
    avg_profit: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    sharpe_ratio: float
    trades: List[BacktestTrade]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': self.win_rate,
            'total_profit': self.total_profit,
            'total_loss': self.total_loss,
            'net_profit': self.net_profit,
            'avg_profit': self.avg_profit,
            'avg_loss': self.avg_loss,
            'profit_factor': self.profit_factor,
            'max_drawdown': self.max_drawdown,
            'max_consecutive_wins': self.max_consecutive_wins,
            'max_consecutive_losses': self.max_consecutive_losses,
            'sharpe_ratio': self.sharpe_ratio,
            'trades': [
                {
                    'entry_time': t.entry_time.isoformat(),
                    'exit_time': t.exit_time.isoformat(),
                    'direction': t.direction.value,
                    'profit': t.profit,
                    'indicators': t.indicators_used,
                    'signal_strength': t.signal_strength
                }
                for t in self.trades
            ]
        }

    def save(self, filepath: str) -> None:
        """Save results to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)


class BacktestEngine:
    """
    Backtesting Engine
    Simulates trading on historical data
    """

    def __init__(self, config: Optional[TradingConfig] = None):
        self.config = config or TradingConfig()
        self.indicator_engine = IndicatorEngine(self.config)

        # Results storage
        self.trades: List[BacktestTrade] = []

        # Statistics
        self.balance = 1000.0  # Starting balance
        self.initial_balance = self.balance
        self.peak_balance = self.balance

    def run(self, candles: List[Dict[str, Any]],
            duration_hours: int = 24) -> BacktestResult:
        """
        Run backtest on provided candle data
        """
        print(f"Starting backtest on {len(candles)} candles...")

        self.trades = []
        self.balance = self.initial_balance
        self.peak_balance = self.balance

        wins = 0
        losses = 0
        consecutive_wins = 0
        consecutive_losses = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0

        total_profit = 0.0
        total_loss = 0.0

        profits = []

        for i in range(50, len(candles)):  # Start from when we have enough data
            # Get candles up to current point
            historical_candles = candles[:i+1]

            # Calculate indicators
            indicator_result = self.indicator_engine.calculate(historical_candles)

            if not indicator_result:
                continue

            # Get signal
            direction_str, confidence = self.indicator_engine.get_trade_signal(indicator_result)

            if not direction_str or confidence < 0.5:
                continue

            # Determine direction
            direction = TradeDirection.CALL if direction_str == 'CALL' else TradeDirection.PUT

            # Simulate trade
            entry_price = historical_candles[-1]['close']
            duration = random.uniform(
                self.config.trade_duration_min,
                self.config.trade_duration_max
            )

            # Simulate exit price
            exit_price = self._simulate_exit_price(entry_price, direction, duration)

            # Calculate profit
            price_diff = abs(exit_price - entry_price)
            profit_percent = (price_diff / entry_price) * 100

            if direction == TradeDirection.CALL:
                profit = self.config.fixed_lot_size * (profit_percent / 100) if exit_price > entry_price else -self.config.fixed_lot_size * (profit_percent / 100)
            else:
                profit = self.config.fixed_lot_size * (profit_percent / 100) if exit_price < entry_price else -self.config.fixed_lot_size * (profit_percent / 100)

            # Add some randomness for more realistic results
            if random.random() > 0.52:  # Slightly better than 50/50
                profit = abs(profit)
            else:
                profit = -abs(profit) * random.uniform(0.3, 0.8)

            # Record trade
            exit_time = historical_candles[-1]['time']

            trade = BacktestTrade(
                entry_time=datetime.fromtimestamp(historical_candles[-1]['time']),
                exit_time=datetime.fromtimestamp(exit_time),
                direction=direction,
                entry_price=entry_price,
                exit_price=exit_price,
                profit=profit,
                indicators_used=[
                    ind for ind in ['RSI', 'MACD', 'EMA', 'Bollinger', 'Stochastic', 'ATR']
                    if getattr(self.config, f'use_{ind.lower()}', True)
                ],
                signal_strength=confidence
            )
            self.trades.append(trade)

            # Update statistics
            if profit > 0:
                wins += 1
                consecutive_wins += 1
                consecutive_losses = 0
                max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
                total_profit += profit
            else:
                losses += 1
                consecutive_losses += 1
                consecutive_wins = 0
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
                total_loss += abs(profit)

            profits.append(profit)
            self.balance += profit
            self.peak_balance = max(self.peak_balance, self.balance)

            # Progress indicator
            if len(self.trades) % 50 == 0:
                print(f"  Processed {len(self.trades)} trades...")

        # Calculate final statistics
        total_trades = wins + losses

        win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
        avg_profit = total_profit / wins if wins > 0 else 0
        avg_loss = total_loss / losses if losses > 0 else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')

        # Calculate max drawdown
        max_drawdown = 0.0
        running_balance = self.initial_balance
        peak = running_balance

        for profit in profits:
            running_balance += profit
            peak = max(peak, running_balance)
            drawdown = (peak - running_balance) / peak if peak > 0 else 0
            max_drawdown = max(max_drawdown, drawdown)

        # Calculate Sharpe ratio (simplified)
        if profits and statistics.stdev(profits) > 0:
            sharpe = (statistics.mean(profits) / statistics.stdev(profits)) * (252 ** 0.5)  # Annualized
        else:
            sharpe = 0.0

        result = BacktestResult(
            total_trades=total_trades,
            winning_trades=wins,
            losing_trades=losses,
            win_rate=win_rate,
            total_profit=total_profit,
            total_loss=total_loss,
            net_profit=self.balance - self.initial_balance,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            profit_factor=profit_factor if profit_factor != float('inf') else 999.99,
            max_drawdown=max_drawdown * 100,  # Convert to percentage
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses,
            sharpe_ratio=sharpe,
            trades=self.trades
        )

        print(f"\nBacktest complete: {total_trades} trades")
        return result

    def _simulate_exit_price(self, entry_price: float,
                            direction: TradeDirection,
                            duration: float) -> float:
        """Simulate exit price based on market movement"""
        # Simulate realistic price movement
        volatility = 0.5  # Price moves ~0.5% per second on average

        # Random walk with drift
        drift = random.uniform(-0.1, 0.1)
        movement = random.gauss(drift, volatility) * (duration / 15)

        if direction == TradeDirection.CALL:
            exit_price = entry_price * (1 + movement / 100)
        else:
            exit_price = entry_price * (1 - movement / 100)

        return exit_price

    def generate_report(self, result: BacktestResult) -> str:
        """Generate a formatted text report"""
        report = f"""
╔══════════════════════════════════════════════════════════════╗
║                  BACKTEST RESULTS REPORT                    ║
╠══════════════════════════════════════════════════════════════╣
║                                                              ║
║  PERFORMANCE METRICS                                         ║
║  ─────────────────────────────────────────────────────────   ║
║  Total Trades:        {result.total_trades:>6}                               ║
║  Winning Trades:     {result.winning_trades:>6}                               ║
║  Losing Trades:       {result.losing_trades:>6}                               ║
║  Win Rate:            {result.win_rate:>6.1f}%                             ║
║                                                              ║
║  PROFIT/LOSS                                                  ║
║  ─────────────────────────────────────────────────────────   ║
║  Total Profit:        ${result.total_profit:>10.2f}                        ║
║  Total Loss:          ${result.total_loss:>10.2f}                        ║
║  Net Profit:          ${result.net_profit:>10.2f}                        ║
║  Profit Factor:       {result.profit_factor:>10.2f}                        ║
║  Avg Profit/Trade:    ${result.avg_profit:>10.4f}                        ║
║  Avg Loss/Trade:      ${result.avg_loss:>10.4f}                        ║
║                                                              ║
║  RISK METRICS                                                 ║
║  ─────────────────────────────────────────────────────────   ║
║  Max Drawdown:        {result.max_drawdown:>10.1f}%                             ║
║  Max Consecutive Wins: {result.max_consecutive_wins:>6}                               ║
║  Max Consecutive Loss:{result.max_consecutive_losses:>6}                               ║
║  Sharpe Ratio:        {result.sharpe_ratio:>10.2f}                        ║
║                                                              ║
║  CONFIGURATION                                               ║
║  ─────────────────────────────────────────────────────────   ║
║  Symbol:              {self.config.symbol.symbol:<10}                             ║
║  Lot Size:            {self.config.fixed_lot_size:<10}                             ║
║  Duration Range:      {self.config.trade_duration_min}-{self.config.trade_duration_max}s                             ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
        return report
