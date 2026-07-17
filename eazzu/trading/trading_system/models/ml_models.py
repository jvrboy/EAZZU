"""
Machine Learning Models
=======================
Ensemble ML models for signal prediction across all timeframes.
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import pickle
import os
import warnings
from pathlib import Path

from core.logger import model_logger
from core.types import MarketData, TechnicalIndicators
from analysis.indicators import TechnicalAnalyzer

warnings.filterwarnings('ignore')


@dataclass
class ModelPrediction:
    """Prediction result from ML model."""
    direction: str  # BUY, SELL, HOLD
    confidence: float
    probability_up: float
    probability_down: float
    probability_hold: float
    model_name: str
    features_used: List[str]


class FeatureEngineer:
    """
    Feature engineering for ML models.
    Creates 100+ features from raw OHLCV data.
    """
    
    def __init__(self):
        self.analyzer = TechnicalAnalyzer()
        self.scaler = StandardScaler()
        self.feature_names: List[str] = []
        self.is_fitted = False
    
    def create_features(self, market_data: MarketData, indicators: TechnicalIndicators = None) -> np.ndarray:
        """Create feature vector from market data."""
        if indicators is None:
            indicators = self.analyzer.analyze(market_data)
        
        closes = market_data.closes
        highs = market_data.highs
        lows = market_data.lows
        volumes = market_data.volumes
        
        if len(closes) < 200:
            return np.zeros(100)
        
        features = []
        
        # Price features
        returns = np.diff(closes) / closes[:-1]
        log_returns = np.log(closes[1:] / closes[:-1])
        
        features.extend([
            closes[-1] / closes[-2] - 1,  # Last return
            closes[-1] / closes[-5] - 1,  # 5-period return
            closes[-1] / closes[-10] - 1,  # 10-period return
            closes[-1] / closes[-20] - 1,  # 20-period return
            np.mean(returns[-5:]),  # Mean short return
            np.mean(returns[-20:]),  # Mean medium return
            np.std(returns[-20:]),  # Volatility
            np.std(returns[-50:]),  # Long volatility
            np.max(highs[-20:]) / closes[-1] - 1,  # Distance to 20-period high
            closes[-1] / np.max(lows[-20:]) - 1,  # Distance from 20-period low
        ])
        
        # Technical indicator features
        features.extend([
            indicators.rsi_14 / 100,  # Normalized RSI
            indicators.rsi_6 / 100,  # Fast RSI
            (closes[-1] - indicators.sma_20) / indicators.atr_14 if indicators.atr_14 > 0 else 0,  # Price vs SMA20 in ATR
            (closes[-1] - indicators.sma_50) / indicators.atr_14 if indicators.atr_14 > 0 else 0,  # Price vs SMA50 in ATR
            (closes[-1] - indicators.sma_200) / indicators.atr_14 if indicators.atr_14 > 0 else 0,  # Price vs SMA200 in ATR
            indicators.macd_histogram / closes[-1] * 100 if closes[-1] > 0 else 0,  # MACD normalized
            indicators.bb_position,  # Bollinger position
            indicators.bb_width,  # Bollinger width
            indicators.atr_14 / closes[-1] if closes[-1] > 0 else 0,  # ATR%
            indicators.adx / 100,  # Normalized ADX
            (indicators.adx_plus_di - indicators.adx_minus_di) / 100,  # DI spread
            indicators.stochastic_k / 100,  # Stochastic K
            indicators.stochastic_d / 100,  # Stochastic D
            (indicators.stochastic_k - indicators.stochastic_d) / 100,  # Stochastic spread
            indicators.cci_20 / 200,  # Normalized CCI
            (indicators.williams_r + 100) / 100,  # Normalized Williams %R
            indicators.momentum_10 / closes[-1] if closes[-1] > 0 else 0,  # Momentum normalized
            indicators.roc_12 / 100,  # ROC normalized
            indicators.mfi_14 / 100,  # MFI normalized
            indicators.volume_ratio,  # Volume ratio
        ])
        
        # Moving average crossovers
        features.extend([
            1.0 if closes[-1] > indicators.sma_20 > indicators.sma_50 else 0.0,  # Bullish alignment
            1.0 if indicators.ema_12 > indicators.ema_26 else 0.0,  # EMA cross
            1.0 if indicators.sma_20 > indicators.sma_50 else 0.0,  # Golden cross
            1.0 if indicators.sma_50 > indicators.sma_200 else 0.0,  # Long-term trend
        ])
        
        # Statistical features
        features.extend([
            np.percentile(returns[-20:], 25),
            np.percentile(returns[-20:], 75),
            stats.skew(returns[-50:]) if len(returns) >= 50 else 0,
            stats.kurtosis(returns[-50:]) if len(returns) >= 50 else 0,
        ])
        
        # Trend features
        x = np.arange(len(closes[-20:]))
        slope, _, r_value, _, _ = stats.linregress(x, closes[-20:])
        features.extend([
            slope / closes[-1] if closes[-1] > 0 else 0,  # Trend slope
            r_value ** 2,  # R-squared
        ])
        
        # Volatility regime
        vol_short = np.std(returns[-10:])
        vol_long = np.std(returns[-50:])
        features.append(vol_short / vol_long if vol_long > 0 else 1.0)
        
        # Ichimoku features
        features.extend([
            1.0 if closes[-1] > indicators.ichimoku_senkou_a else 0.0,
            1.0 if closes[-1] > indicators.ichimoku_senkou_b else 0.0,
            1.0 if indicators.ichimoku_tenkan > indicators.ichimoku_kijun else 0.0,
        ])
        
        # Fill any NaN values
        features = np.nan_to_num(features, nan=0.0, posinf=0.0, neginf=0.0)
        
        return np.array(features)
    
    def prepare_training_data(
        self,
        market_data: MarketData,
        lookahead: int = 10,
        threshold: float = 0.001
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Prepare training data from market data.
        
        Args:
            market_data: Market data object
            lookahead: How many periods ahead to predict
            threshold: Minimum price move to count as signal
        """
        closes = market_data.closes
        
        X = []
        y = []
        
        # Need enough data for indicators + lookahead
        for i in range(200, len(closes) - lookahead):
            # Create a slice of market data
            slice_data = MarketData(
                symbol=market_data.symbol,
                asset_class=market_data.asset_class,
                timeframe=market_data.timeframe,
                candles=market_data.candles[:i+1]
            )
            
            indicators = self.analyzer.analyze(slice_data)
            features = self.create_features(slice_data, indicators)
            
            # Label: future price movement
            future_return = (closes[i + lookahead] - closes[i]) / closes[i]
            
            if future_return > threshold:
                label = 1  # BUY
            elif future_return < -threshold:
                label = 2  # SELL
            else:
                label = 0  # HOLD
            
            X.append(features)
            y.append(label)
        
        return np.array(X), np.array(y)
    
    def fit_scaler(self, X: np.ndarray):
        """Fit the feature scaler."""
        self.scaler.fit(X)
        self.is_fitted = True
    
    def scale_features(self, X: np.ndarray) -> np.ndarray:
        """Scale features using fitted scaler."""
        if not self.is_fitted:
            return X
        return self.scaler.transform(X)


