"""Link diagram and waterfall visualization helpers.

Standalone drawing functions — accepts matplotlib axes/figures and data dicts.
"""

import numpy as np
from matplotlib.patches import Rectangle, FancyBboxPatch, Circle


def draw_waterfall_detailed(ax, title, eirp, fspl, gaseous_loss, rain_loss,
                            cloud_loss, scint_loss, pointing_loss, pol_loss,
                            backoff, rx_gain, gt, cn0, is_uplink, color_theme):
    """Waterfall bar chart of all individual gains and losses."""
    ax.set_facecolor('#fafafa')

    bo_label = 'IBO' if is_uplink else 'OBO'

    labels = ['EIRP', f'-{bo_label}', 'FSPL', 'Gas', 'Rain', 'Cloud',
              'Scint', 'Point', 'Pol', 'G/T', '+k', 'C/N\u2080']
    values = [
        eirp + backoff, -backoff, -fspl, -gaseous_loss, -rain_loss,
        -cloud_loss, -scint_loss, -pointing_loss, -pol_loss, gt, 228.6, 0,
    ]

    cumulative = [0]
    for v in values[:-1]:
        cumulative.append(cumulative[-1] + v)

    colors = []
    for i, v in enumerate(values[:-1]):
        if v > 0:
            colors.append('#4CAF50')
        elif v < -0.1:
            if labels[i] == 'FSPL':
                colors.append('#E53935')
            elif labels[i] in ('Gas', 'Rain', 'Cloud', 'Scint'):
                colors.append('#FF7043')
            else:
                colors.append('#f44336')
        else:
            colors.append('#9E9E9E')
    colors.append(color_theme)

    bw = 0.6
    n = len(labels)
    x_pos = np.arange(n)

    for i, (lbl, val, cum) in enumerate(zip(labels[:-1], values[:-1], cumulative[:-1])):
        if abs(val) < 0.001:
            ax.plot([i - bw/2, i + bw/2], [cum, cum],
                    color='#BDBDBD', linewidth=1, alpha=0.5)
            continue
        bottom = cum if val >= 0 else cum + val
        ax.bar(i, abs(val), bw, bottom=bottom, color=colors[i],
               edgecolor='white', linewidth=1, alpha=0.85, zorder=3)

    ax.bar(n - 1, cn0, bw, bottom=0,
           color=color_theme, edgecolor='white', linewidth=2, alpha=0.9, zorder=3)

    # connector lines
    for i in range(len(values) - 2):
        y1 = cumulative[i] + values[i]
        ax.plot([i + bw/2, i + 1 - bw/2], [y1, y1],
                color='gray', linestyle='--', linewidth=0.8, alpha=0.4)

    # value table on right side
    display_vals = values[:-1] + [cn0]
    table_x = 1.02
    row_h = 1.0 / (n + 1)
    ax.text(table_x, 1.0 - 0.5 * row_h, 'Value', fontsize=7,
            fontweight='bold', color='#555', transform=ax.transAxes,
            ha='left', va='center', family='monospace')
    for idx in range(n):
        y_frac = 1.0 - (idx + 1.5) * row_h
        val = display_vals[idx]
        if idx == n - 1:
            txt = f'{val:.1f} dB-Hz'
        elif abs(val) < 0.01:
            txt = '  0.0 dB'
        else:
            txt = f'{val:+.1f} dB'
        ax.text(table_x, y_frac, f'{labels[idx]:>5s}  {txt}',
                fontsize=6.5, fontweight='bold', color=colors[idx],
                transform=ax.transAxes, ha='left', va='center',
                family='monospace')

    ax.set_xticks(x_pos)
    ax.set_xticklabels(labels, fontsize=7, rotation=35, ha='right')
    ax.set_ylabel('Power Level (dB)')
    ax.set_title(title, fontweight='bold', color=color_theme)
    ax.axhline(y=0, color='gray', linewidth=0.5, alpha=0.5)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.set_xlim(-0.6, n - 0.4)


