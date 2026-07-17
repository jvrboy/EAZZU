#!/usr/bin/env python3
"""
DERIV Multi-Agent Trading Analysis System
=========================================
A comprehensive trading analysis tool using the Deriv API.

Features:
  - Multi-asset analysis (Forex, Crypto, Synthetic Indices)
  - 7 specialized AI agents with council voting
  - ML ensemble models trained on 5 years of data
  - Multi-timeframe analysis (1m, 5m, 15m, 30m, 1h, 4h, 1d)
  - High-accuracy signal generation
  - Professional charting and visualization
  - Comprehensive backtesting

Usage:
    python main.py analyze --symbol R_100 --timeframe 1h
    python main.py analyze-all --assets forex,crypto
    python main.py train --asset-class synthetic --max-assets 5
    python main.py train-all
    python main.py backtest --symbol R_100 --timeframe 1h
    python main.py dashboard
    python main.py monitor --symbols R_100,R_50,frxEURUSD --interval 60
    python main.py live --symbols R_100 --timeframes 5m,1h

Author: AI Trading System v2.0
"""

import os
import sys
import time
import signal as sig
import argparse
import json
from datetime import datetime
from typing import List
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.system import DerivTradingSystem
from core.logger import system_logger, setup_logger
from config.settings import DERIV_ASSETS, AssetClass
from training.pipeline import TrainingPipeline


# Global system instance
_system = None


def get_system(app_id=None):
    """Get or create trading system instance."""
    global _system
    if _system is None:
        _system = DerivTradingSystem(app_id=app_id)
    return _system


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    print("\n\nShutting down gracefully...")
    if _system:
        _system.stop()
    sys.exit(0)


sig.signal(sig.SIGINT, signal_handler)
sig.signal(sig.SIGTERM, signal_handler)


def print_banner():
    """Print system banner."""
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║     DERIV Multi-Agent Trading Analysis System v2.0            ║
    ║                                                               ║
    ║     7 AI Agents | Council Voting | ML Ensembles              ║
    ║     Forex | Crypto | Synthetic Indices                        ║
    ║     1m | 5m | 15m | 30m | 1h | 4h | 1d                      ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)


def cmd_analyze(args):
    """Analyze a single symbol."""
    print(f"\n[ANALYZE] {args.symbol} ({args.timeframe})")
    print("-" * 50)
    
    system = get_system(args.app_id)
    
    if not system.start():
        print("ERROR: Could not connect to Deriv API")
        return 1
    
    try:
        # Load models if available
        system.load_models(args.model_dir)
        
        # Analyze
        result = system.analyze_symbol(
            symbol=args.symbol,
            asset_class=args.asset_class,
            data_count=args.count
        )
        
        # Print results
        print(f"\nSymbol: {result['symbol']}")
        print(f"Status: {result['status']}")
        print(f"Timestamp: {result['timestamp']}")
        
        # Timeframes
        print(f"\n--- Timeframes ---")
        for tf, info in result['timeframes'].items():
            print(f"  {tf}: {info['candles']} candles | Price: {info['current_price']:.5f}")
        
        # ML Predictions
        if result['ml_predictions']:
            print(f"\n--- ML Predictions ---")
            for tf, pred in result['ml_predictions'].items():
                print(f"  {tf}: {pred['direction']} ({pred['confidence']:.1%})")
        
        # Signals
        if result['signals']:
            print(f"\n--- TRADING SIGNALS ---")
            for tf, sig_data in result['signals'].items():
                emoji = "BUY" if 'BUY' in sig_data['type'] else "SELL"
                print(f"\n  [{emoji}] {tf} Signal")
                print(f"    Type:        {sig_data['type']}")
                print(f"    Confidence:  {sig_data['confidence']:.1%}")
                print(f"    Strength:    {sig_data['strength']}")
                print(f"    Entry:       {sig_data['entry']:.5f}")
                print(f"    Stop Loss:   {sig_data['stop_loss']:.5f}")
                print(f"    Take Profit: {sig_data['take_profit']:.5f}")
                print(f"    Risk/Reward: {sig_data['risk_reward']:.2f}")
                print(f"    Strategy:    {sig_data['metadata'].get('strategy', 'N/A')[:80]}")
        else:
            print("\n--- No signals generated (insufficient confidence) ---")
        
        # Chart
        if 'chart' in result:
            print(f"\nChart saved: {result['chart']}")
        
        # Save JSON
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            print(f"Results saved: {args.output}")
    
    finally:
        system.stop()
    
    return 0


