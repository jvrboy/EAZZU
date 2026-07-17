"""
Helper Functions
Common utility functions used throughout the bot
"""

import re
from typing import Any, Dict, Optional
from datetime import datetime, timedelta


def format_currency(amount: float, currency: str = "USD") -> str:
    """Format amount as currency string"""
    symbols = {
        'USD': '$',
        'EUR': '€',
        'GBP': '£',
        'JPY': '¥'
    }
    symbol = symbols.get(currency, '$')
    return f"{symbol}{amount:,.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format value as percentage string"""
    return f"{value:.{decimals}f}%"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def parse_duration(duration_str: str) -> Optional[int]:
    """
    Parse duration string to seconds
    Examples: '30s', '5m', '1h', '1d'
    """
    if not duration_str:
        return None

    duration_str = duration_str.lower().strip()

    # Try to match pattern
    match = re.match(r'^(\d+)(s|m|h|d)?$', duration_str)
    if not match:
        return None

    value = int(match.group(1))
    unit = match.group(2) or 's'

    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400
    }

    return value * multipliers.get(unit, 1)


def validate_config(config: Any) -> Dict[str, Any]:
    """
    Validate trading configuration
    Returns dict of validation errors (empty if valid)
    """
    errors = {}

    # Check required numeric fields
    numeric_fields = [
        ('fixed_lot_size', 0.01, 100000),
        ('profit_target_percent', 0.01, 100),
        ('loss_threshold_percent', 0.01, 100),
        ('max_consecutive_losses', 1, 100)
    ]

    for field, min_val, max_val in numeric_fields:
        value = getattr(config, field, None)
        if value is None:
            errors[field] = "Missing required field"
        elif not isinstance(value, (int, float)):
            errors[field] = "Must be a number"
        elif value < min_val or value > max_val:
            errors[field] = f"Must be between {min_val} and {max_val}"

    # Check boolean fields
    bool_fields = ['never_stop', 'use_rsi', 'use_macd', 'use_ema']

    for field in bool_fields:
        value = getattr(config, field, None)
        if value is not None and not isinstance(value, bool):
            errors[field] = "Must be a boolean"

    return errors


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe file system usage
    """
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '', filename)

    # Replace spaces with underscores
    filename = filename.replace(' ', '_')

    # Limit length
    if len(filename) > 255:
        filename = filename[:255]

    return filename


def calculate_position_size(balance: float,
                           risk_percent: float,
                           stop_loss_pips: float,
                           pip_value: float = 0.01) -> float:
    """
    Calculate position size based on risk parameters
    """
    if stop_loss_pips <= 0:
        return 0

    risk_amount = balance * (risk_percent / 100)
    position_size = risk_amount / (stop_loss_pips * pip_value)

    return round(position_size, 2)


def get_timestamp() -> str:
    """Get current timestamp string"""
    return datetime.now().isoformat()


def get_date_string() -> str:
    """Get current date string"""
    return datetime.now().strftime('%Y-%m-%d')


def get_time_string() -> str:
    """Get current time string"""
    return datetime.now().strftime('%H:%M:%S')


def format_datetime(dt: datetime) -> str:
    """Format datetime for display"""
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def format_time_ago(dt: datetime) -> str:
    """Format datetime as 'time ago' string"""
    now = datetime.now()
    diff = now - dt

    if diff.total_seconds() < 60:
        return "just now"
    elif diff.total_seconds() < 3600:
        minutes = int(diff.total_seconds() / 60)
        return f"{minutes}m ago"
    elif diff.total_seconds() < 86400:
        hours = int(diff.total_seconds() / 3600)
        return f"{hours}h ago"
    else:
        days = int(diff.total_seconds() / 86400)
        return f"{days}d ago"
