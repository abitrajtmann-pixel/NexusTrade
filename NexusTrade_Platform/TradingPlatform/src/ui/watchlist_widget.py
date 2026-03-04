"""
Watchlist Widget - Sidebar watchlist with live prices
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QScrollArea, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont

from data.portfolio_manager import portfolio_manager
import yfinance as yf


COLORS = {
    "bg": "#080c18", "surface": "#0f1629", "border": "#1a2744",
    "accent": "#00d4ff", "green": "#00ff88", "red": "#ff4466",
    "yellow": "#ffdd44", "text": "#e0e6ff", "muted": "#445577",
}


class WatchlistPriceWorker(QThread):
    prices_ready = pyqtSignal(dict)

    def __init__(self, tickers):
        super().__init__()
        self.tickers = tickers

    def run(self):
        result = {}
        for ticker in self.tickers:
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(period="2d", interval="1d")
                if len(hist) >= 2:
                    current = float(hist.iloc[-1]['Close'])
                    prev = float(hist.iloc[-2]['Close'])
                    chg_pct = (current - prev) / prev * 100
                    result[ticker] = {"price": current, "change_pct": chg_pct}
            except Exception:
                pass
        self.prices_ready.emit(result)


class WatchlistItem(QFrame):
    clicked = pyqtSignal(str)

    def __init__(self, ticker):
        super().__init__()
        self.ticker = ticker
        self.setFixedHeight(52)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(f"""
            QFrame {{
                background: transparent;
                border-bottom: 1px solid {COLORS['border']};
            }}
            QFrame:hover {{
                background: #0f1629;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 0, 14, 0)
        layout.setSpacing(0)

        self.ticker_label = QLabel(ticker)
        self.ticker_label.setStyleSheet("color: white; font-size: 13px; font-weight: bold;")

        right = QVBoxLayout()
        right.setSpacing(2)
        self.price_label = QLabel("$—")
        self.price_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 12px;")
        self.price_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.change_label = QLabel("—")
        self.change_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 10px;")
        self.change_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        right.addWidget(self.price_label)
        right.addWidget(self.change_label)

        layout.addWidget(self.ticker_label)
        layout.addStretch()
        layout.addLayout(right)

    def update_price(self, price, change_pct):
        self.price_label.setText(f"${price:.2f}")
        sign = "+" if change_pct >= 0 else ""
        self.change_label.setText(f"{sign}{change_pct:.2f}%")
        color = COLORS["green"] if change_pct >= 0 else COLORS["red"]
        self.change_label.setStyleSheet(f"color: {color}; font-size: 10px;")

    def mousePressEvent(self, event):
        self.clicked.emit(self.ticker)


class WatchlistWidget(QWidget):
    ticker_selected = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.items = {}
        self._setup_ui()
        self._load_watchlist()

        # Auto-refresh prices every 60 seconds
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_prices)
        self.refresh_timer.start(60_000)
        QTimer.singleShot(2000, self._refresh_prices)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; } QScrollBar { width: 4px; background: #080c18; } QScrollBar::handle { background: #1a2744; border-radius: 2px; }")

        self.list_widget = QWidget()
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(0)
        self.list_layout.addStretch()

        scroll.setWidget(self.list_widget)
        layout.addWidget(scroll, 1)

        # Add ticker button
        add_bar = QFrame()
        add_bar.setFixedHeight(40)
        add_bar.setStyleSheet(f"background: {COLORS['bg']}; border-top: 1px solid {COLORS['border']};")
        add_layout = QHBoxLayout(add_bar)
        add_layout.setContentsMargins(10, 0, 10, 0)
        self.add_input = QLineEdit()
        self.add_input.setPlaceholderText("Add ticker...")
        self.add_input.setStyleSheet(f"""
            QLineEdit {{
                background: #0f1629; color: white;
                border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 4px 8px; font-size: 11px;
            }}
        """)
        self.add_input.returnPressed.connect(self._add_ticker)
        add_layout.addWidget(self.add_input)

        add_btn = QPushButton("+")
        add_btn.setFixedSize(28, 28)
        add_btn.setStyleSheet(f"background: {COLORS['accent']}; color: #000; border: none; border-radius: 4px; font-weight: bold; font-size: 14px;")
        add_btn.clicked.connect(self._add_ticker)
        add_layout.addWidget(add_btn)
        layout.addWidget(add_bar)

    def _load_watchlist(self):
        tickers = portfolio_manager.get_watchlist()
        for ticker in tickers:
            self._add_item(ticker)

    def _add_item(self, ticker):
        if ticker in self.items:
            return
        item = WatchlistItem(ticker)
        item.clicked.connect(self.ticker_selected)
        # Insert before the stretch
        self.list_layout.insertWidget(self.list_layout.count() - 1, item)
        self.items[ticker] = item

    def _add_ticker(self):
        ticker = self.add_input.text().strip().upper()
        if ticker and ticker not in self.items:
            portfolio_manager.add_to_watchlist(ticker)
            self._add_item(ticker)
            self.add_input.clear()
            self._refresh_prices()

    def _refresh_prices(self):
        if not self.items:
            return
        self.worker = WatchlistPriceWorker(list(self.items.keys()))
        self.worker.prices_ready.connect(self._on_prices_ready)
        self.worker.start()

    def _on_prices_ready(self, prices):
        for ticker, data in prices.items():
            if ticker in self.items:
                self.items[ticker].update_price(data["price"], data["change_pct"])