def cmd_analyze_all(args):
    """Analyze multiple assets."""
    print(f"\n[ANALYZE ALL] Assets: {args.assets}")
    print("-" * 50)
    
    # Parse asset classes
    asset_classes = args.assets.split(',') if args.assets else ['synthetic']
    
    symbols = []
    for ac in asset_classes:
        ac = ac.strip()
        try:
            enum_ac = AssetClass(ac)
            symbols.extend(DERIV_ASSETS.get(enum_ac, [])[:args.max_assets])
        except:
            # Try as individual symbols
            symbols.append(ac)
    
    print(f"Analyzing {len(symbols)} symbols: {', '.join(symbols[:10])}")
    
    system = get_system(args.app_id)
    
    if not system.start():
        print("ERROR: Could not connect to Deriv API")
        return 1
    
    try:
        system.load_models(args.model_dir)
        
        results = system.analyze_multiple(symbols)
        
        # Print summary
        print(f"\n{'='*60}")
        print(f"  ANALYSIS SUMMARY - {len(results)} symbols")
        print(f"{'='*60}")
        
        total_signals = 0
        for symbol, result in results.items():
            n_signals = len(result.get('signals', {}))
            total_signals += n_signals
            status = "OK" if result['status'] == 'success' else result['status']
            print(f"  {symbol:15s} | Signals: {n_signals} | Status: {status}")
        
        print(f"\n  Total signals: {total_signals}")
        print(f"{'='*60}\n")
        
        # Save results
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            print(f"Results saved: {args.output}")
    
    finally:
        system.stop()
    
    return 0


def cmd_train(args):
    """Train ML models."""
    print(f"\n[TRAIN] Asset class: {args.asset_class}")
    print("-" * 50)
    
    pipeline = TrainingPipeline(
        app_id=args.app_id,
        model_dir=args.model_dir
    )
    
    stats = pipeline.train_all_assets(
        asset_classes=[args.asset_class] if args.asset_class else None,
        max_assets_per_class=args.max_assets
    )
    
    pipeline.print_summary()
    
    return 0


def cmd_train_all(args):
    """Train all models."""
    print(f"\n[TRAIN ALL]")
    print("-" * 50)
    
    pipeline = TrainingPipeline(
        app_id=args.app_id,
        model_dir=args.model_dir
    )
    
    asset_classes = args.asset_classes.split(',') if args.asset_classes else None
    
    stats = pipeline.train_all_assets(
        asset_classes=asset_classes,
        max_assets_per_class=args.max_assets
    )
    
    pipeline.print_summary()
    
    return 0


def cmd_backtest(args):
    """Run backtest."""
    print(f"\n[BACKTEST] {args.symbol} ({args.timeframe})")
    print("-" * 50)
    
    system = get_system(args.app_id)
    
    if not system.start():
        print("ERROR: Could not connect to Deriv API")
        return 1
    
    try:
        system.load_models(args.model_dir)
        
        result = system.backtest_symbol(
            symbol=args.symbol,
            timeframe=args.timeframe,
            data_count=args.count
        )
        
        # Print results
        if 'error' in result:
            print(f"Error: {result['error']}")
        else:
            print(f"\nBacktest Results for {result['symbol']} {result['timeframe']}")
            print(f"  Total Trades:   {result['total_trades']}")
            print(f"  Win Rate:       {result['win_rate']:.1%}")
            print(f"  Profit Factor:  {result['profit_factor']:.2f}")
            print(f"  Total Return:   {result['total_return']:.2f}%")
            print(f"  Max Drawdown:   {result['max_drawdown']:.2%}")
            print(f"  Sharpe Ratio:   {result['sharpe_ratio']:.2f}")
            print(f"  Expectancy:     ${result['expectancy']:.2f}")
        
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\nResults saved: {args.output}")
    
    finally:
        system.stop()
    
    return 0


def cmd_dashboard(args):
    """Generate dashboard."""
    print(f"\n[DASHBOARD]")
    print("-" * 50)
    
    system = get_system(args.app_id)
    
    if not system.start():
        print("ERROR: Could not connect to Deriv API")
        return 1
    
    try:
        system.load_models(args.model_dir)
        
        # Analyze some assets to get signals
        symbols = args.symbols.split(',') if args.symbols else ["R_100", "frxEURUSD", "cryBTCUSD"]
        
        for symbol in symbols:
            print(f"Analyzing {symbol}...")
            system.analyze_symbol(symbol, data_count=1000)
            time.sleep(1)
        
        # Generate dashboard
        path = system.generate_dashboard(args.output or "./dashboard.html")
        print(f"\nDashboard generated: {path}")
    
    finally:
        system.stop()
    
    return 0


