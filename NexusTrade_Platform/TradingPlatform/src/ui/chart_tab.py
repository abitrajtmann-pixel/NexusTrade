"""
Chart Tab - Main trading view with candlestick charts, indicators, AI panel
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QSplitter, QGridLayout, QComboBox,
    QCheckBox, QProgressBar
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QColor
import pyqtgraph as pg
import numpy as np
import pandas as pd

from data.data_manager import DataManager, DataFetcher
from ai.prediction_engine import AIPredictionEngine


COLORS = {
    "bg": "#0a0e1a",
    "surface": "#0f1629",
    "border": "#1a2744",
    "accent": "#00d4ff",
    "green": "#00ff88",
    "red": "#ff4466",
    "yellow": "#ffdd44",
    "text": "#e0e6ff",
    "muted": "#445577",
    "candle_up": "#00cc66",
    "candle_down": "#ff3355",
}

TIMEFRAMES = ["1D", "5D", "1M", "3M", "6M", "1Y", "5Y", "MAX"]
INDICATORS = ["SMA 20", "SMA 50", "EMA 12", "EMA 26", "Bollinger Bands", "VWAP"]


class AIWorker(QThread):
    result_ready = pyqtSignal(dict)

    def __init__(self, df):
        super().__init__()
        self.df = df
        self.engine = AIPredictionEngine()

    def run(self):
        result = self.engine.predict(self.df)
        self.result_ready.emit(result)


class CandlestickItem(pg.GraphicsObject):
    """Custom candlestick chart item for pyqtgraph."""

    def __init__(self, data):
        super().__init__()
        self.data = data  # list of (time, open, high, low, close, volume)
        self.picture = None
        self.generatePicture()

    def generatePicture(self):
        import pyqtgraph as pg
        from PyQt6.QtGui import QPainter, QPen, QBrush
        from PyQt6.QtCore import QRectF

        self.picture = pg.QtGui.QPicture()
        p = QPainter(self.picture)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = 0.4
        for i, (t, o, h, l, c, v) in enumerate(self.data):
            is_up = c >= o
            color = QColor(COLORS["candle_up"]) if is_up else QColor(COLORS["candle_down"])

            pen = QPen(color)
            pen.setWidth(0)
            p.setPen(pen)
            p.setBrush(QBrush(color))

            # Wick
            p.drawLine(
                pg.QtCore.QPointF(i, l),
                pg.QtCore.QPointF(i, h)
            )

            # Body
            body_top = max(o, c)
            body_bot = min(o, c)
            if body_top == body_bot:
                body_top += 0.001

            p.drawRect(QRectF(i - w, body_bot, w * 2, body_top - body_bot))

        p.end()

    def paint(self, p, *args):
        p.drawPicture(0, 0, self.picture)

    def boundingRect(self):
        return pg.QtCore.QRectF(self.picture.boundingRect())


class ChartTab(QWidget):
    """Main chart view."""

    def __init__(self):
        super().__init__()
        self.current_ticker = "AAPL"
        self.current_timeframe = "1Y"
        self.current_data = None
        self.fetcher = None
        self.ai_worker = None
        self.active_indicators = set()
        self._setup_ui()
        self.load_ticker("AAPL")

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Top bar
        top_bar = self._build_top_bar()
        layout.addWidget(top_bar)

        # Main content splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background: #1a2744; width: 1px; }")

        # Chart area
        chart_container = self._build_chart_area()
        splitter.addWidget(chart_container)

        # Right panel (AI + stats)
        right_panel = self._build_right_panel()
        splitter.addWidget(right_panel)

        splitter.setSizes([1100, 320])
        layout.addWidget(splitter, 1)

    def _build_top_bar(self):
        bar = QFrame()
        bar.setFixedHeight(80)
        bar.setStyleSheet(f"background: {COLORS['surface']}; border-bottom: 1px solid {COLORS['border']};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)

        # Ticker info
        info_layout = QVBoxLayout()
        self.ticker_label = QLabel("AAPL")
        self.ticker_label.setStyleSheet(f"color: white; font-size: 22px; font-weight: bold;")
        self.name_label = QLabel("Apple Inc.")
        self.name_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 12px;")
        info_layout.addWidget(self.ticker_label)
        info_layout.addWidget(self.name_label)
        layout.addLayout(info_layout)

        layout.addSpacing(30)

        # Price info
        price_layout = QVBoxLayout()
        self.price_label = QLabel("$0.00")
        self.price_label.setStyleSheet("color: white; font-size: 26px; font-weight: bold;")
        self.change_label = QLabel("$0.00  (0.00%)")
        self.change_label.setStyleSheet(f"color: {COLORS['green']}; font-size: 13px;")
        price_layout.addWidget(self.price_label)
        price_layout.addWidget(self.change_label)
        layout.addLayout(price_layout)

        layout.addSpacing(30)

        # Stats row
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet("background: transparent;")
        self.stats_layout = QHBoxLayout(self.stats_frame)
        self.stats_layout.setSpacing(25)
        for label in ["Vol", "Mkt Cap", "P/E", "52W H", "52W L"]:
            stat = QWidget()
            v = QVBoxLayout(stat)
            v.setSpacing(2)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {COLORS['muted']}; font-size: 10px;")
            val = QLabel("—")
            val.setStyleSheet(f"color: {COLORS['text']}; font-size: 12px; font-weight: bold;")
            val.setObjectName(f"stat_{label.replace(' ', '_')}")
            v.addWidget(lbl)
            v.addWidget(val)
            self.stats_layout.addWidget(stat)
        layout.addWidget(self.stats_frame)

        layout.addStretch()

        # Timeframe buttons
        tf_frame = QFrame()
        tf_layout = QHBoxLayout(tf_frame)
        tf_layout.setSpacing(4)
        self.tf_buttons = {}
        for tf in TIMEFRAMES:
            btn = QPushButton(tf)
            btn.setFixedSize(45, 30)
            btn.setStyleSheet(self._tf_btn_style(tf == self.current_timeframe))
            btn.clicked.connect(lambda checked, t=tf: self._set_timeframe(t))
            tf_layout.addWidget(btn)
            self.tf_buttons[tf] = btn
        layout.addWidget(tf_frame)

        return bar

    def _tf_btn_style(self, active=False):
        if active:
            return f"""
                QPushButton {{
                    background: {COLORS['accent']};
                    color: #000;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 11px;
                }}
            """
        return f"""
            QPushButton {{
                background: {COLORS['surface']};
                color: {COLORS['muted']};
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background: {COLORS['bg']};
                color: {COLORS['accent']};
                border: 1px solid {COLORS['accent']};
            }}
        """

    def _build_chart_area(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Indicator toggles
        ind_bar = QFrame()
        ind_bar.setStyleSheet(f"background: {COLORS['bg']}; padding: 6px 16px; border-bottom: 1px solid {COLORS['border']};")
        ind_layout = QHBoxLayout(ind_bar)
        ind_layout.setSpacing(12)
        ind_layout.addWidget(QLabel("Indicators:").also(lambda l: l.setStyleSheet(f"color:{COLORS['muted']}; font-size:11px;")))

        self.ind_checks = {}
        ind_colors = {
            "SMA 20": "#ffdd44", "SMA 50": "#ff9900", "EMA 12": "#44aaff",
            "EMA 26": "#aa44ff", "Bollinger Bands": "#00ffaa", "VWAP": "#ff44aa"
        }
        for ind in INDICATORS:
            cb = QCheckBox(ind)
            color = ind_colors.get(ind, "#ffffff")
            cb.setStyleSheet(f"""
                QCheckBox {{color: {color}; font-size: 11px;}}
                QCheckBox::indicator {{width:12px; height:12px; border:1px solid {color}; border-radius:2px; background:transparent;}}
                QCheckBox::indicator:checked {{background: {color};}}
            """)
            cb.stateChanged.connect(lambda state, i=ind: self._toggle_indicator(i, state))
            ind_layout.addWidget(cb)
            self.ind_checks[ind] = cb

        # RSI toggle
        self.rsi_check = QCheckBox("RSI")
        self.rsi_check.setStyleSheet(f"QCheckBox {{color: #ff6688; font-size: 11px;}} QCheckBox::indicator {{width:12px; height:12px; border:1px solid #ff6688; border-radius:2px; background:transparent;}} QCheckBox::indicator:checked {{background: #ff6688;}}")
        self.rsi_check.stateChanged.connect(self._toggle_rsi)
        ind_layout.addWidget(self.rsi_check)

        # MACD toggle
        self.macd_check = QCheckBox("MACD")
        self.macd_check.setStyleSheet(f"QCheckBox {{color: #aaffdd; font-size: 11px;}} QCheckBox::indicator {{width:12px; height:12px; border:1px solid #aaffdd; border-radius:2px; background:transparent;}} QCheckBox::indicator:checked {{background: #aaffdd;}}")
        self.macd_check.stateChanged.connect(self._toggle_macd)
        ind_layout.addWidget(self.macd_check)

        ind_layout.addStretch()
        layout.addWidget(ind_bar)

        # PyQtGraph plots
        pg.setConfigOptions(antialias=True, background=COLORS["bg"], foreground=COLORS["muted"])

        self.plot_layout = pg.GraphicsLayoutWidget()
        self.plot_layout.setStyleSheet(f"background: {COLORS['bg']};")

        # Main price chart
        self.price_plot = self.plot_layout.addPlot(row=0, col=0)
        self._style_plot(self.price_plot)

        # Volume chart
        self.vol_plot = self.plot_layout.addPlot(row=1, col=0)
        self._style_plot(self.vol_plot)
        self.vol_plot.setFixedHeight(80)

        # RSI chart (hidden by default)
        self.rsi_plot = self.plot_layout.addPlot(row=2, col=0)
        self._style_plot(self.rsi_plot)
        self.rsi_plot.setFixedHeight(100)
        self.rsi_plot.setVisible(False)

        # MACD chart (hidden by default)
        self.macd_plot = self.plot_layout.addPlot(row=3, col=0)
        self._style_plot(self.macd_plot)
        self.macd_plot.setFixedHeight(100)
        self.macd_plot.setVisible(False)

        # Link X axes
        self.vol_plot.setXLink(self.price_plot)
        self.rsi_plot.setXLink(self.price_plot)
        self.macd_plot.setXLink(self.price_plot)

        layout.addWidget(self.plot_layout, 1)
        return container

    def _style_plot(self, plot):
        plot.setMenuEnabled(False)
        plot.getAxis('bottom').setStyle(tickTextOffset=5, tickLength=5)
        plot.getAxis('left').setStyle(tickTextOffset=5, tickLength=5)
        plot.getAxis('bottom').setPen(pg.mkPen(color=COLORS["border"], width=1))
        plot.getAxis('left').setPen(pg.mkPen(color=COLORS["border"], width=1))
        plot.getAxis('bottom').setTextPen(pg.mkPen(color=COLORS["muted"]))
        plot.getAxis('left').setTextPen(pg.mkPen(color=COLORS["muted"]))
        plot.showGrid(x=True, y=True, alpha=0.15)

    def _build_right_panel(self):
        panel = QFrame()
        panel.setStyleSheet(f"background: {COLORS['surface']}; border-left: 1px solid {COLORS['border']};")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # AI Panel header
        ai_header = QLabel("  🤖  AI ANALYSIS")
        ai_header.setFixedHeight(40)
        ai_header.setStyleSheet(f"background: #080c18; color: {COLORS['accent']}; font-size: 12px; font-weight: bold; border-bottom: 1px solid {COLORS['border']};")
        layout.addWidget(ai_header)

        # AI content (scrollable)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; } QScrollBar { width: 6px; background: #080c18; } QScrollBar::handle { background: #1a2744; border-radius: 3px; }")

        ai_content = QWidget()
        self.ai_layout = QVBoxLayout(ai_content)
        self.ai_layout.setContentsMargins(16, 16, 16, 16)
        self.ai_layout.setSpacing(12)

        # Signal widget
        self.signal_frame = QFrame()
        self.signal_frame.setStyleSheet(f"background: #080c18; border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 12px;")
        signal_layout = QVBoxLayout(self.signal_frame)
        signal_layout.setSpacing(4)
        sig_title = QLabel("AI SIGNAL")
        sig_title.setStyleSheet(f"color: {COLORS['muted']}; font-size: 10px; font-weight: bold;")
        self.signal_label = QLabel("ANALYZING...")
        self.signal_label.setStyleSheet(f"color: {COLORS['yellow']}; font-size: 20px; font-weight: bold;")
        self.signal_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.confidence_label = QLabel("Confidence: —")
        self.confidence_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 11px;")
        self.confidence_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        signal_layout.addWidget(sig_title)
        signal_layout.addWidget(self.signal_label)
        signal_layout.addWidget(self.confidence_label)
        self.ai_layout.addWidget(self.signal_frame)

        # Probability bars
        prob_frame = QFrame()
        prob_frame.setStyleSheet(f"background: #080c18; border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 12px;")
        prob_layout = QVBoxLayout(prob_frame)
        prob_layout.setSpacing(8)
        prob_title = QLabel("MOVEMENT PROBABILITY")
        prob_title.setStyleSheet(f"color: {COLORS['muted']}; font-size: 10px; font-weight: bold;")
        prob_layout.addWidget(prob_title)

        # Up probability
        up_lbl = QLabel("▲ Upward")
        up_lbl.setStyleSheet(f"color: {COLORS['green']}; font-size: 11px;")
        prob_layout.addWidget(up_lbl)
        self.up_bar = QProgressBar()
        self.up_bar.setStyleSheet(f"QProgressBar {{background: #1a2744; border-radius:3px; height:14px;}} QProgressBar::chunk {{background: {COLORS['green']}; border-radius:3px;}}")
        self.up_bar.setValue(50)
        self.up_bar.setTextVisible(True)
        prob_layout.addWidget(self.up_bar)

        # Down probability
        dn_lbl = QLabel("▼ Downward")
        dn_lbl.setStyleSheet(f"color: {COLORS['red']}; font-size: 11px;")
        prob_layout.addWidget(dn_lbl)
        self.dn_bar = QProgressBar()
        self.dn_bar.setStyleSheet(f"QProgressBar {{background: #1a2744; border-radius:3px; height:14px;}} QProgressBar::chunk {{background: {COLORS['red']}; border-radius:3px;}}")
        self.dn_bar.setValue(50)
        self.dn_bar.setTextVisible(True)
        prob_layout.addWidget(self.dn_bar)
        self.ai_layout.addWidget(prob_frame)

        # Price target
        target_frame = QFrame()
        target_frame.setStyleSheet(f"background: #080c18; border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 12px;")
        target_layout = QVBoxLayout(target_frame)
        target_title = QLabel("PRICE TARGET (5D)")
        target_title.setStyleSheet(f"color: {COLORS['muted']}; font-size: 10px; font-weight: bold;")
        target_layout.addWidget(target_title)
        self.target_label = QLabel("$—")
        self.target_label.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        self.target_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.range_label = QLabel("Range: $— – $—")
        self.range_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 11px;")
        self.range_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        target_layout.addWidget(self.target_label)
        target_layout.addWidget(self.range_label)
        self.ai_layout.addWidget(target_frame)

        # Trend strength + volatility
        metrics_frame = QFrame()
        metrics_frame.setStyleSheet(f"background: #080c18; border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 12px;")
        metrics_layout = QGridLayout(metrics_frame)
        metrics_layout.setSpacing(8)

        metrics_title = QLabel("MARKET METRICS")
        metrics_title.setStyleSheet(f"color: {COLORS['muted']}; font-size: 10px; font-weight: bold;")
        metrics_layout.addWidget(metrics_title, 0, 0, 1, 2)

        for i, (label, attr) in enumerate([
            ("Trend Strength", "trend_strength_label"),
            ("Volatility", "volatility_label"),
            ("Beta", "beta_label"),
            ("52W Position", "position_label"),
        ]):
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {COLORS['muted']}; font-size: 10px;")
            val = QLabel("—")
            val.setStyleSheet(f"color: {COLORS['text']}; font-size: 12px; font-weight: bold;")
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            metrics_layout.addWidget(lbl, i + 1, 0)
            metrics_layout.addWidget(val, i + 1, 1)
            setattr(self, attr, val)

        self.ai_layout.addWidget(metrics_frame)

        # Pre/After hours
        self.ext_frame = QFrame()
        self.ext_frame.setStyleSheet(f"background: #080c18; border: 1px solid {COLORS['border']}; border-radius: 8px; padding: 12px;")
        ext_layout = QVBoxLayout(self.ext_frame)
        ext_title = QLabel("EXTENDED HOURS")
        ext_title.setStyleSheet(f"color: {COLORS['muted']}; font-size: 10px; font-weight: bold;")
        ext_layout.addWidget(ext_title)
        self.pre_market_label = QLabel("Pre-Market: —")
        self.pre_market_label.setStyleSheet(f"color: {COLORS['yellow']}; font-size: 12px;")
        self.after_hours_label = QLabel("After Hours: —")
        self.after_hours_label.setStyleSheet(f"color: {COLORS['yellow']}; font-size: 12px;")
        ext_layout.addWidget(self.pre_market_label)
        ext_layout.addWidget(self.after_hours_label)
        self.ai_layout.addWidget(self.ext_frame)

        self.ai_layout.addStretch()
        scroll.setWidget(ai_content)
        layout.addWidget(scroll, 1)
        return panel

    def load_ticker(self, ticker: str):
        self.current_ticker = ticker.upper()
        if self.fetcher and self.fetcher.isRunning():
            self.fetcher.terminate()

        period, interval = DataManager.TIMEFRAME_MAP.get(self.current_timeframe, ("1y", "1d"))
        self.fetcher = DataFetcher(self.current_ticker, period, interval)
        self.fetcher.data_ready.connect(self._on_data_ready)
        self.fetcher.error.connect(self._on_data_error)
        self.fetcher.start()

        self.ticker_label.setText(self.current_ticker)
        self.signal_label.setText("ANALYZING...")

    def _set_timeframe(self, tf):
        self.current_timeframe = tf
        for t, btn in self.tf_buttons.items():
            btn.setStyleSheet(self._tf_btn_style(t == tf))
        self.load_ticker(self.current_ticker)

    def _toggle_indicator(self, ind, state):
        if state:
            self.active_indicators.add(ind)
        else:
            self.active_indicators.discard(ind)
        if self.current_data:
            self._draw_charts(self.current_data)

    def _toggle_rsi(self, state):
        self.rsi_plot.setVisible(bool(state))
        if self.current_data and state:
            self._draw_rsi(self.current_data)

    def _toggle_macd(self, state):
        self.macd_plot.setVisible(bool(state))
        if self.current_data and state:
            self._draw_macd(self.current_data)

    def _on_data_ready(self, ticker, data):
        if ticker != self.current_ticker:
            return
        self.current_data = data
        self._update_header(data)
        self._draw_charts(data)
        self._run_ai_prediction(data)

    def _on_data_error(self, ticker, error):
        self.name_label.setText(f"Error: {error}")

    def _update_header(self, data):
        info = data.get("info", {})
        price_data = data.get("price_data", {})

        name = info.get("name", self.current_ticker)
        self.name_label.setText(name)

        price = price_data.get("current_price", 0)
        change = price_data.get("day_change", 0)
        change_pct = price_data.get("day_change_pct", 0)

        self.price_label.setText(f"${price:,.2f}")
        sign = "+" if change >= 0 else ""
        self.change_label.setText(f"{sign}${change:.2f}  ({sign}{change_pct:.2f}%)")
        color = COLORS["green"] if change >= 0 else COLORS["red"]
        self.change_label.setStyleSheet(f"color: {color}; font-size: 13px;")

        # Stats
        def fmt_num(n):
            if not n:
                return "—"
            if n >= 1e12:
                return f"${n/1e12:.1f}T"
            if n >= 1e9:
                return f"${n/1e9:.1f}B"
            if n >= 1e6:
                return f"${n/1e6:.1f}M"
            return f"${n:,.0f}"

        stats = {
            "Vol": f"{price_data.get('volume', 0):,}",
            "Mkt_Cap": fmt_num(info.get("market_cap", 0)),
            "P/E": f"{info.get('pe_ratio', 0):.1f}" if info.get("pe_ratio") else "—",
            "52W_H": f"${info.get('52w_high', 0):.2f}" if info.get("52w_high") else "—",
            "52W_L": f"${info.get('52w_low', 0):.2f}" if info.get("52w_low") else "—",
        }
        for key, val in stats.items():
            widget = self.stats_frame.findChild(QLabel, f"stat_{key}")
            if widget:
                widget.setText(val)

        # Extended hours
        pre = info.get("pre_market")
        after = info.get("after_hours")
        if pre:
            pct = info.get("pre_market_change", 0) or 0
            self.pre_market_label.setText(f"Pre-Market: ${pre:.2f}  ({pct*100:+.2f}%)")
        if after:
            pct = info.get("after_hours_change", 0) or 0
            self.after_hours_label.setText(f"After Hours: ${after:.2f}  ({pct*100:+.2f}%)")

    def _draw_charts(self, data):
        hist = data.get("history")
        if hist is None or hist.empty:
            return

        indicators = data.get("indicators", {})

        self.price_plot.clear()
        self.vol_plot.clear()

        close = hist['Close'].astype(float).values
        high = hist['High'].astype(float).values
        low = hist['Low'].astype(float).values
        open_ = hist['Open'].astype(float).values
        volume = hist['Volume'].astype(float).values
        n = len(close)
        x = np.arange(n)

        # Candlesticks
        candle_data = list(zip(x, open_, high, low, close, volume))
        candles = CandlestickItem(candle_data)
        self.price_plot.addItem(candles)

        # AI prediction overlay (price range shading)
        # Will be added after AI runs

        # Indicators on price chart
        ind_map = {
            "SMA 20": ("SMA_20", "#ffdd44"),
            "SMA 50": ("SMA_50", "#ff9900"),
            "EMA 12": ("EMA_12", "#44aaff"),
            "EMA 26": ("EMA_26", "#aa44ff"),
            "VWAP":   ("VWAP", "#ff44aa"),
        }
        for ind_name, (key, color) in ind_map.items():
            if ind_name in self.active_indicators and key in indicators:
                vals = indicators[key].values
                valid = ~np.isnan(vals)
                if valid.any():
                    self.price_plot.plot(x[valid], vals[valid], pen=pg.mkPen(color=color, width=1.5), name=ind_name)

        # Bollinger Bands
        if "Bollinger Bands" in self.active_indicators:
            for key, color in [("BB_upper", "#00ffaa"), ("BB_lower", "#00ffaa"), ("BB_middle", "#007755")]:
                if key in indicators:
                    vals = indicators[key].values
                    valid = ~np.isnan(vals)
                    if valid.any():
                        self.price_plot.plot(x[valid], vals[valid], pen=pg.mkPen(color=color, width=1, style=Qt.PenStyle.DotLine))

        # Support & Resistance
        if "support" in indicators:
            vals = indicators["support"].values
            valid = ~np.isnan(vals)
            if valid.any():
                self.price_plot.plot(x[valid], vals[valid], pen=pg.mkPen(color="#ff6644", width=1, style=Qt.PenStyle.DashLine), name="Support")
        if "resistance" in indicators:
            vals = indicators["resistance"].values
            valid = ~np.isnan(vals)
            if valid.any():
                self.price_plot.plot(x[valid], vals[valid], pen=pg.mkPen(color="#44aaff", width=1, style=Qt.PenStyle.DashLine), name="Resistance")

        # Volume bars
        for i in range(n):
            is_up = close[i] >= open_[i]
            color = QColor(COLORS["candle_up"] if is_up else COLORS["candle_down"])
            color.setAlpha(150)
            bar = pg.BarGraphItem(x=[i], height=[volume[i]], width=0.8, brush=pg.mkBrush(color))
            self.vol_plot.addItem(bar)

        # RSI / MACD if visible
        if self.rsi_check.isChecked():
            self._draw_rsi(data)
        if self.macd_check.isChecked():
            self._draw_macd(data)

        self.price_plot.autoRange()

    def _draw_rsi(self, data):
        self.rsi_plot.clear()
        indicators = data.get("indicators", {})
        if "RSI" not in indicators:
            return
        rsi = indicators["RSI"].values
        x = np.arange(len(rsi))
        valid = ~np.isnan(rsi)
        self.rsi_plot.plot(x[valid], rsi[valid], pen=pg.mkPen(color="#ff6688", width=1.5))
        # Overbought/oversold lines
        self.rsi_plot.addLine(y=70, pen=pg.mkPen(color="#ff3344", width=1, style=Qt.PenStyle.DashLine))
        self.rsi_plot.addLine(y=30, pen=pg.mkPen(color="#33cc66", width=1, style=Qt.PenStyle.DashLine))
        self.rsi_plot.setYRange(0, 100)
        rsi_label = pg.TextItem("RSI", color=COLORS["muted"], anchor=(0, 0))
        rsi_label.setPos(0, 90)
        self.rsi_plot.addItem(rsi_label)

    def _draw_macd(self, data):
        self.macd_plot.clear()
        indicators = data.get("indicators", {})
        if "MACD" not in indicators:
            return
        macd = indicators["MACD"].values
        signal = indicators["MACD_signal"].values
        hist_vals = indicators["MACD_hist"].values
        x = np.arange(len(macd))
        valid = ~np.isnan(macd)
        self.macd_plot.plot(x[valid], macd[valid], pen=pg.mkPen(color="#00aaff", width=1.5))
        self.macd_plot.plot(x[valid], signal[valid], pen=pg.mkPen(color="#ff6644", width=1.5))

        # Histogram
        pos_hist = np.where(hist_vals > 0, hist_vals, 0)
        neg_hist = np.where(hist_vals < 0, hist_vals, 0)
        self.macd_plot.addItem(pg.BarGraphItem(x=x[valid], height=pos_hist[valid], width=0.6, brush=pg.mkBrush(COLORS["green"] + "88")))
        self.macd_plot.addItem(pg.BarGraphItem(x=x[valid], height=neg_hist[valid], width=0.6, brush=pg.mkBrush(COLORS["red"] + "88")))

    def _run_ai_prediction(self, data):
        hist = data.get("history")
        if hist is None:
            return
        self.ai_worker = AIWorker(hist)
        self.ai_worker.result_ready.connect(self._on_ai_result)
        self.ai_worker.start()

    def _on_ai_result(self, result):
        self.signal_label.setText(result["signal"])
        self.signal_label.setStyleSheet(f"color: {result['signal_color']}; font-size: 20px; font-weight: bold;")

        conf = result.get("confidence", 50)
        self.confidence_label.setText(f"Model Confidence: {conf:.0f}%")

        up = int(result.get("up_probability", 50))
        dn = int(result.get("down_probability", 50))
        self.up_bar.setValue(up)
        self.up_bar.setFormat(f"{up}%")
        self.dn_bar.setValue(dn)
        self.dn_bar.setFormat(f"{dn}%")

        pred = result.get("predicted_price", 0)
        lo = result.get("price_range_low", 0)
        hi = result.get("price_range_high", 0)
        ret = result.get("predicted_return_pct", 0)
        sign = "+" if ret >= 0 else ""
        self.target_label.setText(f"${pred:.2f}  ({sign}{ret:.1f}%)")
        self.range_label.setText(f"Range: ${lo:.2f} – ${hi:.2f}")

        # Metrics
        trend = result.get("trend_strength", 50)
        vol_f = result.get("volatility_forecast", 0)
        self.trend_strength_label.setText(f"{trend:.0f} / 100")
        self.volatility_label.setText(f"{vol_f:.2f}%")

        if self.current_data:
            info = self.current_data.get("info", {})
            beta = info.get("beta", 0)
            self.beta_label.setText(f"{beta:.2f}" if beta else "—")

            h52 = info.get("52w_high", 0)
            l52 = info.get("52w_low", 0)
            cp = self.current_data.get("price_data", {}).get("current_price", 0)
            if h52 and l52 and cp:
                pos = (cp - l52) / (h52 - l52) * 100
                self.position_label.setText(f"{pos:.0f}%")

        # Overlay prediction band on chart
        if self.current_data:
            hist = self.current_data.get("history")
            if hist is not None and not hist.empty:
                n = len(hist)
                x_end = n - 1
                self.price_plot.addLine(x=x_end, pen=pg.mkPen(color="#ffffff44", width=1, style=Qt.PenStyle.DashLine))

                lo_item = pg.InfiniteLine(
                    pos=lo, angle=0,
                    pen=pg.mkPen(color=COLORS["red"], width=1, style=Qt.PenStyle.DotLine),
                    label=f"Low ${lo:.2f}", labelOpts={"color": COLORS["red"], "position": 0.95}
                )
                hi_item = pg.InfiniteLine(
                    pos=hi, angle=0,
                    pen=pg.mkPen(color=COLORS["green"], width=1, style=Qt.PenStyle.DotLine),
                    label=f"High ${hi:.2f}", labelOpts={"color": COLORS["green"], "position": 0.95}
                )
                self.price_plot.addItem(lo_item)
                self.price_plot.addItem(hi_item)


# Monkey-patch QLabel for chaining
def _also(self, fn):
    fn(self)
    return self

QLabel.also = _also
