"""
Training Pipeline
=================
Automated training pipeline for ML models across all assets and timeframes.
Uses 5 years of historical data for robust model training.
"""

import os
import time
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import json

from core.logger import system_logger, model_logger
from core.system import DerivTradingSystem
from config.settings import DERIV_ASSETS, AssetClass


class TrainingPipeline:
    """
    Automated training pipeline for the entire system.
    Trains ML models on 5 years of historical data across all timeframes.
    """
    
    def __init__(
        self,
        app_id: int = None,
        model_dir: str = "./models",
        min_candles: int = 5000
    ):
        self.system = DerivTradingSystem(app_id=app_id, mode="training")
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.min_candles = min_candles
        
        self.training_log = []
        self.stats = {
            'assets_trained': 0,
            'models_trained': 0,
            'failed': [],
            'start_time': None,
            'end_time': None
        }
        
        system_logger.info("Training Pipeline initialized")
    
    def train_all_assets(
        self,
        asset_classes: List[str] = None,
        max_assets_per_class: int = 5
    ) -> Dict:
        """
        Train models for all assets in specified classes.
        
        Args:
            asset_classes: List of asset classes to train (forex, crypto, synthetic)
            max_assets_per_class: Maximum assets to train per class
        """
        self.stats['start_time'] = datetime.now().isoformat()
        
        if asset_classes is None:
            asset_classes = ['forex', 'crypto', 'synthetic']
        
        # Connect to API
        connected = self.system.start()
        if not connected:
            system_logger.error("Failed to connect to Deriv API")
            return self.stats
        
        try:
            for ac_str in asset_classes:
                system_logger.info(f"Training {ac_str.upper()} assets...")
                
                try:
                    ac = AssetClass(ac_str)
                    assets = DERIV_ASSETS.get(ac, [])[:max_assets_per_class]
                except:
                    # Manual asset lists
                    assets = self._get_default_assets(ac_str)
                
                for symbol in assets:
                    try:
                        self._train_single_asset(symbol, ac_str)
                        self.stats['assets_trained'] += 1
                    except Exception as e:
                        system_logger.error(f"Failed to train {symbol}: {e}")
                        self.stats['failed'].append(f"{symbol}: {str(e)}")
                    
                    # Small delay to avoid rate limiting
                    time.sleep(1)
        
        finally:
            self.system.stop()
        
        self.stats['end_time'] = datetime.now().isoformat()
        self._save_training_log()
        
        system_logger.info(
            f"Training complete | Assets: {self.stats['assets_trained']} | "
            f"Models: {self.stats['models_trained']} | "
            f"Failed: {len(self.stats['failed'])}"
        )
        
        return self.stats
    
    def _train_single_asset(self, symbol: str, asset_class: str):
        """Train models for a single asset across all timeframes."""
        system_logger.info(f"Training {symbol}...")
        
        # Fetch large amount of data (up to 5 years equivalent)
        # Deriv API limits to 5000 candles per request, so we make multiple requests
        all_timeframes = ['1m', '5m', '15m', '30m', '1h', '4h', '1d']
        
        # Calculate candles needed for ~5 years per timeframe
        # 1m: ~5 years is too much, limit to what API allows
        # We'll use multiple batches for larger timeframes
        tf_candle_targets = {
            '1m': 5000,    # ~3.5 days per batch
            '5m': 5000,    # ~17 days per batch
            '15m': 5000,   # ~52 days per batch
            '30m': 5000,   # ~104 days per batch
            '1h': 5000,    # ~208 days per batch
            '4h': 5000,    # ~833 days per batch
            '1d': 1825     # ~5 years
        }
        
        metrics = self.system.train_models(
            symbol=symbol,
            asset_class=asset_class,
            data_count=5000  # Maximum per request
        )
        
        if metrics:
            self.stats['models_trained'] += len(metrics)
            self.training_log.append({
                'symbol': symbol,
                'asset_class': asset_class,
                'metrics': metrics,
                'timestamp': datetime.now().isoformat()
            })
            
            system_logger.info(f"Training complete for {symbol}")
        else:
            raise ValueError("No training metrics returned")
    
    def train_custom_asset_list(
        self,
        assets: Dict[str, str]  # symbol -> asset_class
    ) -> Dict:
        """
        Train models for a custom list of assets.
        
        Args:
            assets: Dictionary of {symbol: asset_class}
        """
        self.stats['start_time'] = datetime.now().isoformat()
        
        connected = self.system.start()
        if not connected:
            return self.stats
        
        try:
            for symbol, asset_class in assets.items():
                try:
                    self._train_single_asset(symbol, asset_class)
                    self.stats['assets_trained'] += 1
                except Exception as e:
                    system_logger.error(f"Failed to train {symbol}: {e}")
                    self.stats['failed'].append(f"{symbol}: {str(e)}")
                
                time.sleep(1)
        
        finally:
            self.system.stop()
        
        self.stats['end_time'] = datetime.now().isoformat()
        self._save_training_log()
        
        return self.stats
    
    def _get_default_assets(self, asset_class: str) -> List[str]:
        """Get default asset list for a class."""
        defaults = {
            'forex': ["frxEURUSD", "frxGBPUSD", "frxUSDJPY", "frxAUDUSD", "frxUSDCAD"],
            'crypto': ["cryBTCUSD", "cryETHUSD", "crySOLUSD", "cryXRPUSD", "cryADAUSD"],
            'synthetic': ["R_100", "R_50", "R_25", "R_10", "1HZ100V"],
            'commodity': ["OTC_AUUSD", "OTC_WTI"],
            'index': ["OTC_DJI", "OTC_SPC"]
        }
        return defaults.get(asset_class, ["R_100"])
    
    def _save_training_log(self):
        """Save training log to file."""
        log_path = self.model_dir / "training_log.json"
        with open(log_path, 'w') as f:
            json.dump({
                'stats': self.stats,
                'log': self.training_log
            }, f, indent=2, default=str)
        system_logger.info(f"Training log saved to {log_path}")
    
    def print_summary(self):
        """Print training summary."""
        print("\n" + "="*60)
        print("  TRAINING PIPELINE SUMMARY")
        print("="*60)
        print(f"  Assets Trained:    {self.stats['assets_trained']}")
        print(f"  Models Trained:    {self.stats['models_trained']}")
        print(f"  Failed:            {len(self.stats['failed'])}")
        print(f"  Start:             {self.stats['start_time']}")
        print(f"  End:               {self.stats['end_time']}")
        
        if self.stats['failed']:
            print("\n  Failed Assets:")
            for f in self.stats['failed']:
                print(f"    - {f}")
        
        print("="*60 + "\n")


def run_training(
    app_id: int = None,
    asset_classes: List[str] = None,
    max_assets: int = 5,
    model_dir: str = "./models"
):
    """
    Run the complete training pipeline.
    
    Usage:
        python -m training.pipeline
    """
    pipeline = TrainingPipeline(app_id=app_id, model_dir=model_dir)
    
    stats = pipeline.train_all_assets(
        asset_classes=asset_classes,
        max_assets_per_class=max_assets
    )
    
    pipeline.print_summary()
    
    return stats


if __name__ == "__main__":
    import sys
    
    # Parse arguments
    asset_classes = sys.argv[1:] if len(sys.argv) > 1 else None
    
    run_training(asset_classes=asset_classes)
