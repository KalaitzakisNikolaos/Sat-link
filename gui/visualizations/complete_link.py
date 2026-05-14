"""Link budget results displayed as tabular subplots."""

from gui.core.mpl_canvas import MplCanvas

# table colours
_HDR = '#6366f1'
_ALT = ('#f8fafc', '#eef2ff')
_OK_BG, _OK_FG = '#dcfce7', '#166534'
_BAD_BG, _BAD_FG = '#fee2e2', '#991b1b'


def create_complete_link_tab(mw):
    """Single-canvas tab for the full link budget breakdown."""
    from PyQt5.QtWidgets import QWidget, QVBoxLayout

    tab = QWidget()
    layout = QVBoxLayout(tab)
    mw.complete_results_canvas = MplCanvas(mw, width=14, height=9, dpi=100)
    layout.addWidget(mw.complete_results_canvas, 1)
    return tab


def _render_table(ax, title, data, col_widths=None, hl_last=False, margin=None):
    """Draw a two-column parameter/value table on *ax*."""
    ax.axis('off')
    ax.set_facecolor('#f8fafc')
    cw = col_widths or [0.52, 0.44]

    tbl = ax.table(
        cellText=data, colLabels=['Parameter', 'Value'],
        cellLoc='left', colLoc='center', loc='upper center', colWidths=cw,
    )
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(8)

    n = len(data)
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor('#e2e8f0')
        cell.set_linewidth(0.5)
        cell.set_height(0.055)

        if r == 0:                                      # header row
            cell.set_facecolor(_HDR)
            cell.set_text_props(color='white', fontweight='bold', fontsize=10,
                                ha='center', va='center')
            cell.PAD = 0.5
            continue

        cell.set_facecolor(_ALT[r % 2])
        cell.set_text_props(fontsize=8)
        if c == 1:
            cell.set_text_props(fontsize=8, fontfamily='monospace', fontweight='600')
        cell.get_text().set_clip_on(True)

        # colour the last row green/red based on margin
        if hl_last and r == n and margin is not None:
            bg, fg = (_OK_BG, _OK_FG) if margin > 0 else (_BAD_BG, _BAD_FG)
            cell.set_facecolor(bg)
            cell.set_text_props(color=fg, fontweight='bold', fontsize=10)

    ax.set_title(title, fontsize=11, fontweight='700',
                 color='#4338ca', pad=14, loc='center')
    ax.title.set_position([0.5, 1.02])


