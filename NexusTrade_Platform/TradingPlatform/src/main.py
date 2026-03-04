import sys
import os

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, BASE_DIR)

from PyQt6.QtWidgets import QApplication, QSplashScreen
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QPixmap, QFont, QPainter, QColor, QLinearGradient
import qdarktheme
from ui.main_window import MainWindow


def create_splash():
    pixmap = QPixmap(600, 350)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient = QLinearGradient(0, 0, 600, 350)
    gradient.setColorAt(0, QColor("#0a0e1a"))
    gradient.setColorAt(1, QColor("#0d1f3c"))
    painter.fillRect(0, 0, 600, 350, gradient)
    painter.setPen(QColor("#00d4ff"))
    painter.drawLine(40, 200, 560, 200)
    font = QFont("Segoe UI", 42, QFont.Weight.Bold)
    painter.setFont(font)
    painter.setPen(QColor("#ffffff"))
    painter.drawText(0, 0, 600, 200, Qt.AlignmentFlag.AlignCenter, "NEXUS TRADE")
    font2 = QFont("Segoe UI", 13)
    painter.setFont(font2)
    painter.setPen(QColor("#00d4ff"))
    painter.drawText(0, 200, 600, 80, Qt.AlignmentFlag.AlignCenter, "Professional AI-Powered Trading Platform")
    painter.end()
    return pixmap


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("NexusTrade")
    app.setApplicationVersion("2.0")

    qdarktheme.setup_theme("dark")

    splash_pix = create_splash()
    splash = QSplashScreen(splash_pix, Qt.WindowType.WindowStaysOnTopHint)
    splash.show()
    app.processEvents()

    window = MainWindow()

    def show_main():
        splash.finish(window)
        window.show()

    QTimer.singleShot(2500, show_main)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
