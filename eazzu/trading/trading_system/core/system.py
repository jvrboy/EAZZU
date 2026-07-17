"""
Main Trading System
===================
Central orchestrator for the entire multi-agent trading system.
Coordinates data fetching, analysis, ML, agents, council, and signals.
"""

import asyncio
import threading
import time
from typing import Dict, List, Optional, Callable
from datetime import datetime
from pathlib import Path
import json

from config.settings import (
    DERIV_ASSETS, AssetClass, get_config, load_env_config
)
from core.logger import (
    system_logger, signal_logger, perf_logger, 
    setup_logger
)
from core.types import (
    MarketData, TradingSignal, TechnicalIndicators,
    ModelPrediction
)
from api.deriv_client import AsyncDerivExecutor, DataManager
from analysis.indicators import TechnicalAnalyzer, PatternDetector
from models.ml_models import (
    EnsemblePredictor, MultiTimeframeEnsemble, FeatureEngineer
)
from agents.signal_agents import (
    BaseAgent, AgentFactory, AgentType
)
from council.voting_system import VotingCouncil, MultiTimeframeCouncil
from signals.signal_engine import SignalEngine, MultiTimeframeSignalEngine
from visualization.charts import ChartEngine, Dashboard
from backtest.backtester import Backtester


class DerivTradingSystem:
    """
    Complete multi-agent trading analysis system for Deriv.
    
    Features:
    - Multi-asset support (Forex, Crypto, Synthetic Indices)
    - Multi-timeframe analysis (1m, 5m, 15m, 30m, 1h, 4h, 1d)
    - 7 specialized AI agents with different strategies
    - Council voting system for consensus decisions
    - ML ensemble models for pattern recognition
    - High-accuracy signal generation
    - Real-time and historical data analysis
    - Comprehensive backtesting
    - Professional charting and visualization
    """
    
    def __init__(
        self,
        app_id: int = None,
        mode: str = "analysis",
        assets: List[str] = None,
        timeframes: List[str] = None,
        min_confidence: float = 0.65
    ):
        """
        Initialize the trading system.
        
        Args:
            app_id: Deriv API app ID
            mode: 'analysis', 'backtest', or 'training'
            assets: List of symbols to analyze (default: all)
            timeframes: Timeframes to use (default: ['5m', '1h', '4h'])
            min_confidence: Minimum signal confidence threshold
        """
        load_env_config()
        
        self.mode = mode
        self.min_confidence = min_confidence
        self.is_running = False
        
        # Default timeframes
        self.timeframes = timeframes or ['5m', '15m', '1h', '4h']
        
        # API client
        self.executor = AsyncDerivExecutor(app_id)
        
        # Analysis components
        self.analyzer = TechnicalAnalyzer()
        self.pattern_detector = PatternDetector()
        
        # ML models storage
        self.models: Dict[str, MultiTimeframeEnsemble] = {}
        
        # Signal engines
        self.signal_engines: Dict[str, MultiTimeframeSignalEngine] = {}
        
        # Visualization
        self.chart_engine = ChartEngine(style='dark')
        self.dashboard = Dashboard(self.chart_engine)
        
        # Performance tracking
        self.performance = {
            'signals_generated': 0,
            'analysis_cycles': 0,
            'start_time': None,
            'errors': 0
        }
        
        # Callbacks
        self._signal_callbacks: List[Callable] = []
        
        system_logger.info(
            f"DERIV Trading System v2.0 initialized | "
            f"Mode: {mode} | Timeframes: {', '.join(self.timeframes)}"
        )
    
    def start(self):
        """Start the trading system."""
        system_logger.info("Starting trading system...")
        self.is_running = True
        self.performance['start_time'] = datetime.now()
        
        # Connect to API
        connected = self.executor.start()
        if not connected:
            system_logger.error("Failed to connect to Deriv API")
            return False
        
        system_logger.info("Trading system started successfully")
        return True
    
    def stop(self):
        """Stop the trading system."""
        system_logger.info("Stopping trading system...")
        self.is_running = False
        self.executor.stop()
        system_logger.info("Trading system stopped")
    
    def load_models(self, model_dir: str = "./models") -> Dict[str, bool]:
        """Load trained ML models from disk."""
        results = {}
        model_path = Path(model_dir)
        
        if not model_path.exists():
            system_logger.warning(f"Model directory not found: {model_dir}")
            return results
        
        # Find all model files
        for symbol_dir in model_path.iterdir():
            if symbol_dir.is_dir():
                symbol = symbol_dir.name
                mte = MultiTimeframeEnsemble(symbol)
                success = mte.load_all(str(symbol_dir))
                if success:
                    self.models[symbol] = mte
                    results[symbol] = True
                    system_logger.info(f"Loaded models for {symbol}")
                else:
                    results[symbol] = False
        
        return results
    
    def save_models(self, model_dir: str = "./models"):
        """Save all trained ML models to disk."""
        for symbol, mte in self.models.items():
            path = f"{model_dir}/{symbol}"
            mte.save_all(path)
        system_logger.info(f"All models saved to {model_dir}")
    
    def initialize_signal_engine(
        self,
        symbol: str,
        asset_class: str = None
    ) -> MultiTimeframeSignalEngine:
        """Initialize signal engine for a symbol."""
        # Detect asset class
        if asset_class is None:
            if symbol.startswith("frx"):
                asset_class = "forex"
            elif symbol.startswith("cry"):
                asset_class = "crypto"
            elif symbol.startswith(("R_", "1HZ", "JD", "RDB", "WLD", "BOOM", "CRASH", "STEP")):
                asset_class = "synthetic"
            else:
                asset_class = "forex"
        
        # Get ML predictors for this symbol
        ml_predictors = {}
        if symbol in self.models:
            for tf in self.timeframes:
                if tf in self.models[symbol].models:
                    ml_predictors[tf] = self.models[symbol].models[tf]
        
        # Create signal engine
        engine = MultiTimeframeSignalEngine(
            symbol=symbol,
            asset_class=asset_class,
            timeframes=self.timeframes,
            ml_predictors=ml_predictors
        )
        
        self.signal_engines[symbol] = engine
        return engine
    
    def analyze_symbol(
        self,
        symbol: str,
        asset_class: str = None,
        data_count: int = 2000
    ) -> Dict[str, any]:
        """
        Complete analysis of a single symbol across all timeframes.
        
        Returns:
            Dictionary containing signals, indicators, charts, and stats.
        """
        system_logger.info(f"Analyzing {symbol}...")
        
        results = {
            'symbol': symbol,
            'timestamp': datetime.now().isoformat(),
            'timeframes': {},
            'signals': {},
            'ml_predictions': {},
            'status': 'success'
        }
        
        try:
            # Fetch data for all timeframes
            timeframe_data = self.executor.fetch_multi_timeframe(
                symbol, self.timeframes, count=data_count
            )
            
            if not timeframe_data:
                results['status'] = 'no_data'
                return results
            
            # Store market data
            for tf, data in timeframe_data.items():
                results['timeframes'][tf] = {
                    'candles': len(data.candles),
                    'current_price': data.current_price,
                    'timestamp': data.timestamp.isoformat() if data.timestamp else None
                }
            
            # Calculate indicators for each timeframe
            timeframe_indicators = {}
            for tf, data in timeframe_data.items():
                indicators = self.analyzer.analyze(data)
                timeframe_indicators[tf] = indicators
            
            # Get ML predictions
            if symbol in self.models:
                predictions = self.models[symbol].predict(
                    {tf: data for tf, data in timeframe_data.items()},
                    timeframe_indicators
                )
                for tf, pred in predictions.items():
                    results['ml_predictions'][tf] = {
                        'direction': pred.direction,
                        'confidence': pred.confidence,
                        'prob_up': pred.probability_up,
                        'prob_down': pred.probability_down
                    }
            
            # Initialize signal engine if needed
            if symbol not in self.signal_engines:
                self.initialize_signal_engine(symbol, asset_class)
            
            # Generate signals
            engine = self.signal_engines[symbol]
            
            # Build ML predictions dict
            mlp_dict = {}
            for tf, pred_data in results['ml_predictions'].items():
                mlp_dict[tf] = ModelPrediction(
                    direction=pred_data['direction'],
                    confidence=pred_data['confidence'],
                    probability_up=pred_data['prob_up'],
                    probability_down=pred_data['prob_down'],
                    probability_hold=1 - pred_data['prob_up'] - pred_data['prob_down'],
                    model_name=f"{symbol}_{tf}",
                    features_used=[]
                )
            
            signals = engine.generate_all_signals(timeframe_data, mlp_dict)
            
            # Format signals for output
            for tf, signal in signals.items():
                results['signals'][tf] = {
                    'type': signal.signal_type,
                    'confidence': signal.confidence,
                    'strength': signal.strength.name,
                    'entry': signal.entry_price,
                    'stop_loss': signal.stop_loss,
                    'take_profit': signal.take_profit,
                    'risk_reward': signal.risk_reward_ratio,
                    'direction': signal.direction.name,
                    'indicators': signal.indicators,
                    'metadata': signal.metadata
                }
            
            # Generate chart
            primary_tf = self.timeframes[0] if self.timeframes else '1h'
            if primary_tf in timeframe_data:
                chart_path = f"./charts/{symbol}_{primary_tf}.png"
                primary_signals = [s for tf, s in signals.items() if tf == primary_tf]
                self.chart_engine.create_full_chart(
                    market_data=timeframe_data[primary_tf],
                    indicators=timeframe_indicators.get(primary_tf),
                    signals=primary_signals,
                    title=f"{symbol} - {primary_tf}",
                    save_path=chart_path
                )
                results['chart'] = chart_path
            
            self.performance['signals_generated'] += len(signals)
            self.performance['analysis_cycles'] += 1
            
        except Exception as e:
            system_logger.error(f"Analysis error for {symbol}: {e}")
            results['status'] = f'error: {str(e)}'
            self.performance['errors'] += 1
        
        return results
    
    def analyze_multiple(
        self,
        symbols: List[str],
        asset_classes: Dict[str, str] = None
    ) -> Dict[str, Dict]:
        """Analyze multiple symbols."""
        all_results = {}
        
        for symbol in symbols:
            ac = asset_classes.get(symbol) if asset_classes else None
            result = self.analyze_symbol(symbol, ac)
            all_results[symbol] = result
        
        return all_results
    
    def train_models(
        self,
        symbol: str,
        asset_class: str = None,
        data_count: int = 5000
    ) -> Dict[str, float]:
        """
        Train ML models for a symbol across all timeframes.
        
        Args:
            symbol: Symbol to train on
            asset_class: Asset class (auto-detected if None)
            data_count: Amount of historical data to use
            
        Returns:
            Training metrics
        """
        system_logger.info(f"Training models for {symbol}...")
        
        # Fetch data for all timeframes
        timeframe_data = self.executor.fetch_multi_timeframe(
            symbol, self.timeframes, count=data_count
        )
        
        if not timeframe_data:
            system_logger.error(f"No data available for {symbol}")
            return {}
        
        # Create and train multi-timeframe ensemble
        mte = MultiTimeframeEnsemble(symbol)
        metrics = mte.train(timeframe_data)
        
        # Store model
        self.models[symbol] = mte
        
        # Save models
        mte.save_all(f"./models/{symbol}")
        
        system_logger.info(f"Training complete for {symbol}")
        return metrics
    
    def backtest_symbol(
        self,
        symbol: str,
        timeframe: str = '1h',
        data_count: int = 5000
    ) -> Dict:
        """
        Run backtest on a symbol.
        
        Returns:
            Backtest results dictionary
        """
        system_logger.info(f"Backtesting {symbol} {timeframe}...")
        
        # Fetch data
        data = self.executor.fetch_data(symbol, timeframe, count=data_count)
        
        if not data or len(data.candles) < 500:
            return {'error': 'Insufficient data'}
        
        # Initialize engine
        if symbol not in self.signal_engines:
            self.initialize_signal_engine(symbol)
        
        # Create backtester
        backtester = Backtester(initial_balance=10000, risk_per_trade=0.02)
        
        # Define signal generator function
        engine = self.signal_engines[symbol]
        
        def signal_gen(md):
            signals = engine.generate_all_signals({timeframe: md})
            return [s for s in signals.values()]
        
        # Run backtest
        result = backtester.run_walk_forward(data, signal_gen)
        
        # Print report
        backtester.print_report()
        
        return {
            'symbol': symbol,
            'timeframe': timeframe,
            'total_trades': result.total_trades,
            'win_rate': result.win_rate,
            'profit_factor': result.profit_factor,
            'total_return': result.total_return,
            'max_drawdown': result.max_drawdown,
            'sharpe_ratio': result.sharpe_ratio,
            'expectancy': result.expectancy,
            'avg_trade': result.avg_trade
        }
    
    def generate_dashboard(self, save_path: str = "./dashboard.html") -> str:
        """Generate HTML dashboard with all signals."""
        all_signals = []
        for symbol, engine in self.signal_engines.items():
            for tf, signals in engine.get_all_active_signals().items():
                all_signals.extend(signals)
        
        self.dashboard.update('signals', all_signals)
        return self.dashboard.generate_html_report(save_path)
    
    def get_system_stats(self) -> Dict:
        """Get system performance statistics."""
        uptime = datetime.now() - self.performance['start_time'] if self.performance['start_time'] else timedelta(0)
        
        return {
            'is_running': self.is_running,
            'uptime_seconds': uptime.total_seconds(),
            'signals_generated': self.performance['signals_generated'],
            'analysis_cycles': self.performance['analysis_cycles'],
            'errors': self.performance['errors'],
            'symbols_tracked': len(self.signal_engines),
            'models_loaded': len(self.models),
            'timeframes': self.timeframes
        }
    
    def register_signal_callback(self, callback: Callable):
        """Register callback for new signals."""
        self._signal_callbacks.append(callback)
    
    def get_recommended_assets(self, asset_class: str = None) -> List[str]:
        """Get recommended assets based on configuration."""
        if asset_class:
            ac = AssetClass(asset_class) if asset_class in [e.value for e in AssetClass] else None
            if ac and ac in DERIV_ASSETS:
                return DERIV_ASSETS[ac]
        
        # Return default set
        defaults = [
            # Forex majors
            "frxEURUSD", "frxGBPUSD", "frxUSDJPY", "frxAUDUSD",
            # Crypto
            "cryBTCUSD", "cryETHUSD", "crySOLUSD",
            # Synthetic indices
            "R_100", "R_50", "R_25", "R_10",
            # Volatility indices
            "1HZ100V", "1HZ50V", "1HZ25V",
            # Boom/Crash
            "BOOM1000", "CRASH1000",
        ]
        return defaults
