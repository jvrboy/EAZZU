# DERIV Multi-Agent Trading Analysis System v2.0

A comprehensive, professional-grade trading analysis tool built on Python that integrates with the **Deriv API** to generate high-accuracy trading signals across **Forex**, **Cryptocurrency**, and **Synthetic Indices** markets.

---

## Features

### Multi-Agent AI System
- **7 Specialized Agents**, each with unique expertise:
  1. **TrendMaster** - Moving average analysis, trend detection, Ichimoku cloud
  2. **MomentumForce** - RSI, MACD, Stochastic, CCI, Williams %R, MFI
  3. **VolatilityEdge** - Bollinger Bands, ATR, volatility regime detection
  4. **PatternHunter** - Candlestick patterns, support/resistance, volume analysis
  5. **NeuralPredictor** - ML ensemble predictions (Random Forest, Gradient Boosting, Extra Trees, Neural Network)
  6. **LevelFinder** - Pivot points, Fibonacci levels, S/R zones
  7. **SentimentGauge** - Volume analysis, market structure, OBV, VWAP

### Council Voting System
- Weighted democratic voting with configurable consensus thresholds
- Multi-timeframe aggregation (higher TF = more weight)
- Dissent tracking and risk assessment

### Machine Learning
- **Ensemble of 4 models**: Random Forest, Gradient Boosting, Extra Trees, Neural Network
- **100+ engineered features** per prediction
- Multi-timeframe ensemble with weighted aggregation
- Trained on up to 5 years of historical data

### Technical Analysis (50+ Indicators)
- **Trend**: SMA(20/50/200), EMA(12/26/50/200), WMA, HMA, VWMA
- **Momentum**: RSI(6/14), MACD, Stochastic, CCI, Williams %R, Momentum, ROC, MFI
- **Volatility**: Bollinger Bands, ATR(7/14), Keltner Channels, Donchian Channels
- **Trend Strength**: ADX, +DI, -DI
- **Volume**: OBV, VWAP, Chaikin Oscillator, Volume Ratio
- **Pattern**: Parabolic SAR, Ichimoku Cloud, Fibonacci Retracement
- **Levels**: Pivot Points (R1-R3, S1-S3), Support/Resistance detection
- **Candlestick**: 15+ pattern recognition (engulfing, stars, doji, harami, etc.)

### Signal Generation
- High-confidence signals (>65% default threshold)
- Entry, Stop Loss, Take Profit calculation using ATR
- Risk/Reward ratio calculation
- Signal strength classification (Weak to Extreme)
- Signal expiry management
- Full audit trail with agent votes

### Visualization
- Professional candlestick charts with indicators
- Signal markers on charts
- Dashboard with signal distribution, confidence histograms
- Agent voting visualization
- HTML report generation

### Backtesting
- Walk-forward backtesting engine
- Realistic execution simulation
- Comprehensive metrics: Win Rate, Profit Factor, Sharpe Ratio, Sortino Ratio, Calmar Ratio, Max Drawdown, Expectancy
- Trade-by-trade reporting

### Supported Assets

| Asset Class | Examples | Count |
|------------|----------|-------|
| **Forex** | EURUSD, GBPUSD, USDJPY, AUDUSD... | 28 |
| **Crypto** | BTCUSD, ETHUSD, SOLUSD, ADAUSD... | 15 |
| **Synthetic** | Volatility 10/25/50/75/100, Boom/Crash, Jump... | 27 |
| **Commodity** | Gold, Silver, Oil, Copper... | 6 |
| **Index** | Dow Jones, Nikkei, FTSE, DAX... | 7 |

### Supported Timeframes
1m, 5m, 15m, 30m, 1h, 4h, 1d

---

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd deriv_trading_system

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

---

## Quick Start

### 1. Analyze a Single Symbol

```bash
python main.py analyze --symbol R_100 --timeframe 1h
```

### 2. Analyze Multiple Assets

```bash
python main.py analyze-all --assets synthetic,forex --max-assets 5
```

### 3. Train ML Models

```bash
# Train synthetic indices
python main.py train --asset-class synthetic --max-assets 5

# Train all asset classes
python main.py train-all --asset-classes forex,crypto,synthetic
```

### 4. Run Backtest

```bash
python main.py backtest --symbol R_100 --timeframe 1h --count 5000
```

### 5. Monitor Mode (Continuous Signals)

```bash
python main.py monitor --symbols R_100,frxEURUSD,cryBTCUSD --interval 60
```

### 6. Live High-Frequency Signals

```bash
python main.py live --symbols R_100 --timeframes 5m,1h --interval 30
```

### 7. Generate Dashboard

```bash
python main.py dashboard --symbols R_100,frxEURUSD
```

---

## Python API Usage

