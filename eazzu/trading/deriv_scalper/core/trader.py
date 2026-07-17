"""
Trading Engine
Handles trade execution and management
"""

import asyncio
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
import traceback

from .deriv_client import DerivClient
from ..config import TradingConfig


class TradeDirection(Enum):
    """Trade direction"""
    CALL = "CALL"  # Price will go up
    PUT = "PUT"    # Price will go down


@dataclass
class TradeResult:
    """Result of a completed trade"""
    contract_id: str
    direction: TradeDirection
    entry_price: float
    exit_price: float
    profit: float
    entry_time: datetime
    exit_time: datetime
    duration_seconds: float
    symbol: str
    amount: float
    success: bool
    error_message: Optional[str] = None

    @property
    def profit_percent(self) -> float:
        """Calculate profit percentage"""
        if self.entry_price == 0:
            return 0
        return (self.profit / self.amount) * 100

    @property
    def is_winning(self) -> bool:
        """Check if trade was profitable"""
        return self.profit > 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'contract_id': self.contract_id,
            'direction': self.direction.value,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'profit': self.profit,
            'entry_time': self.entry_time.isoformat(),
            'exit_time': self.exit_time.isoformat(),
            'duration_seconds': self.duration_seconds,
            'symbol': self.symbol,
            'amount': self.amount,
            'success': self.success,
            'profit_percent': self.profit_percent,
            'is_winning': self.is_winning,
            'error_message': self.error_message
        }


@dataclass
class ActiveTrade:
    """Active trade being managed"""
    contract_id: str
    direction: TradeDirection
    symbol: str
    amount: float
    entry_time: datetime
    duration: int
    entry_price: float
    proposal_id: Optional[str] = None
    target_profit: float = 0
    stop_loss: float = 0
    candle_data: List[Dict] = field(default_factory=list)
    tick_count: int = 0
    peak_profit: float = 0
    current_loss: float = 0