def draw_combined_summary(ax, results, params):
    """C/N\u2080 comparison bar chart with margin indicator."""
    ax.set_facecolor('#fafafa')

    categories = ['Uplink C/N\u2080', 'Downlink C/N\u2080', 'Total C/N\u2080']
    cn0_vals = [results['uplink_cn0_db'],
                results['downlink_cn0_db'],
                results['total_cn0_db']]
    bar_colors = ['#2196F3', '#FF9800', '#4CAF50']

    margin = results['total_margin_db']
    mc = '#4CAF50' if margin > 0 else '#f44336'
    status = '\u2714 LINK OK' if margin > 0 else '\u2718 LINK FAIL'

    categories.append('Link\nMargin')
    cn0_vals.append(margin)
    bar_colors.append(mc)

    x = np.arange(len(categories))
    bars = ax.bar(x, cn0_vals, width=0.55, color=bar_colors, alpha=0.88,
                  edgecolor='white', linewidth=2)

    for bar, val in zip(bars, cn0_vals):
        yoff = 0.6 if val >= 0 else -0.6
        unit = 'dB-Hz' if abs(val) > 30 else 'dB'
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + yoff,
                f'{val:.1f} {unit}', ha='center',
                va='bottom' if val >= 0 else 'top',
                fontsize=11, fontweight='bold', color='#333')

    ax.set_xticks(x)
    ax.set_xticklabels(categories, fontweight='bold')
    ax.set_ylabel('dB / dB-Hz')
    ax.set_title(f'COMBINED LINK SUMMARY \u2014 {status}', fontweight='bold', color=mc)
    ax.axhline(y=0, color='gray', linewidth=0.6, alpha=0.5)
    ax.grid(axis='y', alpha=0.3, linestyle='--')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)


# waterfall figure (full figure with up to 3 subplots)

def _uplink_waterfall_kwargs(uplink, params):
    return dict(
        title=' UPLINK Waterfall (Ground \u2192 Satellite)',
        eirp=uplink['gs_eirp_dbw'],
        fspl=uplink['fspl_db'],
        gaseous_loss=uplink.get('atmospheric_atten_db', 0),
        rain_loss=uplink.get('rain_atten_db', 0),
        cloud_loss=uplink.get('cloud_atten_db', 0),
        scint_loss=uplink.get('scintillation_db', 0),
        pointing_loss=params.get('gs_pointing_loss_tx_db', params.get('gs_pointing_loss_db', 0.3)),
        pol_loss=params['polarization_loss_db'],
        backoff=params['input_backoff_db'],
        rx_gain=params['sat_rx_gain_dbi'],
        gt=uplink['sat_gt_db'],
        cn0=uplink['uplink_cn0_db'],
        is_uplink=True,
        color_theme='#2196F3',
    )


def _downlink_waterfall_kwargs(downlink, params):
    return dict(
        title=' DOWNLINK Waterfall (Satellite \u2192 Ground)',
        eirp=downlink['sat_eirp_dbw'],
        fspl=downlink['fspl_db'],
        gaseous_loss=downlink.get('atmospheric_atten_db', 0),
        rain_loss=downlink.get('rain_atten_db', 0),
        cloud_loss=downlink.get('cloud_atten_db', 0),
        scint_loss=downlink.get('scintillation_db', 0),
        pointing_loss=params.get('gs_pointing_loss_rx_db', params.get('gs_pointing_loss_db', 0.2)),
        pol_loss=params['polarization_loss_db'],
        backoff=params['output_backoff_db'],
        rx_gain=downlink['gs_antenna_gain_dbi'],
        gt=downlink['gs_gt_db'],
        cn0=downlink['downlink_cn0_db'],
        is_uplink=False,
        color_theme='#FF9800',
    )


