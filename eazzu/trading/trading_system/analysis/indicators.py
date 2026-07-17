"""
Technical Analysis Engine
==========================
50+ technical indicators for comprehensive market analysis.
"""

import numpy as np
import pandas as pd
from typing import List, Optional, Tuple, Dict
from dataclasses import dataclass
from scipy import stats
from scipy.signal import argrelextrema
import warnings

from core.types import OHLCV, TechnicalIndicators, MarketData
from core.logger import system_logger

warnings.filterwarnings('ignore')


class TechnicalAnalyzer:
    """
    Comprehensive technical analysis with 50+ indicators.
    """
    
    def __init__(self):
        system_logger.info("TechnicalAnalyzer initialized")
    
    def analyze(self, market_data: MarketData) -> TechnicalIndicators:
        """
        Compute all technical indicators for given market data.
        """
        closes = market_data.closes
        highs = market_data.highs
        lows = market_data.lows
        opens = market_data.opens
        volumes = market_data.volumes
        
        if len(closes) < 200:
            system_logger.warning(f"Insufficient data: {len(closes)} candles")
            return TechnicalIndicators()
        
        ti = TechnicalIndicators()
        
        # === Trend Indicators ===
        ti.sma_20 = self.sma(closes, 20)
        ti.sma_50 = self.sma(closes, 50)
        ti.sma_200 = self.sma(closes, 200)
        
        ti.ema_12 = self.ema(closes, 12)
        ti.ema_26 = self.ema(closes, 26)
        ti.ema_50 = self.ema(closes, 50)
        ti.ema_200 = self.ema(closes, 200)
        
        # === Momentum Indicators ===
        ti.rsi_14 = self.rsi(closes, 14)
        ti.rsi_6 = self.rsi(closes, 6)
        
        macd_result = self.macd(closes)
        ti.macd_line = macd_result[0]
        ti.macd_signal = macd_result[1]
        ti.macd_histogram = macd_result[2]
        
        ti.stochastic_k, ti.stochastic_d = self.stochastic(highs, lows, closes)
        ti.cci_20 = self.cci(highs, lows, closes, 20)
        ti.williams_r = self.williams_r(highs, lows, closes)
        ti.momentum_10 = self.momentum(closes, 10)
        ti.roc_12 = self.roc(closes, 12)
        ti.mfi_14 = self.mfi(highs, lows, closes, volumes)
        
        # === Volatility Indicators ===
        bb_result = self.bollinger_bands(closes)
        ti.bb_upper = bb_result[0]
        ti.bb_middle = bb_result[1]
        ti.bb_lower = bb_result[2]
        ti.bb_width = bb_result[3]
        ti.bb_position = bb_result[4]
        
        ti.atr_14 = self.atr(highs, lows, closes, 14)
        ti.atr_7 = self.atr(highs, lows, closes, 7)
        
        # === Trend Strength ===
        adx_result = self.adx(highs, lows, closes)
        ti.adx = adx_result[0]
        ti.adx_plus_di = adx_result[1]
        ti.adx_minus_di = adx_result[2]
        
        # === Volume Indicators ===
        ti.obv = self.obv(closes, volumes)
        ti.vwma = self.vwma(closes, volumes, 20)
        ti.volume_sma = self.sma(volumes, 20) if len(volumes) >= 20 else np.mean(volumes)
        ti.volume_ratio = volumes[-1] / ti.volume_sma if ti.volume_sma > 0 else 1.0
        
        # === Pattern Recognition ===
        ti.psar, ti.psar_trend = self.parabolic_sar(highs, lows)
        
        ichimoku = self.ichimoku(highs, lows)
        ti.ichimoku_tenkan = ichimoku[0]
        ti.ichimoku_kijun = ichimoku[1]
        ti.ichimoku_senkou_a = ichimoku[2]
        ti.ichimoku_senkou_b = ichimoku[3]
        ti.ichimoku_chikou = ichimoku[4]
        
        # === Fibonacci Levels ===
        fibs = self.fibonacci_retracement(highs, lows)
        ti.fib_236 = fibs[0]
        ti.fib_382 = fibs[1]
        ti.fib_500 = fibs[2]
        ti.fib_618 = fibs[3]
        ti.fib_786 = fibs[4]
        
        # === Pivot Points ===
        pivots = self.pivot_points(highs, lows, closes)
        ti.pivot_point = pivots[0]
        ti.pivot_r1 = pivots[1]
        ti.pivot_r2 = pivots[2]
        ti.pivot_r3 = pivots[3]
        ti.pivot_s1 = pivots[4]
        ti.pivot_s2 = pivots[5]
        ti.pivot_s3 = pivots[6]
        
        # === Computed Metrics ===
        ti.trend_strength = self._compute_trend_strength(closes, ti)
        ti.volatility = ti.atr_14 / closes[-1] if closes[-1] > 0 else 0
        
        return ti
    
    # === Moving Averages ===
    
    @staticmethod
    def sma(data: np.ndarray, period: int) -> float:
        """Simple Moving Average."""
        if len(data) < period:
            return float(data[-1]) if len(data) > 0 else 0.0
        return float(np.mean(data[-period:]))
    
    @staticmethod
    def ema(data: np.ndarray, period: int) -> float:
        """Exponential Moving Average."""
        if len(data) < period:
            return float(data[-1]) if len(data) > 0 else 0.0
        alpha = 2.0 / (period + 1)
        ema_vals = np.zeros_like(data)
        ema_vals[0] = data[0]
        for i in range(1, len(data)):
            ema_vals[i] = alpha * data[i] + (1 - alpha) * ema_vals[i - 1]
        return float(ema_vals[-1])
    
    @staticmethod
    def wma(data: np.ndarray, period: int) -> float:
        """Weighted Moving Average."""
        if len(data) < period:
            return float(data[-1]) if len(data) > 0 else 0.0
        weights = np.arange(1, period + 1)
        return float(np.dot(data[-period:], weights) / weights.sum())
    
    @staticmethod
    def vwma(closes: np.ndarray, volumes: np.ndarray, period: int) -> float:
        """Volume Weighted Moving Average."""
        if len(closes) < period or len(volumes) < period:
            return float(closes[-1]) if len(closes) > 0 else 0.0
        return float(np.sum(closes[-period:] * volumes[-period:]) / np.sum(volumes[-period:]))
    
    @staticmethod
    def hull_ma(data: np.ndarray, period: int) -> float:
        """Hull Moving Average."""
        if len(data) < period:
            return float(data[-1]) if len(data) > 0 else 0.0
        half_period = period // 2
        sqrt_period = int(np.sqrt(period))
        
        # WMA of half period
        weights_half = np.arange(1, half_period + 1)
        wma_half = np.dot(data[-half_period:], weights_half) / weights_half.sum()
        
        # WMA of full period
        weights_full = np.arange(1, period + 1)
        wma_full = np.dot(data[-period:], weights_full) / weights_full.sum()
        
        raw_hma = 2 * wma_half - wma_full
        # WMA of sqrt period on raw_hma
        # Simplified: return raw_hma
        return float(raw_hma)
    
    # === Momentum Indicators ===
    
    @staticmethod
    def rsi(data: np.ndarray, period: int = 14) -> float:
        """Relative Strength Index."""
        if len(data) < period + 1:
            return 50.0
        deltas = np.diff(data)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)
        
        avg_gain = np.mean(gains[-period:])
        avg_loss = np.mean(losses[-period:])
        
        if avg_loss == 0:
            return 100.0 if avg_gain > 0 else 50.0
        
        rs = avg_gain / avg_loss
        return float(100 - (100 / (1 + rs)))
    
    @staticmethod
    def macd(data: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[float, float, float]:
        """MACD indicator."""
        if len(data) < slow:
            return 0.0, 0.0, 0.0
        
        ema_fast = pd.Series(data).ewm(span=fast, adjust=False).mean()
        ema_slow = pd.Series(data).ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        
        return float(macd_line.iloc[-1]), float(signal_line.iloc[-1]), float(histogram.iloc[-1])
    
    @staticmethod
    def stochastic(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, 
                   k_period: int = 14, d_period: int = 3) -> Tuple[float, float]:
        """Stochastic Oscillator."""
        if len(closes) < k_period:
            return 50.0, 50.0
        
        lowest_low = np.min(lows[-k_period:])
        highest_high = np.max(highs[-k_period:])
        
        if highest_high == lowest_low:
            return 50.0, 50.0
        
        k = 100 * (closes[-1] - lowest_low) / (highest_high - lowest_low)
        
        # %D is SMA of %K
        k_values = []
        for i in range(d_period):
            if len(closes) >= k_period + i:
                ll = np.min(lows[-(k_period+i):-i if i > 0 else None])
                hh = np.max(highs[-(k_period+i):-i if i > 0 else None])
                if hh != ll:
                    k_val = 100 * (closes[-(1+i)] - ll) / (hh - ll)
                    k_values.append(k_val)
        
        d = np.mean(k_values) if k_values else k
        return float(k), float(d)
    
    @staticmethod
    def cci(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 20) -> float:
        """Commodity Channel Index."""
        if len(closes) < period:
            return 0.0
        
        tp = (highs + lows + closes) / 3
        sma_tp = np.mean(tp[-period:])
        mean_dev = np.mean(np.abs(tp[-period:] - sma_tp))
        
        if mean_dev == 0:
            return 0.0
        
        return float((tp[-1] - sma_tp) / (0.015 * mean_dev))
    
    @staticmethod
    def williams_r(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """Williams %R."""
        if len(closes) < period:
            return -50.0
        
        highest_high = np.max(highs[-period:])
        lowest_low = np.min(lows[-period:])
        
        if highest_high == lowest_low:
            return -50.0
        
        return float(-100 * (highest_high - closes[-1]) / (highest_high - lowest_low))
    
    @staticmethod
    def momentum(data: np.ndarray, period: int = 10) -> float:
        """Momentum indicator."""
        if len(data) < period:
            return 0.0
        return float(data[-1] - data[-period])
    
    @staticmethod
    def roc(data: np.ndarray, period: int = 12) -> float:
        """Rate of Change."""
        if len(data) < period or data[-period] == 0:
            return 0.0
        return float((data[-1] - data[-period]) / data[-period] * 100)
    
    @staticmethod
    def mfi(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, 
            volumes: np.ndarray, period: int = 14) -> float:
        """Money Flow Index."""
        if len(closes) < period + 1:
            return 50.0
        
        tp = (highs + lows + closes) / 3
        raw_money_flow = tp * volumes
        
        money_flow_ratio = 0
        positive_flow = 0
        negative_flow = 0
        
        for i in range(1, period + 1):
            if len(tp) >= i + 1:
                if tp[-i] > tp[-(i+1)]:
                    positive_flow += raw_money_flow[-i]
                else:
                    negative_flow += raw_money_flow[-i]
        
        if negative_flow == 0:
            return 100.0
        
        money_flow_ratio = positive_flow / negative_flow
        return float(100 - (100 / (1 + money_flow_ratio)))
    
    # === Volatility Indicators ===
    
    @staticmethod
    def bollinger_bands(data: np.ndarray, period: int = 20, std_dev: float = 2.0) -> Tuple[float, float, float, float, float]:
        """Bollinger Bands."""
        if len(data) < period:
            last = float(data[-1]) if len(data) > 0 else 0.0
            return last, last, last, 0.0, 0.5
        
        middle = np.mean(data[-period:])
        std = np.std(data[-period:])
        
        upper = middle + std_dev * std
        lower = middle - std_dev * std
        width = (upper - lower) / middle if middle != 0 else 0
        
        # %B position
        if upper == lower:
            position = 0.5
        else:
            position = (data[-1] - lower) / (upper - lower)
        
        return float(upper), float(middle), float(lower), float(width), float(position)
    
    @staticmethod
    def atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
        """Average True Range."""
        if len(closes) < 2:
            return 0.0
        
        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        
        if len(tr) < period:
            return float(np.mean(tr))
        
        return float(np.mean(tr[-period:]))
    
    @staticmethod
    def keltner_channels(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, 
                         period: int = 20, atr_period: int = 10, multiplier: float = 2.0) -> Tuple[float, float, float]:
        """Keltner Channels."""
        ema_val = pd.Series(closes).ewm(span=period, adjust=False).mean().iloc[-1]
        atr_val = TechnicalAnalyzer.atr(highs, lows, closes, atr_period)
        
        upper = ema_val + multiplier * atr_val
        lower = ema_val - multiplier * atr_val
        
        return float(upper), float(ema_val), float(lower)
    
    @staticmethod
    def donchian_channels(highs: np.ndarray, lows: np.ndarray, period: int = 20) -> Tuple[float, float, float]:
        """Donchian Channels."""
        upper = np.max(highs[-period:])
        lower = np.min(lows[-period:])
        middle = (upper + lower) / 2
        return float(upper), float(middle), float(lower)
    
    # === Trend Strength ===
    
    @staticmethod
    def adx(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> Tuple[float, float, float]:
        """Average Directional Index."""
        if len(closes) < period + 1:
            return 0.0, 0.0, 0.0
        
        # True Range
        tr1 = highs[1:] - lows[1:]
        tr2 = np.abs(highs[1:] - closes[:-1])
        tr3 = np.abs(lows[1:] - closes[:-1])
        tr = np.maximum(np.maximum(tr1, tr2), tr3)
        
        # +DM and -DM
        plus_dm = np.where(
            (highs[1:] - highs[:-1]) > (lows[:-1] - lows[1:]),
            np.maximum(highs[1:] - highs[:-1], 0),
            0
        )
        minus_dm = np.where(
            (lows[:-1] - lows[1:]) > (highs[1:] - highs[:-1]),
            np.maximum(lows[:-1] - lows[1:], 0),
            0
        )
        
        # Smooth
        atr_val = np.mean(tr[-period:])
        plus_di = 100 * np.mean(plus_dm[-period:]) / atr_val if atr_val > 0 else 0
        minus_di = 100 * np.mean(minus_dm[-period:]) / atr_val if atr_val > 0 else 0
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
        adx_val = dx  # Simplified
        
        return float(adx_val), float(plus_di), float(minus_di)
    
    # === Volume Indicators ===
    
    @staticmethod
    def obv(closes: np.ndarray, volumes: np.ndarray) -> float:
        """On-Balance Volume."""
        if len(closes) < 2:
            return 0.0
        
        obv_vals = [volumes[0]]
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                obv_vals.append(obv_vals[-1] + volumes[i])
            elif closes[i] < closes[i-1]:
                obv_vals.append(obv_vals[-1] - volumes[i])
            else:
                obv_vals.append(obv_vals[-1])
        
        return float(obv_vals[-1])
    
    @staticmethod
    def vwap(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray) -> float:
        """Volume Weighted Average Price."""
        tp = (highs + lows + closes) / 3
        return float(np.sum(tp * volumes) / np.sum(volumes))
    
    @staticmethod
    def chaikin_oscillator(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, 
                           volumes: np.ndarray, fast: int = 3, slow: int = 10) -> float:
        """Chaikin Oscillator."""
        if len(closes) < slow + 1:
            return 0.0
        
        adl = []
        for i in range(len(closes)):
            money_flow_multiplier = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / (highs[i] - lows[i]) if highs[i] != lows[i] else 0
            adl.append(money_flow_multiplier * volumes[i])
        
        adl_series = pd.Series(adl).cumsum()
        adl_ema_fast = adl_series.ewm(span=fast, adjust=False).mean()
        adl_ema_slow = adl_series.ewm(span=slow, adjust=False).mean()
        
        return float(adl_ema_fast.iloc[-1] - adl_ema_slow.iloc[-1])
    
    # === Pattern Recognition ===
    
    @staticmethod
    def parabolic_sar(highs: np.ndarray, lows: np.ndarray, af: float = 0.02, max_af: float = 0.2) -> Tuple[float, str]:
        """Parabolic SAR."""
        if len(highs) < 2:
            return lows[-1] if len(lows) > 0 else 0.0, "neutral"
        
        # Simplified calculation - use last values
        if len(highs) >= 5:
            trend = "bullish" if highs[-1] > highs[-5] else "bearish"
        else:
            trend = "bullish" if highs[-1] > highs[0] else "bearish"
        
        if trend == "bullish":
            psar_val = np.min(lows[-5:]) if len(lows) >= 5 else lows[0]
        else:
            psar_val = np.max(highs[-5:]) if len(highs) >= 5 else highs[0]
        
        return float(psar_val), trend
    
    @staticmethod
    def ichimoku(highs: np.ndarray, lows: np.ndarray, tenkan_period: int = 9, 
                 kijun_period: int = 26, senkou_b_period: int = 52) -> Tuple[float, float, float, float, float]:
        """Ichimoku Cloud."""
        tenkan = (np.max(highs[-tenkan_period:]) + np.min(lows[-tenkan_period:])) / 2 if len(highs) >= tenkan_period else 0
        kijun = (np.max(highs[-kijun_period:]) + np.min(lows[-kijun_period:])) / 2 if len(highs) >= kijun_period else 0
        senkou_a = (tenkan + kijun) / 2
        senkou_b = (np.max(highs[-senkou_b_period:]) + np.min(lows[-senkou_b_period:])) / 2 if len(highs) >= senkou_b_period else 0
        chikou = closes[-1] if len(closes) > kijun_period else 0
        
        return float(tenkan), float(kijun), float(senkou_a), float(senkou_b), float(chikou)
    
    @staticmethod
    def fibonacci_retracement(highs: np.ndarray, lows: np.ndarray) -> Tuple[float, float, float, float, float]:
        """Fibonacci Retracement Levels."""
        high = np.max(highs[-100:])
        low = np.min(lows[-100:])
        diff = high - low
        
        fib_236 = high - 0.236 * diff
        fib_382 = high - 0.382 * diff
        fib_500 = high - 0.500 * diff
        fib_618 = high - 0.618 * diff
        fib_786 = high - 0.786 * diff
        
        return float(fib_236), float(fib_382), float(fib_500), float(fib_618), float(fib_786)
    
    @staticmethod
    def pivot_points(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray) -> Tuple[float, float, float, float, float, float, float]:
        """Pivot Points."""
        if len(closes) < 2:
            last_close = closes[-1] if len(closes) > 0 else 0
            return last_close, last_close, last_close, last_close, last_close, last_close, last_close
        
        high = highs[-2]
        low = lows[-2]
        close = closes[-2]
        
        pivot = (high + low + close) / 3
        r1 = 2 * pivot - low
        r2 = pivot + (high - low)
        r3 = high + 2 * (pivot - low)
        s1 = 2 * pivot - high
        s2 = pivot - (high - low)
        s3 = low - 2 * (high - pivot)
        
        return float(pivot), float(r1), float(r2), float(r3), float(s1), float(s2), float(s3)
    
    # === Advanced Indicators ===
    
    @staticmethod
    def detect_support_resistance(data: np.ndarray, order: int = 5) -> Tuple[List[float], List[float]]:
        """Detect support and resistance levels using local extrema."""
        if len(data) < order * 2 + 1:
            return [float(data[-1])], [float(data[-1])]
        
        # Local minima (support)
        local_min_idx = argrelextrema(data, np.less, order=order)[0]
        support_levels = sorted(set([float(data[i]) for i in local_min_idx[-10:]]))
        
        # Local maxima (resistance)
        local_max_idx = argrelextrema(data, np.greater, order=order)[0]
        resistance_levels = sorted(set([float(data[i]) for i in local_max_idx[-10:]]))
        
        return support_levels, resistance_levels
    
    @staticmethod
    def trend_line(data: np.ndarray, period: int = 20) -> Tuple[float, float]:
        """Calculate trend line (slope and intercept)."""
        if len(data) < 2:
            return 0.0, float(data[-1]) if len(data) > 0 else 0.0
        
        x = np.arange(len(data[-period:]))
        y = data[-period:]
        
        slope, intercept, _, _, _ = stats.linregress(x, y)
        return float(slope), float(intercept)
    
    @staticmethod
    def calculate_all_indicators_df(df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all indicators and add to DataFrame."""
        df = df.copy()
        
        # Moving Averages
        for period in [10, 20, 50, 100, 200]:
            df[f'SMA_{period}'] = df['close'].rolling(window=period).mean()
            df[f'EMA_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI_14'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema_12 = df['close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema_12 - ema_26
        df['MACD_signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['MACD_hist'] = df['MACD'] - df['MACD_signal']
        
        # Bollinger Bands
        df['BB_middle'] = df['close'].rolling(window=20).mean()
        bb_std = df['close'].rolling(window=20).std()
        df['BB_upper'] = df['BB_middle'] + (bb_std * 2)
        df['BB_lower'] = df['BB_middle'] - (bb_std * 2)
        df['BB_width'] = (df['BB_upper'] - df['BB_lower']) / df['BB_middle']
        df['BB_position'] = (df['close'] - df['BB_lower']) / (df['BB_upper'] - df['BB_lower'])
        
        # ATR
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        df['ATR_14'] = tr.rolling(window=14).mean()
        
        # Stochastic
        low_14 = df['low'].rolling(window=14).min()
        high_14 = df['high'].rolling(window=14).max()
        df['Stoch_K'] = 100 * (df['close'] - low_14) / (high_14 - low_14)
        df['Stoch_D'] = df['Stoch_K'].rolling(window=3).mean()
        
        # ADX
        plus_dm = df['high'].diff()
        minus_dm = df['low'].diff(-1).abs()
        df['ADX'] = pd.Series(np.where(plus_dm > minus_dm, plus_dm, 0)).rolling(14).mean()
        
        # OBV
        obv = [0]
        for i in range(1, len(df)):
            if df['close'].iloc[i] > df['close'].iloc[i-1]:
                obv.append(obv[-1] + df['volume'].iloc[i])
            elif df['close'].iloc[i] < df['close'].iloc[i-1]:
                obv.append(obv[-1] - df['volume'].iloc[i])
            else:
                obv.append(obv[-1])
        df['OBV'] = obv[:len(df)]
        
        # VWAP
        tp = (df['high'] + df['low'] + df['close']) / 3
        df['VWAP'] = (tp * df['volume']).cumsum() / df['volume'].cumsum()
        
        # CCI
        tp_sma = tp.rolling(window=20).mean()
        tp_md = tp.rolling(window=20).apply(lambda x: np.mean(np.abs(x - np.mean(x))))
        df['CCI'] = (tp - tp_sma) / (0.015 * tp_md)
        
        # Williams %R
        df['Williams_R'] = -100 * (high_14 - df['close']) / (high_14 - low_14)
        
        # Momentum
        df['Momentum'] = df['close'] - df['close'].shift(10)
        
        return df
    
    def _compute_trend_strength(self, closes: np.ndarray, ti: TechnicalIndicators) -> float:
        """Compute overall trend strength score."""
        score = 0.0
        
        # Moving average alignment
        if closes[-1] > ti.sma_20 > ti.sma_50 > ti.sma_200:
            score += 0.4
        elif closes[-1] < ti.sma_20 < ti.sma_50 < ti.sma_200:
            score -= 0.4
        
        # MACD
        if ti.macd_histogram > 0 and ti.macd_line > ti.macd_signal:
            score += 0.2
        elif ti.macd_histogram < 0 and ti.macd_line < ti.macd_signal:
            score -= 0.2
        
        # ADX
        if ti.adx > 25:
            score *= 1.2  # Strengthen signal in trending markets
        
        # RSI direction
        if ti.rsi_14 > 60:
            score += 0.1
        elif ti.rsi_14 < 40:
            score -= 0.1
        
        return np.clip(score, -1.0, 1.0)


class PatternDetector:
    """
    Candlestick pattern and chart pattern detection.
    """
    
    PATTERNS = {
        # Bullish patterns
        'hammer': 'bullish',
        'inverse_hammer': 'bullish',
        'bullish_engulfing': 'bullish',
        'piercing_line': 'bullish',
        'morning_star': 'bullish',
        'three_white_soldiers': 'bullish',
        'bullish_harami': 'bullish',
        'tweezer_bottom': 'bullish',
        # Bearish patterns
        'hanging_man': 'bearish',
        'shooting_star': 'bearish',
        'bearish_engulfing': 'bearish',
        'evening_star': 'bearish',
        'three_black_crows': 'bearish',
        'dark_cloud_cover': 'bearish',
        'bearish_harami': 'bearish',
        'tweezer_top': 'bearish',
        # Neutral
        'doji': 'neutral',
        'spinning_top': 'neutral',
    }
    
    def detect_patterns(self, ohlcv_list: List[OHLCV]) -> Dict[str, float]:
        """
        Detect all candlestick patterns in recent data.
        Returns dict of pattern name -> confidence score.
        """
        if len(ohlcv_list) < 5:
            return {}
        
        patterns = {}
        c = ohlcv_list
        
        # Single candle patterns (using last candle)
        last = c[-1]
        
        # Doji
        if last.body < last.range * 0.1 and last.range > 0:
            patterns['doji'] = 0.8
        
        # Hammer
        if last.is_bullish:
            lower_shadow = last.open - last.low
            upper_shadow = last.high - last.close
            if lower_shadow > last.body * 2 and upper_shadow < last.body * 0.5:
                patterns['hammer'] = 0.75
        
        # Hanging Man
        if last.is_bearish:
            lower_shadow = last.close - last.low
            upper_shadow = last.high - last.open
            if lower_shadow > last.body * 2 and upper_shadow < last.body * 0.5:
                patterns['hanging_man'] = 0.75
        
        # Shooting Star
        if last.is_bearish:
            upper_shadow = last.open - last.high if last.open > last.close else last.close - last.high
            lower_shadow = last.low - last.close if last.open > last.close else last.low - last.open
            if upper_shadow > last.body * 2 and lower_shadow < last.body * 0.5:
                patterns['shooting_star'] = 0.75
        
        # Spinning Top
        if last.range > 0:
            body_ratio = last.body / last.range
            if 0.2 < body_ratio < 0.5:
                patterns['spinning_top'] = 0.6
        
        # Two candle patterns
        if len(c) >= 2:
            prev, curr = c[-2], c[-1]
            
            # Bullish Engulfing
            if prev.is_bearish and curr.is_bullish:
                if curr.open < prev.close and curr.close > prev.open:
                    patterns['bullish_engulfing'] = 0.85
            
            # Bearish Engulfing
            if prev.is_bullish and curr.is_bearish:
                if curr.open > prev.close and curr.close < prev.open:
                    patterns['bearish_engulfing'] = 0.85
            
            # Bullish Harami
            if prev.is_bearish and curr.is_bullish:
                if curr.open > prev.close and curr.close < prev.open:
                    patterns['bullish_harami'] = 0.7
            
            # Bearish Harami
            if prev.is_bullish and curr.is_bearish:
                if curr.open < prev.close and curr.close > prev.open:
                    patterns['bearish_harami'] = 0.7
            
            # Tweezer patterns
            if abs(prev.low - curr.low) < prev.range * 0.1:
                patterns['tweezer_bottom'] = 0.65
            if abs(prev.high - curr.high) < prev.range * 0.1:
                patterns['tweezer_top'] = 0.65
        
        # Three candle patterns
        if len(c) >= 3:
            c1, c2, c3 = c[-3], c[-2], c[-1]
            
            # Morning Star
            if c1.is_bearish and c2.body < c1.body * 0.3 and c3.is_bullish:
                patterns['morning_star'] = 0.9
            
            # Evening Star
            if c1.is_bullish and c2.body < c1.body * 0.3 and c3.is_bearish:
                patterns['evening_star'] = 0.9
            
            # Three White Soldiers
            if c1.is_bullish and c2.is_bullish and c3.is_bullish:
                if c3.close > c2.close > c1.close:
                    patterns['three_white_soldiers'] = 0.85
            
            # Three Black Crows
            if c1.is_bearish and c2.is_bearish and c3.is_bearish:
                if c3.close < c2.close < c1.close:
                    patterns['three_black_crows'] = 0.85
            
            # Dark Cloud Cover
            if c1.is_bullish and c2.is_bearish:
                if c2.open > c1.high and c2.close < (c1.open + c1.close) / 2:
                    patterns['dark_cloud_cover'] = 0.8
            
            # Piercing Line
            if c1.is_bearish and c2.is_bullish:
                if c2.open < c1.low and c2.close > (c1.open + c1.close) / 2:
                    patterns['piercing_line'] = 0.8
        
        return patterns
    
    def get_pattern_bias(self, patterns: Dict[str, float]) -> float:
        """
        Calculate overall pattern bias.
        Returns: -1.0 (strongly bearish) to +1.0 (strongly bullish)
        """
        if not patterns:
            return 0.0
        
        bias = 0.0
        for pattern, confidence in patterns.items():
            direction = self.PATTERNS.get(pattern, 'neutral')
            if direction == 'bullish':
                bias += confidence
            elif direction == 'bearish':
                bias -= confidence
        
        return np.clip(bias / max(len(patterns), 1), -1.0, 1.0)