```python
from core.system import DerivTradingSystem

# Initialize system
system = DerivTradingSystem(app_id=1089)

# Start (connects to Deriv API)
system.start()

# Load pre-trained models
system.load_models("./models")

# Analyze a symbol
result = system.analyze_symbol("R_100", asset_class="synthetic")

# Access signals
for tf, signal in result['signals'].items():
    print(f"{tf}: {signal['type']} at {signal['entry']}")
    print(f"  Confidence: {signal['confidence']:.1%}")
    print(f"  SL: {signal['stop_loss']} | TP: {signal['take_profit']}")

# Train models for a symbol
metrics = system.train_models("R_100", asset_class="synthetic")

# Backtest
bt_result = system.backtest_symbol("R_100", timeframe="1h")
print(f"Win Rate: {bt_result['win_rate']:.1%}")

# Stop
system.stop()
```

---

## Architecture

```
deriv_trading_system/
|-- main.py              # CLI entry point
|-- config/
|   |-- settings.py      # Configuration & asset definitions
|-- core/
|   |-- system.py        # Main orchestrator
|   |-- types.py         # Data types (OHLCV, Signal, etc.)
|   |-- logger.py        # Logging system
|-- api/
|   |-- deriv_client.py  # Deriv WebSocket API client
|-- analysis/
|   |-- indicators.py    # 50+ technical indicators
|-- models/
|   |-- ml_models.py     # Ensemble ML models
|-- agents/
|   |-- signal_agents.py # 7 specialized AI agents
|-- council/
|   |-- voting_system.py # Democratic voting system
|-- signals/
|   |-- signal_engine.py # Signal generation pipeline
|-- visualization/
|   |-- charts.py        # Charts & dashboard
|-- backtest/
|   |-- backtester.py    # Backtesting engine
|-- training/
    |-- pipeline.py      # Model training pipeline
```

---

## System Components

### Signal Generation Pipeline

1. **Data Ingestion** - Fetch historical data from Deriv API (up to 5000 candles per request)
2. **Indicator Calculation** - Compute 50+ technical indicators
3. **ML Prediction** - Ensemble model prediction (if trained)
4. **Agent Analysis** - Each of 7 agents analyzes and votes
5. **Council Deliberation** - Weighted voting with consensus threshold
6. **Signal Construction** - Build signal with entry/SL/TP
7. **Validation** - Risk/reward check, confidence threshold

### Agent Specialization by Asset Class

| Asset Class | Specialized Agent Weights |
|------------|--------------------------|
| **Forex** | Trend (+30%), Momentum, ML |
| **Crypto** | Volatility (+30%), Momentum (+20%) |
| **Synthetic** | ML (+40%), Patterns (+10%) |

---

## Performance Metrics

The backtester tracks:
- **Win Rate** - Percentage of winning trades
- **Profit Factor** - Gross profit / Gross loss
- **Sharpe Ratio** - Risk-adjusted returns
- **Sortino Ratio** - Downside risk-adjusted returns
- **Calmar Ratio** - Return / Max Drawdown
- **Max Drawdown** - Peak-to-trough decline
- **Expectancy** - Average expected return per trade
- **Consecutive Wins/Losses** - Streak analysis

---

## Configuration

### Environment Variables
```bash
export DERIV_APP_ID=1089      # Your Deriv App ID
export DERIV_DEBUG=true       # Enable debug logging
export DERIV_LOG_LEVEL=INFO   # Log level
```

### Signal Thresholds
Edit `config/settings.py`:
```python
SignalConfig(
    MIN_CONFIDENCE=0.65,      # Minimum confidence (65%)
    CONFIRMATION_THRESHOLD=3,  # Min agreeing agents
    RISK_REWARD_MIN=1.5,      # Minimum risk/reward ratio
    STOP_LOSS_ATR=2.0,        # SL = 2x ATR
    TAKE_PROFIT_ATR=3.0       # TP = 3x ATR
)
```

---

## CLI Commands

| Command | Description | Key Arguments |
|---------|-------------|---------------|
| `analyze` | Single symbol analysis | `--symbol`, `--timeframe` |
| `analyze-all` | Batch analysis | `--assets`, `--max-assets` |
| `train` | Train models for class | `--asset-class`, `--max-assets` |
| `train-all` | Train all models | `--asset-classes` |
| `backtest` | Run backtest | `--symbol`, `--timeframe`, `--count` |
| `dashboard` | Generate HTML dashboard | `--symbols`, `--output` |
| `monitor` | Continuous monitoring | `--symbols`, `--interval` |
| `live` | High-frequency signals | `--symbols`, `--timeframes`, `--interval` |
| `list-assets` | Show available assets | - |
| `status` | System status | - |

---

## License

This software is provided for educational and research purposes. Trading carries significant risk of loss. Always test strategies thoroughly before live trading.

---

## Version History

- **v2.0.0** - Multi-agent system with council voting, ML ensembles, full asset coverage