class EnsemblePredictor:
    """
    Ensemble of ML models for high-accuracy predictions.
    Combines Random Forest, Gradient Boosting, Extra Trees, and Neural Network.
    """
    
    def __init__(self, model_name: str = "ensemble"):
        self.model_name = model_name
        self.models: Dict[str, Any] = {}
        self.weights = {
            'rf': 0.30,
            'gb': 0.30,
            'et': 0.20,
            'nn': 0.20
        }
        self.is_trained = False
        self.feature_engineer = FeatureEngineer()
        self.metrics: Dict[str, float] = {}
        
        model_logger.info(f"EnsemblePredictor '{model_name}' initialized")
    
    def initialize_models(self):
        """Initialize all models in the ensemble."""
        self.models['rf'] = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            n_jobs=-1
        )
        
        self.models['gb'] = GradientBoostingClassifier(
            n_estimators=150,
            max_depth=5,
            learning_rate=0.1,
            min_samples_split=5,
            random_state=42
        )
        
        self.models['et'] = ExtraTreesClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )
        
        self.models['nn'] = MLPClassifier(
            hidden_layer_sizes=(128, 64, 32),
            activation='relu',
            solver='adam',
            alpha=0.001,
            learning_rate='adaptive',
            max_iter=500,
            random_state=42,
            early_stopping=True,
            validation_fraction=0.1
        )
        
        model_logger.info("All models initialized")
    
    def train(self, market_data: MarketData, lookahead: int = 10, validation_split: float = 0.2) -> Dict[str, float]:
        """
        Train ensemble models on market data.
        
        Args:
            market_data: Training data
            lookahead: Prediction horizon
            validation_split: Fraction for validation
        """
        self.initialize_models()
        
        model_logger.info(f"Training on {market_data.symbol} {market_data.timeframe}")
        
        # Prepare features
        X, y = self.feature_engineer.prepare_training_data(market_data, lookahead)
        
        if len(X) < 500:
            model_logger.warning("Insufficient training data")
            return {}
        
        # Scale features
        self.feature_engineer.fit_scaler(X)
        X_scaled = self.feature_engineer.scale_features(X)
        
        # Split
        split_idx = int(len(X) * (1 - validation_split))
        X_train, X_val = X_scaled[:split_idx], X_scaled[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        model_logger.info(f"Training: {len(X_train)} samples, Validation: {len(X_val)} samples")
        
        # Train each model
        for name, model in self.models.items():
            model_logger.info(f"Training {name}...")
            try:
                model.fit(X_train, y_train)
                
                # Validate
                if len(X_val) > 0:
                    pred = model.predict(X_val)
                    acc = accuracy_score(y_val, pred)
                    self.metrics[f'{name}_accuracy'] = acc
                    model_logger.info(f"{name} validation accuracy: {acc:.4f}")
            except Exception as e:
                model_logger.error(f"Error training {name}: {e}")
        
        self.is_trained = True
        self.metrics['ensemble_trained'] = 1.0
        
        model_logger.info("Training complete")
        return self.metrics
    
    def predict(self, market_data: MarketData, indicators: TechnicalIndicators = None) -> ModelPrediction:
        """
        Make prediction using ensemble.
        """
        if not self.is_trained:
            return ModelPrediction('HOLD', 0.0, 0.33, 0.33, 0.33, self.model_name, [])
        
        # Create features
        features = self.feature_engineer.create_features(market_data, indicators)
        features = features.reshape(1, -1)
        
        if self.feature_engineer.is_fitted:
            features = self.feature_engineer.scale_features(features)
        
        # Get predictions from each model
        probs = np.zeros((1, 3))  # 3 classes: HOLD, BUY, SELL
        
        for name, model in self.models.items():
            try:
                model_probs = model.predict_proba(features)
                probs += self.weights[name] * model_probs
            except Exception as e:
                model_logger.warning(f"Prediction error in {name}: {e}")
        
        # Normalize
        probs = probs / np.sum(probs)
        
        # Get prediction
        pred_class = np.argmax(probs)
        confidence = np.max(probs)
        
        class_map = {0: 'HOLD', 1: 'BUY', 2: 'SELL'}
        direction = class_map[pred_class]
        
        return ModelPrediction(
            direction=direction,
            confidence=float(confidence),
            probability_up=float(probs[0][1]),
            probability_down=float(probs[0][2]),
            probability_hold=float(probs[0][0]),
            model_name=self.model_name,
            features_used=[]
        )
    
    def save(self, path: str):
        """Save model to disk."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'models': self.models,
            'weights': self.weights,
            'is_trained': self.is_trained,
            'metrics': self.metrics,
            'feature_engineer': self.feature_engineer,
            'model_name': self.model_name
        }
        
        with open(path, 'wb') as f:
            pickle.dump(data, f)
        
        model_logger.info(f"Model saved to {path}")
    
    def load(self, path: str) -> bool:
        """Load model from disk."""
        try:
            with open(path, 'rb') as f:
                data = pickle.load(f)
            
            self.models = data['models']
            self.weights = data['weights']
            self.is_trained = data['is_trained']
            self.metrics = data['metrics']
            self.feature_engineer = data['feature_engineer']
            
            model_logger.info(f"Model loaded from {path}")
            return True
            
        except Exception as e:
            model_logger.error(f"Failed to load model: {e}")
            return False


class MultiTimeframeEnsemble:
    """
    Ensemble model that aggregates predictions across multiple timeframes.
    Higher timeframes provide context for lower timeframe signals.
    """
    
    TIMEFRAME_WEIGHTS = {
        '1m': 0.10,
        '5m': 0.15,
        '15m': 0.15,
        '30m': 0.15,
        '1h': 0.20,
        '4h': 0.15,
        '1d': 0.10
    }
    
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.models: Dict[str, EnsemblePredictor] = {}
        self.is_trained = False
        model_logger.info(f"MultiTimeframeEnsemble for {symbol} initialized")
    
    def train(self, timeframe_data: Dict[str, MarketData]) -> Dict[str, float]:
        """Train models for each timeframe."""
        all_metrics = {}
        
        for tf, data in timeframe_data.items():
            model = EnsemblePredictor(f"{self.symbol}_{tf}")
            metrics = model.train(data)
            self.models[tf] = model
            all_metrics.update(metrics)
        
        self.is_trained = True
        model_logger.info(f"Multi-timeframe training complete for {self.symbol}")
        return all_metrics
    
    def predict(self, timeframe_data: Dict[str, MarketData], 
                timeframe_indicators: Dict[str, TechnicalIndicators]) -> Dict[str, ModelPrediction]:
        """Get predictions for all timeframes."""
        predictions = {}
        
        for tf, data in timeframe_data.items():
            if tf in self.models:
                indicators = timeframe_indicators.get(tf)
                pred = self.models[tf].predict(data, indicators)
                predictions[tf] = pred
        
        return predictions
    
    def aggregate_prediction(self, predictions: Dict[str, ModelPrediction]) -> ModelPrediction:
        """
        Aggregate predictions across timeframes with weighted voting.
        Higher timeframes carry more weight for trend direction.
        """
        if not predictions:
            return ModelPrediction('HOLD', 0.0, 0.33, 0.33, 0.33, 'aggregate', [])
        
        weighted_probs = np.zeros(3)
        total_weight = 0
        
        for tf, pred in predictions.items():
            weight = self.TIMEFRAME_WEIGHTS.get(tf, 0.1)
            probs = np.array([pred.probability_hold, pred.probability_up, pred.probability_down])
            weighted_probs += weight * probs
            total_weight += weight
        
        weighted_probs /= total_weight
        
        pred_class = np.argmax(weighted_probs)
        confidence = np.max(weighted_probs)
        
        class_map = {0: 'HOLD', 1: 'BUY', 2: 'SELL'}
        direction = class_map[pred_class]
        
        return ModelPrediction(
            direction=direction,
            confidence=float(confidence),
            probability_up=float(weighted_probs[1]),
            probability_down=float(weighted_probs[2]),
            probability_hold=float(weighted_probs[0]),
            model_name=f"{self.symbol}_aggregate",
            features_used=list(predictions.keys())
        )
    
    def save_all(self, base_path: str):
        """Save all timeframe models."""
        Path(base_path).mkdir(parents=True, exist_ok=True)
        
        for tf, model in self.models.items():
            path = f"{base_path}/{self.symbol}_{tf}.pkl"
            model.save(path)
        
        model_logger.info(f"All models saved to {base_path}")
    
    def load_all(self, base_path: str) -> bool:
        """Load all timeframe models."""
        import glob
        
        pattern = f"{base_path}/{self.symbol}_*.pkl"
        files = glob.glob(pattern)
        
        if not files:
            model_logger.warning(f"No model files found for {self.symbol}")
            return False
        
        for f in files:
            tf = f.split('_')[-1].replace('.pkl', '')
            model = EnsemblePredictor(f"{self.symbol}_{tf}")
            if model.load(f):
                self.models[tf] = model
        
        self.is_trained = len(self.models) > 0
        model_logger.info(f"Loaded {len(self.models)} models for {self.symbol}")
        return self.is_trained
