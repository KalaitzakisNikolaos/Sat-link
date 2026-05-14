"""Splash screen and shared color constants."""

import os
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QPainter, QLinearGradient, QColor, QFont

# IEEE color scheme
IEEE_COLORS = {
    'primary': '#4f46e5',
    'secondary': '#7c3aed',
    'tertiary': '#ec4899',
    'quaternary': '#f59e0b',
    'success': '#10b981',
    'warning': '#f97316',
    'error': '#ef4444',
    'grid': '#cbd5e1',
}


def create_splash_screen():
    """Create a gradient splash screen with university logo."""
    splash_pix = QPixmap(620, 480)
    splash_pix.fill(Qt.GlobalColor.transparent)

    painter = QPainter(splash_pix)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    gradient = QLinearGradient(0, 0, 620, 480)
    gradient.setColorAt(0, QColor("#4f46e5"))
    gradient.setColorAt(0.4, QColor("#7c3aed"))
    gradient.setColorAt(0.7, QColor("#6366f1"))
    gradient.setColorAt(1, QColor("#4338ca"))

    painter.setBrush(gradient)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, 620, 480, 24, 24)

    highlight = QLinearGradient(0, 0, 0, 240)
    highlight.setColorAt(0, QColor(255, 255, 255, 30))
    highlight.setColorAt(1, QColor(255, 255, 255, 0))
    painter.setBrush(highlight)
    painter.drawRoundedRect(0, 0, 620, 240, 24, 24)

    # Draw the university logo
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logo_path = os.path.join(base_dir, "hmu.png")
    logo_pix = QPixmap(logo_path)
    if not logo_pix.isNull():
        logo_size = 130
        scaled_logo = logo_pix.scaled(logo_size, logo_size,
                                       Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
        logo_x = (620 - scaled_logo.width()) // 2
        logo_y = 30
        painter.drawPixmap(logo_x, logo_y, scaled_logo)

    painter.setPen(QColor("white"))
    painter.setFont(QFont("Segoe UI", 28, QFont.Weight.Bold))
    painter.drawText(0, 175, 620, 50, Qt.AlignmentFlag.AlignCenter, "Sat-Link")

    painter.setPen(QColor(200, 200, 255, 200))
    painter.setFont(QFont("Segoe UI", 13, QFont.Weight.Normal))
    painter.drawText(0, 235, 620, 30, Qt.AlignmentFlag.AlignCenter,
                     "Professional ITU-R Compliant Link Budget Analysis")

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 255, 255, 25))
    painter.drawRoundedRect(190, 290, 240, 40, 20, 20)
    painter.setPen(QColor("#fbbf24"))
    painter.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
    painter.drawText(190, 290, 240, 40, Qt.AlignmentFlag.AlignCenter, "Professional Edition")

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 255, 255, 20))
    painter.drawRoundedRect(160, 390, 300, 6, 3, 3)
    painter.setBrush(QColor(255, 255, 255, 80))
    painter.drawRoundedRect(160, 390, 180, 6, 3, 3)

    painter.setPen(QColor(200, 200, 255, 180))
    painter.setFont(QFont("Segoe UI", 10, QFont.Weight.Normal))
    painter.drawText(0, 410, 620, 30, Qt.AlignmentFlag.AlignCenter,
                     "Loading models and initializing...")

    painter.end()
    return splash_pix
