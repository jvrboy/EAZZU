"""
DERIV Multi-Agent Trading Analysis System v2.0
================================================

A comprehensive trading analysis tool using the Deriv API.

Modules:
    core: System core, logging, types
    api: Deriv API WebSocket client
    analysis: Technical indicators (50+)
    models: ML ensemble models
    agents: 7 specialized signal agents
    council: Voting consensus system
    signals: Signal generation engine
    visualization: Charts and dashboards
    backtest: Strategy backtesting
    training: Model training pipeline

Usage:
    from core.system import DerivTradingSystem
    
    system = DerivTradingSystem()
    system.start()
    
    # Analyze a symbol
    result = system.analyze_symbol("R_100", asset_class="synthetic")
    
    # Train models
    system.train_models("R_100")
    
    # Backtest
    system.backtest_symbol("R_100")
    
    system.stop()
"""

__version__ = "2.0.0"
__author__ = "AI Trading System"

from core.system import DerivTradingSystem

__all__ = ['DerivTradingSystem']