class Trader:
    """
    Trading Engine
    Manages trade execution, monitoring, and settlement
    """

    def __init__(self, client: DerivClient, config: Optional[TradingConfig] = None):
        self.client = client
        self.config = config or TradingConfig()
        self.logger = logging.getLogger(__name__)

        # Active trades
        self.active_trades: Dict[str, ActiveTrade] = {}
        self.trade_history: List[TradeResult] = []

        # Statistics
        self.stats = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_profit': 0,
            'consecutive_losses': 0,
            'max_consecutive_losses': 0
        }

        # Internal state
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._trade_count = 0

    async def start(self) -> None:
        """Start the trading engine"""
        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_trades())
        self.logger.info("Trading engine started")

    async def stop(self) -> None:
        """Stop the trading engine"""
        self._running = False

        # Close all active trades
        for contract_id in list(self.active_trades.keys()):
            await self.close_trade(contract_id, reason="Bot stopped")

        if self._monitor_task:
            self._monitor_task.cancel()

        self.logger.info("Trading engine stopped")

    async def execute_trade(self, direction: TradeDirection,
                           duration: Optional[int] = None,
                           amount: Optional[float] = None) -> Optional[ActiveTrade]:
        """
        Execute a new trade
        Returns ActiveTrade if successful
        """
        if len(self.active_trades) >= self.config.max_open_trades:
            self.logger.warning("Maximum open trades reached")
            return None

        symbol = self.config.symbol.symbol
        duration = duration or self.config.trade_duration_min
        amount = amount or self.config.fixed_lot_size

        self.logger.info(f"Executing {direction.value} trade on {symbol}, duration={duration}s, amount={amount}")

        try:
            # Get proposal
            proposal = await self.client.proposal(
                symbol=symbol,
                contract_type=direction.value,
                duration=duration,
                duration_type='s',
                amount=amount
            )

            if not proposal:
                self.logger.error("Failed to get proposal")
                return None

            proposal_id = proposal.get('id')
            if not proposal_id:
                self.logger.error("No proposal ID returned")
                return None

            # Buy the contract
            buy_response = await self.client.buy(proposal_id, price=amount)

            # Create active trade
            trade = ActiveTrade(
                contract_id=buy_response.get('contract_id', f"sim_{self._trade_count}") if buy_response else f"sim_{self._trade_count}",
                direction=direction,
                symbol=symbol,
                amount=amount,
                entry_time=datetime.now(),
                duration=duration,
                entry_price=float(proposal.get('ask_price', 0)),
                proposal_id=proposal_id,
                target_profit=amount * (self.config.profit_target_percent / 100),
                stop_loss=amount * (self.config.loss_threshold_percent / 100)
            )

            self.active_trades[trade.contract_id] = trade
            self._trade_count += 1

            self.logger.info(f"Trade opened: {trade.contract_id}, entry={trade.entry_price}")
            return trade

        except Exception as e:
            self.logger.error(f"Trade execution failed: {e}")
            self.logger.debug(traceback.format_exc())
            return None

    async def simulate_trade(self, direction: TradeDirection,
                            entry_price: float) -> Optional[TradeResult]:
        """
        Simulate a trade for testing/demo purposes
        """
        symbol = self.config.symbol.symbol
        amount = self.config.fixed_lot_size
        duration = self.config.trade_duration_min

        self.logger.info(f"Simulating {direction.value} trade on {symbol}, entry={entry_price}")

        contract_id = f"sim_{self._trade_count}"
        entry_time = datetime.now()

        # Simulate price movement
        await asyncio.sleep(duration / 10)  # Faster simulation

        # Get current price
        exit_price = self.client.get_latest_price(symbol) or entry_price

        # Simulate outcome based on direction and price movement
        if direction == TradeDirection.CALL:
            price_change = exit_price - entry_price
        else:
            price_change = entry_price - exit_price

        # Calculate profit (simplified)
        profit_multiplier = price_change / entry_price * 100
        profit = amount * profit_multiplier if profit_multiplier > 0 else -amount * abs(profit_multiplier)

        # Add some randomness for realism
        import random
        if random.random() > 0.55:  # ~45% win rate for realistic volatility
            profit = abs(profit)
        else:
            profit = -abs(profit) * 0.5

        exit_time = datetime.now()

        result = TradeResult(
            contract_id=contract_id,
            direction=direction,
            entry_price=entry_price,
            exit_price=exit_price,
            profit=profit,
            entry_time=entry_time,
            exit_time=exit_time,
            duration_seconds=(exit_time - entry_time).total_seconds(),
            symbol=symbol,
            amount=amount,
            success=True
        )

        self._trade_count += 1
        self._record_result(result)

        return result

    async def close_trade(self, contract_id: str,
                         reason: str = "Manual close",
                         profit: float = 0) -> Optional[TradeResult]:
        """
        Close an active trade
        """
        if contract_id not in self.active_trades:
            self.logger.warning(f"Trade {contract_id} not found")
            return None

        trade = self.active_trades[contract_id]
        exit_time = datetime.now()

        # Calculate actual profit from contract
        try:
            await self.client.sell(contract_id)
        except Exception as e:
            self.logger.warning(f"Could not sell contract: {e}")

        # Create trade result
        result = TradeResult(
            contract_id=contract_id,
            direction=trade.direction,
            entry_price=trade.entry_price,
            exit_price=self.client.get_latest_price(trade.symbol) or trade.entry_price,
            profit=profit,
            entry_time=trade.entry_time,
            exit_time=exit_time,
            duration_seconds=(exit_time - trade.entry_time).total_seconds(),
            symbol=trade.symbol,
            amount=trade.amount,
            success=True
        )

        # Remove from active trades
        del self.active_trades[contract_id]

        # Record result
        self._record_result(result)

        self.logger.info(f"Trade closed: {contract_id}, profit={profit:.2f}, reason={reason}")
        return result

    def _record_result(self, result: TradeResult) -> None:
        """Record trade result and update statistics"""
        self.trade_history.append(result)
        self.stats['total_trades'] += 1

        if result.is_winning:
            self.stats['winning_trades'] += 1
            self.stats['consecutive_losses'] = 0
        else:
            self.stats['losing_trades'] += 1
            self.stats['consecutive_losses'] += 1
            self.stats['max_consecutive_losses'] = max(
                self.stats['max_consecutive_losses'],
                self.stats['consecutive_losses']
            )

        self.stats['total_profit'] += result.profit

    async def _monitor_trades(self) -> None:
        """Monitor active trades and close when conditions met"""
        while self._running:
            try:
                await asyncio.sleep(1)  # Check every second

                for contract_id, trade in list(self.active_trades.items()):
                    trade.tick_count += 1
                    elapsed = (datetime.now() - trade.entry_time).total_seconds()

                    # Check if duration exceeded
                    if elapsed >= trade.duration:
                        await self.close_trade(contract_id, reason="Duration exceeded")
                        continue

                    # Get current price
                    current_price = self.client.get_latest_price(trade.symbol)
                    if not current_price:
                        continue

                    # Calculate P&L
                    if trade.direction == TradeDirection.CALL:
                        pnl = (current_price - trade.entry_price) / trade.entry_price * trade.amount * 100
                    else:
                        pnl = (trade.entry_price - current_price) / trade.entry_price * trade.amount * 100

                    # Track peak profit
                    if pnl > trade.peak_profit:
                        trade.peak_profit = pnl

                    # Check profit target
                    if pnl >= trade.target_profit:
                        self.logger.info(f"Profit target reached: {pnl:.2f}")
                        await self.close_trade(contract_id, reason="Profit target", profit=pnl)
                        continue

                    # Check stop loss
                    if pnl <= -trade.stop_loss:
                        self.logger.info(f"Stop loss hit: {pnl:.2f}")
                        await self.close_trade(contract_id, reason="Stop loss", profit=pnl)
                        continue

                    # Check circuit breaker
                    if self.stats['consecutive_losses'] >= self.config.max_consecutive_losses:
                        self.logger.warning("Circuit breaker: max consecutive losses reached")
                        await self.close_trade(contract_id, reason="Circuit breaker", profit=pnl)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Monitor error: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get trading statistics"""
        win_rate = (self.stats['winning_trades'] / self.stats['total_trades'] * 100
                   if self.stats['total_trades'] > 0 else 0)

        return {
            **self.stats,
            'win_rate': win_rate,
            'active_trades': len(self.active_trades),
            'total_trades': self.stats['total_trades']
        }

    def get_recent_trades(self, count: int = 10) -> List[TradeResult]:
        """Get recent trade history"""
        return self.trade_history[-count:]

    @property
    def is_circuit_breaker_active(self) -> bool:
        """Check if circuit breaker is active"""
        return self.stats['consecutive_losses'] >= self.config.max_consecutive_losses
