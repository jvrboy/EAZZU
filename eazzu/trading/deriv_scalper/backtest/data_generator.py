"""
Data Generator
Generates synthetic market data for backtesting
"""

import random
from typing import List, Dict, Any
from datetime import datetime, timedelta


class SyntheticDataGenerator:
    """
    Generates synthetic OHLC candle data
    Simulates realistic volatility index behavior
    """

    def __init__(self,
                 base_price: float = 5000.0,
                 volatility: float = 0.5,
                 seed: int = None):
        self.base_price = base_price
        self.volatility = volatility
        self.current_price = base_price

        if seed:
            random.seed(seed)

    def generate_candles(self,
                        count: int = 1000,
                        interval_seconds: int = 60) -> List[Dict[str, Any]]:
        """
        Generate synthetic candle data
        count: Number of candles to generate
        interval_seconds: Time interval between candles
        """
        candles = []
        base_time = datetime.now() - timedelta(seconds=count * interval_seconds)

        for i in range(count):
            # Generate OHLC values
            open_price = self.current_price

            # Simulate price movement
            change = random.gauss(0, self.volatility)

            # Add some trend and mean reversion
            trend = (self.base_price - self.current_price) * 0.001
            change += trend

            high_price = open_price * (1 + abs(change) / 100 + random.uniform(0, 0.2))
            low_price = open_price * (1 - abs(change) / 100 - random.uniform(0, 0.2))

            close_price = open_price * (1 + change / 100)

            # Ensure OHLC relationships are valid
            high_price = max(open_price, close_price, high_price)
            low_price = min(open_price, close_price, low_price)

            self.current_price = close_price

            # Create candle
            candle = {
                'time': base_time + timedelta(seconds=i * interval_seconds),
                'epoch': (base_time + timedelta(seconds=i * interval_seconds)).timestamp(),
                'open': round(open_price, 2),
                'high': round(high_price, 2),
                'low': round(low_price, 2),
                'close': round(close_price, 2),
                'symbol': 'R_75'
            }
            candles.append(candle)

        return candles

    def generate_ticks(self, count: int = 1000) -> List[Dict[str, Any]]:
        """Generate synthetic tick data"""
        ticks = []
        base_time = datetime.now()

        for i in range(count):
            change = random.gauss(0, self.volatility / 10)
            self.current_price *= (1 + change / 100)

            tick = {
                'time': base_time + timedelta(milliseconds=i * 100),
                'epoch': (base_time + timedelta(milliseconds=i * 100)).timestamp(),
                'bid': round(self.current_price - random.uniform(0.01, 0.05), 2),
                'ask': round(self.current_price + random.uniform(0.01, 0.05), 2),
                'last': round(self.current_price, 2),
                'symbol': 'R_75'
            }
            ticks.append(tick)

        return ticks


class HistoricalDataLoader:
    """
    Load historical data from various sources
    """

    def __init__(self):
        self.data = []

    def load_from_csv(self, filepath: str) -> List[Dict[str, Any]]:
        """Load OHLC data from CSV file"""
        import csv

        candles = []
        with open(filepath, 'r') as f:
            reader = csv.DictReader(f)

            for row in reader:
                candle = {
                    'time': datetime.fromisoformat(row['time']),
                    'epoch': float(row.get('epoch', 0)),
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'symbol': row.get('symbol', 'UNKNOWN')
                }
                candles.append(candle)

        self.data = candles
        return candles

    def load_synthetic(self, **kwargs) -> List[Dict[str, Any]]:
        """Load synthetic data"""
        generator = SyntheticDataGenerator(**kwargs)
        self.data = generator.generate_candles()
        return self.data

    def get_data(self) -> List[Dict[str, Any]]:
        """Get loaded data"""
        return self.data
