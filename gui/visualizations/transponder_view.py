"""Transponder black-box diagram with transfer curve and noise cascade."""

import numpy as np
from matplotlib.patches import FancyBboxPatch, Circle
from gui.core.mpl_canvas import MplCanvas


def create_transponder_tab(mw):
    """Splitter: block diagram on top, transfer + noise side-by-side below."""
    from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter
    from PyQt5.QtCore import Qt

    tab = QWidget()
    lay = QVBoxLayout(tab)

    splitter = QSplitter(Qt.Orientation.Vertical)

    mw.transponder_block_canvas = MplCanvas(mw, width=12, height=5, dpi=100)
    splitter.addWidget(mw.transponder_block_canvas)

    bottom = QWidget()
    bl = QHBoxLayout(bottom)
    mw.transponder_transfer_canvas = MplCanvas(mw, width=6, height=4, dpi=100)
    bl.addWidget(mw.transponder_transfer_canvas)
    mw.transponder_noise_canvas = MplCanvas(mw, width=6, height=4, dpi=100)
    bl.addWidget(mw.transponder_noise_canvas)
    splitter.addWidget(bottom)
    splitter.setSizes([400, 350])

    lay.addWidget(splitter)
    return tab


def _stage_box(ax, x, y, w, h, label, fc, ec, sub_lines, label_color='black'):
    """Draw one transponder stage block with sub-labels underneath."""
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h, boxstyle='round,pad=0.15',
        facecolor=fc, edgecolor=ec, lw=1.5))
    ax.text(x + w/2, y + h*0.65, label, fontsize=10, ha='center',
            fontweight='bold', color=label_color)
    for i, (txt, fs, clr) in enumerate(sub_lines):
        ax.text(x + w/2, y + h*0.3 - i*0.35, txt,
                fontsize=fs, ha='center', color=clr)


def _arrow(ax, x_to, x_from, y=2.0, color='#333'):
    ax.annotate('', xy=(x_to, y), xytext=(x_from, y),
                arrowprops=dict(arrowstyle='->', color=color, lw=1.5))


def update_transponder_block_diagram(mw):
    """Redraw the transponder chain: Rx Ant → LNA → Mixer → IF Amp → PA → Tx Ant."""
    ax = mw.transponder_block_canvas.axes
    ax.clear()
    ax.set_xlim(-1, 16)
    ax.set_ylim(-2, 5)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Satellite Transponder \u2014 Block Diagram ("Black Box")',
                 fontweight='bold')

    s = mw.transponder.get_chain_summary()
    stg = s['stages']

    # transponder enclosure
    ax.add_patch(FancyBboxPatch(
        (1.5, -0.5), 11.5, 4.5, boxstyle='round,pad=0.3',
        facecolor='#FFF3E0', edgecolor='#FF5722', linewidth=2.5, alpha=0.9))
    ax.text(7.25, 4.4, 'TRANSPONDER (Black Box)',
            fontsize=11, ha='center', fontweight='bold', color='#BF360C')

    # rx antenna + uplink label
    _arrow(ax, 0.8, -0.2, color='#1565C0')
    ax.text(-0.5, 2.7, 'f\u2081 (uplink)', fontsize=9, color='#1565C0',
            fontweight='bold', ha='center')
    ax.text(-0.5, 1.4, f'{s["uplink_freq_ghz"]:.1f} GHz',
            fontsize=8, color='#666', ha='center')
    ax.plot([0.8, 1.3, 0.8], [2.6, 2.0, 1.4], 'k-', lw=2)
    ax.text(0.8, 0.7, 'Rx Ant', fontsize=8, ha='center', color='#333')
    ax.text(0.8, 0.2, f'G={s["rx_antenna_gain_dbi"]:.0f} dBi',
            fontsize=7, ha='center', color='#666')

    # LNA
    _arrow(ax, 2.2, 1.5)
    _stage_box(ax, 2.2, 1.2, 2.0, 1.6, 'LNA', '#E3F2FD', '#1976D2', [
        (f'G={stg[0]["gain_db"]:.0f} dB', 8, '#333'),
        (f'NF={stg[0]["noise_figure_db"]:.1f} dB', 7, '#666'),
    ], label_color='#1565C0')

    # Mixer
    _arrow(ax, 5.0, 4.3)
    mx, my = 5.8, 2.0
    ax.add_patch(Circle((mx, my), 0.7,
                        facecolor='#FFF9C4', edgecolor='#F57F17', lw=1.5))
    ax.text(mx, my, '\u00d7', fontsize=18, ha='center', va='center',
            fontweight='bold', color='#E65100')
    ax.text(mx, 0.7, 'Mixer', fontsize=8, ha='center', color='#333')
    ax.text(mx, 0.2, f'G={stg[1]["gain_db"]:.0f} dB',
            fontsize=7, ha='center', color='#666')
    ax.annotate('', xy=(mx, 1.2), xytext=(mx, -0.3),
                arrowprops=dict(arrowstyle='->', color='#E65100', lw=1.5))
    ax.text(mx, -0.8, f'LO\n{s["lo_freq_ghz"]:.1f} GHz',
            fontsize=8, ha='center', color='#E65100', fontweight='bold')

    # IF Amp
    _arrow(ax, 7.5, 6.7)
    _stage_box(ax, 7.5, 1.2, 2.0, 1.6, 'IF Amp', '#E8F5E9', '#388E3C', [
        (f'G={stg[2]["gain_db"]:.0f} dB', 8, '#333'),
        (f'NF={stg[2]["noise_figure_db"]:.1f} dB', 7, '#666'),
    ], label_color='#2E7D32')

    # PA
    _arrow(ax, 10.3, 9.6)
    _stage_box(ax, 10.3, 1.0, 2.3, 2.0, 'PA', '#FCE4EC', '#C62828', [
        (f'G={stg[3]["gain_db"]:.0f} dB', 8, '#333'),
        (f'P_sat={s["saturated_power_dbw"]:.0f} dBW', 7, '#666'),
        (f'OBO={mw.transponder.output_backoff_db:.1f} dB', 7, '#999'),
    ], label_color='#B71C1C')

    # tx antenna + downlink label
    _arrow(ax, 13.5, 12.7)
    ax.plot([13.5, 14.0, 13.5], [2.6, 2.0, 1.4], 'k-', lw=2)
    ax.text(14.0, 0.7, 'Tx Ant', fontsize=8, ha='center', color='#333')
    ax.text(14.0, 0.2, f'G={s["tx_antenna_gain_dbi"]:.0f} dBi',
            fontsize=7, ha='center', color='#666')
    _arrow(ax, 15.5, 14.2, color='#C62828')
    ax.text(15.7, 2.7, 'f\u2082 (downlink)', fontsize=9, color='#C62828',
            fontweight='bold', ha='center')
    ax.text(15.7, 1.4, f'{s["downlink_freq_ghz"]:.1f} GHz',
            fontsize=8, color='#666', ha='center')

    # summary bar
    txt = (f'Total Gain: {s["total_gain_db"]:.1f} dB  |  '
           f'Cascade NF: {s["cascade_noise_figure_db"]:.2f} dB  |  '
           f'T_sys: {s["cascade_noise_temp_k"]:.0f} K  |  '
           f'G/T: {s["satellite_gt_db_k"]:.1f} dB/K  |  '
           f'EIRP: {s["satellite_eirp_dbw"]:.1f} dBW  |  '
           f'BW: {s["bandwidth_mhz"]:.0f} MHz')
    ax.text(7.5, -1.5, txt, fontsize=9, ha='center', fontweight='bold',
            color='#333', bbox=dict(boxstyle='round,pad=0.4',
                                    facecolor='#EEEEEE', edgecolor='#999', alpha=0.9))

    mw.transponder_block_canvas.figure.tight_layout()
    mw.transponder_block_canvas.draw()


