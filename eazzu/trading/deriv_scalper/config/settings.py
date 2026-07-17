"""
Trading Configuration Settings
Configures all trading parameters for the Deriv Scalper Bot
"""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from pathlib import Path


@dataclass
class APIConfig:
    """Deriv API Configuration"""
    api_endpoint: str = "wss://ws.binaryws.com/websockets/v3"
    app_id: int = 1089  # Default Deriv app ID for public API
    language: str = "en"
    timeout: int = 30
    ping_interval: int = 30
    max_retries: int = 5
    retry_delay: float = 1.0


@dataclass
class SymbolConfig:
    """Trading Symbol Configuration"""
    symbol: str = "R_75"  # Volatility 75 Index
    display_name: str = "Volatility 75 Index"
    pip_size: float = 0.01
    tick_size: float = 0.01
    min_lot_size: float = 0.35
    max_lot_size: float = 20000
    default_lot_size: float = 0.35  # Lowest accepted lot size


@dataclass
class TradingConfig:
    """Main Trading Configuration"""
    # API Settings
    api: APIConfig = field(default_factory=APIConfig)

    # Symbol Settings
    symbol: SymbolConfig = field(default_factory=SymbolConfig)

    # Trading Mode
    is_demo: bool = True  # Demo mode by default, ready for real
    token: Optional[str] = None  # Will use public API if not set

    # Trade Parameters
    trade_duration_min: int = 15  # Minimum 15 seconds
    trade_duration_max: int = 30  # Maximum 30 seconds
    profit_target_percent: float = 0.5  # Close at 0.5% profit
    loss_threshold_percent: float = 0.3  # Close at 0.3% loss

    # Risk Management
    fixed_lot_size: float = 0.35  # Lowest lot size
    max_daily_loss: float = 100.0  # Max daily loss in account currency
    max_open_trades: int = 1  # One trade at a time
    stop_loss_pips: float = 10.0  # Stop loss in pips

    # Strategy Configuration
    use_rsi: bool = True
    rsi_period: int = 14
    rsi_overbought: float = 70
    rsi_oversold: float = 30

    use_macd: bool = True
    macd_fast: int = 12
    macd_slow: int = 26
    macd_signal: int = 9

    use_ema: bool = True
    ema_fast_period: int = 9
    ema_slow_period: int = 21
    ema_trend_lookback: int = 50

    use_bollinger: bool = True
    bollinger_period: int = 20
    bollinger_std: float = 2.0

    use_stochastic: bool = True
    stochastic_k: int = 14
    stochastic_d: int = 3
    stochastic_overbought: float = 80
    stochastic_oversold: float = 20

    use_atr: bool = True
    atr_period: int = 14

    # Confluence Settings
    min_indicators_agree: int = 2  # Minimum indicators that must agree

    # Bot Behavior
    never_stop: bool = True  # Always keep trading
    log_level: str = "INFO"
    save_logs: bool = True
    log_dir: str = "logs"

    # Performance
    max_consecutive_losses: int = 10  # Circuit breaker
    cooldown_seconds: int = 5  # Cooldown between trades

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary"""
        return asdict(self)

    def save(self, filepath: str) -> None:
        """Save configuration to JSON file"""
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=4)

    @classmethod
    def load(cls, filepath: str) -> 'TradingConfig':
        """Load configuration from JSON file"""
        with open(filepath, 'r') as f:
            data = json.load(f)

        # Reconstruct nested objects
        api_config = APIConfig(**data.get('api', {}))
        symbol_config = SymbolConfig(**data.get('symbol', {}))
        data['api'] = api_config
        data['symbol'] = symbol_config

        return cls(**data)


def load_config(filepath: Optional[str] = None) -> TradingConfig:
    """Load configuration from file or return defaults"""
    if filepath and os.path.exists(filepath):
        return TradingConfig.load(filepath)
    return TradingConfig()


# Default configuration instance
default_config = TradingConfig()