def draw_waterfall_figure(fig, results, params):
    """Populate fig with waterfall sub-plots based on link mode."""
    fig.clf()
    mode = params.get('link_mode', 'Full Link')
    ul, dl = results['uplink'], results['downlink']

    if mode == 'Uplink Only':
        ax = fig.add_subplot(1, 1, 1)
        draw_waterfall_detailed(ax, **_uplink_waterfall_kwargs(ul, params))
        fig.suptitle('Uplink Only \u2014 Waterfall Analysis',
                     fontweight='bold', color='#1565C0')
    elif mode == 'Downlink Only':
        ax = fig.add_subplot(1, 1, 1)
        draw_waterfall_detailed(ax, **_downlink_waterfall_kwargs(dl, params))
        fig.suptitle('Downlink Only \u2014 Waterfall Analysis',
                     fontweight='bold', color='#E65100')
    else:
        gs = fig.add_gridspec(2, 2, height_ratios=[1.3, 1],
                              hspace=0.38, wspace=0.35)
        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])
        ax3 = fig.add_subplot(gs[1, :])

        kw_up = _uplink_waterfall_kwargs(ul, params)
        kw_up['title'] = 'UPLINK Waterfall'
        draw_waterfall_detailed(ax1, **kw_up)

        kw_dn = _downlink_waterfall_kwargs(dl, params)
        kw_dn['title'] = 'DOWNLINK Waterfall'
        draw_waterfall_detailed(ax2, **kw_dn)

        draw_combined_summary(ax3, results, params)
        fig.suptitle('Complete Link Budget \u2014 Waterfall Analysis',
                     fontweight='bold', color='#1565C0', y=0.99)

    try:
        fig.tight_layout(rect=[0.01, 0.02, 0.88, 0.94])
    except Exception:
        pass


# SVG-inspired link diagram ────────────────────────────────────────────────
#
# Coordinate system: data coords matching SVG proportions, Y inverted.
#   plot_x \u2248 svg_x  (0\u2013500),  plot_y \u2248 377 \u2212 svg_y  (0 at ground, ~254 at top)
#   Canvas: [-15, 515] \u00d7 [-65, 275]

# antenna shape data (sampled from exported SVG)
_LGS_DISH_OUTER_X = np.array([55.1, 52.8, 50.1, 47.5, 45.0, 42.5, 40.1, 37.8, 35.9, 33.7,
                               31.7, 29.7, 27.9, 26.1, 24.5, 23.2, 21.8, 20.6, 19.5, 18.5,
                               17.7, 17.0, 16.6, 16.2, 16.0, 16.0, 16.1, 16.5, 17.0, 17.7])
_LGS_DISH_OUTER_Y = np.array([38.0, 36.9, 35.8, 35.1, 34.5, 34.3, 34.2, 34.4, 34.7, 35.3,
                               36.0, 37.0, 38.1, 39.3, 40.7, 42.0, 43.6, 45.4, 47.2, 49.1,
                               51.1, 53.1, 55.0, 57.1, 59.3, 61.4, 63.6, 65.8, 68.0, 70.1])
_LGS_DISH_CLOSE_X = np.array([17.9, 21.9, 26.0, 30.1, 34.2, 38.3, 42.4, 46.5, 50.6, 54.9])
_LGS_DISH_CLOSE_Y = np.array([70.4, 66.9, 63.3, 59.7, 56.2, 52.6, 49.0, 45.5, 41.9, 38.2])
_LGS_INN0_X = np.array([27.2, 28.5, 29.9, 31.2, 32.5, 34.0, 35.3, 36.6, 38.0, 39.3,
                          40.7, 42.1, 43.4, 44.7, 46.2])
_LGS_INN0_Y = np.array([62.6, 62.9, 63.3, 63.6, 63.9, 64.3, 64.6, 64.9, 65.2, 65.5,
                          65.9, 66.2, 66.5, 66.8, 67.2])
_LGS_INN1_X = np.array([46.3, 46.3, 46.3, 46.4, 46.4, 46.4, 46.5, 46.5, 46.6, 46.6])
_LGS_INN1_Y = np.array([67.2, 64.8, 62.4, 59.9, 57.5, 55.1, 52.7, 50.2, 47.8, 45.3])

_SAL_OUT0_X = np.array([114.2, 116.9, 119.5, 122.2, 124.6, 127.2, 129.3, 131.5, 133.4,
                         135.2, 136.7, 138.1, 139.3, 140.2, 140.9, 141.3, 141.5, 141.4,
                         141.0, 140.3])
_SAL_OUT0_Y = np.array([166.0, 167.2, 168.0, 168.5, 168.6, 168.3, 167.8, 166.9, 165.8,
                         164.4, 162.8, 161.0, 159.2, 157.0, 155.0, 152.6, 150.5, 148.0,
                         145.9, 143.5])
