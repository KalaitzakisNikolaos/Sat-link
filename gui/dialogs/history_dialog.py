"""
History dialog module — shows calculation history and CSV export.
"""
import csv
from datetime import datetime
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit,
    QPushButton, QFileDialog, QMessageBox
)
from PyQt5.QtGui import QFont


def show_history_dialog(mw):
    """Show calculation history in a professional dialog"""
    if not mw.calculation_history:
        QMessageBox.information(mw, "History", "No calculations recorded yet.")
        return

    dialog = QDialog(mw)
    dialog.setWindowTitle(" Calculation History")
    dialog.setMinimumSize(900, 500)
    layout = QVBoxLayout(dialog)

    # Header
    header = QLabel(f" Calculation History ({len(mw.calculation_history)} entries)")
    header.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
    header.setStyleSheet("color: #1976D2;")
    layout.addWidget(header)

    # Table-like display
    history_text = QTextEdit()
    history_text.setReadOnly(True)
    history_text.setFont(QFont("Consolas", 9))

    lines = []
    cn0_label = "C/N\u2080"
    ebn0_label = "Eb/N\u2080"
    lines.append(
        f"{'#':>3} {'Time':>10} {'Mode':<14} {'Sat':>4} {'f_up':>6} {'f_dn':>6} "
        f"{'Mod':>6} {'Margin':>8} {cn0_label:>8} {ebn0_label:>7} {'El':>6}"
    )
    lines.append("\u2500" * 100)

    for i, h in enumerate(reversed(mw.calculation_history), 1):
        margin = h['total_margin_db']
        status = "\u2705" if margin > 0 else "\u274c"
        lines.append(
            f"{i:>3} {h['timestamp']:>10} {h['link_mode']:<14} {h['sat_type']:>4} "
            f"{h['frequency_up']:>5.1f}G {h['frequency_dn']:>5.1f}G {h['modulation']:>6} "
            f"{margin:>7.2f} {status} {h['total_cn0_db']:>7.1f} {h['total_ebn0_db']:>6.1f} "
            f"{h['elevation_deg']:>5.1f}\u00b0"
        )

    history_text.setPlainText("\n".join(lines))
    layout.addWidget(history_text)

    # Buttons
    btn_layout = QHBoxLayout()
    clear_btn = QPushButton(" Clear History")
    clear_btn.setProperty('variant', 'warning')
    clear_btn.clicked.connect(lambda: (mw.calculation_history.clear(), dialog.close()))
    btn_layout.addWidget(clear_btn)

    export_btn = QPushButton("\U0001f4e4 Export to CSV")
    export_btn.clicked.connect(lambda: _export_history_csv(mw, dialog))
    btn_layout.addWidget(export_btn)

    btn_layout.addStretch()
    close_btn = QPushButton("Close")
    close_btn.setProperty('variant', 'outline')
    close_btn.clicked.connect(dialog.close)
    btn_layout.addWidget(close_btn)
    layout.addLayout(btn_layout)

    dialog.exec()


def _export_history_csv(mw, parent_dialog=None):
    """Export calculation history to CSV"""
    filepath, _ = QFileDialog.getSaveFileName(
        parent_dialog or mw, "Export History",
        f"link_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        "CSV Files (*.csv)")
    if not filepath:
        return
    try:
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['#', 'Time', 'Link Mode', 'Satellite', 'Uplink Freq (GHz)',
                             'Downlink Freq (GHz)', 'Modulation', 'Margin (dB)',
                             'C/N0 (dB-Hz)', 'Eb/N0 (dB)', 'Elevation (deg)'])
            for i, h in enumerate(mw.calculation_history, 1):
                writer.writerow([i, h['timestamp'], h['link_mode'], h['sat_type'],
                                 h['frequency_up'], h['frequency_dn'], h['modulation'],
                                 f"{h['total_margin_db']:.2f}", f"{h['total_cn0_db']:.2f}",
                                 f"{h['total_ebn0_db']:.2f}", f"{h['elevation_deg']:.1f}"])
        QMessageBox.information(parent_dialog or mw, "Export", f"History exported to:\n{filepath}")
    except Exception as e:
        QMessageBox.warning(parent_dialog or mw, "Export Error", str(e))