def cmd_monitor(args):
    """Monitor mode - continuous signal generation."""
    print(f"\n[MONITOR] Symbols: {args.symbols}")
    print(f"Interval: {args.interval}s")
    print("-" * 50)
    print("Press Ctrl+C to stop\n")
    
    system = get_system(args.app_id)
    
    if not system.start():
        print("ERROR: Could not connect to Deriv API")
        return 1
    
    symbols = [s.strip() for s in args.symbols.split(',')]
    
    try:
        system.load_models(args.model_dir)
        
        cycle = 0
        while True:
            cycle += 1
            print(f"\n--- Cycle {cycle} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ---")
            
            for symbol in symbols:
                try:
                    result = system.analyze_symbol(symbol, data_count=1000)
                    
                    if result['signals']:
                        for tf, sig in result['signals'].items():
                            emoji = "BUY " if 'BUY' in sig['type'] else "SELL"
                            print(f"  {emoji} {symbol} {tf} | "
                                  f"Conf: {sig['confidence']:.1%} | "
                                  f"Entry: {sig['entry']:.5f} | "
                                  f"TP: {sig['take_profit']:.5f} | "
                                  f"SL: {sig['stop_loss']:.5f}")
                    else:
                        print(f"  --- {symbol} | No signals")
                
                except Exception as e:
                    print(f"  ERROR {symbol}: {e}")
            
            time.sleep(args.interval)
    
    except KeyboardInterrupt:
        print("\n\nMonitoring stopped.")
    
    finally:
        system.stop()
    
    return 0


def cmd_live(args):
    """Live trading signal mode."""
    print(f"\n[LIVE] Symbols: {args.symbols}")
    print("-" * 50)
    print("High-frequency signal generation mode")
    print("Press Ctrl+C to stop\n")
    
    system = get_system(args.app_id)
    
    if not system.start():
        print("ERROR: Could not connect to Deriv API")
        return 1
    
    symbols = [s.strip() for s in args.symbols.split(',')]
    timeframes = [tf.strip() for tf in args.timeframes.split(',')] if args.timeframes else ['5m', '1h']
    
    try:
        system.load_models(args.model_dir)
        
        cycle = 0
        while True:
            cycle += 1
            print(f"\n{'='*60}")
            print(f"  LIVE SIGNAL CYCLE #{cycle}")
            print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}")
            
            all_signals = []
            
            for symbol in symbols:
                try:
                    result = system.analyze_symbol(symbol, data_count=2000)
                    
                    if result['signals']:
                        for tf, sig in result['signals'].items():
                            all_signals.append({
                                'symbol': symbol,
                                'timeframe': tf,
                                **sig
                            })
                except Exception as e:
                    print(f"  Error analyzing {symbol}: {e}")
            
            # Sort by confidence
            all_signals.sort(key=lambda x: x['confidence'], reverse=True)
            
            # Display top signals
            if all_signals:
                print(f"\n  TOP SIGNALS:")
                for i, sig in enumerate(all_signals[:10], 1):
                    emoji = "BUY " if 'BUY' in sig['type'] else "SELL"
                    print(f"  {i}. {emoji} {sig['symbol']} {sig['timeframe']} | "
                          f"Conf: {sig['confidence']:.1%} | "
                          f"R/R: {sig['risk_reward']:.2f}")
            else:
                print(f"\n  No signals this cycle.")
            
            # Stats
            stats = system.get_system_stats()
            print(f"\n  Stats: {stats['signals_generated']} signals | "
                  f"{stats['analysis_cycles']} cycles | "
                  f"{stats['errors']} errors")
            
            time.sleep(args.interval)
    
    except KeyboardInterrupt:
        print("\n\nLive mode stopped.")
    
    finally:
        system.stop()
    
    return 0


def cmd_list_assets(args):
    """List available assets."""
    print(f"\n[AVAILABLE ASSETS]")
    print("-" * 60)
    
    for asset_class in AssetClass:
        assets = DERIV_ASSETS.get(asset_class, [])
        print(f"\n{asset_class.value.upper()} ({len(assets)} assets):")
        for symbol in assets:
            print(f"  - {symbol}")
    
    return 0


