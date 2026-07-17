"""
Visualization System
====================
Advanced charting and dashboard for trading signals and market data.
"""

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle, FancyBboxPatch
from matplotlib.lines import Line2D
from matplotlib.gridspec import GridSpec
import matplotlib.patheffects as path_effects
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from pathlib import Path
import io
import base64

from core.types import TradingSignal, MarketData, TechnicalIndicators, OHLCV, AgentVote
from core.logger import system_logger


class ChartEngine:
    """
    Professional charting engine for trading analysis.
    Creates publication-quality charts with indicators and signals.
    """
    
    def __init__(self, style: str = 'dark'):
        self.style = style
        self._setup_style()
        system_logger.info(f"ChartEngine initialized with {style} style")
    
    def _setup_style(self):
        """Configure matplotlib style."""
        if self.style == 'dark':
            plt.style.use('dark_background')
            self.colors = {
                'bg': '#0a0a0a',
                'grid': '#2a2a2a',
                'bullish': '#00e676',
                'bearish': '#ff5252',
                'text': '#ffffff',
                'accent': '#448aff',
                'signal_buy': '#00ff88',
                'signal_sell': '#ff4444',
                'sma_20': '#ffab40',
                'sma_50': '#e040fb',
                'sma_200': '#69f0ae',
                'bb_upper': '#82b1ff',
                'bb_lower': '#82b1ff',
                'volume': '#616161',
                'macd_pos': '#00e676',
                'macd_neg': '#ff5252'
            }
        else:
            self.colors = {
                'bg': '#ffffff',
                'grid': '#e0e0e0',
                'bullish': '#2e7d32',
                'bearish': '#c62828',
                'text': '#212121',
                'accent': '#1565c0',
                'signal_buy': '#00c853',
                'signal_sell': '#d50000',
                'sma_20': '#ef6c00',
                'sma_50': '#6a1b9a',
                'sma_200': '#2e7d32',
                'bb_upper': '#42a5f5',
                'bb_lower': '#42a5f5',
                'volume': '#bdbdbd',
                'macd_pos': '#2e7d32',
                'macd_neg': '#c62828'
            }
    
    def create_full_chart(
        self,
        market_data: MarketData,
        indicators: TechnicalIndicators,
        signals: Optional[List[TradingSignal]] = None,
        title: str = None,
        save_path: str = None
    ) -> str:
        """
        Create comprehensive chart with all indicators and signals.
        
        Returns:
            Base64 encoded PNG image or file path.
        """
        candles = market_data.candles[-200:]  # Last 200 candles
        if not candles:
            return ""
        
        # Prepare data
        df = pd.DataFrame([
            {
                'timestamp': c.timestamp,
                'open': c.open,
                'high': c.high,
                'low': c.low,
                'close': c.close,
                'volume': c.volume
            }
            for c in candles
        ])
        
        # Create figure
        fig = plt.figure(figsize=(16, 12), facecolor=self.colors['bg'])
        fig.patch.set_facecolor(self.colors['bg'])
        
        gs = GridSpec(4, 1, height_ratios=[3, 1, 1, 1], hspace=0.05)
        
        # Main price chart
        ax1 = fig.add_subplot(gs[0])
        ax1.set_facecolor(self.colors['bg'])
        
        # Plot candlesticks
        self._plot_candlesticks(ax1, df)
        
        # Plot moving averages
        if len(df) >= 20:
            sma20 = df['close'].rolling(20).mean()
            ax1.plot(df['timestamp'], sma20, color=self.colors['sma_20'], 
                    linewidth=1, label='SMA 20', alpha=0.8)
        
        if len(df) >= 50:
            sma50 = df['close'].rolling(50).mean()
            ax1.plot(df['timestamp'], sma50, color=self.colors['sma_50'], 
                    linewidth=1, label='SMA 50', alpha=0.8)
        
        # Bollinger Bands
        if len(df) >= 20:
            bb_mid = df['close'].rolling(20).mean()
            bb_std = df['close'].rolling(20).std()
            bb_upper = bb_mid + 2 * bb_std
            bb_lower = bb_mid - 2 * bb_std
            
            ax1.fill_between(df['timestamp'], bb_upper, bb_lower, 
                           alpha=0.1, color=self.colors['bb_upper'])
            ax1.plot(df['timestamp'], bb_upper, color=self.colors['bb_upper'], 
                    linewidth=0.5, alpha=0.5)
            ax1.plot(df['timestamp'], bb_lower, color=self.colors['bb_lower'], 
                    linewidth=0.5, alpha=0.5)
        
        # Plot signals
        if signals:
            self._plot_signals(ax1, df, signals)
        
        ax1.set_ylabel('Price', color=self.colors['text'])
        ax1.legend(loc='upper left', facecolor=self.colors['bg'], 
                  edgecolor=self.colors['grid'])
        ax1.grid(True, alpha=0.2, color=self.colors['grid'])
        
        # Title
        chart_title = title or f"{market_data.symbol} - {market_data.timeframe}"
        ax1.set_title(chart_title, color=self.colors['text'], fontsize=14, fontweight='bold')
        
        # Volume
        ax2 = fig.add_subplot(gs[1], sharex=ax1)
        ax2.set_facecolor(self.colors['bg'])
        colors_vol = [self.colors['bullish'] if c >= o else self.colors['bearish'] 
                      for c, o in zip(df['close'], df['open'])]
        ax2.bar(df['timestamp'], df['volume'], color=colors_vol, alpha=0.7, width=0.8)
        ax2.set_ylabel('Volume', color=self.colors['text'])
        ax2.grid(True, alpha=0.2, color=self.colors['grid'])
        
        # RSI
        ax3 = fig.add_subplot(gs[2], sharex=ax1)
        ax3.set_facecolor(self.colors['bg'])
        rsi = self._calculate_rsi(df['close'], 14)
        ax3.plot(df['timestamp'], rsi, color=self.colors['accent'], linewidth=1)
        ax3.axhline(y=70, color=self.colors['bearish'], linestyle='--', alpha=0.5)
        ax3.axhline(y=30, color=self.colors['bullish'], linestyle='--', alpha=0.5)
        ax3.axhline(y=50, color='gray', linestyle='-', alpha=0.3)
        ax3.fill_between(df['timestamp'], 30, 70, alpha=0.05, color='gray')
        ax3.set_ylabel('RSI(14)', color=self.colors['text'])
        ax3.set_ylim(0, 100)
        ax3.grid(True, alpha=0.2, color=self.colors['grid'])
        
        # MACD
        ax4 = fig.add_subplot(gs[3], sharex=ax1)
        ax4.set_facecolor(self.colors['bg'])
        macd_line, signal_line, hist = self._calculate_macd(df['close'])
        
        colors_macd = [self.colors['macd_pos'] if h >= 0 else self.colors['macd_neg'] 
                       for h in hist]
        ax4.bar(df['timestamp'], hist, color=colors_macd, alpha=0.7, width=0.8)
        ax4.plot(df['timestamp'], macd_line, color='#2196f3', linewidth=1, label='MACD')
        ax4.plot(df['timestamp'], signal_line, color='#ff9800', linewidth=1, label='Signal')
        ax4.axhline(y=0, color='gray', linestyle='-', alpha=0.3)
        ax4.set_ylabel('MACD', color=self.colors['text'])
        ax4.legend(loc='upper left', facecolor=self.colors['bg'])
        ax4.grid(True, alpha=0.2, color=self.colors['grid'])
        
        # Format x-axis
        ax4.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
        plt.setp(ax1.get_xticklabels(), visible=False)
        plt.setp(ax2.get_xticklabels(), visible=False)
        plt.setp(ax3.get_xticklabels(), visible=False)
        plt.xticks(rotation=45)
        
        plt.tight_layout()
        
        # Save or return base64
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches='tight', 
                       facecolor=self.colors['bg'])
            plt.close()
            return save_path
        else:
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                       facecolor=self.colors['bg'])
            plt.close()
            buf.seek(0)
            return base64.b64encode(buf.read()).decode('utf-8')
    
    def create_signal_dashboard(
        self,
        signals: List[TradingSignal],
        save_path: str = None
    ) -> str:
        """
        Create dashboard showing recent signals and their performance.
        """
        if not signals:
            return ""
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 10), facecolor=self.colors['bg'])
        fig.patch.set_facecolor(self.colors['bg'])
        
        # Signal distribution
        ax1 = axes[0, 0]
        ax1.set_facecolor(self.colors['bg'])
        
        buy_count = sum(1 for s in signals if 'BUY' in s.signal_type)
        sell_count = sum(1 for s in signals if 'SELL' in s.signal_type)
        strong_buy = sum(1 for s in signals if s.signal_type == 'STRONG_BUY')
        strong_sell = sum(1 for s in signals if s.signal_type == 'STRONG_SELL')
        
        categories = ['Strong Buy', 'Buy', 'Sell', 'Strong Sell']
        values = [strong_buy, buy_count - strong_buy, sell_count - strong_sell, strong_sell]
        colors = [self.colors['signal_buy'], '#66bb6a', 
                 '#ef5350', self.colors['signal_sell']]
        
        bars = ax1.bar(categories, values, color=colors, alpha=0.8)
        ax1.set_title('Signal Distribution', color=self.colors['text'], fontweight='bold')
        ax1.set_ylabel('Count', color=self.colors['text'])
        ax1.tick_params(colors=self.colors['text'])
        ax1.grid(True, alpha=0.2, color=self.colors['grid'])
        
        # Add value labels
        for bar, val in zip(bars, values):
            if val > 0:
                ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                        str(val), ha='center', va='bottom', color=self.colors['text'])
        
        # Confidence distribution
        ax2 = axes[0, 1]
        ax2.set_facecolor(self.colors['bg'])
        
        confidences = [s.confidence for s in signals]
        ax2.hist(confidences, bins=20, color=self.colors['accent'], alpha=0.7, edgecolor='white')
        ax2.axvline(x=np.mean(confidences), color='red', linestyle='--', 
                   label=f'Mean: {np.mean(confidences):.2%}')
        ax2.set_title('Confidence Distribution', color=self.colors['text'], fontweight='bold')
        ax2.set_xlabel('Confidence', color=self.colors['text'])
        ax2.set_ylabel('Frequency', color=self.colors['text'])
        ax2.tick_params(colors=self.colors['text'])
        ax2.legend()
        ax2.grid(True, alpha=0.2, color=self.colors['grid'])
        
        # Signal timeline
        ax3 = axes[1, 0]
        ax3.set_facecolor(self.colors['bg'])
        
        times = [s.timestamp for s in signals]
        confs = [s.confidence for s in signals]
        colors_ts = [self.colors['signal_buy'] if 'BUY' in s.signal_type else self.colors['signal_sell'] 
                     for s in signals]
        
        ax3.scatter(times, confs, c=colors_ts, alpha=0.7, s=50)
        ax3.set_title('Signal Timeline', color=self.colors['text'], fontweight='bold')
        ax3.set_ylabel('Confidence', color=self.colors['text'])
        ax3.tick_params(colors=self.colors['text'])
        ax3.grid(True, alpha=0.2, color=self.colors['grid'])
        
        # Risk/Reward distribution
        ax4 = axes[1, 1]
        ax4.set_facecolor(self.colors['bg'])
        
        rr_ratios = [s.risk_reward_ratio for s in signals if s.risk_reward_ratio > 0]
        if rr_ratios:
            ax4.hist(rr_ratios, bins=15, color='#ab47bc', alpha=0.7, edgecolor='white')
            ax4.axvline(x=np.mean(rr_ratios), color='red', linestyle='--',
                       label=f'Mean R/R: {np.mean(rr_ratios):.2f}')
            ax4.set_title('Risk/Reward Distribution', color=self.colors['text'], fontweight='bold')
            ax4.set_xlabel('Risk/Reward Ratio', color=self.colors['text'])
            ax4.set_ylabel('Frequency', color=self.colors['text'])
            ax4.tick_params(colors=self.colors['text'])
            ax4.legend()
            ax4.grid(True, alpha=0.2, color=self.colors['grid'])
        
        plt.tight_layout()
        
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches='tight',
                       facecolor=self.colors['bg'])
            plt.close()
            return save_path
        else:
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                       facecolor=self.colors['bg'])
            plt.close()
            buf.seek(0)
            return base64.b64encode(buf.read()).decode('utf-8')
    
    def create_agent_votes_chart(
        self,
        votes: List[AgentVote],
        save_path: str = None
    ) -> str:
        """Create visualization of agent votes."""
        fig, ax = plt.subplots(figsize=(12, 6), facecolor=self.colors['bg'])
        ax.set_facecolor(self.colors['bg'])
        
        agents = [v.agent_name for v in votes]
        confidences = [v.confidence for v in votes]
        directions = [v.direction.name for v in votes]
        
        colors = []
        for d in directions:
            if 'BULL' in d:
                colors.append(self.colors['signal_buy'])
            elif 'BEAR' in d:
                colors.append(self.colors['signal_sell'])
            else:
                colors.append('gray')
        
        y_pos = np.arange(len(agents))
        bars = ax.barh(y_pos, confidences, color=colors, alpha=0.8)
        ax.set_yticks(y_pos)
        ax.set_yticklabels([f"{a}\n({d})" for a, d in zip(agents, directions)])
        ax.set_xlabel('Confidence', color=self.colors['text'])
        ax.set_title('Agent Voting Results', color=self.colors['text'], fontweight='bold')
        ax.tick_params(colors=self.colors['text'])
        ax.grid(True, alpha=0.2, color=self.colors['grid'], axis='x')
        ax.set_xlim(0, 1)
        
        # Add confidence values
        for bar, conf in zip(bars, confidences):
            ax.text(bar.get_width() + 0.02, bar.get_y() + bar.get_height()/2,
                   f'{conf:.1%}', va='center', color=self.colors['text'])
        
        plt.tight_layout()
        
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            plt.savefig(save_path, dpi=150, bbox_inches='tight',
                       facecolor=self.colors['bg'])
            plt.close()
            return save_path
        else:
            buf = io.BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight',
                       facecolor=self.colors['bg'])
            plt.close()
            buf.seek(0)
            return base64.b64encode(buf.read()).decode('utf-8')
    
    def _plot_candlesticks(self, ax, df: pd.DataFrame):
        """Plot candlestick chart."""
        width = 0.6
        width2 = 0.05
        
        for idx, row in df.iterrows():
            color = self.colors['bullish'] if row['close'] >= row['open'] else self.colors['bearish']
            
            # Body
            height = abs(row['close'] - row['open'])
            bottom = min(row['open'], row['close'])
            rect = Rectangle((mdates.date2num(row['timestamp']) - width/2, bottom), 
                           width, height or 0.0001, 
                           facecolor=color, edgecolor=color, alpha=0.9)
            ax.add_patch(rect)
            
            # Wick
            ax.plot([mdates.date2num(row['timestamp']), mdates.date2num(row['timestamp'])],
                   [row['low'], row['high']], color=color, linewidth=0.5)
    
    def _plot_signals(self, ax, df: pd.DataFrame, signals: List[TradingSignal]):
        """Plot signal markers on chart."""
        for signal in signals:
            # Find closest timestamp in data
            signal_time = signal.timestamp
            
            color = self.colors['signal_buy'] if 'BUY' in signal.signal_type else self.colors['signal_sell']
            marker = '^' if 'BUY' in signal.signal_type else 'v'
            
            # Plot entry point
            ax.scatter(signal_time, signal.entry_price, 
                      marker=marker, s=200, color=color, 
                      edgecolors='white', linewidth=1.5, zorder=5)
            
            # Draw SL and TP lines if visible
            ax.axhline(y=signal.stop_loss, color='red', linestyle=':', 
                      alpha=0.3, xmin=0.7, xmax=1.0)
            ax.axhline(y=signal.take_profit, color='green', linestyle=':', 
                      alpha=0.3, xmin=0.7, xmax=1.0)
    
    @staticmethod
    def _calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI."""
        delta = prices.diff()
        gain = delta.where(delta > 0, 0)
        loss = -delta.where(delta < 0, 0)
        
        avg_gain = gain.rolling(window=period).mean()
        avg_loss = loss.rolling(window=period).mean()
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def _calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
        """Calculate MACD."""
        ema_fast = prices.ewm(span=fast, adjust=False).mean()
        ema_slow = prices.ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal, adjust=False).mean()
        histogram = macd_line - signal_line
        return macd_line, signal_line, histogram


class Dashboard:
    """
    Real-time dashboard for monitoring signals and system performance.
    """
    
    def __init__(self, chart_engine: ChartEngine = None):
        self.chart_engine = chart_engine or ChartEngine()
        self.data = {
            'signals': [],
            'performance': {},
            'agent_votes': [],
            'market_data': {}
        }
    
    def update(self, key: str, value):
        """Update dashboard data."""
        self.data[key] = value
    
    def generate_html_report(self, save_path: str = None) -> str:
        """Generate HTML report with all charts."""
        # This is a simplified version - full implementation would be more comprehensive
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>DERIV Trading System - Dashboard</title>
            <style>
                body {{ background: #0a0a0a; color: #fff; font-family: monospace; }}
                .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
                .header {{ text-align: center; padding: 20px; border-bottom: 2px solid #333; }}
                .stats {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; margin: 20px 0; }}
                .stat-card {{ background: #1a1a1a; padding: 15px; border-radius: 8px; text-align: center; }}
                .stat-value {{ font-size: 24px; font-weight: bold; color: #00e676; }}
                .stat-label {{ font-size: 12px; color: #999; margin-top: 5px; }}
                .signal-list {{ margin-top: 20px; }}
                .signal {{ background: #1a1a1a; padding: 10px; margin: 5px 0; 
                          border-left: 4px solid #00e676; border-radius: 4px; }}
                .signal.sell {{ border-left-color: #ff5252; }}
                .signal strong {{ color: #448aff; }}
                .timestamp {{ color: #666; font-size: 11px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>DERIV Multi-Agent Trading System</h1>
                    <p>Real-Time Signal Dashboard</p>
                </div>
        """
        
        # Add stats
        signals = self.data.get('signals', [])
        if signals:
            buy_count = sum(1 for s in signals if 'BUY' in s.signal_type)
            sell_count = sum(1 for s in signals if 'SELL' in s.signal_type)
            avg_conf = np.mean([s.confidence for s in signals]) if signals else 0
            
            html += f"""
                <div class="stats">
                    <div class="stat-card">
                        <div class="stat-value">{len(signals)}</div>
                        <div class="stat-label">Total Signals</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: #00e676;">{buy_count}</div>
                        <div class="stat-label">Buy Signals</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value" style="color: #ff5252;">{sell_count}</div>
                        <div class="stat-label">Sell Signals</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">{avg_conf:.1%}</div>
                        <div class="stat-label">Avg Confidence</div>
                    </div>
                </div>
            """
            
            # Add recent signals
            html += '<div class="signal-list"><h2>Recent Signals</h2>'
            for signal in reversed(signals[-20:]):
                css_class = "signal sell" if 'SELL' in signal.signal_type else "signal"
                html += f"""
                    <div class="{css_class}">
                        <span class="timestamp">{signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</span>
                        <strong>{signal.signal_type}</strong> {signal.symbol} ({signal.timeframe}) | 
                        Confidence: {signal.confidence:.1%} | 
                        Entry: {signal.entry_price:.5f} | 
                        SL: {signal.stop_loss:.5f} | 
                        TP: {signal.take_profit:.5f} | 
                        R/R: {signal.risk_reward_ratio:.2f}
                    </div>
                """
            html += '</div>'
        
        html += """
            </div>
        </body>
        </html>
        """
        
        if save_path:
            Path(save_path).parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w') as f:
                f.write(html)
            return save_path
        
        return html