_SAL_OUT1_X = np.array([140.2, 138.3, 136.5, 134.7, 132.9, 130.9, 129.1, 127.3, 125.5,
                         123.7, 121.7, 119.9, 118.1, 116.3, 114.3])
_SAL_OUT1_Y = np.array([143.3, 144.9, 146.5, 148.1, 149.6, 151.3, 152.9, 154.5, 156.1,
                         157.7, 159.4, 161.0, 162.6, 164.1, 165.8])
_SAL_INN0_X = np.array([133.6, 132.2, 130.7, 129.3, 127.8, 126.3, 124.9, 123.4, 121.9, 120.4])
_SAL_INN0_Y = np.array([148.8, 148.4, 148.1, 147.7, 147.3, 147.0, 146.6, 146.3, 145.9, 145.6])
_SAL_INN1_X = np.array([120.3, 120.3, 120.3, 120.3, 120.2, 120.2, 120.2, 120.1, 120.1, 120.1])
_SAL_INN1_Y = np.array([145.6, 147.2, 148.9, 150.6, 152.3, 154.0, 155.7, 157.4, 159.1, 160.9])

_MIRROR = 500.0


def _draw_gs_antenna(ax, mirror=False):
    """Ground-station dish (left TX or mirrored right RX)."""
    mx = (lambda x: _MIRROR - x) if mirror else (lambda x: x)

    ax.plot([mx(1.9), mx(55.1)], [0.4, 0.4], 'k-', lw=1.5, solid_capstyle='round')
    ax.plot([mx(21.7), mx(18.5)], [30.5, 0.7], 'k-', lw=1)
    ax.plot([mx(29.0), mx(37.0)], [31.3, 0.4], 'k-', lw=1)
    ax.plot(mx(_LGS_DISH_OUTER_X), _LGS_DISH_OUTER_Y, 'k-', lw=1.5)
    ax.plot(mx(_LGS_DISH_CLOSE_X), _LGS_DISH_CLOSE_Y, 'k-', lw=1.5)
    ax.plot(mx(_LGS_INN0_X), _LGS_INN0_Y, 'k-', lw=0.8, alpha=0.6)
    ax.plot(mx(_LGS_INN1_X), _LGS_INN1_Y, 'k-', lw=0.8, alpha=0.6)
    ax.add_patch(Circle((mx(25.0), 34.0), 4.6, fc='white', ec='black', lw=1, zorder=5))
    ax.add_patch(Circle((mx(47.6), 69.1), 2.9, fc='white', ec='black', lw=1, zorder=5))


def _draw_sat_antenna(ax, side='left'):
    """Small satellite dish (left=uplink RX, right=downlink TX)."""
    mx = (lambda x: x) if side == 'left' else (lambda x: _MIRROR - x)

    ax.plot(mx(_SAL_OUT0_X), _SAL_OUT0_Y, 'k-', lw=1.2)
    ax.plot(mx(_SAL_OUT1_X), _SAL_OUT1_Y, 'k-', lw=1.2)
    ax.plot(mx(_SAL_INN0_X), _SAL_INN0_Y, 'k-', lw=0.6, alpha=0.5)
    ax.plot(mx(_SAL_INN1_X), _SAL_INN1_Y, 'k-', lw=0.6, alpha=0.5)
    ax.add_patch(Circle((mx(119.4), 145.6), 2.0, fc='white', ec='black', lw=0.8, zorder=5))


