"""
Backtesting Engine
==================
Comprehensive backtesting framework for strategy validation.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from core.logger import system_logger
from core.types import (
    TradingSignal, BacktestResult, MarketData, 
    OHLCV, Direction, SignalStrength
)


class Backtester:
    """
    Walk-forward backtesting engine.
    Simulates trading with realistic execution and accounting.
    """
    
    def __init__(
        self,
        initial_balance: float = 10000.0,
        risk_per_trade: float = 0.02,  # 2% risk per trade
        spread: float = 0.0001,  # Default spread
        commission: float = 0.0
    ):
        self.initial_balance = initial_balance
        self.risk_per_trade = risk_per_trade
        self.spread = spread
        self.commission = commission
        
        self.balance = initial_balance
        self.equity_curve = []
        self.trades = []
        self.signals_tested = 0
        
        system_logger.info(
            f"Backtester initialized | Balance: ${initial_balance:,.2f} | "
            f"Risk: {risk_per_trade:.0%} per trade"
        )
    
    def run_walk_forward(
        self,
        market_data: MarketData,
        signal_generator_func,
        train_size: int = 1000,
        step_size: int = 100
    ) -> BacktestResult:
        """
        Run walk-forward backtest.
        
        Args:
            market_data: Full historical market data
            signal_generator_func: Function that generates signals from market data
            train_size: Initial training window size
            step_size: How many candles to step forward each iteration
        """
        candles = market_data.candles
        n = len(candles)
        
        if n < train_size + step_size:
            system_logger.warning("Insufficient data for backtest")
            return BacktestResult()
        
        self.balance = self.initial_balance
        self.equity_curve = [(candles[train_size].timestamp, self.initial_balance)]
        self.trades = []
        
        # Walk forward
        for i in range(train_size, n - step_size, step_size):
            # Use data up to current point
            train_data = MarketData(
                symbol=market_data.symbol,
                asset_class=market_data.asset_class,
                timeframe=market_data.timeframe,
                candles=candles[:i]
            )
            
            # Generate signals
            try:
                signals = signal_generator_func(train_data)
                if not signals:
                    continue
                
                for signal in signals:
                    self.signals_tested += 1
                    
                    # Simulate trade outcome using future data
                    result = self._simulate_trade(signal, candles[i:i+step_size])
                    
                    if result:
                        self.trades.append(result)
                        self.balance += result['pnl']
            except Exception as e:
                system_logger.debug(f"Backtest iteration error: {e}")
                continue
            
            # Record equity
            self.equity_curve.append((candles[min(i+step_size-1, n-1)].timestamp, self.balance))
        
        # Calculate results
        return self._calculate_results()
    
    def _simulate_trade(
        self,
        signal: TradingSignal,
        future_candles: List[OHLCV]
    ) -> Optional[Dict]:
        """
        Simulate a single trade.
        
        Returns trade result with P&L.
        """
        if not future_candles:
            return None
        
        entry = signal.entry_price
        sl = signal.stop_loss
        tp = signal.take_profit
        is_buy = 'BUY' in signal.signal_type
        
        # Apply spread
        if is_buy:
            entry += self.spread
        else:
            entry -= self.spread
        
        # Calculate position size based on risk
        risk_amount = self.balance * self.risk_per_trade
        sl_distance = abs(entry - sl)
        
        if sl_distance == 0:
            return None
        
        position_size = risk_amount / sl_distance
        
        # Simulate price movement
        for candle in future_candles:
            if is_buy:
                # Check SL
                if candle.low <= sl:
                    pnl = -risk_amount
                    return {
                        'signal': signal,
                        'entry': entry,
                        'exit': sl,
                        'pnl': pnl,
                        'pnl_pct': pnl / self.balance * 100,
                        'result': 'loss',
                        'hold_time': len(future_candles),
                        'timestamp': candle.timestamp
                    }
                # Check TP
                if candle.high >= tp:
                    pnl = abs(tp - entry) * position_size
                    return {
                        'signal': signal,
                        'entry': entry,
                        'exit': tp,
                        'pnl': pnl,
                        'pnl_pct': pnl / self.balance * 100,
                        'result': 'win',
                        'hold_time': len(future_candles),
                        'timestamp': candle.timestamp
                    }
            else:
                # Sell - SL is above, TP is below
                if candle.high >= sl:
                    pnl = -risk_amount
                    return {
                        'signal': signal,
                        'entry': entry,
                        'exit': sl,
                        'pnl': pnl,
                        'pnl_pct': pnl / self.balance * 100,
                        'result': 'loss',
                        'hold_time': len(future_candles),
                        'timestamp': candle.timestamp
                    }
                if candle.low <= tp:
                    pnl = abs(entry - tp) * position_size
                    return {
                        'signal': signal,
                        'entry': entry,
                        'exit': tp,
                        'pnl': pnl,
                        'pnl_pct': pnl / self.balance * 100,
                        'result': 'win',
                        'hold_time': len(future_candles),
                        'timestamp': candle.timestamp
                    }
        
        # Trade didn't hit SL or TP - close at last price
        last_price = future_candles[-1].close
        if is_buy:
            pnl = (last_price - entry) * position_size
        else:
            pnl = (entry - last_price) * position_size
        
        return {
            'signal': signal,
            'entry': entry,
            'exit': last_price,
            'pnl': pnl,
            'pnl_pct': pnl / self.balance * 100,
            'result': 'win' if pnl > 0 else 'loss',
            'hold_time': len(future_candles),
            'timestamp': future_candles[-1].timestamp
        }
    
    def _calculate_results(self) -> BacktestResult:
        """Calculate backtest performance metrics."""
        if not self.trades:
            return BacktestResult()
        
        wins = [t for t in self.trades if t['result'] == 'win']
        losses = [t for t in self.trades if t['result'] == 'loss']
        
        n_total = len(self.trades)
        n_wins = len(wins)
        n_losses = len(losses)
        
        win_rate = n_wins / n_total if n_total > 0 else 0
        
        total_pnl = sum(t['pnl'] for t in self.trades)
        gross_profit = sum(t['pnl'] for t in wins) if wins else 0
        gross_loss = abs(sum(t['pnl'] for t in losses)) if losses else 0
        
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        total_return = (self.balance - self.initial_balance) / self.initial_balance * 100
        
        # Calculate max drawdown
        peak = self.initial_balance
        max_dd = 0
        for _, equity in self.equity_curve:
            if equity > peak:
                peak = equity
            dd = (peak - equity) / peak
            max_dd = max(max_dd, dd)
        
        # Calculate Sharpe ratio
        returns = [t['pnl_pct'] for t in self.trades]
        if len(returns) > 1:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            sharpe = (avg_return / std_return * np.sqrt(252)) if std_return > 0 else 0
        else:
            sharpe = 0
        
        avg_trade = total_pnl / n_total if n_total > 0 else 0
        avg_win = np.mean([t['pnl'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['pnl'] for t in losses]) if losses else 0
        
        largest_win = max([t['pnl'] for t in wins]) if wins else 0
        largest_loss = min([t['pnl'] for t in losses]) if losses else 0
        
        # Consecutive wins/losses
        max_consec_wins = 0
        max_consec_losses = 0
        current_wins = 0
        current_losses = 0
        
        for t in self.trades:
            if t['result'] == 'win':
                current_wins += 1
                current_losses = 0
                max_consec_wins = max(max_consec_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_consec_losses = max(max_consec_losses, current_losses)
        
        avg_hold_time = np.mean([t['hold_time'] for t in self.trades])
        
        # Expectancy
        expectancy = (win_rate * avg_win + (1 - win_rate) * avg_loss) if n_total > 0 else 0
        
        # Calmar ratio
        calmar = (total_return / 100) / max_dd if max_dd > 0 else 0
        
        # Sortino ratio
        negative_returns = [r for r in returns if r < 0]
        downside_std = np.std(negative_returns) if negative_returns else 0
        sortino = (np.mean(returns) / downside_std * np.sqrt(252)) if downside_std > 0 else 0
        
        result = BacktestResult(
            total_trades=n_total,
            winning_trades=n_wins,
            losing_trades=n_losses,
            win_rate=win_rate,
            profit_factor=profit_factor,
            total_return=total_return,
            max_drawdown=max_dd,
            sharpe_ratio=sharpe,
            avg_trade=avg_trade,
            avg_win=avg_win,
            avg_loss=avg_loss,
            largest_win=largest_win,
            largest_loss=largest_loss,
            consecutive_wins=max_consec_wins,
            consecutive_losses=max_consec_losses,
            avg_holding_time=avg_hold_time,
            expectancy=expectancy,
            calmar_ratio=calmar,
            sortino_ratio=sortino
        )
        
        system_logger.info(
            f"Backtest complete | Trades: {n_total} | "
            f"Win rate: {win_rate:.1%} | Return: {total_return:.2f}% | "
            f"Max DD: {max_dd:.1%} | Sharpe: {sharpe:.2f}"
        )
        
        return result
    
    def get_equity_curve(self) -> List[Tuple[datetime, float]]:
        """Get equity curve for plotting."""
        return self.equity_curve
    
    def get_trade_report(self) -> pd.DataFrame:
        """Get detailed trade report as DataFrame."""
        if not self.trades:
            return pd.DataFrame()
        
        data = []
        for t in self.trades:
            s = t['signal']
            data.append({
                'timestamp': t['timestamp'],
                'type': s.signal_type,
                'symbol': s.symbol,
                'timeframe': s.timeframe,
                'entry': t['entry'],
                'exit': t['exit'],
                'pnl': t['pnl'],
                'pnl_pct': t['pnl_pct'],
                'result': t['result'],
                'confidence': s.confidence,
                'r_r_ratio': s.risk_reward_ratio
            })
        
        return pd.DataFrame(data)
    
    def print_report(self):
        """Print formatted backtest report."""
        result = self._calculate_results()
        
        print("\n" + "="*60)
        print("  BACKTEST RESULTS")
        print("="*60)
        print(f"  Total Trades:       {result.total_trades}")
        print(f"  Winning Trades:     {result.winning_trades} ({result.win_rate:.1%})")
        print(f"  Losing Trades:      {result.losing_trades}")
        print(f"  Profit Factor:      {result.profit_factor:.2f}")
        print(f"  Total Return:       {result.total_return:.2f}%")
        print(f"  Max Drawdown:       {result.max_drawdown:.2%}")
        print(f"  Sharpe Ratio:       {result.sharpe_ratio:.2f}")
        print(f"  Sortino Ratio:      {result.sortino_ratio:.2f}")
        print(f"  Calmar Ratio:       {result.calmar_ratio:.2f}")
        print(f"  Average Trade:      ${result.avg_trade:.2f}")
        print(f"  Average Win:        ${result.avg_win:.2f}")
        print(f"  Average Loss:       ${result.avg_loss:.2f}")
        print(f"  Largest Win:        ${result.largest_win:.2f}")
        print(f"  Largest Loss:       ${result.largest_loss:.2f}")
        print(f"  Expectancy:         ${result.expectancy:.2f}")
        print(f"  Max Consec. Wins:   {result.consecutive_wins}")
        print(f"  Max Consec. Losses: {result.consecutive_losses}")
        print("="*60 + "\n")