def update_complete_results_text(mw, results, params):
    """Render geometry, UL, DL, modulation, transponder and E2E tables."""
    fig = mw.complete_results_canvas.figure
    fig.set_tight_layout(False)
    fig.set_constrained_layout(False)
    fig.clear()
    fig.patch.set_facecolor('#f8fafc')

    ul = results['uplink']
    dl = results['downlink']
    mode = params.get('link_mode', 'Full Link')
    tot_margin = results['total_margin_db']

    d_gs = params['gs_antenna_diameter_m']
    d_rx = mw.gs_diameter_spin.value()
    gs_tx_bw = 21.0 / (params['uplink_frequency_ghz'] * d_gs) if d_gs > 0 else 0
    gs_rx_bw = 21.0 / (params['downlink_frequency_ghz'] * d_rx) if d_rx > 0 else 0
    gamma = params.get('central_angle_deg', 0)

    dop = results.get('doppler', {})
    dop_ul = dop.get('uplink_doppler_khz', 0)
    dop_dl = dop.get('downlink_doppler_khz', 0)
    v_rad = dop.get('radial_velocity_kms', 0)
    v_sat = dop.get('satellite_velocity_kms', 0)
    f_ul_s = dop.get('uplink_freq_shifted_ghz', params['uplink_frequency_ghz'])
    f_dl_s = dop.get('downlink_freq_shifted_ghz', params['downlink_frequency_ghz'])
    max_dop_ul = dop.get('max_doppler_ul_khz', 0)
    max_dop_dl = dop.get('max_doppler_dl_khz', 0)

    geo_data = [
        ['Central Angle \u03b3', f'{gamma:.2f}\u00b0'],
        ['Elevation E', f'{params.get("elevation_deg", 45.0):.2f}\u00b0'],
        ['Slant Range d', f'{params.get("distance_km", 38000):.1f} km'],
        ['Altitude h', f'{params.get("altitude_km", 35786):.0f} km'],
        ['Sat Velocity', f'{v_sat:.3f} km/s'],
        ['Radial Velocity', f'{v_rad:+.4f} km/s'],
        ['UL Doppler \u0394f', f'{dop_ul:+.2f} kHz'],
        ['DL Doppler \u0394f', f'{dop_dl:+.2f} kHz'],
    ]

    ul_data = [
        ['TX Power', f'{params["gs_tx_power_dbw"]:.2f} dBW'],
        ['GS Antenna', f'{d_gs:.2f} m'],
        ['GS EIRP', f'{ul["gs_eirp_dbw"]:.2f} dBW'],
        ['\u03b8\u2083dB (TX)', f'{gs_tx_bw:.3f}\u00b0'],
        ['Frequency', f'{params["uplink_frequency_ghz"]:.3f} GHz'],
        ['Freq (Doppler)', f'{f_ul_s:.6f} GHz'],
        ['FSPL', f'{ul["fspl_db"]:.2f} dB'],
        ['Atm Loss', f'{ul["atmospheric_atten_db"]:.2f} dB'],
        ['Rain Atten', f'{ul["rain_atten_db"]:.2f} dB'],
        ['Sat RX Gain', f'{params["sat_rx_gain_dbi"]:.2f} dBi'],
        ['Sat G/T', f'{ul["sat_gt_db"]:.2f} dB/K'],
        ['Noise Temp', f'{ul["sat_noise_temp_k"]:.1f} K'],
        ['C/N\u2080', f'{ul["uplink_cn0_db"]:.2f} dB-Hz'],
        ['C/N', f'{ul["uplink_cn_db"]:.2f} dB'],
        ['Eb/N\u2080', f'{ul["uplink_ebn0_db"]:.2f} dB'],
        ['UL MARGIN', f'{ul["uplink_margin_db"]:+.2f} dB'],
    ]

    dl_data = [
        ['TX Power', f'{params["sat_power_dbw"]:.2f} dBW'],
        ['TX Gain', f'{params["sat_antenna_gain_dbi"]:.2f} dBi'],
        ['Sat EIRP', f'{dl["sat_eirp_dbw"]:.2f} dBW'],
        ['Frequency', f'{params["downlink_frequency_ghz"]:.3f} GHz'],
        ['Freq (Doppler)', f'{f_dl_s:.6f} GHz'],
        ['FSPL', f'{dl["fspl_db"]:.2f} dB'],
        ['Atm Loss', f'{dl["atmospheric_atten_db"]:.2f} dB'],
        ['Rain Atten', f'{dl["rain_atten_db"]:.2f} dB'],
        ['GS Antenna', f'{d_rx:.2f} m'],
        ['GS RX Gain', f'{dl["gs_antenna_gain_dbi"]:.2f} dBi'],
        ['G/T', f'{dl["gs_gt_db"]:.2f} dB/K'],
        ['Sys Temp', f'{dl["system_temp_k"]:.1f} K'],
        ['\u03b8\u2083dB (RX)', f'{gs_rx_bw:.3f}\u00b0'],
        ['C/N\u2080', f'{dl["downlink_cn0_db"]:.2f} dB-Hz'],
        ['C/N', f'{dl["downlink_cn_db"]:.2f} dB'],
        ['DL MARGIN', f'{dl["downlink_margin_db"]:+.2f} dB'],
    ]

    mod_data = [
        ['Modulation', params.get('modulation', 'QPSK')],
        ['Coding', params.get('coding', 'LDPC (R=3/4)')],
        ['Spec. Efficiency', f'{params.get("spectral_efficiency", 2.0):.1f} b/sym'],
        ['Code Rate', f'{params.get("coding_rate", 0.75):.3f}'],
        ['Code Gain', f'{params.get("coding_gain_db", 5.5):.1f} dB'],
        ['Symbol Rate', f'{params.get("symbol_rate_sps", 30e6)/1e6:.2f} Ms/s'],
        ['Data Rate', f'{params.get("data_rate_bps", 36e6)/1e6:.2f} Mbps'],
        ['Bandwidth', f'{params["bandwidth_hz"]/1e6:.2f} MHz'],
    ]

    if mode == 'Full Link':
        tp = mw.transponder
        tp_data = [
            ['LNA Gain', f'{tp.stages[0].gain_db:.1f} dB'],
            ['LNA NF', f'{tp.stages[0].noise_figure_db:.2f} dB'],
            ['Mixer Gain', f'{tp.stages[1].gain_db:.1f} dB'],
            ['LO Frequency', f'{tp.lo_freq_ghz:.2f} GHz'],
            ['IF Amp Gain', f'{tp.stages[2].gain_db:.1f} dB'],
            ['PA Gain', f'{tp.stages[3].gain_db:.1f} dB'],
            ['Total Gain', f'{tp.calculate_total_gain():.1f} dB'],
            ['Cascade NF', f'{tp.calculate_cascade_noise_figure():.2f} dB'],
            ['P_sat', f'{tp.saturated_power_dbw:.1f} dBW'],
            ['T_sys (Friis)', f'{tp.calculate_cascade_noise_temperature():.0f} K'],
            ['Sat G/T', f'{tp.calculate_satellite_gt():.1f} dB/K'],
            ['Sat EIRP', f'{tp.calculate_satellite_eirp():.1f} dBW'],
        ]
        status = 'LINK AVAILABLE' if tot_margin > 0 else 'LINK UNAVAILABLE'
        e2e_data = [
            ['UL C/N\u2080', f'{results["uplink_cn0_db"]:.2f} dB-Hz'],
            ['DL C/N\u2080', f'{results["downlink_cn0_db"]:.2f} dB-Hz'],
            ['Total C/N\u2080', f'{results["total_cn0_db"]:.2f} dB-Hz'],
            ['Total C/N', f'{results["total_cn_db"]:.2f} dB'],
            ['Total Eb/N\u2080', f'{results["total_ebn0_db"]:.2f} dB'],
            ['Req Eb/N\u2080', f'{params["ebn0_required_db"]:.2f} dB'],
            ['Max Doppler UL', f'\u00b1{max_dop_ul:.2f} kHz'],
            ['Max Doppler DL', f'\u00b1{max_dop_dl:.2f} kHz'],
            ['TOTAL MARGIN', f'{tot_margin:+.2f} dB'],
            ['STATUS', status],
        ]
        axes = fig.subplots(2, 3)
        _render_table(axes[0, 0], 'Geometry (ITU-R S.1257)', geo_data)
        _render_table(axes[0, 1], 'Uplink (GS \u2192 Satellite)', ul_data,
                      hl_last=True, margin=ul['uplink_margin_db'])
        _render_table(axes[0, 2], 'Downlink (Satellite \u2192 GS)', dl_data,
                      hl_last=True, margin=dl['downlink_margin_db'])
        _render_table(axes[1, 0], 'Modulation & Coding', mod_data)
        _render_table(axes[1, 1], 'Transponder', tp_data)
        _render_table(axes[1, 2], 'End-to-End Budget', e2e_data,
                      hl_last=True, margin=tot_margin)
    elif mode == 'Uplink Only':
        axes = fig.subplots(1, 3)
        _render_table(axes[0], 'Geometry (ITU-R S.1257)', geo_data)
        _render_table(axes[1], 'Uplink (GS \u2192 Satellite)', ul_data,
                      hl_last=True, margin=ul['uplink_margin_db'])
        _render_table(axes[2], 'Modulation & Coding', mod_data)
    else:
        axes = fig.subplots(1, 3)
        _render_table(axes[0], 'Geometry (ITU-R S.1257)', geo_data)
        _render_table(axes[1], 'Downlink (Satellite \u2192 GS)', dl_data,
                      hl_last=True, margin=dl['downlink_margin_db'])
        _render_table(axes[2], 'Modulation & Coding', mod_data)

    fig.suptitle(f'Complete Link Budget \u2014 {mode}',
                 fontsize=15, fontweight='700', color='#4338ca', y=0.98)
    fig.subplots_adjust(left=0.02, right=0.98, top=0.88, bottom=0.02,
                        wspace=0.15, hspace=0.25)
    mw.complete_results_canvas.draw()
