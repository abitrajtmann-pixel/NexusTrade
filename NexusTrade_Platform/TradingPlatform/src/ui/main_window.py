"""
Main Window - Primary UI container with tab navigation
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTabWidget, QStatusBar, QLabel, QPushButton,
    QLineEdit, QFrame, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QIcon

from ui.chart_tab import ChartTab
from ui.scanner_tab import ScannerTab
from ui.portfolio_tab import PortfolioTab
from ui.alerts_tab import AlertsTab
from ui.watchlist_widget import WatchlistWidget


class MainWindow(QMainWindow):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NexusTrade — Professional Trading Platform")
        self.setMinimumSize(1400, 900)
        self.resize(1600, 1000)

        self._setup_ui()
        self._setup_statusbar()
        self._start_clock()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Left sidebar
        sidebar = self._build_sidebar()
        main_layout.addWidget(sidebar)

        # Main content area
        content = self._build_content()
        main_layout.addWidget(content, 1)

    def _build_sidebar(self):
        sidebar = QFrame()
        sidebar.setFixedWidth(220)
        sidebar.setObjectName("sidebar")
        sidebar.setStyleSheet("""
            QFrame#sidebar {
                background-color: #080c18;
                border-right: 1px solid #1a2744;
            }
        """)

        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Logo area
        logo_frame = QFrame()
        logo_frame.setFixedHeight(70)
        logo_frame.setStyleSheet("background-color: #0a0e1a; border-bottom: 1px solid #1a2744;")
        logo_layout = QHBoxLayout(logo_frame)
        logo_label = QLabel("⬡ NEXUS<span style='color:#00d4ff'>TRADE</span>")
        logo_label.setTextFormat(Qt.TextFormat.RichText)
        logo_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white; padding-left: 15px;")
        logo_layout.addWidget(logo_label)
        layout.addWidget(logo_frame)

        # Search box
        search_frame = QFrame()
        search_frame.setStyleSheet("padding: 10px; background: transparent;")
        search_layout = QVBoxLayout(search_frame)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍  Search ticker (AAPL...)")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #0f1629;
                color: #e0e6ff;
                border: 1px solid #1e3060;
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 13px;
            }
            QLineEdit:focus {
                border: 1px solid #00d4ff;
            }
        """)
        self.search_input.returnPressed.connect(self._on_search)
        search_layout.addWidget(self.search_input)
        layout.addWidget(search_frame)

        # Watchlist
        watch_label = QLabel("  WATCHLIST")
        watch_label.setStyleSheet("color: #445577; font-size: 10px; font-weight: bold; padding: 8px 0 4px 14px;")
        layout.addWidget(watch_label)

        self.watchlist_widget = WatchlistWidget()
        self.watchlist_widget.ticker_selected.connect(self._on_ticker_selected)
        layout.addWidget(self.watchlist_widget, 1)

        # Nav buttons at bottom
        nav_frame = QFrame()
        nav_frame.setStyleSheet("background: #080c18; border-top: 1px solid #1a2744; padding: 10px;")
        nav_layout = QVBoxLayout(nav_frame)

        nav_buttons = [
            ("📊  Dashboard", 0),
            ("🔭  Scanner", 1),
            ("💼  Portfolio", 2),
            ("🔔  Alerts", 3),
        ]
        self.nav_btns = []
        for label, idx in nav_buttons:
            btn = QPushButton(label)
            btn.setStyleSheet("""
                QPushButton {
                    background: transparent;
                    color: #7799bb;
                    border: none;
                    text-align: left;
                    padding: 8px 12px;
                    font-size: 13px;
                    border-radius: 6px;
                }
                QPushButton:hover {
                    background: #0f1629;
                    color: #00d4ff;
                }
                QPushButton:checked {
                    background: #0f1a35;
                    color: #00d4ff;
                    border-left: 3px solid #00d4ff;
                }
            """)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, i=idx: self._switch_tab(i))
            nav_layout.addWidget(btn)
            self.nav_btns.append(btn)

        if self.nav_btns:
            self.nav_btns[0].setChecked(True)

        layout.addWidget(nav_frame)
        return sidebar

    def _build_content(self):
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab widget (hidden tabs, controlled by sidebar)
        self.tabs = QTabWidget()
        self.tabs.tabBar().setVisible(False)
        self.tabs.setStyleSheet("QTabWidget::pane { border: none; }")

        # Instantiate tabs
        self.chart_tab = ChartTab()
        self.scanner_tab = ScannerTab()
        self.portfolio_tab = PortfolioTab()
        self.alerts_tab = AlertsTab()

        self.tabs.addTab(self.chart_tab, "Chart")
        self.tabs.addTab(self.scanner_tab, "Scanner")
        self.tabs.addTab(self.portfolio_tab, "Portfolio")
        self.tabs.addTab(self.alerts_tab, "Alerts")

        layout.addWidget(self.tabs)
        return container

    def _setup_statusbar(self):
        self.status_bar = self.statusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: #060a14;
                color: #445577;
                border-top: 1px solid #1a2744;
                font-size: 11px;
            }
        """)

        self.clock_label = QLabel()
        self.clock_label.setStyleSheet("color: #00d4ff; padding: 0 10px;")
        self.status_bar.addPermanentWidget(self.clock_label)

        self.market_status = QLabel("● MARKET OPEN")
        self.market_status.setStyleSheet("color: #00ff88; padding: 0 10px;")
        self.status_bar.addPermanentWidget(self.market_status)

        self.status_bar.showMessage("  NexusTrade v2.0 — Ready")

    def _start_clock(self):
        self.clock_timer = QTimer()
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)
        self._update_clock()

    def _update_clock(self):
        from datetime import datetime
        now = datetime.now()
        self.clock_label.setText(now.strftime("%H:%M:%S  %a %b %d, %Y"))

        # Simple market hours check (9:30-16:00 ET weekdays)
        hour = now.hour
        weekday = now.weekday()
        if weekday < 5 and (9 <= hour < 16):
            self.market_status.setText("● MARKET OPEN")
            self.market_status.setStyleSheet("color: #00ff88; padding: 0 10px;")
        elif weekday < 5 and hour < 9:
            self.market_status.setText("◎ PRE-MARKET")
            self.market_status.setStyleSheet("color: #ffaa00; padding: 0 10px;")
        elif weekday < 5 and hour >= 16:
            self.market_status.setText("◎ AFTER HOURS")
            self.market_status.setStyleSheet("color: #ffaa00; padding: 0 10px;")
        else:
            self.market_status.setText("○ MARKET CLOSED")
            self.market_status.setStyleSheet("color: #ff4466; padding: 0 10px;")

    def _on_search(self):
        ticker = self.search_input.text().strip().upper()
        if ticker:
            self._on_ticker_selected(ticker)
            self.search_input.clear()

    def _on_ticker_selected(self, ticker):
        self._switch_tab(0)
        self.chart_tab.load_ticker(ticker)
        self.status_bar.showMessage(f"  Loading {ticker}...")

    def _switch_tab(self, index):
        self.tabs.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_btns):
            btn.setChecked(i == index)
