"""
Portfolio Tab - Holdings, P&L, risk analysis, trade journal
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QTabWidget, QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
    QDialogButtonBox, QTextEdit, QSplitter, QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QBrush
import pyqtgraph as pg
import numpy as np

from data.data_manager import DataManager
from data.portfolio_manager import portfolio_manager

COLORS = {
    "bg": "#0a0e1a", "surface": "#0f1629", "border": "#1a2744",
    "accent": "#00d4ff", "green": "#00ff88", "red": "#ff4466",
    "yellow": "#ffdd44", "text": "#e0e6ff", "muted": "#445577",
}

TABLE_STYLE = """
    QTableWidget {
        background: #0a0e1a; color: #e0e6ff; border: none;
        gridline-color: #1a2744; font-size: 12px;
    }
    QTableWidget::item { padding: 8px; border-bottom: 1px solid #111827; }
    QHeaderView::section {
        background: #080c18; color: #445577; font-size: 10px;
        font-weight: bold; border: none; border-bottom: 1px solid #1a2744; padding: 8px;
    }
"""


class PortfolioLoader(QThread):
    loaded = pyqtSignal(list, dict)

    def run(self):
        holdings = portfolio_manager.get_holdings()
        if not holdings:
            self.loaded.emit([], {})
            return
        enriched = DataManager.get_portfolio_data(holdings)
        stats = portfolio_manager.get_portfolio_stats(enriched)
        self.loaded.emit(enriched, stats)


class AddPositionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Position")
        self.setMinimumWidth(360)
        self.setStyleSheet(f"background: {COLORS['surface']}; color: {COLORS['text']};")
        layout = QFormLayout(self)
        layout.setSpacing(12)

        self.ticker_input = QLineEdit()
        self.ticker_input.setPlaceholderText("e.g. AAPL")
        self.ticker_input.setStyleSheet(self._input_style())
        layout.addRow("Ticker:", self.ticker_input)

        self.shares_input = QDoubleSpinBox()
        self.shares_input.setRange(0.001, 1_000_000)
        self.shares_input.setDecimals(3)
        self.shares_input.setStyleSheet(self._input_style())
        layout.addRow("Shares:", self.shares_input)

        self.cost_input = QDoubleSpinBox()
        self.cost_input.setRange(0.01, 1_000_000)
        self.cost_input.setDecimals(2)
        self.cost_input.setPrefix("$")
        self.cost_input.setStyleSheet(self._input_style())
        layout.addRow("Avg Cost:", self.cost_input)

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        self.notes_input.setStyleSheet(self._input_style())
        layout.addRow("Notes:", self.notes_input)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.setStyleSheet(f"""
            QPushButton {{
                background: {COLORS['accent']}; color: #000; border: none;
                border-radius: 4px; padding: 6px 16px; font-weight: bold;
            }}
        """)
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def _input_style(self):
        return f"""
            QLineEdit, QDoubleSpinBox, QTextEdit {{
                background: #080c18; color: {COLORS['text']};
                border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 6px;
            }}
        """

    def get_values(self):
        return {
            "ticker": self.ticker_input.text().strip().upper(),
            "shares": self.shares_input.value(),
            "avg_cost": self.cost_input.value(),
            "notes": self.notes_input.toPlainText(),
        }


class PortfolioTab(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self.refresh()

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
        title = QLabel("💼  PORTFOLIO")
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        hdr_layout.addWidget(title)
        hdr_layout.addStretch()

        add_btn = QPushButton("+ Add Position")
        add_btn.setStyleSheet(f"background: {COLORS['accent']}; color: #000; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold;")
        add_btn.clicked.connect(self._add_position)
        hdr_layout.addWidget(add_btn)

        refresh_btn = QPushButton("⟳ Refresh")
        refresh_btn.setStyleSheet(f"background: {COLORS['surface']}; color: {COLORS['accent']}; border: 1px solid {COLORS['accent']}; border-radius: 6px; padding: 8px 16px;")
        refresh_btn.clicked.connect(self.refresh)
        hdr_layout.addWidget(refresh_btn)
        layout.addWidget(header)

        # Stats bar
        self.stats_bar = self._build_stats_bar()
        layout.addWidget(self.stats_bar)

        # Inner tabs
        inner_tabs = QTabWidget()
        inner_tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; background: {COLORS['bg']}; }}
            QTabBar::tab {{ background: {COLORS['surface']}; color: {COLORS['muted']};
                padding: 10px 20px; border: none; border-bottom: 2px solid transparent; font-size: 12px; }}
            QTabBar::tab:selected {{ color: {COLORS['accent']}; border-bottom: 2px solid {COLORS['accent']}; }}
        """)

        # Holdings table
        holdings_widget = QWidget()
        holdings_layout = QVBoxLayout(holdings_widget)
        holdings_layout.setContentsMargins(0, 0, 0, 0)
        self.holdings_table = self._make_holdings_table()
        holdings_layout.addWidget(self.holdings_table)
        inner_tabs.addTab(holdings_widget, "📊 Holdings")

        # Performance chart
        perf_widget = QWidget()
        perf_layout = QVBoxLayout(perf_widget)
        perf_layout.setContentsMargins(10, 10, 10, 10)
        self.perf_plot = pg.PlotWidget(background=COLORS["bg"])
        self.perf_plot.showGrid(x=True, y=True, alpha=0.15)
        perf_layout.addWidget(self.perf_plot)
        inner_tabs.addTab(perf_widget, "📈 Performance")

        # Trade journal
        journal_widget = self._build_journal_widget()
        inner_tabs.addTab(journal_widget, "📓 Trade Journal")

        layout.addWidget(inner_tabs, 1)

    def _build_stats_bar(self):
        bar = QFrame()
        bar.setFixedHeight(90)
        bar.setStyleSheet(f"background: {COLORS['bg']}; border-bottom: 1px solid {COLORS['border']};")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 10, 20, 10)
        layout.setSpacing(30)

        self.stat_labels = {}
        stats = [
            ("Total Value", "total_value"),
            ("Total P&L", "total_pnl"),
            ("P&L %", "total_pnl_pct"),
            ("Cash", "cash"),
            ("Win Rate", "win_rate"),
            ("Best", "best_performer"),
            ("Worst", "worst_performer"),
        ]
        for label, key in stats:
            frame = QFrame()
            v = QVBoxLayout(frame)
            v.setSpacing(4)
            lbl = QLabel(label)
            lbl.setStyleSheet(f"color: {COLORS['muted']}; font-size: 10px;")
            val = QLabel("—")
            val.setStyleSheet(f"color: {COLORS['text']}; font-size: 15px; font-weight: bold;")
            v.addWidget(lbl)
            v.addWidget(val)
            layout.addWidget(frame)
            self.stat_labels[key] = val

        layout.addStretch()
        return bar

    def _make_holdings_table(self):
        cols = ["Ticker", "Shares", "Avg Cost", "Current", "Day %", "Total Value", "P&L", "P&L %", "Actions"]
        table = QTableWidget()
        table.setColumnCount(len(cols))
        table.setHorizontalHeaderLabels(cols)
        table.setStyleSheet(TABLE_STYLE)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        return table

    def _build_journal_widget(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(16, 16, 16, 16)

        add_entry_btn = QPushButton("+ Log Trade")
        add_entry_btn.setStyleSheet(f"background: {COLORS['accent']}; color: #000; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold; max-width: 150px;")
        add_entry_btn.clicked.connect(self._add_journal_entry)
        layout.addWidget(add_entry_btn)

        self.journal_table = QTableWidget()
        self.journal_table.setColumnCount(7)
        self.journal_table.setHorizontalHeaderLabels(["Date", "Ticker", "Action", "Shares", "Price", "Total", "Notes"])
        self.journal_table.setStyleSheet(TABLE_STYLE)
        self.journal_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.journal_table.verticalHeader().setVisible(False)
        self.journal_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.journal_table, 1)

        self._refresh_journal()
        return widget

    def refresh(self):
        self.loader = PortfolioLoader()
        self.loader.loaded.connect(self._on_loaded)
        self.loader.start()

    def _on_loaded(self, holdings, stats):
        self._populate_holdings(holdings)
        self._update_stats(stats)
        self._draw_perf_chart(holdings)

    def _populate_holdings(self, holdings):
        self.holdings_table.setRowCount(len(holdings))
        self._current_holdings = holdings
        for i, h in enumerate(holdings):
            day_chg = h.get("day_change_pct", 0)
            pnl = h.get("pnl", 0)
            pnl_pct = h.get("pnl_pct", 0)

            row_data = [
                (h["ticker"], QColor("white"), True),
                (f"{h['shares']:.3f}", QColor(COLORS["text"]), False),
                (f"${h['avg_cost']:.2f}", QColor(COLORS["text"]), False),
                (f"${h.get('current_price', 0):.2f}", QColor("white"), False),
                (f"{day_chg:+.2f}%", QColor(COLORS["green"]) if day_chg >= 0 else QColor(COLORS["red"]), False),
                (f"${h.get('total_value', 0):,.2f}", QColor("white"), False),
                (f"${pnl:+,.2f}", QColor(COLORS["green"]) if pnl >= 0 else QColor(COLORS["red"]), False),
                (f"{pnl_pct:+.2f}%", QColor(COLORS["green"]) if pnl_pct >= 0 else QColor(COLORS["red"]), False),
            ]
            for j, (text, color, bold) in enumerate(row_data):
                item = QTableWidgetItem(text)
                item.setForeground(QBrush(color))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if bold:
                    f = QFont(); f.setBold(True); item.setFont(f)
                self.holdings_table.setItem(i, j, item)

            # Remove button
            rm_btn = QPushButton("Remove")
            rm_btn.setStyleSheet(f"background: #330011; color: {COLORS['red']}; border: 1px solid {COLORS['red']}; border-radius: 4px; padding: 4px 8px; font-size: 11px;")
            rm_btn.clicked.connect(lambda _, t=h["ticker"]: self._remove_position(t))
            self.holdings_table.setCellWidget(i, 8, rm_btn)
            self.holdings_table.setRowHeight(i, 48)

    def _update_stats(self, stats):
        if not stats:
            return
        def fmt_money(v):
            return f"${v:,.2f}"
        def fmt_pct(v):
            s = "+" if v >= 0 else ""
            return f"{s}{v:.2f}%"

        mapping = {
            "total_value": fmt_money(stats.get("total_value", 0)),
            "total_pnl": fmt_money(stats.get("total_pnl", 0)),
            "total_pnl_pct": fmt_pct(stats.get("total_pnl_pct", 0)),
            "cash": fmt_money(stats.get("cash", 0)),
            "win_rate": f"{stats.get('win_rate', 0):.0f}%",
            "best_performer": stats.get("best_performer", "—"),
            "worst_performer": stats.get("worst_performer", "—"),
        }
        for key, val in mapping.items():
            if key in self.stat_labels:
                self.stat_labels[key].setText(val)
                if key in ("total_pnl", "total_pnl_pct"):
                    pnl = stats.get("total_pnl", 0)
                    color = COLORS["green"] if pnl >= 0 else COLORS["red"]
                    self.stat_labels[key].setStyleSheet(f"color: {color}; font-size: 15px; font-weight: bold;")

    def _draw_perf_chart(self, holdings):
        if not holdings:
            return
        self.perf_plot.clear()
        tickers = [h["ticker"] for h in holdings]
        pnl_pcts = [h.get("pnl_pct", 0) for h in holdings]
        x = np.arange(len(tickers))

        for i, (t, pct) in enumerate(zip(tickers, pnl_pcts)):
            color = COLORS["green"] if pct >= 0 else COLORS["red"]
            bar = pg.BarGraphItem(x=[i], height=[pct], width=0.6, brush=pg.mkBrush(color + "bb"))
            self.perf_plot.addItem(bar)

        ax = self.perf_plot.getAxis('bottom')
        ax.setTicks([list(enumerate(tickers))])
        self.perf_plot.addLine(y=0, pen=pg.mkPen(color=COLORS["border"], width=1))

    def _add_position(self):
        dlg = AddPositionDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            vals = dlg.get_values()
            if vals["ticker"] and vals["shares"] > 0:
                portfolio_manager.add_holding(vals["ticker"], vals["shares"], vals["avg_cost"])
                portfolio_manager.add_journal_entry(
                    vals["ticker"], "BUY", vals["shares"], vals["avg_cost"], vals["notes"]
                )
                self.refresh()
                self._refresh_journal()

    def _remove_position(self, ticker):
        portfolio_manager.remove_holding(ticker)
        self.refresh()

    def _add_journal_entry(self):
        dlg = AddPositionDialog(self)
        dlg.setWindowTitle("Log Trade")
        if dlg.exec() == QDialog.DialogCode.Accepted:
            vals = dlg.get_values()
            if vals["ticker"]:
                portfolio_manager.add_journal_entry(
                    vals["ticker"], "BUY", vals["shares"], vals["avg_cost"], vals["notes"]
                )
                self._refresh_journal()

    def _refresh_journal(self):
        entries = portfolio_manager.get_journal_entries()
        self.journal_table.setRowCount(len(entries))
        for i, e in enumerate(reversed(entries)):
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(e["date"]).strftime("%Y-%m-%d %H:%M")
            except Exception:
                dt = e.get("date", "")
            action_color = QColor(COLORS["green"]) if e.get("action") == "BUY" else QColor(COLORS["red"])
            row = [
                (dt, QColor(COLORS["muted"])),
                (e.get("ticker", ""), QColor("white")),
                (e.get("action", ""), action_color),
                (f"{e.get('shares', 0):.3f}", QColor(COLORS["text"])),
                (f"${e.get('price', 0):.2f}", QColor(COLORS["text"])),
                (f"${e.get('total', 0):.2f}", QColor(COLORS["text"])),
                (e.get("notes", ""), QColor(COLORS["muted"])),
            ]
            for j, (text, color) in enumerate(row):
                item = QTableWidgetItem(text)
                item.setForeground(QBrush(color))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.journal_table.setItem(i, j, item)
            self.journal_table.setRowHeight(i, 40)
