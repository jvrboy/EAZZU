"""
Trading Dashboard
Main GUI window for the Deriv Scalper Bot
"""

import asyncio
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
from typing import Optional, Dict, Any
import sys
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import ScalperBot
from config import TradingConfig


class TradingDashboard:
    """
    Main Trading Dashboard
    Tkinter-based GUI for the trading bot
    """

    def __init__(self):
        # Initialize Tkinter
        self.root = tk.Tk()
        self.root.title("Deriv Scalper Bot - 24/7 Perpetual Trading")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)

        # Configure styles
        self._setup_styles()

        # Bot instance
        self.bot: Optional[ScalperBot] = None
        self.update_job: Optional[Any] = None

        # Create UI
        self._create_widgets()

        # Bind close event
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')

        # Colors
        bg_color = '#1a1a2e'
        fg_color = '#eaeaea'
        accent_color = '#00d4aa'
        danger_color = '#ff4757'
        success_color = '#2ed573'

        style.configure('.', background=bg_color, foreground=fg_color)
        style.configure('TFrame', background=bg_color)
        style.configure('Card.TFrame', background='#16213e', relief='raised')

        # Labels
        style.configure('Title.TLabel',
                       font=('Helvetica', 18, 'bold'),
                       foreground=accent_color,
                       background=bg_color)

        style.configure('Header.TLabel',
                       font=('Helvetica', 12, 'bold'),
                       foreground=fg_color,
                       background=bg_color)

        style.configure('Stat.TLabel',
                       font=('Helvetica', 10),
                       foreground=fg_color,
                       background=bg_color)

        # Buttons
        style.configure('Start.TButton',
                       font=('Helvetica', 10, 'bold'),
                       foreground='#1a1a2e',
                       background=success_color)

        style.configure('Stop.TButton',
                       font=('Helvetica', 10, 'bold'),
                       foreground='#fff',
                       background=danger_color)

        style.configure('Action.TButton',
                       font=('Helvetica', 9),
                       foreground=fg_color,
                       background='#16213e')

        # Treeview
        style.configure('Treeview',
                       background='#16213e',
                       foreground=fg_color,
                       fieldbackground='#16213e',
                       rowheight=25)

        style.configure('Treeview.Heading',
                       background='#0f3460',
                       foreground=accent_color)

    def _create_widgets(self):
        """Create all UI widgets"""
        # Main container
        main_container = ttk.Frame(self.root)
        main_container.pack(fill='both', expand=True, padx=10, pady=10)

        # Header
        header_frame = ttk.Frame(main_container)
        header_frame.pack(fill='x', pady=(0, 10))

        title = ttk.Label(header_frame, text="DERIV SCALPER BOT", style='Title.TLabel')
        title.pack(side='left')

        self.status_label = ttk.Label(header_frame, text="Status: STOPPED",
                                     font=('Helvetica', 10, 'bold'),
                                     foreground='#ff4757')
        self.status_label.pack(side='right')

        # Main content area
        content = ttk.Frame(main_container)
        content.pack(fill='both', expand=True)

        # Left panel - Controls and Stats
        left_panel = ttk.Frame(content, width=300)
        left_panel.pack(side='left', fill='y', padx=(0, 10))
        left_panel.pack_propagate(False)

        self._create_control_panel(left_panel)
        self._create_stats_panel(left_panel)

        # Center panel - Trade History
        center_panel = ttk.Frame(content)
        center_panel.pack(side='left', fill='both', expand=True)

        self._create_trade_history_panel(center_panel)

        # Right panel - Log
        right_panel = ttk.Frame(content, width=350)
        right_panel.pack(side='right', fill='both', padx=(10, 0))
        right_panel.pack_propagate(False)

        self._create_log_panel(right_panel)

        # Indicator status bar
        self._create_indicator_bar(main_container)

    def _create_control_panel(self, parent):
        """Create control buttons panel"""
        control_frame = ttk.LabelFrame(parent, text="Controls", padding=10)
        control_frame.pack(fill='x', pady=(0, 10))

        # Buttons
        btn_frame = ttk.Frame(control_frame)
        btn_frame.pack()

        self.start_btn = ttk.Button(btn_frame, text="START",
                                    style='Start.TButton',
                                    command=self._on_start)
        self.start_btn.pack(side='left', padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="STOP",
                                   style='Stop.TButton',
                                   command=self._on_stop, state='disabled')
        self.stop_btn.pack(side='left', padx=5)

        # Mode selection
        mode_frame = ttk.Frame(control_frame)
        mode_frame.pack(fill='x', pady=(10, 0))

        self.live_mode = tk.BooleanVar(value=False)
        mode_check = ttk.Checkbutton(mode_frame, text="Live Mode (Real Money)",
                                     variable=self.live_mode,
                                     command=self._on_mode_change)
        mode_check.pack(anchor='w')

        # Pause/Resume
        pause_frame = ttk.Frame(control_frame)
        pause_frame.pack(fill='x', pady=(10, 0))

        self.pause_btn = ttk.Button(pause_frame, text="PAUSE",
                                    style='Action.TButton',
                                    command=self._on_pause, state='disabled')
        self.pause_btn.pack(side='left', padx=5)

        self.resume_btn = ttk.Button(pause_frame, text="RESUME",
                                      style='Action.TButton',
                                      command=self._on_resume, state='disabled')
        self.resume_btn.pack(side='left', padx=5)

        # Backtest button
        backtest_btn = ttk.Button(pause_frame, text="BACKTEST",
                                  style='Action.TButton',
                                  command=self._on_backtest)
        backtest_btn.pack(side='left', padx=5)

    def _create_stats_panel(self, parent):
        """Create statistics panel"""
        stats_frame = ttk.LabelFrame(parent, text="Statistics", padding=10)
        stats_frame.pack(fill='both', expand=True)

        # Stats grid
        self.stat_labels = {}

        stats = [
            ('Total Trades', 'total_trades'),
            ('Win Rate', 'win_rate'),
            ('Total Profit', 'total_profit'),
            ('Current Streak', 'current_streak'),
            ('Max Streak', 'max_streak'),
            ('Consecutive Losses', 'consecutive_losses'),
            ('Wins', 'wins'),
            ('Losses', 'losses'),
            ('Uptime', 'uptime'),
        ]

        for i, (label, key) in enumerate(stats):
            row = i // 2
            col = (i % 2) * 2

            lbl = ttk.Label(stats_frame, text=f"{label}:", style='Stat.TLabel')
            lbl.grid(row=row, column=col, sticky='w', padx=(0, 5), pady=2)

            val_lbl = ttk.Label(stats_frame, text="--", style='Stat.TLabel',
                                foreground='#00d4aa')
            val_lbl.grid(row=row, column=col+1, sticky='w', pady=2)

            self.stat_labels[key] = val_lbl

        # Balance display
        balance_frame = ttk.Frame(stats_frame)
        balance_frame.grid(row=5, column=0, columnspan=4, pady=(10, 0), sticky='ew')

        ttk.Label(balance_frame, text="Balance:", style='Header.TLabel').pack(side='left')
        self.balance_label = ttk.Label(balance_frame, text="$0.00",
                                       font=('Helvetica', 14, 'bold'),
                                       foreground='#00d4aa')
        self.balance_label.pack(side='left', padx=10)

    def _create_trade_history_panel(self, parent):
        """Create trade history table"""
        history_frame = ttk.LabelFrame(parent, text="Trade History", padding=10)
        history_frame.pack(fill='both', expand=True)

        # Treeview
        columns = ('ID', 'Direction', 'Entry', 'Exit', 'Profit', 'Duration', 'Status')
        self.trade_tree = ttk.Treeview(history_frame, columns=columns,
                                       show='headings', height=15)

        # Column configuration
        self.trade_tree.heading('ID', text='Contract ID')
        self.trade_tree.heading('Direction', text='Direction')
        self.trade_tree.heading('Entry', text='Entry Price')
        self.trade_tree.heading('Exit', text='Exit Price')
        self.trade_tree.heading('Profit', text='Profit')
        self.trade_tree.heading('Duration', text='Duration (s)')
        self.trade_tree.heading('Status', text='Status')

        self.trade_tree.column('ID', width=120)
        self.trade_tree.column('Direction', width=80)
        self.trade_tree.column('Entry', width=100)
        self.trade_tree.column('Exit', width=100)
        self.trade_tree.column('Profit', width=100)
        self.trade_tree.column('Duration', width=100)
        self.trade_tree.column('Status', width=100)

        # Scrollbar
        scrollbar = ttk.Scrollbar(history_frame, orient='vertical',
                                  command=self.trade_tree.yview)
        self.trade_tree.configure(yscrollcommand=scrollbar.set)

        self.trade_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Tags for coloring
        self.trade_tree.tag_configure('win', foreground='#2ed573')
        self.trade_tree.tag_configure('loss', foreground='#ff4757')

    def _create_log_panel(self, parent):
        """Create log display panel"""
        log_frame = ttk.LabelFrame(parent, text="Activity Log", padding=10)
        log_frame.pack(fill='both', expand=True)

        self.log_text = scrolledtext.ScrolledText(log_frame,
                                                   width=40,
                                                   height=30,
                                                   font=('Consolas', 9),
                                                   bg='#0d1117',
                                                   fg='#c9d1d9',
                                                   insertbackground='white',
                                                   relief='flat')
        self.log_text.pack(fill='both', expand=True)

        # Clear button
        clear_btn = ttk.Button(log_frame, text="Clear Log",
                              style='Action.TButton',
                              command=self._clear_log)
        clear_btn.pack(pady=(5, 0))

    def _create_indicator_bar(self, parent):
        """Create indicator status bar at bottom"""
        indicator_frame = ttk.Frame(parent)
        indicator_frame.pack(fill='x', pady=(10, 0))

        ttk.Label(indicator_frame, text="Indicators:",
                 style='Header.TLabel').pack(side='left', padx=(0, 10))

        self.indicator_labels = {}

        indicators = ['RSI', 'MACD', 'EMA', 'Bollinger', 'Stochastic', 'ATR', 'PriceAction']

        for ind in indicators:
            lbl = ttk.Label(indicator_frame, text=f"{ind}: ON",
                           font=('Helvetica', 9),
                           foreground='#2ed573',
                           background='#16213e',
                           padding=(5, 2))
            lbl.pack(side='left', padx=5)
            self.indicator_labels[ind] = lbl

    def _log(self, message: str):
        """Add message to log panel"""
        self.log_text.insert('end', f"{message}\n")
        self.log_text.see('end')

    def _clear_log(self):
        """Clear the log panel"""
        self.log_text.delete(1.0, 'end')

    def _on_start(self):
        """Start button clicked"""
        self._log("[INFO] Starting bot...")

        mode = "LIVE" if self.live_mode.get() else "SIMULATION"
        self._log(f"[INFO] Mode: {mode}")

        # Create bot
        self.bot = ScalperBot()

        # Set up callbacks
        def on_trade(result, indicator_result):
            if result:
                self._log(f"[TRADE] {result.direction.value} | P/L: {result.profit:+.2f}")
                self.root.after(0, self._add_trade_to_tree, result)

        def on_stats(stats):
            self.root.after(0, self._update_stats, stats)

        self.bot.on_trade = on_trade
        self.bot.on_stats_update = on_stats

        # Start bot in thread
        def run_bot():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.bot.start(use_simulation=not self.live_mode.get()))
            finally:
                loop.close()

        self.bot_thread = threading.Thread(target=run_bot, daemon=True)
        self.bot_thread.start()

        # Update UI
        self.start_btn.configure(state='disabled')
        self.stop_btn.configure(state='normal')
        self.pause_btn.configure(state='normal')
        self.status_label.configure(text="Status: RUNNING", foreground='#2ed573')

        self._log("[INFO] Bot started successfully!")

    def _on_stop(self):
        """Stop button clicked"""
        if self.bot:
            self._log("[INFO] Stopping bot...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.bot.stop())
            loop.close()

        self.start_btn.configure(state='normal')
        self.stop_btn.configure(state='disabled')
        self.pause_btn.configure(state='disabled')
        self.resume_btn.configure(state='disabled')
        self.status_label.configure(text="Status: STOPPED", foreground='#ff4757')

        self._log("[INFO] Bot stopped.")

    def _on_pause(self):
        """Pause button clicked"""
        if self.bot:
            self.bot._paused = True
            self.pause_btn.configure(state='disabled')
            self.resume_btn.configure(state='normal')
            self.status_label.configure(text="Status: PAUSED", foreground='#ffa502')
            self._log("[INFO] Bot paused.")

    def _on_resume(self):
        """Resume button clicked"""
        if self.bot:
            self.bot._paused = False
            self.pause_btn.configure(state='normal')
            self.resume_btn.configure(state='disabled')
            self.status_label.configure(text="Status: RUNNING", foreground='#2ed573')
            self._log("[INFO] Bot resumed.")

    def _on_mode_change(self):
        """Mode checkbox changed"""
        if self.live_mode.get():
            self._log("[WARNING] Live mode enabled - REAL MONEY will be used!")

    def _on_backtest(self):
        """Backtest button clicked"""
        self._log("[INFO] Running backtest...")

        def run_backtest():
            if not self.bot:
                self.bot = ScalperBot()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            results = loop.run_until_complete(self.bot.run_backtest(300))
            loop.close()

            self.root.after(0, self._show_backtest_results, results)

        thread = threading.Thread(target=run_backtest, daemon=True)
        thread.start()

    def _show_backtest_results(self, results):
        """Display backtest results"""
        msg = f"""
BACKTEST RESULTS
================
Total Trades: {results['total_trades']}
Wins: {results['wins']}
Losses: {results['losses']}
Win Rate: {results['win_rate']:.1f}%
Total Profit: ${results['total_profit']:.2f}
"""
        messagebox.showinfo("Backtest Results", msg)
        self._log("[INFO] Backtest completed!")

    def _add_trade_to_tree(self, result):
        """Add trade to the tree view"""
        # Clear existing items
        for item in self.trade_tree.get_children():
            self.trade_tree.delete(item)

        # Add new trade
        status = "WIN" if result.is_winning else "LOSS"
        tag = 'win' if result.is_winning else 'loss'

        self.trade_tree.insert('', 0, values=(
            result.contract_id,
            result.direction.value,
            f"{result.entry_price:.2f}",
            f"{result.exit_price:.2f}",
            f"${result.profit:.2f}",
            f"{result.duration_seconds:.1f}",
            status
        ), tags=(tag,))

    def _update_stats(self, stats):
        """Update statistics display"""
        self.stat_labels['total_trades'].configure(text=str(stats.get('total_trades', 0)))
        self.stat_labels['win_rate'].configure(text=f"{stats.get('win_rate', 0):.1f}%")
        self.stat_labels['total_profit'].configure(text=f"${stats.get('total_profit', 0):.2f}")
        self.stat_labels['current_streak'].configure(text=str(stats.get('current_streak', 0)))
        self.stat_labels['max_streak'].configure(text=str(stats.get('max_streak', 0)))
        self.stat_labels['consecutive_losses'].configure(text=str(stats.get('consecutive_losses', 0)))
        self.stat_labels['wins'].configure(text=str(stats.get('winning_trades', 0)))
        self.stat_labels['losses'].configure(text=str(stats.get('losing_trades', 0)))

        uptime = stats.get('uptime_seconds', 0)
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        seconds = int(uptime % 60)
        self.stat_labels['uptime'].configure(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")

        self.balance_label.configure(text=f"${stats.get('balance', 0):.2f}")

    def _on_close(self):
        """Window close event"""
        if self.bot and self.bot.is_running:
            if messagebox.askyesno("Confirm", "Bot is running. Stop and exit?"):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.bot.stop())
                loop.close()
        self.root.destroy()

    def run(self):
        """Start the GUI main loop"""
        self._log("=" * 40)
        self._log("DERIV SCALPER BOT - Ready")
        self._log("=" * 40)
        self._log("Click START to begin trading")
        self._log("Enable Live Mode at your own risk!")
        self.root.mainloop()


def main():
    """Main entry point for GUI"""
    app = TradingDashboard()
    app.run()


if __name__ == '__main__':
    main()
