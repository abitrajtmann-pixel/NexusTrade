# ⬡ NexusTrade — Professional AI-Powered Trading Platform

> A fully-featured, production-grade stock market desktop application with real-time data, AI predictions, portfolio management, and advanced charting.

---

## 🚀 Quick Start — Build Your .EXE in 3 Steps

### Windows

1. **Install Python 3.10+** from [python.org](https://www.python.org/downloads/)
   - ✅ Check **"Add Python to PATH"** during installation — this is critical!

2. **Extract this folder** anywhere on your computer (e.g., `C:\NexusTrade\`)

3. **Double-click `BUILD.bat`**
   - It will automatically install all dependencies and compile `NexusTrade.exe`
   - The process takes **3–8 minutes** depending on your internet speed
   - When complete, `NexusTrade.exe` appears in the same folder — just double-click it!

### macOS

```bash
# In Terminal, navigate to the folder and run:
chmod +x build_mac.sh
./build_mac.sh
```

---

## ✨ Features

### 📊 Real-Time Charts
- Candlestick charts with full OHLCV data
- 8 timeframes: 1D, 5D, 1M, 3M, 6M, 1Y, 5Y, MAX
- Technical indicators: SMA 20/50, EMA 12/26, MACD, RSI, Bollinger Bands, VWAP
- Automatic Support & Resistance detection
- Pre-market and after-hours data display

### 🤖 AI Prediction Engine
- Machine learning model (RandomForest + GradientBoosting)
- Probability of upward/downward movement (%)
- 5-day price target with range forecast
- Trend strength score (0–100)
- Volatility forecast
- Visual overlays on chart (prediction bands)
- Signals: STRONG BUY / BUY / NEUTRAL / SELL / STRONG SELL

### 🔭 Market Scanner
- Top Gainers / Top Losers
- Unusual Volume detection
- Momentum stocks
- AI-based signal rating per stock
- Double-click any row to open its chart

### 💼 Portfolio Manager
- Add/remove positions
- Real-time P&L calculation
- Day change tracking
- Win rate & risk metrics
- Performance bar chart
- Trade Journal (log all your trades)

### 🔔 Alerts System
- Price alerts (above / below)
- RSI alerts (overbought/oversold)
- Volume alerts
- Triggered alerts log

### 🎨 UI/UX
- Professional dark-mode trading interface
- Sidebar watchlist with live price updates
- Multi-tab layout
- Market hours status indicator (Pre-Market / Open / After Hours / Closed)
- Real-time clock

---

## 📁 Project Structure

```
NexusTrade/
├── BUILD.bat               ← Double-click to build the .exe
├── build_mac.sh            ← macOS build script
├── requirements.txt        ← Python dependencies
├── README.md               ← This file
└── src/
    ├── main.py             ← Application entry point
    ├── ui/
    │   ├── main_window.py  ← Main window & navigation
    │   ├── chart_tab.py    ← Candlestick charts & AI panel
    │   ├── scanner_tab.py  ← Market scanner
    │   ├── portfolio_tab.py← Portfolio management
    │   ├── alerts_tab.py   ← Alerts system
    │   └── watchlist_widget.py ← Sidebar watchlist
    ├── data/
    │   ├── data_manager.py ← Yahoo Finance data layer
    │   └── portfolio_manager.py ← Portfolio & alerts persistence
    └── ai/
        └── prediction_engine.py ← ML prediction models
```

---

## 💾 Data Storage

Your portfolio, alerts, watchlist, and trade journal are saved in:
- **Windows:** `C:\Users\<YourName>\.nexustrade\`
- **macOS/Linux:** `~/.nexustrade/`

Data persists across sessions automatically.

---

## 🔧 Manual Run (Without Building)

If you just want to run it directly with Python:

```bash
cd src
pip install -r ../requirements.txt
python main.py
```

---

## 📡 Data Source

- **Yahoo Finance** via `yfinance` — Free, no API key required
- Data refreshes automatically every 15 seconds for watchlist
- Full chart data loads on demand

---

## ⚠️ Disclaimer

This software is for educational and informational purposes only. AI predictions are not financial advice. Always do your own research before making investment decisions.

---

## 🛠 Troubleshooting

| Problem | Solution |
|---|---|
| `python` not recognized | Reinstall Python and check "Add to PATH" |
| Build fails at pip install | Run `BUILD.bat` as Administrator |
| App opens but no data | Check internet connection |
| Charts don't render | Update graphics drivers |
| Slow startup | Normal — PyInstaller apps take 5–10s to start |

---

*NexusTrade v2.0 — Built with PyQt6 + PyQtGraph + scikit-learn + yfinance*
