"""
DERIV Multi-Agent Trading System - Configuration
================================================
Central configuration for all system components.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class TimeFrame(Enum):
    """Supported timeframes for analysis."""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"


class AssetClass(Enum):
    """Asset categories available on Deriv."""
    FOREX = "forex"
    CRYPTO = "crypto"
    SYNTHETIC = "synthetic"
    COMMODITY = "commodity"
    INDEX = "index"


class SignalType(Enum):
    """Types of trading signals."""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"


class ConfidenceLevel(Enum):
    """Signal confidence levels."""
    VERY_LOW = 0.1
    LOW = 0.3
    MEDIUM = 0.5
    HIGH = 0.7
    VERY_HIGH = 0.9


@dataclass
class APIConfig:
    """Deriv API configuration."""
    APP_ID: int = 1089  # Default test app ID
    ENDPOINT: str = "wss://ws.derivws.com/websockets/v3"
    REST_ENDPOINT: str = "https://api.derivws.com"
    TIMEOUT: int = 30
    RECONNECT_ATTEMPTS: int = 5
    RECONNECT_DELAY: int = 5
    PING_INTERVAL: int = 30


@dataclass
class DataConfig:
    """Data management configuration."""
    HISTORICAL_YEARS: int = 5
    BATCH_SIZE: int = 5000
    CACHE_SIZE: int = 10000
    DB_PATH: str = "./data/market_data.db"
    RAW_DATA_PATH: str = "./data/raw"
    PROCESSED_PATH: str = "./data/processed"
    UPDATE_INTERVAL: int = 1  # seconds


@dataclass
class ModelConfig:
    """Machine learning model configuration."""
    SEQUENCE_LENGTH: int = 100
    PREDICTION_HORIZON: int = 10
    TRAIN_SPLIT: float = 0.8
    VALIDATION_SPLIT: float = 0.1
    BATCH_SIZE: int = 64
    EPOCHS: int = 100
    LEARNING_RATE: float = 0.001
    DROPOUT: float = 0.2
    LSTM_UNITS: int = 128
    ATTENTION_HEADS: int = 8
    EARLY_STOPPING_PATIENCE: int = 15
    MODEL_PATH: str = "./models"
    RETRAIN_INTERVAL: int = 86400  # 24 hours


@dataclass
class SignalConfig:
    """Signal generation configuration."""
    MIN_CONFIDENCE: float = 0.65
    SIGNAL_EXPIRY: int = 300  # 5 minutes
    MAX_CONCURRENT_SIGNALS: int = 10
    COOLDOWN_PERIOD: int = 60  # 1 minute between signals
    CONFIRMATION_THRESHOLD: int = 3  # Min agents agreeing
    RISK_REWARD_MIN: float = 1.5
    STOP_LOSS_ATR: float = 2.0
    TAKE_PROFIT_ATR: float = 3.0


@dataclass
class AgentConfig:
    """Multi-agent system configuration."""
    AGENT_COUNT: int = 7
    COUNCIL_SIZE: int = 5
    VOTING_THRESHOLD: float = 0.6
    DISSENT_TOLERANCE: float = 0.3
    SPECIALIZATION_DEPTH: int = 3


@dataclass
class SystemConfig:
    """Overall system configuration."""
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    LOG_PATH: str = "./logs"
    MAX_WORKERS: int = 8
    MODE: str = "analysis"  # analysis, backtest, live
    VERSION: str = "2.0.0"


# Asset definitions for Deriv
DERIV_ASSETS: Dict[AssetClass, List[str]] = {
    AssetClass.FOREX: [
        "frxEURUSD", "frxGBPUSD", "frxUSDJPY", "frxAUDUSD",
        "frxUSDCAD", "frxUSDCHF", "frxNZDUSD", "frxEURGBP",
        "frxEURJPY", "frxGBPJPY", "frxAUDJPY", "frxEURCHF",
        "frxGBPAUD", "frxCADJPY", "frxCHFJPY", "frxEURAUD",
        "frxGBPCAD", "frxAUDCAD", "frxAUDCHF", "frxAUDNZD",
        "frxEURNZD", "frxGBPNZD", "frxGBPCHF", "frxNZDCAD",
        "frxNZDCHF", "frxNZDJPY", "frxCADCHF", "frxUSDSGD",
    ],
    AssetClass.CRYPTO: [
        "cryBTCUSD", "cryETHUSD", "cryLTCUSD", "cryUSDTUSD",
        "cryXRPUSD", "cryBCHUSD", "cryEOSUSD", "cryXLMUSD",
        "cryTRXUSD", "cryDOGUSD", "cryBNBUSD", "cryADAUSD",
        "crySOLUSD", "cryDOTUSD", "cryMATICUSD",
    ],
    AssetClass.SYNTHETIC: [
        "R_10", "R_25", "R_50", "R_75", "R_100",
        "1HZ10V", "1HZ25V", "1HZ50V", "1HZ75V", "1HZ100V",
        "JD10", "JD25", "JD50", "JD75", "JD100",
        "RDBEAR", "RDBULL", "WLDAUD", "WLDEUR", "WLDUSD",
        "BOOM1000", "CRASH1000", "BOOM500", "CRASH500",
        "BOOM300", "CRASH300", "STEPINDEX",
    ],
    AssetClass.COMMODITY: [
        "OTC_AUUSD", "OTC_AGUSD", "OTC_WTI", "OTC_BRENT",
        "OTC_COPPER", "OTC_NGUSD",
    ],
    AssetClass.INDEX: [
        "OTC_DJI", "OTC_N225", "OTC_FTSE", "OTC_GDAXI",
        "OTC_HSI", "OTC_AS51", "OTC_SPC",
    ],
}

# Timeframe granularity mapping (in seconds)
TIMEFRAME_SECONDS: Dict[TimeFrame, int] = {
    TimeFrame.M1: 60,
    TimeFrame.M5: 300,
    TimeFrame.M15: 900,
    TimeFrame.M30: 1800,
    TimeFrame.H1: 3600,
    TimeFrame.H4: 14400,
    TimeFrame.D1: 86400,
}

# Default configuration instance
CONFIG = {
    "api": APIConfig(),
    "data": DataConfig(),
    "model": ModelConfig(),
    "signal": SignalConfig(),
    "agent": AgentConfig(),
    "system": SystemConfig(),
}


def get_config(section: str):
    """Get configuration section."""
    return CONFIG.get(section)


def load_env_config():
    """Load configuration from environment variables."""
    if os.getenv("DERIV_APP_ID"):
        CONFIG["api"].APP_ID = int(os.getenv("DERIV_APP_ID"))
    if os.getenv("DERIV_DEBUG"):
        CONFIG["system"].DEBUG = os.getenv("DERIV_DEBUG").lower() == "true"
    if os.getenv("DERIV_LOG_LEVEL"):
        CONFIG["system"].LOG_LEVEL = os.getenv("DERIV_LOG_LEVEL")
