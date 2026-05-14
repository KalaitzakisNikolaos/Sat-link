"""IQ constellation diagram with noise overlay."""

import numpy as np
from gui.core.mpl_canvas import MplCanvas
from models.modulation import ModulationPerformance

_MODE_SUFFIX = {
    'Uplink Only': 'Uplink',
    'Downlink Only': 'Downlink',
}


def create_constellation_tab(mw):
    """Single-canvas tab for the IQ scatter plot."""
    from PyQt5.QtWidgets import QWidget, QVBoxLayout

    tab = QWidget()
    layout = QVBoxLayout(tab)
    mw.constellation_canvas = MplCanvas(mw, width=6, height=6, dpi=100)
    layout.addWidget(mw.constellation_canvas)
    return tab


def _ideal_points(mod):
    """Return (I, Q) arrays of ideal constellation reference points."""
    if mod == 'BPSK':
        return np.array([-1.0, 1.0]), np.array([0.0, 0.0])

    if mod == 'QPSK':
        ph = [np.pi/4, 3*np.pi/4, 5*np.pi/4, 7*np.pi/4]
        return np.cos(ph), np.sin(ph)

    if mod == '8PSK':
        ph = np.linspace(0, 2*np.pi, 9)[:-1]
        return np.cos(ph), np.sin(ph)

    if mod == '16QAM':
        lv = [-3, -1, 1, 3]
        gi, gq = np.meshgrid(lv, lv)
        s = np.sqrt(10)
        return gi.flatten() / s, gq.flatten() / s

    if mod == '16APSK':
        inner = [np.pi/4, 3*np.pi/4, 5*np.pi/4, 7*np.pi/4]
        outer = np.linspace(0, 2*np.pi, 13)[:-1]
        i = np.concatenate([1.0 * np.cos(inner), 2.85 * np.cos(outer)])
        q = np.concatenate([1.0 * np.sin(inner), 2.85 * np.sin(outer)])
        n = np.sqrt(np.mean(i**2 + q**2))
        return i / n, q / n

    if mod == '32APSK':
        r0 = [np.pi/4, 3*np.pi/4, 5*np.pi/4, 7*np.pi/4]
        r1 = np.linspace(0, 2*np.pi, 13)[:-1]
        r2 = np.linspace(0, 2*np.pi, 17)[:-1]
        i = np.concatenate([1.0*np.cos(r0), 2.84*np.cos(r1), 5.27*np.cos(r2)])
        q = np.concatenate([1.0*np.sin(r0), 2.84*np.sin(r1), 5.27*np.sin(r2)])
        n = np.sqrt(np.mean(i**2 + q**2))
        return i / n, q / n

    if mod == '64QAM':
        lv = [-7, -5, -3, -1, 1, 3, 5, 7]
        gi, gq = np.meshgrid(lv, lv)
        s = np.sqrt(42)
        return gi.flatten() / s, gq.flatten() / s

    # fallback: QPSK
    ph = [np.pi/4, 3*np.pi/4, 5*np.pi/4, 7*np.pi/4]
    return np.cos(ph), np.sin(ph)


def update_constellation(mw):
    """Scatter received symbols over ideal reference points."""
    ax = mw.constellation_canvas.axes
    ax.clear()
    ax.set_facecolor('#ffffff')

    mod = mw.modulation_combo.currentText()
    link_mode = mw.link_mode_combo.currentText()

    I_id, Q_id = ModulationPerformance.generate_constellation(mod, 1000)

    # determine operating Eb/N0 from last calculation
    ebn0_db = 10.0
    subtitle = ''
    if hasattr(mw, 'last_results') and mw.last_results is not None:
        r = mw.last_results
        if link_mode == 'Uplink Only':
            ebn0_db = r['uplink']['uplink_ebn0_db']
        elif link_mode == 'Downlink Only':
            ebn0_db = r['downlink']['downlink_ebn0_db']
        else:
            ebn0_db = r['total_ebn0_db']
        subtitle = f"Eb/N\u2080 = {ebn0_db:.1f} dB"

    sigma = 1.0 / np.sqrt(2 * 10 ** (ebn0_db / 10))
    np.random.seed(None)
    I_rx = I_id + np.random.normal(0, sigma, len(I_id))
    Q_rx = Q_id + np.random.normal(0, sigma, len(Q_id))

    ax.scatter(I_rx, Q_rx, alpha=0.5, s=12,
               c='#2196F3', edgecolors='none', label='Received')

    I_ref, Q_ref = _ideal_points(mod)
    ax.scatter(I_ref, Q_ref, alpha=1.0, s=80,
               c='#FF5722', marker='x', linewidths=2, label='Ideal')

    ax.axhline(y=0, color='black', linestyle='--', alpha=0.3)
    ax.axvline(x=0, color='black', linestyle='--', alpha=0.3)
    ax.set_xlabel('In-Phase (I)')
    ax.set_ylabel('Quadrature (Q)')

    suffix = _MODE_SUFFIX.get(link_mode, 'End-to-End')
    ax.set_title(f'{mod} - {suffix}\n{subtitle}', fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_aspect('equal')
    ax.legend(loc='upper right', fontsize=8)

    lim = max(np.max(np.abs(I_rx)), np.max(np.abs(Q_rx)), 0.1) * 1.3
    ax.set_xlim([-lim, lim])
    ax.set_ylim([-lim, lim])

    mw.constellation_canvas.figure.tight_layout()
    mw.constellation_canvas.draw()
