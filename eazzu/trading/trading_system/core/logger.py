"""
Logging System
==============
Centralized logging for all components.
"""

import logging
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import colorama
from colorama import Fore, Style

colorama.init()


class ColoredFormatter(logging.Formatter):
    """Colored log formatter for terminal output."""
    
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.MAGENTA + Style.BRIGHT,
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, '')
        reset = Style.RESET_ALL
        record.levelname = f"{color}{record.levelname}{reset}"
        record.msg = f"{color}{record.msg}{reset}"
        return super().format(record)


def setup_logger(
    name: str,
    level: str = "INFO",
    log_file: Optional[str] = None,
    colored: bool = True
) -> logging.Logger:
    """Setup a logger with file and console handlers."""
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    logger.handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    
    if colored:
        console_format = ColoredFormatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%H:%M:%S'
        )
    else:
        console_format = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
    
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)
    
    # File handler
    if log_file:
        Path(log_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    
    return logger


class SignalLogger:
    """Specialized logger for trading signals."""
    
    def __init__(self, log_dir: str = "./logs/signals"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.signals_file = self.log_dir / f"signals_{datetime.now().strftime('%Y%m%d')}.log"
        self.logger = setup_logger("signals", "INFO", str(self.signals_file), colored=False)
    
    def log_signal(self, signal_data: dict):
        """Log a trading signal with full details."""
        timestamp = datetime.now().isoformat()
        self.logger.info(
            f"SIGNAL | {timestamp} | "
            f"Symbol: {signal_data.get('symbol')} | "
            f"Type: {signal_data.get('signal_type')} | "
            f"Confidence: {signal_data.get('confidence', 0):.2%} | "
            f"Entry: {signal_data.get('entry_price')} | "
            f"SL: {signal_data.get('stop_loss')} | "
            f"TP: {signal_data.get('take_profit')} | "
            f"TF: {signal_data.get('timeframe')} | "
            f"Agents: {signal_data.get('agreeing_agents')}/{signal_data.get('total_agents')}"
        )


class PerformanceLogger:
    """Logger for system performance metrics."""
    
    def __init__(self, log_dir: str = "./logs/performance"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.perf_file = self.log_dir / f"perf_{datetime.now().strftime('%Y%m%d')}.log"
        self.logger = setup_logger("performance", "INFO", str(self.perf_file), colored=False)
    
    def log_metric(self, metric_name: str, value: float, details: dict = None):
        """Log a performance metric."""
        timestamp = datetime.now().isoformat()
        details_str = " | ".join([f"{k}: {v}" for k, v in (details or {}).items()])
        self.logger.info(f"METRIC | {timestamp} | {metric_name}: {value:.4f} | {details_str}")


# Global loggers
system_logger = setup_logger("system", "INFO", "./logs/system.log")
api_logger = setup_logger("api", "INFO", "./logs/api.log")
data_logger = setup_logger("data", "INFO", "./logs/data.log")
model_logger = setup_logger("model", "INFO", "./logs/model.log")
agent_logger = setup_logger("agent", "INFO", "./logs/agent.log")
signal_logger = SignalLogger()
perf_logger = PerformanceLogger()