def draw_link_diagram(fig, results, params, *,
                      clear_sky=True, sat_type_name='GEO',
                      gs_rx_diameter_m=1.2, transponder=None):
    """SVG-inspired satellite link schematic with transponder chain."""
    fig.clf()
    ax = fig.add_subplot(111)
    ax.set_facecolor('#f8f9fa')
    ax.set_xlim(-15, 515)
    ax.set_ylim(-65, 275)
    ax.axis('off')

    ul, dl = results['uplink'], results['downlink']
    mode = params.get('link_mode', 'Full Link')

    gs_tx_bw = (21.0 / (params['uplink_frequency_ghz'] * params['gs_antenna_diameter_m'])
                if params['gs_antenna_diameter_m'] > 0 else 0)
    gs_rx_bw = (21.0 / (params['downlink_frequency_ghz'] * gs_rx_diameter_m)
                if gs_rx_diameter_m > 0 else 0)

    # title
    sky = ("Clear Sky" if clear_sky
           else f"Rain (UL {params['uplink_rain_rate']:.0f}, "
                f"DL {params['downlink_rain_rate']:.0f} mm/h)")
    _titles = {
        'Uplink Only':   (f'Uplink: Ground Station \u2192 Satellite ({sat_type_name})  \u2022  {sky}', '#1565C0'),
        'Downlink Only': (f'Downlink: Satellite \u2192 Ground Station ({sat_type_name})  \u2022  {sky}', '#E65100'),
    }
    ttl, tc = _titles.get(mode, (f'Complete Satellite Link ({sat_type_name})  \u2022  {sky}', '#1565C0'))
    ax.text(250, 270, ttl, ha='center', va='top', fontsize=11, fontweight='bold', color=tc)

    # ground stations
    GL, GR = 28, 472
    _draw_gs_antenna(ax, mirror=False)
    ax.text(GL, -6, 'TX Earth Station', ha='center', va='top',
            fontsize=7, fontweight='bold', color='#2E7D32')
    _draw_gs_antenna(ax, mirror=True)
    ax.text(GR, -6, 'RX Earth Station', ha='center', va='top',
            fontsize=7, fontweight='bold', color='#E65100')

    # satellite transponder body
    SX, SY, SW, SH = 136, 176, 229, 78
    ax.add_patch(FancyBboxPatch(
        (SX, SY), SW, SH, boxstyle='round,pad=3',
        fc='white', ec='black', lw=2, zorder=3))
    ax.text(SX + SW/2, SY - 6, 'SATELLITE TRANSPONDER',
            ha='center', va='top', fontsize=8, fontweight='bold', color='#555')

    # stage blocks
    for name, sx, sy, sw, sh, fc, tc, fs in [
        ('LNA',    152, 195, 35, 34, '#96CBD6', 'black',  8),
        ('IF AMP', 253, 195, 34, 34, '#A8E442', 'black',  7),
        ('PA',     306, 191, 44, 43, '#EC5B5B', 'white', 11),
    ]:
        ax.add_patch(FancyBboxPatch(
            (sx, sy), sw, sh, boxstyle='round,pad=2',
            fc=fc, ec='black', lw=1, zorder=4))
        ax.text(sx + sw/2, sy + sh/2, name,
                ha='center', va='center', fontsize=fs,
                fontweight='bold', color=tc, zorder=5)

    # mixer
    MX, MY = 222, 212
    ax.add_patch(Circle((MX, MY), 13, fc='#DAC656', ec='black', lw=1, zorder=4))
    ax.text(MX, MY, '\u00d7', ha='center', va='center',
            fontsize=14, fontweight='bold', zorder=5)

    # inter-stage arrows
    _arr = dict(arrowstyle='->', lw=1.5, color='#333')
    ax.annotate('', xy=(209, 212), xytext=(187, 212), arrowprops=_arr)
    ax.annotate('', xy=(253, 212), xytext=(235, 212), arrowprops=_arr)
    ax.annotate('', xy=(306, 212), xytext=(287, 212), arrowprops=_arr)

    # per-stage gain/NF labels
    if transponder is not None and hasattr(transponder, 'stages'):
        _sx = {'LNA': 169, 'Mixer': 222, 'IF_Amp': 270, 'PA': 328}
        for stg in transponder.stages:
            px = _sx.get(stg.name)
            if px is not None:
                ax.text(px, 238,
                        f'G={stg.gain_db:+.0f} NF={stg.noise_figure_db:.1f}',
                        ha='center', va='bottom', fontsize=5.0,
                        color='#333', zorder=6)
        try:
            tg = transponder.calculate_total_gain()
            cn = transponder.calculate_cascade_noise_figure()
            ct = transponder.calculate_cascade_noise_temperature()
            ax.text(SX + SW/2, SY + 4,
                    f'Total Gain {tg:.1f} dB  \u2022  '
                    f'Cascade NF {cn:.1f} dB  \u2022  '
                    f'T_sys {ct:.0f} K',
                    ha='center', va='bottom', fontsize=6, color='#1565C0',
                    bbox=dict(boxstyle='round,pad=0.2', fc='#E3F2FD',
                              ec='#90CAF9', lw=0.5, alpha=0.85),
                    zorder=6)
        except Exception:
            pass

    # satellite antennas + feed lines
    _draw_sat_antenna(ax, side='left')
    ax.plot([136.1, 156], [163, 196], 'k-', lw=1.2)
    _draw_sat_antenna(ax, side='right')
    ax.plot([_MIRROR - 136.1, _MIRROR - 156], [163, 196], 'k-', lw=1.2)

    # signal-path arrows
    _uarr = dict(arrowstyle='->', lw=3, color='#2196F3', connectionstyle='arc3,rad=0.12')
    _darr = dict(arrowstyle='->', lw=3, color='#FF9800', connectionstyle='arc3,rad=0.12')

    # uplink annotations
    if mode in ('Uplink Only', 'Full Link'):
        ax.annotate('', xy=(119.4, 145.6), xytext=(47.6, 69.1), arrowprops=_uarr)

        ul_tot = ul['fspl_db'] + ul['atmospheric_atten_db'] + ul['rain_atten_db']
        ax.text(58, 118,
                f'UPLINK  {params["uplink_frequency_ghz"]:.2f} GHz\n'
                f'FSPL   {ul["fspl_db"]:.1f} dB\n'
                f'Atm     {ul["atmospheric_atten_db"]:.2f} dB\n'
                f'Rain    {ul["rain_atten_db"]:.2f} dB\n'
                f'Total  {ul_tot:.1f} dB',
                ha='right', va='center', fontsize=6, fontweight='bold', color='#1565C0',
                bbox=dict(boxstyle='round,pad=0.3', fc='#E3F2FD', ec='#2196F3', lw=1.5))

        ax.text(GL + 6, -18,
                f'P_TX = {params["gs_tx_power_dbw"]:.1f} dBW\n'
                f'G_TX = {ul["gs_antenna_gain_dbi"]:.1f} dBi\n'
                f'\u03b8\u2083dB = {gs_tx_bw:.2f}\u00b0\n'
                f'EIRP = {ul["gs_eirp_dbw"]:.1f} dBW',
                ha='center', va='top', fontsize=6, fontweight='bold', color='#1B5E20',
                bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='#4CAF50', lw=1))

        ax.text(100, 138,
                f'G_RX = {params["sat_rx_gain_dbi"]:.1f} dBi\n'
                f'(G/T)_SL = {ul["sat_gt_db"]:.1f} dB/K\n'
                f'T_sys = {ul["sat_noise_temp_k"]:.0f} K\n'
                f'IBO = {params["input_backoff_db"]:.1f} dB',
                ha='right', va='top', fontsize=5.5, color='#0D47A1',
                bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='#1976D2', lw=0.8))

    # downlink annotations
    if mode in ('Downlink Only', 'Full Link'):
        ax.annotate('', xy=(452.4, 69.1), xytext=(380.6, 145.6), arrowprops=_darr)

        dl_tot = dl['fspl_db'] + dl['atmospheric_atten_db'] + dl['rain_atten_db']
        ax.text(442, 118,
                f'DOWNLINK  {params["downlink_frequency_ghz"]:.2f} GHz\n'
                f'FSPL   {dl["fspl_db"]:.1f} dB\n'
                f'Atm     {dl["atmospheric_atten_db"]:.2f} dB\n'
                f'Rain    {dl["rain_atten_db"]:.2f} dB\n'
                f'Total  {dl_tot:.1f} dB',
                ha='left', va='center', fontsize=6, fontweight='bold', color='#E65100',
                bbox=dict(boxstyle='round,pad=0.3', fc='#FFF3E0', ec='#FF9800', lw=1.5))

        ax.text(400, 138,
                f'P_TX = {params["sat_power_dbw"]:.1f} dBW\n'
                f'G_TX = {params["sat_antenna_gain_dbi"]:.1f} dBi\n'
                f'EIRP = {dl["sat_eirp_dbw"]:.1f} dBW\n'
                f'OBO = {params["output_backoff_db"]:.1f} dB',
                ha='left', va='top', fontsize=5.5, color='#E65100',
                bbox=dict(boxstyle='round,pad=0.2', fc='#FFF3E0', ec='#FF9800', lw=0.8))

        ax.text(GR - 6, -18,
                f'G_RX = {dl["gs_antenna_gain_dbi"]:.1f} dBi\n'
                f'\u03b8\u2083dB = {gs_rx_bw:.2f}\u00b0\n'
                f'(G/T)_ES = {dl["gs_gt_db"]:.1f} dB/K\n'
                f'T_sys = {dl["system_temp_k"]:.0f} K',
                ha='center', va='top', fontsize=6, fontweight='bold', color='#BF360C',
                bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='#FF9800', lw=1))

    # distance/elevation label
    ax.text(250, 72,
            f'Distance: {params["distance_km"]:.0f} km  \u2022  '
            f'Elevation: {params["elevation_deg"]:.1f}\u00b0',
            ha='center', va='center', fontsize=8,
            bbox=dict(boxstyle='round,pad=0.4', fc='#FFEB3B', ec='black', lw=1.5))

    # result box
    if mode == 'Uplink Only':
        mg = ul['uplink_margin_db']
        mc = '#4CAF50' if mg > 0 else '#f44336'
        st = 'UPLINK OK' if mg > 0 else 'UPLINK FAIL'
        ax.text(250, -20,
                f'UPLINK RESULT\n'
                f'C/(N\u2080+I) = {ul["uplink_cn0_db"]:.2f} dB-Hz    '
                f'Eb/N\u2080 = {ul["uplink_ebn0_db"]:.2f} dB    '
                f'Margin = {mg:.2f} dB    {st}',
                ha='center', va='center', fontsize=8, fontweight='bold', color='white',
                bbox=dict(boxstyle='round,pad=0.5', fc=mc, ec='black', lw=2))
        formula = '(C/(N\u2080+I))\u1d64\u207b\u00b9 = (C/N\u2080)\u1d64\u207b\u00b9 + (C/I)\u1d64\u207b\u00b9'

    elif mode == 'Downlink Only':
        mg = dl['downlink_margin_db']
        mc = '#4CAF50' if mg > 0 else '#f44336'
        st = 'DOWNLINK OK' if mg > 0 else 'DOWNLINK FAIL'
        ax.text(250, -20,
                f'DOWNLINK RESULT\n'
                f'C/(N\u2080+I) = {dl["downlink_cn0_db"]:.2f} dB-Hz    '
                f'Eb/N\u2080 = {dl["downlink_ebn0_db"]:.2f} dB    '
                f'Margin = {mg:.2f} dB    {st}',
                ha='center', va='center', fontsize=8, fontweight='bold', color='white',
                bbox=dict(boxstyle='round,pad=0.5', fc=mc, ec='black', lw=2))
        formula = '(C/(N\u2080+I))_D\u207b\u00b9 = (C/N\u2080)_D\u207b\u00b9 + (C/I)_D\u207b\u00b9'

    else:
        mg = results['total_margin_db']
        mc = '#4CAF50' if mg > 0 else '#f44336'
        st = 'LINK AVAILABLE' if mg > 0 else 'LINK UNAVAILABLE'
        ax.text(250, -20,
                f'TOTAL LINK\n'
                f'C/(N\u2080+I)_total = {results["total_cn0_db"]:.2f} dB-Hz    '
                f'Eb/N\u2080 = {results["total_ebn0_db"]:.2f} dB    '
                f'Margin = {mg:.2f} dB    {st}',
                ha='center', va='center', fontsize=8, fontweight='bold', color='white',
                bbox=dict(boxstyle='round,pad=0.5', fc=mc, ec='black', lw=2))
        formula = '(C/(N\u2080+I))\u207b\u00b9_T = (C/(N\u2080+I))\u207b\u00b9_U + (C/(N\u2080+I))\u207b\u00b9_D'

    ax.text(250, -42, formula, ha='center', va='top', fontsize=7,
            family='monospace', color='#424242',
            bbox=dict(boxstyle='round,pad=0.3', fc='white', ec='#1976D2', lw=1))

    fig.tight_layout()