def update_transponder_transfer_curve(mw):
    """PA AM/AM transfer characteristic."""
    ax = mw.transponder_transfer_canvas.axes
    ax.clear()

    tc = mw.transponder.get_transfer_curve()

    ax.plot(tc['input_dbw'], tc['output_linear_dbw'],
            'b--', alpha=0.5, lw=1, label='Linear (Ideal)')
    ax.plot(tc['input_dbw'], tc['output_saturated_dbw'],
            'r-', lw=2, label='Actual (Saturated)')
    ax.axhline(y=tc['saturation_power_dbw'], color='orange',
               linestyle=':', lw=1.5, label=f'P_sat = {tc["saturation_power_dbw"]:.1f} dBW')
    ax.plot(tc['p1db_input_dbw'], tc['p1db_output_dbw'],
            'go', markersize=8, label=f'P\u2081dB = {tc["p1db_output_dbw"]:.1f} dBW')

    obo = mw.transponder.output_backoff_db
    op_out = tc['saturation_power_dbw'] - obo
    op_in = op_out - tc['total_gain_db']
    ax.plot(op_in, op_out, 'ms', markersize=10,
            label=f'Operating (OBO={obo:.1f} dB)')

    ax.set_xlabel('Input Power (dBW)')
    ax.set_ylabel('Output Power (dBW)')
    ax.set_title('PA Transfer Characteristic (AM/AM)', fontweight='bold')
    ax.legend(fontsize=8, loc='lower right')
    ax.grid(True, alpha=0.3)
    ax.set_xlim([-40, 5])

    mw.transponder_transfer_canvas.figure.tight_layout()
    mw.transponder_transfer_canvas.draw()


def update_transponder_noise_cascade(mw):
    """Noise cascade bar chart: per-stage gain vs noise temperature."""
    ax = mw.transponder_noise_canvas.axes
    ax.clear()

    s = mw.transponder.get_chain_summary()
    stg = s['stages']

    names = [st['name'] for st in stg]
    gains = [st['gain_db'] for st in stg]
    temps = [st['noise_temp_k'] for st in stg]
    cum_g = [st['cumulative_gain_db'] for st in stg]

    x = np.arange(len(names))
    w = 0.35
    ax2 = ax.twinx()

    ax.bar(x - w/2, gains, w, label='Gain (dB)', color='#2196F3', alpha=0.8)
    ax2.bar(x + w/2, temps, w, label='T_noise (K)', color='#FF9800', alpha=0.8)
    ax.plot(x, cum_g, 'r-o', lw=2, markersize=6, label='Cumulative Gain (dB)')

    ax.set_xlabel('Stage')
    ax.set_ylabel('Gain (dB)', color='#2196F3')
    ax2.set_ylabel('Noise Temp (K)', color='#FF9800')
    ax.set_title('Transponder Cascade Analysis', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.grid(True, alpha=0.3, axis='y')

    ax.text(0.02, 0.95,
            f'Cascade NF: {s["cascade_noise_figure_db"]:.2f} dB\n'
            f'T_total: {s["cascade_noise_temp_k"]:.0f} K',
            transform=ax.transAxes, fontsize=9, va='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc='upper right', fontsize=7)

    mw.transponder_noise_canvas.figure.tight_layout()
    mw.transponder_noise_canvas.draw()
