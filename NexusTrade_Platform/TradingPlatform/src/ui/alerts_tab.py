"""
Alerts Tab - Price and indicator alerts
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView,
    QDialog, QFormLayout, QLineEdit, QDoubleSpinBox,
    QComboBox, QDialogButtonBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QBrush

from data.portfolio_manager import portfolio_manager

COLORS = {
    "bg": "#0a0e1a", "surface": "#0f1629", "border": "#1a2744",
    "accent": "#00d4ff", "green": "#00ff88", "red": "#ff4466",
    "yellow": "#ffdd44", "text": "#e0e6ff", "muted": "#445577",
}

TABLE_STYLE = """
    QTableWidget { background: #0a0e1a; color: #e0e6ff; border: none;
        gridline-color: #1a2744; font-size: 12px; }
    QTableWidget::item { padding: 8px; border-bottom: 1px solid #111827; }
    QHeaderView::section { background: #080c18; color: #445577; font-size: 10px;
        font-weight: bold; border: none; border-bottom: 1px solid #1a2744; padding: 8px; }
"""


class AddAlertDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Alert")
        self.setMinimumWidth(340)
        self.setStyleSheet(f"background: {COLORS['surface']}; color: {COLORS['text']};")
        layout = QFormLayout(self)
        layout.setSpacing(12)

        style = f"background: #080c18; color: {COLORS['text']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 6px;"

        self.ticker_input = QLineEdit()
        self.ticker_input.setPlaceholderText("e.g. AAPL")
        self.ticker_input.setStyleSheet(style)
        layout.addRow("Ticker:", self.ticker_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["Price", "RSI", "Volume"])
        self.type_combo.setStyleSheet(style)
        layout.addRow("Alert Type:", self.type_combo)

        self.condition_combo = QComboBox()
        self.condition_combo.addItems(["Above", "Below"])
        self.condition_combo.setStyleSheet(style)
        layout.addRow("Condition:", self.condition_combo)

        self.value_input = QDoubleSpinBox()
        self.value_input.setRange(0, 1_000_000)
        self.value_input.setDecimals(2)
        self.value_input.setStyleSheet(style)
        layout.addRow("Value:", self.value_input)

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btns.setStyleSheet(f"QPushButton {{background: {COLORS['accent']}; color: #000; border: none; border-radius: 4px; padding: 6px 16px; font-weight: bold;}}")
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addRow(btns)

    def get_values(self):
        return {
            "ticker": self.ticker_input.text().strip().upper(),
            "type": self.type_combo.currentText().lower(),
            "condition": self.condition_combo.currentText().lower(),
            "value": self.value_input.value(),
        }


class AlertsTab(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._refresh_alerts()

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
        title = QLabel("🔔  ALERTS")
        title.setStyleSheet("color: white; font-size: 18px; font-weight: bold;")
        hdr_layout.addWidget(title)
        hdr_layout.addStretch()

        add_btn = QPushButton("+ Add Alert")
        add_btn.setStyleSheet(f"background: {COLORS['accent']}; color: #000; border: none; border-radius: 6px; padding: 8px 16px; font-weight: bold;")
        add_btn.clicked.connect(self._add_alert)
        hdr_layout.addWidget(add_btn)
        layout.addWidget(header)

        # Active alerts
        active_label = QLabel("  ACTIVE ALERTS")
        active_label.setFixedHeight(36)
        active_label.setStyleSheet(f"background: {COLORS['bg']}; color: {COLORS['muted']}; font-size: 10px; font-weight: bold; border-bottom: 1px solid {COLORS['border']};")
        layout.addWidget(active_label)

        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(6)
        self.alerts_table.setHorizontalHeaderLabels(["Ticker", "Type", "Condition", "Target Value", "Status", "Remove"])
        self.alerts_table.setStyleSheet(TABLE_STYLE)
        self.alerts_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.alerts_table.verticalHeader().setVisible(False)
        self.alerts_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.alerts_table, 1)

        # Triggered alerts log
        triggered_label = QLabel("  TRIGGERED ALERTS LOG")
        triggered_label.setFixedHeight(36)
        triggered_label.setStyleSheet(f"background: {COLORS['bg']}; color: {COLORS['muted']}; font-size: 10px; font-weight: bold; border-top: 1px solid {COLORS['border']}; border-bottom: 1px solid {COLORS['border']};")
        layout.addWidget(triggered_label)

        self.log_table = QTableWidget()
        self.log_table.setColumnCount(4)
        self.log_table.setHorizontalHeaderLabels(["Time", "Ticker", "Alert", "Message"])
        self.log_table.setStyleSheet(TABLE_STYLE)
        self.log_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.log_table.verticalHeader().setVisible(False)
        self.log_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.log_table.setMaximumHeight(200)
        layout.addWidget(self.log_table)

        self.triggered_log = []

    def _refresh_alerts(self):
        alerts = portfolio_manager.get_alerts()
        self.alerts_table.setRowCount(len(alerts))
        for i, alert in enumerate(alerts):
            cond = alert.get("condition", "above")
            t_type = alert.get("type", "price")
            row = [
                (alert.get("ticker", ""), QColor("white")),
                (t_type.upper(), QColor(COLORS["accent"])),
                (cond.upper(), QColor(COLORS["yellow"])),
                (f"{alert.get('value', 0):.2f}", QColor(COLORS["text"])),
                ("ACTIVE ●", QColor(COLORS["green"])),
            ]
            for j, (text, color) in enumerate(row):
                item = QTableWidgetItem(text)
                item.setForeground(QBrush(color))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.alerts_table.setItem(i, j, item)

            rm_btn = QPushButton("✕")
            rm_btn.setStyleSheet(f"background: #330011; color: {COLORS['red']}; border: 1px solid {COLORS['red']}; border-radius: 4px; padding: 4px 8px;")
            rm_btn.clicked.connect(lambda _, aid=alert.get("id"): self._remove_alert(aid))
            self.alerts_table.setCellWidget(i, 5, rm_btn)
            self.alerts_table.setRowHeight(i, 44)

    def _add_alert(self):
        dlg = AddAlertDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            vals = dlg.get_values()
            if vals["ticker"]:
                portfolio_manager.add_alert(
                    vals["ticker"], vals["type"], vals["value"], vals["condition"]
                )
                self._refresh_alerts()

    def _remove_alert(self, alert_id):
        portfolio_manager.remove_alert(alert_id)
        self._refresh_alerts()

    def log_triggered(self, alert, current_val):
        from datetime import datetime
        msg = f"{alert['type'].upper()} {alert['condition']} {alert['value']:.2f} (Current: {current_val:.2f})"
        self.triggered_log.append({
            "time": datetime.now().strftime("%H:%M:%S"),
            "ticker": alert["ticker"],
            "alert": f"{alert['type'].upper()} {alert['condition'].upper()}",
            "msg": msg,
        })
        self._refresh_log()

    def _refresh_log(self):
        entries = list(reversed(self.triggered_log))[-50:]
        self.log_table.setRowCount(len(entries))
        for i, e in enumerate(entries):
            row = [
                (e["time"], QColor(COLORS["muted"])),
                (e["ticker"], QColor("white")),
                (e["alert"], QColor(COLORS["yellow"])),
                (e["msg"], QColor(COLORS["text"])),
            ]
            for j, (text, color) in enumerate(row):
                item = QTableWidgetItem(text)
                item.setForeground(QBrush(color))
                self.log_table.setItem(i, j, item)
            self.log_table.setRowHeight(i, 36)