def cmd_status(args):
    """Show system status."""
    print(f"\n[SYSTEM STATUS]")
    print("-" * 50)
    
    system = get_system(args.app_id)
    stats = system.get_system_stats()
    
    print(f"Status:          {'Running' if stats['is_running'] else 'Stopped'}")
    print(f"Uptime:          {stats['uptime_seconds']:.0f}s")
    print(f"Signals:         {stats['signals_generated']}")
    print(f"Analysis Cycles: {stats['analysis_cycles']}")
    print(f"Errors:          {stats['errors']}")
    print(f"Symbols:         {stats['symbols_tracked']}")
    print(f"Models:          {stats['models_loaded']}")
    print(f"Timeframes:      {', '.join(stats['timeframes'])}")
    
    return 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="DERIV Multi-Agent Trading Analysis System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze a single symbol
  python main.py analyze --symbol R_100 --timeframe 1h

  # Analyze all forex pairs
  python main.py analyze-all --assets forex

  # Train models for synthetic indices
  python main.py train --asset-class synthetic

  # Backtest a strategy
  python main.py backtest --symbol R_100 --timeframe 1h --count 5000

  # Monitor multiple symbols
  python main.py monitor --symbols R_100,frxEURUSD,cryBTCUSD --interval 60

  # Live high-frequency signals
  python main.py live --symbols R_100 --timeframes 5m,1h

  # List all available assets
  python main.py list-assets
        """
    )
    
    # Global options
    parser.add_argument('--app-id', type=int, default=1089,
                       help='Deriv API app ID (default: 1089)')
    parser.add_argument('--model-dir', type=str, default='./models',
                       help='Model directory (default: ./models)')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Analyze
    analyze_parser = subparsers.add_parser('analyze', help='Analyze a single symbol')
    analyze_parser.add_argument('--symbol', required=True, help='Symbol to analyze')
    analyze_parser.add_argument('--timeframe', default='1h', help='Timeframe (default: 1h)')
    analyze_parser.add_argument('--asset-class', help='Asset class override')
    analyze_parser.add_argument('--count', type=int, default=2000, help='Candle count')
    analyze_parser.add_argument('--output', help='Save results to JSON file')
    
    # Analyze All
    analyze_all_parser = subparsers.add_parser('analyze-all', help='Analyze multiple assets')
    analyze_all_parser.add_argument('--assets', default='synthetic', 
                                    help='Asset classes (comma-separated)')
    analyze_all_parser.add_argument('--max-assets', type=int, default=5, 
                                    help='Max assets per class')
    analyze_all_parser.add_argument('--output', help='Save results to JSON file')
    
    # Train
    train_parser = subparsers.add_parser('train', help='Train ML models')
    train_parser.add_argument('--asset-class', help='Asset class to train')
    train_parser.add_argument('--max-assets', type=int, default=5, 
                             help='Max assets per class')
    
    # Train All
    train_all_parser = subparsers.add_parser('train-all', help='Train all models')
    train_all_parser.add_argument('--asset-classes', 
                                  help='Comma-separated asset classes')
    train_all_parser.add_argument('--max-assets', type=int, default=5)
    
    # Backtest
    backtest_parser = subparsers.add_parser('backtest', help='Run backtest')
    backtest_parser.add_argument('--symbol', required=True, help='Symbol to backtest')
    backtest_parser.add_argument('--timeframe', default='1h', help='Timeframe')
    backtest_parser.add_argument('--count', type=int, default=5000, 
                                help='Historical candle count')
    backtest_parser.add_argument('--output', help='Save results to JSON')
    
    # Dashboard
    dashboard_parser = subparsers.add_parser('dashboard', help='Generate dashboard')
    dashboard_parser.add_argument('--symbols', help='Symbols (comma-separated)')
    dashboard_parser.add_argument('--output', default='./dashboard.html', 
                                 help='Output file')
    
    # Monitor
    monitor_parser = subparsers.add_parser('monitor', help='Monitor mode')
    monitor_parser.add_argument('--symbols', required=True, 
                               help='Symbols to monitor (comma-separated)')
    monitor_parser.add_argument('--interval', type=int, default=60, 
                               help='Check interval in seconds')
    
    # Live
    live_parser = subparsers.add_parser('live', help='Live signal mode')
    live_parser.add_argument('--symbols', required=True, 
                            help='Symbols (comma-separated)')
    live_parser.add_argument('--timeframes', default='5m,1h', 
                            help='Timeframes (comma-separated)')
    live_parser.add_argument('--interval', type=int, default=30, 
                            help='Cycle interval in seconds')
    
    # List Assets
    subparsers.add_parser('list-assets', help='List available assets')
    
    # Status
    subparsers.add_parser('status', help='Show system status')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Setup logging
    if args.debug:
        import logging
        logging.getLogger().setLevel(logging.DEBUG)
    
    print_banner()
    
    # Route command
    commands = {
        'analyze': cmd_analyze,
        'analyze-all': cmd_analyze_all,
        'train': cmd_train,
        'train-all': cmd_train_all,
        'backtest': cmd_backtest,
        'dashboard': cmd_dashboard,
        'monitor': cmd_monitor,
        'live': cmd_live,
        'list-assets': cmd_list_assets,
        'status': cmd_status,
    }
    
    cmd_func = commands.get(args.command)
    if cmd_func:
        return cmd_func(args)
    else:
        print(f"Unknown command: {args.command}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
