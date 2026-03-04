"""
Data Manager - Handles all market data fetching via yfinance
"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from PyQt6.QtCore import QObject, pyqtSignal, QThread
import time


class DataFetcher(QThread):
    """Background thread for fetching stock data."""
    data_ready = pyqtSignal(str, object)  # ticker, data_dict
    error = pyqtSignal(str, str)          # ticker, error_msg

    def __init__(self, ticker, period="1y", interval="1d"):
        super().__init__()
        self.ticker = ticker.upper()
        self.period = period
        self.interval = interval

    def run(self):
        try:
            data = DataManager.fetch_stock_data(self.ticker, self.period, self.interval)
            if data:
                self.data_ready.emit(self.ticker, data)
            else:
                self.error.emit(self.ticker, "No data returned")
        except Exception as e:
            self.error.emit(self.ticker, str(e))


class LivePriceFetcher(QThread):
    """Continuously fetches live prices."""
    price_updated = pyqtSignal(dict)  # {ticker: price_info}

    def __init__(self, tickers):
        super().__init__()
        self.tickers = tickers
        self._running = True

    def run(self):
        while self._running:
            try:
                result = {}
                for ticker in self.tickers:
                    info = DataManager.get_quick_quote(ticker)
                    if info:
                        result[ticker] = info
                if result:
                    self.price_updated.emit(result)
            except Exception:
                pass
            time.sleep(15)  # refresh every 15 seconds

    def stop(self):
        self._running = False


class DataManager:
    """Static data management class."""

    TIMEFRAME_MAP = {
        "1D":  ("1d",  "5m"),
        "5D":  ("5d",  "15m"),
        "1M":  ("1mo", "1h"),
        "3M":  ("3mo", "1d"),
        "6M":  ("6mo", "1d"),
        "1Y":  ("1y",  "1d"),
        "5Y":  ("5y",  "1wk"),
        "MAX": ("max", "1mo"),
    }

    @staticmethod
    def fetch_stock_data(ticker: str, period: str = "1y", interval: str = "1d") -> dict:
        """Fetch comprehensive stock data."""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period, interval=interval)

            if hist.empty:
                return None

            info = {}
            try:
                raw_info = stock.info
                info = {
                    "name": raw_info.get("longName", ticker),
                    "sector": raw_info.get("sector", "N/A"),
                    "industry": raw_info.get("industry", "N/A"),
                    "market_cap": raw_info.get("marketCap", 0),
                    "pe_ratio": raw_info.get("trailingPE", 0),
                    "eps": raw_info.get("trailingEps", 0),
                    "dividend_yield": raw_info.get("dividendYield", 0),
                    "52w_high": raw_info.get("fiftyTwoWeekHigh", 0),
                    "52w_low": raw_info.get("fiftyTwoWeekLow", 0),
                    "avg_volume": raw_info.get("averageVolume", 0),
                    "beta": raw_info.get("beta", 0),
                    "description": raw_info.get("longBusinessSummary", ""),
                    "current_price": raw_info.get("currentPrice", raw_info.get("regularMarketPrice", 0)),
                    "pre_market": raw_info.get("preMarketPrice", None),
                    "after_hours": raw_info.get("postMarketPrice", None),
                    "pre_market_change": raw_info.get("preMarketChangePercent", None),
                    "after_hours_change": raw_info.get("postMarketChangePercent", None),
                }
            except Exception:
                pass

            # Calculate indicators
            indicators = DataManager.calculate_indicators(hist)

            # Current price data
            if not hist.empty:
                last = hist.iloc[-1]
                prev = hist.iloc[-2] if len(hist) > 1 else last
                current_price = float(last['Close'])
                prev_close = float(prev['Close'])
                day_change = current_price - prev_close
                day_change_pct = (day_change / prev_close) * 100

                price_data = {
                    "current_price": info.get("current_price") or current_price,
                    "day_change": day_change,
                    "day_change_pct": day_change_pct,
                    "volume": int(last['Volume']),
                    "high": float(last['High']),
                    "low": float(last['Low']),
                    "open": float(last['Open']),
                }
            else:
                price_data = {}

            return {
                "ticker": ticker,
                "history": hist,
                "info": info,
                "indicators": indicators,
                "price_data": price_data,
            }
        except Exception as e:
            print(f"Error fetching {ticker}: {e}")
            return None

    @staticmethod
    def get_quick_quote(ticker: str) -> dict:
        """Fast quote fetch for live updates."""
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="2d", interval="1m")
            if hist.empty:
                return None
            last = hist.iloc[-1]
            prev_close = hist.iloc[0]['Close']
            current = float(last['Close'])
            change = current - float(prev_close)
            change_pct = (change / float(prev_close)) * 100
            return {
                "price": current,
                "change": change,
                "change_pct": change_pct,
                "volume": int(last['Volume']),
                "timestamp": datetime.now().strftime("%H:%M:%S"),
            }
        except Exception:
            return None

    @staticmethod
    def calculate_indicators(df: pd.DataFrame) -> dict:
        """Calculate all technical indicators."""
        if df.empty or len(df) < 5:
            return {}

        close = df['Close'].astype(float)
        high = df['High'].astype(float)
        low = df['Low'].astype(float)
        volume = df['Volume'].astype(float)

        indicators = {}

        # SMA
        for period in [20, 50, 200]:
            if len(close) >= period:
                indicators[f'SMA_{period}'] = close.rolling(period).mean()

        # EMA
        for period in [12, 26]:
            indicators[f'EMA_{period}'] = close.ewm(span=period, adjust=False).mean()

        # MACD
        if len(close) >= 26:
            ema12 = close.ewm(span=12, adjust=False).mean()
            ema26 = close.ewm(span=26, adjust=False).mean()
            indicators['MACD'] = ema12 - ema26
            indicators['MACD_signal'] = indicators['MACD'].ewm(span=9, adjust=False).mean()
            indicators['MACD_hist'] = indicators['MACD'] - indicators['MACD_signal']

        # RSI
        if len(close) >= 14:
            delta = close.diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.rolling(14).mean()
            avg_loss = loss.rolling(14).mean()
            rs = avg_gain / avg_loss.replace(0, np.nan)
            indicators['RSI'] = 100 - (100 / (1 + rs))

        # Bollinger Bands
        if len(close) >= 20:
            sma20 = close.rolling(20).mean()
            std20 = close.rolling(20).std()
            indicators['BB_upper'] = sma20 + 2 * std20
            indicators['BB_middle'] = sma20
            indicators['BB_lower'] = sma20 - 2 * std20

        # VWAP (daily rolling)
        if 'Volume' in df.columns:
            typical_price = (high + low + close) / 3
            vwap = (typical_price * volume).cumsum() / volume.cumsum()
            indicators['VWAP'] = vwap

        # Support & Resistance
        if len(close) >= 20:
            window = min(20, len(close) // 4)
            indicators['support'] = low.rolling(window).min()
            indicators['resistance'] = high.rolling(window).max()

        return indicators

    @staticmethod
    def get_market_scanner() -> dict:
        """Scan market for top movers, volume, etc."""
        watchlist = [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META",
            "SPY", "QQQ", "AMD", "INTC", "NFLX", "DIS", "BA", "JPM",
            "GS", "BAC", "XOM", "CVX", "PFE", "JNJ", "V", "MA",
            "PYPL", "CRM", "SHOP", "UBER", "LYFT", "SNAP", "TWTR",
        ]

        results = []
        for ticker in watchlist:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="2d", interval="1d")
                if len(hist) >= 2:
                    current = float(hist.iloc[-1]['Close'])
                    prev = float(hist.iloc[-2]['Close'])
                    change_pct = ((current - prev) / prev) * 100
                    volume = int(hist.iloc[-1]['Volume'])
                    avg_vol = int(hist['Volume'].mean())
                    vol_ratio = volume / avg_vol if avg_vol > 0 else 1

                    results.append({
                        "ticker": ticker,
                        "price": current,
                        "change_pct": change_pct,
                        "volume": volume,
                        "vol_ratio": vol_ratio,
                    })
            except Exception:
                continue

        if not results:
            return {}

        df = pd.DataFrame(results)
        df_sorted_gain = df.sort_values("change_pct", ascending=False)
        df_sorted_loss = df.sort_values("change_pct", ascending=True)
        df_sorted_vol = df.sort_values("vol_ratio", ascending=False)

        return {
            "gainers": df_sorted_gain.head(10).to_dict("records"),
            "losers": df_sorted_loss.head(10).to_dict("records"),
            "unusual_volume": df_sorted_vol.head(10).to_dict("records"),
            "momentum": df_sorted_gain[df_sorted_gain["vol_ratio"] > 1.5].head(10).to_dict("records"),
        }

    @staticmethod
    def get_portfolio_data(holdings: list) -> list:
        """Get current data for portfolio holdings."""
        result = []
        for holding in holdings:
            ticker = holding["ticker"]
            shares = holding["shares"]
            avg_cost = holding["avg_cost"]
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="2d")
                if not hist.empty:
                    current = float(hist.iloc[-1]['Close'])
                    prev = float(hist.iloc[-2]['Close']) if len(hist) > 1 else current
                    day_change = ((current - prev) / prev) * 100
                    total_value = current * shares
                    total_cost = avg_cost * shares
                    pnl = total_value - total_cost
                    pnl_pct = (pnl / total_cost) * 100

                    result.append({
                        **holding,
                        "current_price": current,
                        "day_change_pct": day_change,
                        "total_value": total_value,
                        "total_cost": total_cost,
                        "pnl": pnl,
                        "pnl_pct": pnl_pct,
                    })
            except Exception:
                result.append({**holding, "current_price": 0, "pnl": 0})
        return result
