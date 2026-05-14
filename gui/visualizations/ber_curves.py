"""BER Performance Curves tab — creation and update logic."""

import numpy as np
from gui.core.mpl_canvas import MplCanvas
from models.modulation import ModulationPerformance


def create_ber_tab(mw):
    """Create BER tab."""
    from PyQt5.QtWidgets import QWidget, QVBoxLayout

    tab = QWidget()
    layout = QVBoxLayout(tab)
    mw.ber_canvas = MplCanvas(mw, width=8, height=6, dpi=100)
    layout.addWidget(mw.ber_canvas)
    return tab


def update_ber_plot(mw):
    """Update BER plot based on link mode."""
    mw.ber_canvas.axes.clear()
    mw.ber_canvas.axes.set_facecolor('#ffffff')

    ebn0_range = np.linspace(-2, 20, 100)
    modulations = ['BPSK', 'QPSK', '8PSK', '16QAM', '16APSK', '32APSK']
    colors = ['#4CAF50', '#2196F3', '#FF9800', '#9C27B0', '#F44336', '#00BCD4']
    linestyles = ['--', '-', '-', '-', '-', '-']
    linewidths = [3.0, 2.5, 2.5, 2.5, 2.5, 2.5]

    for mod, color, ls, lw in zip(modulations, colors, linestyles, linewidths):
        ber = ModulationPerformance.get_ber_curve(mod, ebn0_range)
        mw.ber_canvas.axes.semilogy(ebn0_range, ber, label=mod,
                                    linewidth=lw, color=color, linestyle=ls)

    if hasattr(mw, 'last_results') and hasattr(mw, 'last_params'):
        link_mode = mw.last_params.get('link_mode', 'Full Link')
        if link_mode == 'Uplink Only':
            current_ebn0 = mw.last_results['uplink']['uplink_ebn0_db']
            point_label = 'Uplink Operating Point'
            point_color = '#2196F3'
        elif link_mode == 'Downlink Only':
            current_ebn0 = mw.last_results['downlink']['downlink_ebn0_db']
            point_label = 'Downlink Operating Point'
            point_color = '#FF9800'
        else:
            current_ebn0 = mw.last_results['total_ebn0_db']
            point_label = 'Total Link Operating Point'
            point_color = 'red'

        current_mod = mw.modulation_combo.currentText()
        current_ber = ModulationPerformance.get_ber_curve(current_mod, np.array([current_ebn0]))[0]
        mw.ber_canvas.axes.plot(current_ebn0, current_ber, 'o', markersize=12,
                                label=point_label, color=point_color,
                                markeredgecolor='yellow', markeredgewidth=2)

    link_mode = mw.link_mode_combo.currentText()
    mw.ber_canvas.axes.set_xlabel('Eb/N\u2080 (dB)', fontsize=12, color='#212121')
    mw.ber_canvas.axes.set_ylabel('Bit Error Rate (BER)', fontsize=12, color='#212121')
    mw.ber_canvas.axes.set_title(f'BER Performance Curves - {link_mode}',
                                  fontsize=14, fontweight='bold', color='#1976D2')
    mw.ber_canvas.axes.grid(True, which='both', alpha=0.3, color='#bdbdbd')
    mw.ber_canvas.axes.legend(loc='best', facecolor='#ffffff',
                               edgecolor='#bdbdbd', labelcolor='#212121')
    mw.ber_canvas.axes.set_ylim([1e-9, 1])
    mw.ber_canvas.axes.tick_params(colors='#212121')

    mw.ber_canvas.figure.tight_layout()
    mw.ber_canvas.draw()
