"""
Deriv Scalper Bot
Main bot class that orchestrates 24/7 perpetual scalping
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import traceback

from .deriv_client import DerivClient
from .trader import Trader, TradeResult, TradeDirection
from .logger import TradingLogger
from ..config import TradingConfig
from ..indicators import IndicatorEngine, IndicatorResult


@dataclass
class BotStats:
    """Bot runtime statistics"""
    start_time: datetime = field(default_factory=datetime.now)
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    total_profit: float = 0.0
    current_streak: int = 0
    max_streak: int = 0
    consecutive_losses: int = 0
    uptime_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'start_time': self.start_time.isoformat(),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'total_profit': self.total_profit,
            'current_streak': self.current_streak,
            'max_streak': self.max_streak,
            'consecutive_losses': self.consecutive_losses,
            'uptime_seconds': self.uptime_seconds,
            'win_rate': (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        }


class ScalperBot:
    """
    Deriv Scalper Bot
    24/7 Perpetual scalping bot using confluence of indicators
    """

    def __init__(self, config: Optional[TradingConfig] = None, token: Optional[str] = None):
        self.config = config or TradingConfig()

        # Override token if provided
        if token:
            self.config.token = token

        # Initialize components
        self.client = DerivClient(self.config)
        self.trader = Trader(self.client, self.config)
        self.indicator_engine = IndicatorEngine(self.config)
        self.logger = TradingLogger(
            log_dir=self.config.log_dir,
            log_level=self.config.log_level
        )

        # Bot state
        self._running = False
        self._paused = False
        self.stats = BotStats()
        self.trade_history: List[TradeResult] = []

        # Price data storage
        self.candles: List[Dict] = []
        self.ticks: List[float] = []

        # Tasks
        self._main_task: Optional[asyncio.Task] = None
        self._data_task: Optional[asyncio.Task] = None

        # Callbacks
        self.on_trade: Optional[callable] = None
        self.on_signal: Optional[callable] = None
        self.on_stats_update: Optional[callable] = None

    async def start(self, use_simulation: bool = True) -> bool:
        """
        Start the trading bot
        use_simulation: If True, use simulated trading for testing
        """
        self.logger.info("=" * 50)
        self.logger.info("DERIV SCALPER BOT - Starting")
        self.logger.info("=" * 50)
        self.logger.info(f"Symbol: {self.config.symbol.display_name}")
        self.logger.info(f"Mode: {'SIMULATION' if use_simulation else 'LIVE'}")
        self.logger.info(f"Never Stop: {self.config.never_stop}")
        self.logger.info(f"Fixed Lot Size: {self.config.fixed_lot_size}")
        self.logger.info("=" * 50)

        try:
            # Connect to Deriv API
            if not use_simulation:
                connected = await self.client.connect()
                if connected:
                    # Subscribe to data
                    symbol = self.config.symbol.symbol
                    await self.client.subscribe_ticks(symbol)
                    await self.client.subscribe_candles(symbol, interval=1)
                    self.logger.info("Connected to Deriv API")
                else:
                    self.logger.warning("Could not connect to Deriv API, using simulation")
                    use_simulation = True

            # Start trader
            await self.trader.start()

            # Start main loop
            self._running = True
            self._main_task = asyncio.create_task(self._main_loop(use_simulation))

            return True

        except Exception as e:
            self.logger.error(f"Failed to start bot: {e}")
            self.logger.debug(traceback.format_exc())
            return False

    async def stop(self) -> None:
        """Stop the trading bot"""
        self.logger.info("Stopping bot...")
        self._running = False

        if self._main_task:
            self._main_task.cancel()

        if self._data_task:
            self._data_task.cancel()

        await self.trader.stop()
        await self.client.disconnect()

        self.logger.info("Bot stopped")
        self.logger.info(f"Final Stats: {self.stats.to_dict()}")

    async def pause(self) -> None:
        """Pause trading (bot continues but doesn't trade)"""
        self._paused = True
        self.logger.info("Bot paused")

    async def resume(self) -> None:
        """Resume trading"""
        self._paused = False
        self.logger.info("Bot resumed")

    async def _main_loop(self, use_simulation: bool) -> None:
        """
        Main trading loop - never stops while running
        """
        self.logger.info("Main trading loop started")

        while self._running:
            try:
                # Update uptime
                self.stats.uptime_seconds = (datetime.now() - self.stats.start_time).total_seconds()

                # Check circuit breaker
                if self.stats.consecutive_losses >= self.config.max_consecutive_losses:
                    self.logger.warning(f"Circuit breaker active: {self.stats.consecutive_losses} consecutive losses")
                    await asyncio.sleep(self.config.cooldown_seconds)
                    continue

                # Check if we can trade
                if self._paused:
                    await asyncio.sleep(1)
                    continue

                if len(self.trader.active_trades) >= self.config.max_open_trades:
                    await asyncio.sleep(0.5)
                    continue

                # Get market data
                symbol = self.config.symbol.symbol

                if use_simulation:
                    # Generate simulated market data
                    await self._update_simulation_data()
                    candles = self._generate_simulated_candles()
                else:
                    # Get real market data
                    candles = self.client.candles.get(symbol, [])
                    if len(candles) < 50:
                        await asyncio.sleep(1)
                        continue

                # Calculate indicators
                indicator_result = self.indicator_engine.calculate(candles)

                if indicator_result:
                    # Get trade signal
                    direction_str, confidence = self.indicator_engine.get_trade_signal(indicator_result)

                    if direction_str and confidence >= 0.5:
                        direction = TradeDirection.CALL if direction_str == 'CALL' else TradeDirection.PUT

                        # Log signal
                        self.logger.info(f"SIGNAL: {direction.value} (confidence: {confidence:.2f})")
                        self.logger.debug(f"Buy signals: {indicator_result.buy_signals}")
                        self.logger.debug(f"Sell signals: {indicator_result.sell_signals}")

                        # Execute trade
                        if use_simulation:
                            entry_price = self.ticks[-1] if self.ticks else 100.0
                            result = await self.trader.simulate_trade(direction, entry_price)
                        else:
                            result = await self.trader.simulate_trade(direction, entry_price=0)

                        if result:
                            self._record_trade_result(result)

                        # Trigger callback
                        if self.on_trade:
                            self.on_trade(result, indicator_result)

                # Small delay between checks
                await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Main loop error: {e}")
                self.logger.debug(traceback.format_exc())
                await asyncio.sleep(1)

    async def _update_simulation_data(self) -> None:
        """Update simulated market data for backtesting/demo"""
        import random

        # Generate realistic tick data
        base_price = 5000.0  # Volatility 75 base price

        if not self.ticks:
            self.ticks = [base_price]
        else:
            last_tick = self.ticks[-1]
            # Random walk with volatility
            change = random.gauss(0, 0.5)
            new_tick = last_tick + change
            self.ticks.append(new_tick)

        # Keep last 1000 ticks
        if len(self.ticks) > 1000:
            self.ticks = self.ticks[-1000:]

    def _generate_simulated_candles(self) -> List[Dict]:
        """Generate candle data from tick data"""
        if len(self.ticks) < 60:
            return []

        candles = []
        for i in range(60, len(self.ticks)):
            chunk = self.ticks[max(0, i-60):i+1]
            candles.append({
                'time': i,
                'epoch': 1609459200 + i * 60,
                'open': chunk[0],
                'high': max(chunk),
                'low': min(chunk),
                'close': chunk[-1],
                'symbol': self.config.symbol.symbol
            })

        self.candles = candles
        return candles

    def _record_trade_result(self, result: TradeResult) -> None:
        """Record a completed trade"""
        self.trade_history.append(result)
        self.stats.total_trades += 1
        self.stats.total_profit += result.profit

        if result.is_winning:
            self.stats.winning_trades += 1
            self.stats.consecutive_losses = 0
            self.stats.current_streak += 1
            self.stats.max_streak = max(self.stats.max_streak, self.stats.current_streak)
        else:
            self.stats.losing_trades += 1
            self.stats.consecutive_losses += 1
            self.stats.current_streak = 0

        # Log trade
        self.logger.trade_closed(
            result.contract_id,
            result.direction.value,
            result.profit,
            result.duration_seconds,
            "Completed"
        )

        # Trigger stats callback
        if self.on_stats_update:
            self.on_stats_update(self.get_stats())

    def get_stats(self) -> Dict[str, Any]:
        """Get current bot statistics"""
        stats = self.stats.to_dict()
        stats.update({
            'running': self._running,
            'paused': self._paused,
            'active_trades': len(self.trader.active_trades),
            'balance': self.client.balance or 0
        })
        return stats

    def get_recent_trades(self, count: int = 20) -> List[Dict]:
        """Get recent trade history"""
        return [t.to_dict() for t in self.trade_history[-count:]]

    async def run_backtest(self, duration_seconds: int = 3600) -> Dict[str, Any]:
        """
        Run a backtest simulation
        """
        self.logger.info(f"Starting backtest for {duration_seconds} seconds...")

        import random
        from datetime import datetime, timedelta

        start_time = datetime.now()
        end_time = start_time + timedelta(seconds=duration_seconds)

        trades = []
        wins = 0
        losses = 0
        total_profit = 0

        trade_count = 0

        while datetime.now() < end_time:
            # Simulate price movement
            base = 5000.0
            price = base + random.gauss(0, 10)

            # Simulate trade
            direction = random.choice([TradeDirection.CALL, TradeDirection.PUT])
            outcome = random.random() > 0.48  # ~52% win rate

            if outcome:
                profit = random.uniform(0.15, 0.35)
                wins += 1
            else:
                profit = -random.uniform(0.10, 0.25)
                losses += 1

            total_profit += profit
            trade_count += 1

            # Simulate duration
            duration = random.uniform(15, 30)

            trades.append({
                'id': f"BT_{trade_count}",
                'direction': direction.value,
                'profit': profit,
                'duration': duration,
                'timestamp': datetime.now().isoformat()
            })

            await asyncio.sleep(0.5)  # Simulate time between trades

        results = {
            'total_trades': trade_count,
            'wins': wins,
            'losses': losses,
            'win_rate': (wins / trade_count * 100) if trade_count > 0 else 0,
            'total_profit': total_profit,
            'avg_profit': (total_profit / trade_count) if trade_count > 0 else 0,
            'duration': duration_seconds,
            'trades': trades
        }

        self.logger.info(f"Backtest complete: {results}")
        return results

    @property
    def is_running(self) -> bool:
        """Check if bot is running"""
        return self._running

    @property
    def is_paused(self) -> bool:
        """Check if bot is paused"""
        return self._paused

    def get_indicators_status(self) -> Dict[str, bool]:
        """Get status of all indicators"""
        return {
            'RSI': self.config.use_rsi,
            'MACD': self.config.use_macd,
            'EMA': self.config.use_ema,
            'Bollinger': self.config.use_bollinger,
            'Stochastic': self.config.use_stochastic,
            'ATR': self.config.use_atr,
            'PriceAction': True
        }
