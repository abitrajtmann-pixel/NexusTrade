"""
Scanner Tab - Market scanner showing gainers, losers, unusual volume, momentum
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFont, QBrush

from data.data_manager import DataManager

COLORS = {
    "bg": "#0a0e1a", "surface": "#0f1629", "border": "#1a2744",
    "accent": "#00d4ff", "green": "#00ff88", "red": "#ff4466",
    "yellow": "#ffdd44", "text": "#e0e6ff", "muted": "#445577",
}

TABLE_STYLE = """
    QTableWidget {
        background: #0a0e1a;
        color: #e0e6ff;
        border: none;
        gridline-color: #1a2744;
        font-size: 12px;
        selection-background-color: #1a2f5a;
    }
    QTableWidget::item { padding: 8px; border-bottom: 1px solid #111827; }
    QHeaderView::section {
        background: #080c18;
        color: #445577;
        font-size: 10px;
        font-weight: bold;
        border: none;
        border-bottom: 1px solid #1a2744;
        padding: 8px;
    }
"""


class ScannerWorker(QThread):
    data_ready = pyqtSignal(dict)

    def run(self):
        data = DataManager.get_market_scanner()
        self.data_ready.emit(data)


class ScannerTab(QWidget):
    ticker_selected = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._setup_ui()
        # Auto-refresh every 5 minutes
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.refresh)
        self.refresh_timer.start(300_000)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header
        header = QFrame()
        header.setFixedHeight(60)
        header.setStyleSheet(f"background: {COLORS['surface']}; border-bottom: 1px solid {COLORS['border']};")
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(20, 0, 20, 0)

        title = QLabel("🔭  MARKET SCANNER")
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        hdr_layout.addWidget(title)
        hdr_layout.addStretch()

        self.status_label = QLabel("Click Refresh to scan")
        self.status_label.setStyleSheet(f"color: {COLORS['muted']}; font-size: 12px;")
        hdr_layout.addWidget(self.status_label)

        refresh_btn = QPushButton("⟳  Refresh")
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']};
                color: #000;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 12px;
            }}
            QPushButton:hover {{ background: #00aadd; }}
        """)
        refresh_btn.clicked.connect(self.refresh)
        hdr_layout.addWidget(refresh_btn)
        layout.addWidget(header)

        # Tabs for different scan results
        self.inner_tabs = QTabWidget()
        self.inner_tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: {COLORS['bg']}; }}
            QTabBar::tab {{
                background: {COLORS['surface']};
                color: {COLORS['muted']};
                padding: 10px 20px;
                border: none;
                border-bottom: 2px solid transparent;
                font-size: 12px;
            }}
            QTabBar::tab:selected {{
                color: {COLORS['accent']};
                border-bottom: 2px solid {COLORS['accent']};
            }}
        """)

        self.gainers_table = self._make_table()
        self.losers_table = self._make_table()
        self.volume_table = self._make_table()
        self.momentum_table = self._make_table()

        self.inner_tabs.addTab(self.gainers_table, "📈  Top Gainers")
        self.inner_tabs.addTab(self.losers_table, "📉  Top Losers")
        self.inner_tabs.addTab(self.volume_table, "🔊  Unusual Volume")
        self.inner_tabs.addTab(self.momentum_table, "⚡  Momentum")

        layout.addWidget(self.inner_tabs, 1)

    def _make_table(self) -> QTableWidget:
        cols = ["Ticker", "Price", "Change %", "Volume", "Vol Ratio", "Signal"]
        table = QTableWidget()
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.setStyleSheet(TABLE_STYLE)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setAlternatingRowColors(False)
        table.doubleClicked.connect(lambda idx: self._on_row_double_click(table, idx))
        return table

    def _on_row_double_click(self, table, idx):
        ticker = table.item(idx.row(), 0)
        if ticker:
            self.ticker_selected.emit(ticker.text())

    def refresh(self):
        self.status_label.setText("Scanning market...")
        self.worker = ScannerWorker()
        self.worker.data_ready.connect(self._on_data_ready)
        self.worker.start()

    def _on_data_ready(self, data):
        self.status_label.setText(f"Scan complete — {len(data.get('gainers', []))} stocks analyzed")
        self._populate_table(self.gainers_table, data.get("gainers", []), "gainer")
        self._populate_table(self.losers_table, data.get("losers", []), "loser")
        self._populate_table(self.volume_table, data.get("unusual_volume", []), "volume")
        self._populate_table(self.momentum_table, data.get("momentum", []), "momentum")

    def _populate_table(self, table: QTableWidget, rows: list, scan_type: str):
        table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            ticker = row.get("ticker", "")
            price = row.get("price", 0)
            chg = row.get("change_pct", 0)
            volume = row.get("volume", 0)
            vol_ratio = row.get("vol_ratio", 0)

            # Signal
            if scan_type == "gainer":
                if chg > 5:
                    signal = "STRONG BUY"
                    sig_color = COLORS["green"]
                elif chg > 2:
                    signal = "BUY"
                    sig_color = "#44dd77"
                else:
                    signal = "WATCH"
                    sig_color = COLORS["yellow"]
            elif scan_type == "loser":
                if chg < -5:
                    signal = "STRONG SELL"
                    sig_color = COLORS["red"]
                elif chg < -2:
                    signal = "SELL"
                    sig_color = "#ff8844"
                else:
                    signal = "WATCH"
                    sig_color = COLORS["yellow"]
            elif scan_type == "volume":
                if vol_ratio > 3:
                    signal = "HIGH INTEREST"
                    sig_color = COLORS["accent"]
                elif vol_ratio > 2:
                    signal = "ELEVATED"
                    sig_color = COLORS["yellow"]
                else:
                    signal = "MODERATE"
                    sig_color = COLORS["muted"]
            else:  # momentum
                signal = "MOMENTUM"
                sig_color = "#aa44ff"

            items = [
                (ticker, QColor("white")),
                (f"${price:.2f}", QColor("white")),
                (f"{chg:+.2f}%", QColor(COLORS["green"]) if chg >= 0 else QColor(COLORS["red"])),
                (f"{volume:,}", QColor(COLORS["text"])),
                (f"{vol_ratio:.1f}x", QColor(COLORS["accent"] if vol_ratio > 2 else COLORS["muted"])),
                (signal, QColor(sig_color)),
            ]

            for j, (text, color) in enumerate(items):
                item = QTableWidgetItem(text)
                item.setForeground(QBrush(color))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if j == 0:
                    font = QFont()
                    font.setBold(True)
                    item.setFont(font)
                table.setItem(i, j, item)

            table.setRowHeight(i, 44)
