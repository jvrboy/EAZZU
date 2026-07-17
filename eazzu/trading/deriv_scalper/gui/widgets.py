"""
GUI Widgets
Reusable Tkinter widgets for the trading dashboard
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, Any, Callable


class StatsPanel(ttk.Frame):
    """Statistics display panel"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)

        self.stat_labels: Dict[str, tk.Label] = {}
        self._create_widgets()

    def _create_widgets(self):
        """Create stat widgets"""
        stats = [
            ('Total Trades', 'total_trades'),
            ('Win Rate', 'win_rate'),
            ('Total Profit', 'total_profit'),
            ('Current Streak', 'current_streak'),
            ('Max Streak', 'max_streak'),
            ('Consecutive Losses', 'consecutive_losses'),
        ]

        for i, (label, key) in enumerate(stats):
            row = i // 2
            col = (i % 2) * 2

            ttk.Label(self, text=f"{label}:",
                     style='Stat.TLabel').grid(
                row=row, column=col, sticky='w', padx=5, pady=2)

            val_lbl = ttk.Label(self, text="--",
                              foreground='#00d4aa')
            val_lbl.grid(row=row, column=col+1, sticky='w', pady=2)

            self.stat_labels[key] = val_lbl

    def update_stats(self, stats: Dict[str, Any]):
        """Update displayed statistics"""
        for key, label in self.stat_labels.items():
            if key in stats:
                value = stats[key]
                if key == 'win_rate':
                    label.configure(text=f"{value:.1f}%")
                elif key == 'total_profit':
                    label.configure(text=f"${value:.2f}")
                else:
                    label.configure(text=str(value))


class TradeHistoryPanel(ttk.Frame):
    """Trade history table panel"""

    def __init__(self, parent, on_select: Optional[Callable] = None, **kwargs):
        super().__init__(parent, **kwargs)
        self.on_select = on_select
        self._create_widgets()

    def _create_widgets(self):
        """Create table widgets"""
        columns = ('Time', 'Direction', 'Profit', 'Duration')
        self.tree = ttk.Treeview(self, columns=columns,
                               show='headings', height=10)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)

        self.tree.pack(side='left', fill='both', expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self, orient='vertical',
                                 command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')

        # Tags
        self.tree.tag_configure('win', foreground='#2ed573')
        self.tree.tag_configure('loss', foreground='#ff4757')

    def add_trade(self, trade: Dict[str, Any]):
        """Add a trade to the table"""
        tag = 'win' if trade.get('is_winning') else 'loss'

        self.tree.insert('', 0, values=(
            trade.get('entry_time', '')[:19],
            trade.get('direction', ''),
            f"${trade.get('profit', 0):.2f}",
            f"{trade.get('duration_seconds', 0):.1f}s"
        ), tags=(tag,))


class ChartPanel(ttk.Frame):
    """Simple chart display panel"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self._create_widgets()

    def _create_widgets(self):
        """Create chart widgets"""
        self.canvas = tk.Canvas(self, bg='#0d1117', height=200)
        self.canvas.pack(fill='both', expand=True)

        # Placeholder text
        self.canvas.create_text(200, 100,
                               text="Price Chart\n(Connect to live data for real chart)",
                               fill='#c9d1d9', font=('Helvetica', 10))

    def update_chart(self, data: list):
        """Update chart with new data"""
        # Implementation would draw actual chart
        pass


class ControlPanel(ttk.Frame):
    """Control buttons panel"""

    def __init__(self, parent,
                 on_start: Optional[Callable] = None,
                 on_stop: Optional[Callable] = None,
                 on_pause: Optional[Callable] = None,
                 on_resume: Optional[Callable] = None,
                 **kwargs):
        super().__init__(parent, **kwargs)

        self.on_start = on_start
        self.on_stop = on_stop
        self.on_pause = on_pause
        self.on_resume = on_resume

        self._create_widgets()

    def _create_widgets(self):
        """Create control widgets"""
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)

        self.start_btn = ttk.Button(btn_frame, text="START",
                                   style='Start.TButton',
                                   command=self._handle_start)
        self.start_btn.pack(side='left', padx=5)

        self.stop_btn = ttk.Button(btn_frame, text="STOP",
                                  style='Stop.TButton',
                                  command=self._handle_stop,
                                  state='disabled')
        self.stop_btn.pack(side='left', padx=5)

        self.pause_btn = ttk.Button(btn_frame, text="PAUSE",
                                   command=self._handle_pause,
                                   state='disabled')
        self.pause_btn.pack(side='left', padx=5)

        self.resume_btn = ttk.Button(btn_frame, text="RESUME",
                                     command=self._handle_resume,
                                     state='disabled')
        self.resume_btn.pack(side='left', padx=5)

    def _handle_start(self):
        if self.on_start:
            self.on_start()

    def _handle_stop(self):
        if self.on_stop:
            self.on_stop()

    def _handle_pause(self):
        if self.on_pause:
            self.on_pause()

    def _handle_resume(self):
        if self.on_resume:
            self.on_resume()

    def set_running(self, running: bool):
        """Update button states for running state"""
        self.start_btn.configure(state='disabled' if running else 'normal')
        self.stop_btn.configure(state='normal' if running else 'disabled')
        self.pause_btn.configure(state='normal' if running else 'disabled')
        self.resume_btn.configure(state='disabled')

    def set_paused(self, paused: bool):
        """Update button states for paused state"""
        self.pause_btn.configure(state='disabled' if paused else 'normal')
        self.resume_btn.configure(state='normal' if paused else 'disabled')


class LogPanel(ttk.Frame):
    """Activity log panel"""

    def __init__(self, parent, max_lines: int = 100, **kwargs):
        super().__init__(parent, **kwargs)
        self.max_lines = max_lines
        self._create_widgets()

    def _create_widgets(self):
        """Create log widgets"""
        self.text = tk.Text(self, font=('Consolas', 9),
                           bg='#0d1117', fg='#c9d1d9',
                           insertbackground='white',
                           relief='flat', wrap='word')
        self.text.pack(fill='both', expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self, orient='vertical',
                                 command=self.text.yview)
        self.text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side='right', fill='y')

        # Tags for coloring
        self.text.tag_configure('info', foreground='#c9d1d9')
        self.text.tag_configure('success', foreground='#2ed573')
        self.text.tag_configure('warning', foreground='#ffa502')
        self.text.tag_configure('error', foreground='#ff4757')
        self.text.tag_configure('trade', foreground='#00d4aa')

    def log(self, message: str, level: str = 'info'):
        """Add a log message"""
        self.text.insert('end', f"{message}\n", level)
        self.text.see('end')

        # Limit lines
        lines = int(self.text.index('end-1c').split('.')[0])
        if lines > self.max_lines:
            self.text.delete('1.0', f"{lines - self.max_lines}.0")

    def clear(self):
        """Clear the log"""
        self.text.delete(1.0, 'end')
