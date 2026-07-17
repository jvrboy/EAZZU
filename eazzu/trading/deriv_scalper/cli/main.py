"""
CLI Main Interface
Interactive command-line interface for the Deriv Scalper Bot
"""

import asyncio
import sys
import os
import json
from typing import Optional
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import ScalperBot, TradingLogger
from config import TradingConfig


class CLI:
    """
    Command-Line Interface for the trading bot
    """

    def __init__(self):
        self.bot: Optional[ScalperBot] = None
        self.running = False
        self.logger = TradingLogger()

    def print_banner(self):
        """Print ASCII banner"""
        banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║   ██████╗  ██████╗  ██████╗ ███╗   ███╗███████╗████████╗ ║
    ║   ██╔══██╗██╔═══██╗██╔═══██╗████╗ ████║██╔════╝╚══██╔══╝ ║
    ║   ██████╔╝██║   ██║██║   ██║██╔████╔██║█████╗     ██║    ║
    ║   ██╔═══╝ ██║   ██║██║   ██║██║╚██╔╝██║██╔══╝     ██║    ║
    ║   ██║     ╚██████╔╝╚██████╔╝██║ ╚═╝ ██║███████╗   ██║    ║
    ║   ╚═╝      ╚═════╝  ╚═════╝ ╚═╝     ╚═╝╚══════╝   ╚═╝    ║
    ║                                                           ║
    ║   ██████╗  ██████╗  ██████╗ ████████╗ ██████╗  ██████╗ ██████╗╗███████╗██████╗ ║
    ║   ██╔══██╗██╔═══██╗██╔═══██╗╚══██╔══╝██╔═══██╗██╔════╝██╔════╝██╔════╝██╔══██╗║
    ║   ██████╔╝██║   ██║██║   ██║   ██║   ██║   ██║██║     ██║     █████╗  ██████╔╝║
    ║   ██╔═══╝ ██║   ██║██║   ██║   ██║   ██║   ██║██║     ██║     ██╔══╝  ██╔══██╗║
    ║   ██║     ╚██████╔╝╚██████╔╝   ██║   ╚██████╔╝╚██████╗╚██████╗███████╗██║  ██║║
    ║   ╚═╝      ╚═════╝  ╚═════╝    ╚═╝    ╚═════╝  ╚═════╝ ╚═════╝╚══════╝╚═╝  ╚═╝║
    ║                                                           ║
    ║   ═══════════════ 24/7 PERPETUAL SCALPER ═══════════════  ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
        """
        print(banner)

    def print_menu(self):
        """Print command menu"""
        menu = """
    ┌─────────────────────────────────────────────────────────────┐
    │  Commands:                                                 │
    │  ─────────────────────────────────────────────────────────  │
    │  start          - Start the trading bot (simulation mode)  │
    │  start live     - Start the trading bot (live mode)        │
    │  stop           - Stop the trading bot                     │
    │  pause           - Pause trading                           │
    │  resume          - Resume trading                          │
    │  stats          - Show current statistics                   │
    │  trades         - Show recent trades                       │
    │  backtest       - Run a backtest                           │
    │  indicators     - Show indicator configuration             │
    │  set <key> <val>- Set configuration value                  │
    │  config         - Show current configuration               │
    │  clear          - Clear screen                             │
    │  help           - Show this help                           │
    │  exit           - Exit the application                     │
    └─────────────────────────────────────────────────────────────┘
        """
        print(menu)

    async def cmd_start(self, args: list):
        """Start the bot"""
        if self.bot and self.bot.is_running:
            print("Bot is already running. Use 'stop' first.")
            return

        use_live = 'live' in args

        if use_live:
            print("Starting bot in LIVE mode...")
            print("WARNING: Real money will be used!")
        else:
            print("Starting bot in SIMULATION mode...")

        self.bot = ScalperBot()

        # Set up callbacks
        self.bot.on_trade = self._on_trade
        self.bot.on_stats_update = self._on_stats_update

        success = await self.bot.start(use_simulation=not use_live)

        if success:
            print("Bot started successfully!")
            self.running = True
        else:
            print("Failed to start bot.")

    def cmd_stop(self):
        """Stop the bot"""
        if self.bot:
            asyncio.create_task(self.bot.stop())
            print("Bot stopped.")
        else:
            print("Bot is not running.")

    def cmd_pause(self):
        """Pause trading"""
        if self.bot:
            asyncio.create_task(self.bot.pause())
            print("Bot paused.")
        else:
            print("Bot is not running.")

    def cmd_resume(self):
        """Resume trading"""
        if self.bot:
            asyncio.create_task(self.bot.resume())
            print("Bot resumed.")
        else:
            print("Bot is not running.")

    def cmd_stats(self):
        """Show statistics"""
        if self.bot:
            stats = self.bot.get_stats()
            print("\n" + "=" * 50)
            print("BOT STATISTICS")
            print("=" * 50)
            print(f"Status:        {'RUNNING' if stats['running'] else 'STOPPED'} {'(PAUSED)' if stats['paused'] else ''}")
            print(f"Uptime:        {stats['uptime_seconds']:.0f} seconds")
            print(f"Total Trades:  {stats['total_trades']}")
            print(f"Win Rate:      {stats.get('win_rate', 0):.1f}%")
            print(f"Total Profit:  ${stats['total_profit']:.2f}")
            print(f"Current Streak:{stats['current_streak']}")
            print(f"Max Streak:    {stats['max_streak']}")
            print(f"Consecutive:   {stats['consecutive_losses']} losses")
            print("=" * 50)
        else:
            print("Bot is not running.")

    def cmd_trades(self):
        """Show recent trades"""
        if self.bot:
            trades = self.bot.get_recent_trades(10)
            if trades:
                print("\n" + "=" * 70)
                print(f"{'ID':<15} {'Direction':<10} {'Profit':<10} {'Duration':<10}")
                print("-" * 70)
                for trade in trades:
                    emoji = "+" if trade['is_winning'] else "-"
                    print(f"{trade['contract_id']:<15} {trade['direction']:<10} {emoji}${abs(trade['profit']):<9.2f} {trade['duration_seconds']:.1f}s")
                print("=" * 70)
            else:
                print("No trades yet.")
        else:
            print("Bot is not running.")

    async def cmd_backtest(self, args: list):
        """Run backtest"""
        duration = 3600  # Default 1 hour
        if args:
            try:
                duration = int(args[0])
            except ValueError:
                print("Invalid duration. Using default (3600 seconds).")

        print(f"Running backtest for {duration} seconds...")

        if not self.bot:
            self.bot = ScalperBot()

        results = await self.bot.run_backtest(duration)

        print("\n" + "=" * 50)
        print("BACKTEST RESULTS")
        print("=" * 50)
        print(f"Total Trades:   {results['total_trades']}")
        print(f"Wins:           {results['wins']}")
        print(f"Losses:         {results['losses']}")
        print(f"Win Rate:       {results['win_rate']:.1f}%")
        print(f"Total Profit:   ${results['total_profit']:.2f}")
        print(f"Avg Profit:     ${results['avg_profit']:.4f}")
        print("=" * 50)

    def cmd_indicators(self):
        """Show indicator configuration"""
        if self.bot:
            status = self.bot.get_indicators_status()
            print("\n" + "=" * 30)
            print("INDICATOR STATUS")
            print("=" * 30)
            for name, enabled in status.items():
                status_str = "ENABLED" if enabled else "DISABLED"
                print(f"{name:<15} {status_str}")
            print("=" * 30)
        else:
            print("Bot is not initialized. Start first to see indicators.")

    def cmd_config(self):
        """Show current configuration"""
        if self.bot:
            config = self.bot.config
            print("\n" + "=" * 50)
            print("CURRENT CONFIGURATION")
            print("=" * 50)
            print(f"Symbol:         {config.symbol.symbol}")
            print(f"Display Name:   {config.symbol.display_name}")
            print(f"Fixed Lot:      {config.fixed_lot_size}")
            print(f"Min Duration:   {config.trade_duration_min}s")
            print(f"Max Duration:   {config.trade_duration_max}s")
            print(f"Profit Target:  {config.profit_target_percent}%")
            print(f"Loss Threshold: {config.loss_threshold_percent}%")
            print(f"Never Stop:     {config.never_stop}")
            print(f"Max Consecutive:{config.max_consecutive_losses}")
            print("=" * 50)
        else:
            print("Bot is not initialized.")

    def cmd_set(self, args: list):
        """Set configuration value"""
        if len(args) < 2:
            print("Usage: set <key> <value>")
            return

        key, value = args[0], args[1]

        # Map of settable values
        settable = {
            'fixed_lot_size': float,
            'profit_target_percent': float,
            'loss_threshold_percent': float,
            'max_consecutive_losses': int,
            'min_indicators_agree': int,
        }

        if key in settable:
            try:
                converted = settable[key](value)
                if self.bot:
                    setattr(self.bot.config, key, converted)
                print(f"Set {key} = {converted}")
            except ValueError:
                print(f"Invalid value for {key}")
        else:
            print(f"Unknown key: {key}. Available keys: {list(settable.keys())}")

    def _on_trade(self, result, indicator_result):
        """Callback when trade is executed"""
        if result:
            print(f"\n>>> TRADE: {result.direction.value} | Profit: {result.profit:+.2f} | Duration: {result.duration_seconds:.1f}s")

    def _on_stats_update(self, stats):
        """Callback when stats are updated"""
        pass  # Could print periodic updates

    async def run(self):
        """Main CLI loop"""
        self.print_banner()
        self.print_menu()

        while True:
            try:
                command = input("\nderiv-scalper> ").strip().lower()

                if not command:
                    continue

                parts = command.split()
                cmd = parts[0]
                args = parts[1:] if len(parts) > 1 else []

                if cmd == 'start':
                    await self.cmd_start(args)
                elif cmd == 'stop':
                    self.cmd_stop()
                elif cmd == 'pause':
                    self.cmd_pause()
                elif cmd == 'resume':
                    self.cmd_resume()
                elif cmd == 'stats':
                    self.cmd_stats()
                elif cmd == 'trades':
                    self.cmd_trades()
                elif cmd == 'backtest':
                    await self.cmd_backtest(args)
                elif cmd == 'indicators':
                    self.cmd_indicators()
                elif cmd == 'config':
                    self.cmd_config()
                elif cmd == 'set':
                    self.cmd_set(args)
                elif cmd == 'clear' or cmd == 'cls':
                    os.system('cls' if os.name == 'nt' else 'clear')
                elif cmd == 'help' or cmd == '?':
                    self.print_menu()
                elif cmd == 'exit' or cmd == 'quit':
                    if self.bot and self.bot.is_running:
                        await self.bot.stop()
                    print("Goodbye!")
                    break
                else:
                    print(f"Unknown command: {cmd}. Type 'help' for available commands.")

            except KeyboardInterrupt:
                print("\nUse 'exit' to quit.")
            except Exception as e:
                print(f"Error: {e}")

        return 0


def main():
    """Main entry point"""
    cli = CLI()
    try:
        asyncio.run(cli.run())
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == '__main__':
    main()
