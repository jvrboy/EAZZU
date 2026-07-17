"""
Trading Logger
Comprehensive logging for the trading bot
"""

import logging
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from logging.handlers import RotatingFileHandler


class TradingLogger:
    """
    Custom logger for trading operations
    Provides both file and console logging with structured output
    """

    def __init__(self, name: str = "DerivScalper", log_dir: str = "logs", log_level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.log_dir = Path(log_dir)
        self.log_level = getattr(logging, log_level.upper(), logging.INFO)

        # Create log directory
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Configure logger
        self._setup_logger()

        # Trading log file
        self.trade_log_file = self.log_dir / "trades.jsonl"
        self.performance_log_file = self.log_dir / "performance.jsonl"

    def _setup_logger(self) -> None:
        """Configure logging with handlers"""
        self.logger.setLevel(self.log_level)

        # Clear existing handlers
        self.logger.handlers.clear()

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.log_level)
        console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)

        # File handler
        file_handler = RotatingFileHandler(
            self.log_dir / "bot.log",
            maxBytes=5_000_000,  # 5MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)

        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)

    def log_trade(self, trade_data: Dict[str, Any]) -> None:
        """Log trade execution to JSON file"""
        try:
            with open(self.trade_log_file, 'a') as f:
                f.write(json.dumps({
                    **trade_data,
                    'timestamp': datetime.now().isoformat()
                }) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to log trade: {e}")

    def log_performance(self, stats: Dict[str, Any]) -> None:
        """Log performance metrics to JSON file"""
        try:
            with open(self.performance_log_file, 'a') as f:
                f.write(json.dumps({
                    **stats,
                    'timestamp': datetime.now().isoformat()
                }) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to log performance: {e}")

    def get_recent_trades(self, count: int = 100) -> List[Dict]:
        """Read recent trades from log file"""
        trades = []
        try:
            if self.trade_log_file.exists():
                with open(self.trade_log_file, 'r') as f:
                    lines = f.readlines()
                    for line in lines[-count:]:
                        try:
                            trades.append(json.loads(line.strip()))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            self.logger.error(f"Failed to read trades: {e}")
        return trades

    def debug(self, message: str) -> None:
        """Log debug message"""
        self.logger.debug(message)

    def info(self, message: str) -> None:
        """Log info message"""
        self.logger.info(message)

    def warning(self, message: str) -> None:
        """Log warning message"""
        self.logger.warning(message)

    def error(self, message: str) -> None:
        """Log error message"""
        self.logger.error(message)

    def critical(self, message: str) -> None:
        """Log critical message"""
        self.logger.critical(message)

    def trade_opened(self, contract_id: str, direction: str, price: float, amount: float) -> None:
        """Log trade opening"""
        self.info(f"[OPEN] {direction} | {contract_id} | Price: {price:.2f} | Amount: {amount}")
        self.log_trade({
            'event': 'opened',
            'contract_id': contract_id,
            'direction': direction,
            'price': price,
            'amount': amount
        })

    def trade_closed(self, contract_id: str, direction: str, profit: float,
                    duration: float, reason: str) -> None:
        """Log trade closing"""
        emoji = "✓" if profit > 0 else "✗"
        self.info(f"[CLOSE] {emoji} {direction} | {contract_id} | P/L: {profit:+.2f} | Duration: {duration:.1f}s | Reason: {reason}")
        self.log_trade({
            'event': 'closed',
            'contract_id': contract_id,
            'direction': direction,
            'profit': profit,
            'duration': duration,
            'reason': reason
        })

    def strategy_signal(self, direction: str, indicators: Dict[str, Any]) -> None:
        """Log strategy signal"""
        self.debug(f"[SIGNAL] {direction} | Indicators: {indicators}")
        self.log_trade({
            'event': 'signal',
            'direction': direction,
            'indicators': indicators
        })

    def error_with_context(self, message: str, context: Dict[str, Any]) -> None:
        """Log error with additional context"""
        self.error(f"{message} | Context: {json.dumps(context)}")


def get_logger(name: str = "DerivScalper", log_dir: str = "logs",
               log_level: str = "INFO") -> TradingLogger:
    """Get or create a trading logger instance"""
    return TradingLogger(name, log_dir, log_level)
