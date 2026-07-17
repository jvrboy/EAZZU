"""
Deriv Scalper Bot
Main entry point for the 24/7 perpetual trading bot

Usage:
    python main.py              # Start GUI
    python main.py --cli         # Start CLI
    python main.py --backtest   # Run backtest
    python main.py --test       # Test the bot
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from cli.main import CLI
from gui.dashboard import TradingDashboard
from core import ScalperBot
from backtest import BacktestEngine, SyntheticDataGenerator
from config import TradingConfig


def run_gui():
    """Run the GUI dashboard"""
    print("Starting GUI dashboard...")
    app = TradingDashboard()
    app.run()


def run_cli():
    """Run the CLI interface"""
    print("Starting CLI interface...")
    cli = CLI()
    try:
        import asyncio
        asyncio.run(cli.run())
    except KeyboardInterrupt:
        print("\nGoodbye!")


def run_backtest(args):
    """Run backtest simulation"""
    print("=" * 60)
    print("DERIV SCALPER BOT - BACKTEST MODE")
    print("=" * 60)

    # Load config
    config = TradingConfig()

    if args.config:
        config = TradingConfig.load(args.config)
        print(f"Loaded configuration from {args.config}")

    # Generate or load data
    if args.data:
        print(f"Loading data from {args.data}")
        # TODO: Implement data loading
    else:
        print("Generating synthetic data...")
        generator = SyntheticDataGenerator(
            base_price=5000.0,
            volatility=0.5,
            seed=42
        )
        candles = generator.generate_candles(count=5000)

    # Run backtest
    print(f"\nRunning backtest with {len(candles)} candles...")
    engine = BacktestEngine(config)
    result = engine.run(candles)

    # Display results
    report = engine.generate_report(result)
    print(report)

    # Save results
    if args.output:
        output_path = Path(args.output)
        result.save(str(output_path))
        print(f"\nResults saved to {output_path}")


async def test_bot():
    """Test the bot in simulation mode"""
    print("=" * 60)
    print("DERIV SCALPER BOT - TEST MODE")
    print("=" * 60)

    # Create bot
    bot = ScalperBot()

    # Set up callbacks
    def on_trade(result, indicator_result):
        if result:
            print(f"\n>>> TRADE: {result.direction.value} | P/L: ${result.profit:.2f} | Duration: {result.duration_seconds:.1f}s")

    def on_stats(stats):
        if stats['total_trades'] % 10 == 0:
            print(f"Stats: {stats['total_trades']} trades, ${stats['total_profit']:.2f} P/L")

    bot.on_trade = on_trade
    bot.on_stats_update = on_stats

    # Start bot
    print("\nStarting bot in simulation mode...")
    await bot.start(use_simulation=True)

    # Run for 60 seconds
    import asyncio
    await asyncio.sleep(60)

    # Get final stats
    stats = bot.get_stats()
    print("\n" + "=" * 60)
    print("FINAL TEST RESULTS")
    print("=" * 60)
    print(f"Total Trades:    {stats['total_trades']}")
    print(f"Win Rate:        {stats.get('win_rate', 0):.1f}%")
    print(f"Total Profit:    ${stats['total_profit']:.2f}")
    print(f"Max Streak:      {stats['max_streak']}")
    print("=" * 60)

    # Stop bot
    await bot.stop()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Deriv Scalper Bot - 24/7 Perpetual Trading',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python main.py                 # Start GUI dashboard
    python main.py --cli           # Start CLI interface
    python main.py --test          # Test the bot for 60 seconds
    python main.py --backtest      # Run a backtest
    python main.py --backtest --output results.json  # Save backtest results
        """
    )

    parser.add_argument('--cli', action='store_true',
                       help='Start CLI interface instead of GUI')
    parser.add_argument('--test', action='store_true',
                       help='Test the bot in simulation mode')
    parser.add_argument('--backtest', action='store_true',
                       help='Run backtest simulation')
    parser.add_argument('--config', type=str,
                       help='Path to configuration file')
    parser.add_argument('--data', type=str,
                       help='Path to historical data file')
    parser.add_argument('--output', type=str,
                       help='Path to save backtest results')

    args = parser.parse_args()

    if args.test:
        import asyncio
        asyncio.run(test_bot())
    elif args.backtest:
        run_backtest(args)
    elif args.cli:
        run_cli()
    else:
        run_gui()


if __name__ == '__main__':
    main()
