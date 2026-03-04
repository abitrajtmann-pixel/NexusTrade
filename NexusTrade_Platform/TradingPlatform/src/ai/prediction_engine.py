"""
AI Prediction Engine
Uses RandomForest + technical features for price direction prediction.
Also includes volatility forecast and trend strength scoring.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import TimeSeriesSplit
import warnings
warnings.filterwarnings('ignore')


class AIPredictionEngine:
    """ML-based stock prediction engine."""

    def __init__(self):
        self.classifier = RandomForestClassifier(
            n_estimators=100, max_depth=8, random_state=42, n_jobs=-1
        )
        self.regressor = GradientBoostingRegressor(
            n_estimators=100, max_depth=4, random_state=42
        )
        self.scaler = StandardScaler()
        self.trained = False

    def _create_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Create ML features from OHLCV data."""
        feat = pd.DataFrame(index=df.index)
        close = df['Close'].astype(float)
        high = df['High'].astype(float)
        low = df['Low'].astype(float)
        volume = df['Volume'].astype(float)

        # Returns
        for p in [1, 2, 3, 5, 10, 20]:
            feat[f'ret_{p}'] = close.pct_change(p)

        # Moving averages
        for p in [5, 10, 20, 50]:
            if len(close) > p:
                ma = close.rolling(p).mean()
                feat[f'ma_{p}_ratio'] = close / ma

        # Volatility
        feat['vol_5'] = close.pct_change().rolling(5).std()
        feat['vol_20'] = close.pct_change().rolling(20).std()

        # RSI
        delta = close.diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = (-delta.clip(upper=0)).rolling(14).mean()
        rs = gain / loss.replace(0, np.nan)
        feat['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        ema12 = close.ewm(span=12, adjust=False).mean()
        ema26 = close.ewm(span=26, adjust=False).mean()
        feat['macd'] = (ema12 - ema26) / close
        feat['macd_signal'] = feat['macd'].ewm(span=9, adjust=False).mean()

        # Bollinger Band position
        sma20 = close.rolling(20).mean()
        std20 = close.rolling(20).std()
        feat['bb_pos'] = (close - sma20) / (2 * std20 + 1e-10)

        # Volume features
        feat['vol_ratio'] = volume / volume.rolling(20).mean()
        feat['vol_price'] = feat['vol_ratio'] * feat['ret_1'].abs()

        # High/Low features
        feat['hl_ratio'] = (high - low) / close
        feat['close_position'] = (close - low) / (high - low + 1e-10)

        # Momentum
        feat['momentum_10'] = close / close.shift(10) - 1
        feat['momentum_20'] = close / close.shift(20) - 1

        return feat

    def predict(self, df: pd.DataFrame) -> dict:
        """
        Train on historical data and predict for next period.
        Returns prediction dict.
        """
        if len(df) < 60:
            return self._fallback_prediction(df)

        try:
            feat = self._create_features(df)
            close = df['Close'].astype(float)

            # Target: will price be higher in 5 days?
            future_return = close.shift(-5) / close - 1
            direction = (future_return > 0).astype(int)

            # Align
            combined = pd.concat([feat, direction.rename("target"), future_return.rename("future_ret")], axis=1)
            combined = combined.dropna()

            if len(combined) < 50:
                return self._fallback_prediction(df)

            X = combined[feat.columns].values
            y_class = combined["target"].values
            y_reg = combined["future_ret"].values

            # Time series split
            tscv = TimeSeriesSplit(n_splits=3)
            train_idx = list(tscv.split(X))[-1][0]

            X_train = X[train_idx]
            y_train_class = y_class[train_idx]
            y_train_reg = y_reg[train_idx]

            X_scaled = self.scaler.fit_transform(X_train)

            # Train models
            self.classifier.fit(X_scaled, y_train_class)
            self.regressor.fit(X_scaled, y_train_reg)
            self.trained = True

            # Predict on latest data
            latest_feat = feat.iloc[-1:].values
            latest_scaled = self.scaler.transform(latest_feat)

            up_prob = float(self.classifier.predict_proba(latest_scaled)[0][1])
            down_prob = 1 - up_prob
            predicted_return = float(self.regressor.predict(latest_scaled)[0])

            current_price = float(close.iloc[-1])
            predicted_price = current_price * (1 + predicted_return)

            # Price range (with uncertainty)
            vol = float(close.pct_change().rolling(20).std().iloc[-1])
            price_low = current_price * (1 + predicted_return - 1.5 * vol)
            price_high = current_price * (1 + predicted_return + 1.5 * vol)

            # Trend strength
            trend_strength = self._calculate_trend_strength(df)

            # Signal
            if up_prob > 0.65:
                signal = "STRONG BUY"
                signal_color = "#00ff88"
            elif up_prob > 0.55:
                signal = "BUY"
                signal_color = "#44dd77"
            elif up_prob < 0.35:
                signal = "STRONG SELL"
                signal_color = "#ff4466"
            elif up_prob < 0.45:
                signal = "SELL"
                signal_color = "#ff8844"
            else:
                signal = "NEUTRAL"
                signal_color = "#ffdd44"

            return {
                "up_probability": up_prob * 100,
                "down_probability": down_prob * 100,
                "predicted_price": predicted_price,
                "price_range_low": price_low,
                "price_range_high": price_high,
                "predicted_return_pct": predicted_return * 100,
                "signal": signal,
                "signal_color": signal_color,
                "trend_strength": trend_strength,
                "volatility_forecast": vol * 100,
                "horizon": "5 trading days",
                "confidence": min(95, max(50, abs(up_prob - 0.5) * 200)),
            }

        except Exception as e:
            print(f"Prediction error: {e}")
            return self._fallback_prediction(df)

    def _calculate_trend_strength(self, df: pd.DataFrame) -> float:
        """Calculate trend strength 0-100."""
        close = df['Close'].astype(float).tail(50)
        if len(close) < 10:
            return 50.0

        # ADX-inspired calculation
        changes = close.pct_change().dropna()
        positive = changes[changes > 0].sum()
        negative = abs(changes[changes < 0].sum())
        total = positive + negative

        if total == 0:
            return 50.0

        directional_strength = (abs(positive - negative) / total) * 100

        # Weight by recent momentum
        recent = close.tail(10).pct_change().dropna()
        momentum_consistency = (recent > 0).mean() if positive > negative else (recent < 0).mean()

        return min(100, float(directional_strength * 0.7 + momentum_consistency * 30))

    def _fallback_prediction(self, df: pd.DataFrame) -> dict:
        """Simple rule-based fallback when not enough data."""
        close = df['Close'].astype(float)
        current = float(close.iloc[-1])

        # Simple RSI-based signal
        if len(close) > 14:
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(14).mean()
            loss = (-delta.clip(upper=0)).rolling(14).mean()
            rs = (gain / loss.replace(0, np.nan)).iloc[-1]
            rsi = float(100 - (100 / (1 + rs)))
        else:
            rsi = 50

        if rsi < 30:
            up_prob = 65
        elif rsi > 70:
            up_prob = 35
        else:
            up_prob = 50 + (50 - rsi) * 0.3

        vol = float(close.pct_change().rolling(min(20, len(close))).std().iloc[-1]) if len(close) > 5 else 0.02

        return {
            "up_probability": up_prob,
            "down_probability": 100 - up_prob,
            "predicted_price": current,
            "price_range_low": current * (1 - vol * 1.5),
            "price_range_high": current * (1 + vol * 1.5),
            "predicted_return_pct": 0,
            "signal": "NEUTRAL",
            "signal_color": "#ffdd44",
            "trend_strength": 50,
            "volatility_forecast": vol * 100,
            "horizon": "5 trading days",
            "confidence": 50,
        }


# Global instance
ai_engine = AIPredictionEngine()
