"""
Export module — report (PDF), CSV, and clipboard export functionality.
"""
import os
import csv
from datetime import datetime
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QApplication


def export_pdf(mw):
    """Export a styled PDF link-budget report using matplotlib."""
    if not hasattr(mw, 'last_results') or mw.last_results is None:
        QMessageBox.warning(mw, "No Data", "Please run a calculation first.")
        return

    filepath, _ = QFileDialog.getSaveFileName(
        mw, "Export PDF Report",
        f"link_budget_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        "PDF Files (*.pdf)")
    if not filepath:
        return

    try:
        import matplotlib
        matplotlib.use('Agg')
        from matplotlib.backends.backend_pdf import PdfPages
        import matplotlib.pyplot as plt
        import matplotlib.patches as mpatches
        import numpy as np

        results = mw.last_results
        params  = mw.last_params

        # Color palette
        INDIGO      = '#4f46e5'
        PURPLE      = '#7c3aed'
        GREEN       = '#059669'
        GREEN_BG    = '#ecfdf5'
        RED         = '#dc2626'
        RED_LIGHT   = '#fee2e2'
        GRAY_50     = '#f8fafc'
        GRAY_200    = '#e2e8f0'
        GRAY_500    = '#64748b'
        GRAY_700    = '#334155'
        WHITE       = '#ffffff'

        def _draw_section_title(fig, y, text):
            """Draw a section title at the given y position."""
            fig.text(0.07, y, text, fontsize=12, fontweight='bold',
                     color=INDIGO, fontfamily='sans-serif')

        def _draw_table(fig, top_y, headers, rows, height_per_row=0.022):
            """Draw a styled table starting at top_y. Returns the bottom y."""
            n_rows = len(rows) + 1  # +1 for header
            table_height = n_rows * height_per_row + 0.01
            bottom_y = top_y - table_height

            ax = fig.add_axes([0.06, bottom_y, 0.88, table_height])
            ax.axis('off')

            n_cols = len(headers)
            all_data = [headers] + rows
            col_widths = [0.40, 0.35, 0.25] if n_cols == 3 else [1.0 / n_cols] * n_cols

            tbl = ax.table(
                cellText=all_data,
                colWidths=col_widths,
                loc='upper center',
                cellLoc='left')

            tbl.auto_set_font_size(False)
            tbl.set_fontsize(8)
            tbl.scale(1, 1.4)

            for (row, col), cell in tbl.get_celld().items():
                cell.set_edgecolor(GRAY_200)
                cell.set_linewidth(0.5)
                if row == 0:
                    cell.set_facecolor(INDIGO)
                    cell.set_text_props(color='white', fontweight='bold',
                                        fontfamily='sans-serif', fontsize=8.5)
                else:
                    bg = GRAY_50 if row % 2 == 0 else WHITE
                    cell.set_facecolor(bg)
                    cell.set_text_props(color=GRAY_700, fontfamily='sans-serif',
                                        fontsize=8)

            return bottom_y

        with PdfPages(filepath) as pdf:
            # Page 1: header + configuration + status + totals
            fig = plt.figure(figsize=(8.27, 11.69))  # A4
            fig.patch.set_facecolor(WHITE)

            # Header banner (no overlap)
            hdr_ax = fig.add_axes([0.06, 0.91, 0.88, 0.065])
            hdr_ax.axis('off')
            gradient = np.linspace(0, 1, 256).reshape(1, -1)
            cmap = matplotlib.colors.LinearSegmentedColormap.from_list(
                'hdr', [INDIGO, PURPLE, '#6366f1', INDIGO])
            hdr_ax.imshow(gradient, aspect='auto', cmap=cmap,
                          extent=[0, 1, 0, 1])

            # Round corners via a clip path
            from matplotlib.patches import FancyBboxPatch
            clip_box = FancyBboxPatch((0, 0), 1, 1, boxstyle="round,pad=0",
                                      transform=hdr_ax.transAxes, linewidth=0)
            hdr_ax.add_patch(clip_box)

            # Title text (right of logo area)
            hdr_ax.text(0.04, 0.62, 'SATELLITE LINK BUDGET REPORT',
                        fontsize=15, fontweight='bold', color='white',
                        fontfamily='sans-serif', va='center')
            hdr_ax.text(0.04, 0.25,
                        f"Generated: {datetime.now().strftime('%Y-%m-%d  %H:%M:%S')}",
                        fontsize=8.5, color='#c7d2fe', fontfamily='sans-serif',
                        va='center')

            # Logo — placed on the right side to avoid overlap
            logo_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__)))), 'hmu.png')
            if os.path.isfile(logo_path):
                try:
                    from matplotlib.offsetbox import OffsetImage, AnnotationBbox
                    import matplotlib.image as mpimg
                    logo_img = mpimg.imread(logo_path)
                    imagebox = OffsetImage(logo_img, zoom=0.022)
                    ab = AnnotationBbox(imagebox, (0.95, 0.5), frameon=False,
                                        box_alignment=(1.0, 0.5),
                                        xycoords='axes fraction')
                    hdr_ax.add_artist(ab)
                except Exception:
                    pass

            # Configuration Section
            _draw_section_title(fig, 0.89, 'Configuration')

            link_mode = params.get('link_mode', 'Full Link')
            config_rows = [
                ['Link Mode',      link_mode, ''],
                ['Satellite Type', mw.sat_type_combo.currentText(), ''],
                ['Altitude',       f"{params['altitude_km']:.0f}", 'km'],
                ['Ground Station', f"({params['lat_gs']:.2f}, {params['lon_gs']:.2f})", 'deg'],
                ['Satellite Pos',  f"({params['lat_sat']:.2f}, {params['lon_sat']:.2f})", 'deg'],
                ['Elevation',      f"{params['elevation_deg']:.2f}", 'deg'],
                ['Slant Range',    f"{params['distance_km']:.0f}", 'km'],
                ['Uplink Freq',    f"{params['uplink_frequency_ghz']:.3f}", 'GHz'],
                ['Downlink Freq',  f"{params['downlink_frequency_ghz']:.3f}", 'GHz'],
                ['Bandwidth',      f"{params['bandwidth_hz']/1e6:.1f}", 'MHz'],
                ['Data Rate',      f"{params.get('data_rate_bps', 0)/1e6:.2f}", 'Mbps'],
                ['Modulation',     params.get('modulation', 'QPSK'), ''],
                ['Coding',         params.get('coding', ''), ''],
            ]
            bottom = _draw_table(fig, 0.88, ['Parameter', 'Value', 'Unit'], config_rows)

            # Total End-to-End
            margin_val = results['total_margin_db']
            link_ok = margin_val > 0

            y_total_title = bottom - 0.02
            _draw_section_title(fig, y_total_title, 'Total End-to-End Link')

            summary_rows = [
                ['Total C/N0',   f"{results['total_cn0_db']:.2f}",  'dB-Hz'],
                ['Total Eb/N0',  f"{results['total_ebn0_db']:.2f}", 'dB'],
                ['Total Margin', f"{margin_val:.2f}",               'dB'],
            ]
            bottom2 = _draw_table(fig, y_total_title - 0.01,
                                  ['Parameter', 'Value', 'Unit'], summary_rows)

            # Status badge
            badge_y = bottom2 - 0.02
            badge_ax = fig.add_axes([0.15, badge_y, 0.70, 0.035])
            badge_ax.axis('off')

            badge_color = GREEN_BG if link_ok else RED_LIGHT
            text_color  = GREEN if link_ok else RED
            status_text = 'LINK AVAILABLE' if link_ok else 'LINK UNAVAILABLE'

            badge = mpatches.FancyBboxPatch(
                (0.02, 0.05), 0.96, 0.90,
                boxstyle="round,pad=0.02", facecolor=badge_color,
                edgecolor=text_color, linewidth=1.5)
            badge_ax.add_patch(badge)
            badge_ax.text(0.50, 0.50, status_text,
                          fontsize=13, fontweight='bold', color=text_color,
                          ha='center', va='center', fontfamily='sans-serif')

            # Footer
            fig.text(0.50, 0.03,
                                          'Satellite Link Simulator  |  '
                     'ITU-R Compliant  |  Hellenic Mediterranean University',
                     ha='center', fontsize=7, color=GRAY_500,
                     fontfamily='sans-serif', style='italic')
            fig.text(0.50, 0.015, 'Page 1 of 2', ha='center', fontsize=7,
                     color=GRAY_500, fontfamily='sans-serif')

            pdf.savefig(fig, dpi=150)
            plt.close(fig)

            # Page 2: uplink + downlink detail tables
            fig2 = plt.figure(figsize=(8.27, 11.69))
            fig2.patch.set_facecolor(WHITE)

            # Mini header
            mhdr = fig2.add_axes([0.06, 0.94, 0.88, 0.035])
            mhdr.axis('off')
            grad2 = np.linspace(0, 1, 256).reshape(1, -1)
            mhdr.imshow(grad2, aspect='auto', cmap=cmap,
                        extent=[0, 1, 0, 1])
            mhdr.text(0.03, 0.50, 'DETAILED LINK ANALYSIS',
                      fontsize=11, fontweight='bold', color='white',
                      fontfamily='sans-serif', va='center')

            # Uplink table
            up = results['uplink']
            _up_nice = {
                'gs_eirp_dbw':          ('GS EIRP',              'dBW'),
                'fspl_db':              ('Free-Space Path Loss',  'dB'),
                'rain_atten_db':        ('Rain Attenuation',      'dB'),
                'atmospheric_atten_db': ('Atmospheric Atten.',    'dB'),
                'sat_gt_db':            ('Satellite G/T',         'dB/K'),
                'uplink_cn0_db':        ('Uplink C/N0',           'dB-Hz'),
                'uplink_ebn0_db':       ('Uplink Eb/N0',          'dB'),
                'uplink_margin_db':     ('Uplink Margin',         'dB'),
            }
            up_rows = [['Frequency', f"{params['uplink_frequency_ghz']:.3f}", 'GHz']]
            for key, val in up.items():
                nice, unit = _up_nice.get(key, (key, ''))
                up_rows.append([nice, f"{val:.2f}" if isinstance(val, float) else str(val), unit])

            _draw_section_title(fig2, 0.92, 'Uplink  (Ground \u2192 Satellite)')
            bottom_up = _draw_table(fig2, 0.91,
                                    ['Parameter', 'Value', 'Unit'], up_rows)

            # Downlink table
            dn = results['downlink']
            _dn_nice = {
                'sat_eirp_dbw':         ('Satellite EIRP',        'dBW'),
                'fspl_db':              ('Free-Space Path Loss',  'dB'),
                'rain_atten_db':        ('Rain Attenuation',      'dB'),
                'atmospheric_atten_db': ('Atmospheric Atten.',    'dB'),
                'gs_gt_db':             ('GS G/T',                'dB/K'),
                'downlink_cn0_db':      ('Downlink C/N0',         'dB-Hz'),
                'downlink_ebn0_db':     ('Downlink Eb/N0',        'dB'),
                'downlink_margin_db':   ('Downlink Margin',       'dB'),
            }
            dn_rows = [['Frequency', f"{params['downlink_frequency_ghz']:.3f}", 'GHz']]
            for key, val in dn.items():
                nice, unit = _dn_nice.get(key, (key, ''))
                dn_rows.append([nice, f"{val:.2f}" if isinstance(val, float) else str(val), unit])

            y_dn = bottom_up - 0.03
            _draw_section_title(fig2, y_dn, 'Downlink  (Satellite \u2192 Ground)')
            _draw_table(fig2, y_dn - 0.01,
                        ['Parameter', 'Value', 'Unit'], dn_rows)

            # Footer
            fig2.text(0.50, 0.03,
                                           'Satellite Link Simulator  |  '
                      'ITU-R Compliant  |  Hellenic Mediterranean University',
                      ha='center', fontsize=7, color=GRAY_500,
                      fontfamily='sans-serif', style='italic')
            fig2.text(0.50, 0.015, 'Page 2 of 2', ha='center', fontsize=7,
                      color=GRAY_500, fontfamily='sans-serif')

            pdf.savefig(fig2, dpi=150)
            plt.close(fig2)

        # Restore interactive backend
        matplotlib.use('Qt5Agg')

        mw.statusBar().showMessage(f" PDF report exported to: {filepath}")
        QMessageBox.information(mw, "Export Complete",
                                f"PDF report saved to:\n{filepath}")
    except Exception as e:
        import traceback
        traceback.print_exc()
        QMessageBox.warning(mw, "Export Error", f"Failed to export PDF:\n{str(e)}")


def export_csv(mw):
    """Export current results as CSV."""
    if not hasattr(mw, 'last_results') or mw.last_results is None:
        QMessageBox.warning(mw, "No Data", "Please run a calculation first.")
        return

    filepath, _ = QFileDialog.getSaveFileName(
        mw, "Export CSV",
        f"link_budget_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        "CSV Files (*.csv)")
    if not filepath:
        return

    try:
        results = mw.last_results
        params = mw.last_params
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Parameter', 'Value', 'Unit'])
            writer.writerow(['Link Mode', params.get('link_mode', 'Full Link'), ''])
            writer.writerow(['Satellite Type', mw.sat_type_combo.currentText(), ''])
            writer.writerow(['Altitude', params['altitude_km'], 'km'])
            writer.writerow(['Elevation', f"{params['elevation_deg']:.2f}", 'deg'])
            writer.writerow(['Slant Range', f"{params['distance_km']:.0f}", 'km'])
            writer.writerow(['Uplink Freq', params['uplink_frequency_ghz'], 'GHz'])
            writer.writerow(['Downlink Freq', params['downlink_frequency_ghz'], 'GHz'])
            writer.writerow(['Bandwidth', params['bandwidth_hz']/1e6, 'MHz'])
            writer.writerow(['Modulation', params.get('modulation', 'QPSK'), ''])
            writer.writerow(['', '', ''])
            writer.writerow(['--- UPLINK ---', '', ''])
            for k, v in results['uplink'].items():
                writer.writerow([k, f"{v:.4f}" if isinstance(v, float) else v, ''])
            writer.writerow(['', '', ''])
            writer.writerow(['--- DOWNLINK ---', '', ''])
            for k, v in results['downlink'].items():
                writer.writerow([k, f"{v:.4f}" if isinstance(v, float) else v, ''])
            writer.writerow(['', '', ''])
            writer.writerow(['--- TOTAL ---', '', ''])
            writer.writerow(['Total C/N0', f"{results['total_cn0_db']:.2f}", 'dB-Hz'])
            writer.writerow(['Total Eb/N0', f"{results['total_ebn0_db']:.2f}", 'dB'])
            writer.writerow(['Total Margin', f"{results['total_margin_db']:.2f}", 'dB'])

        mw.statusBar().showMessage(f" CSV exported to: {filepath}")
    except Exception as e:
        QMessageBox.warning(mw, "Export Error", str(e))


def copy_results_to_clipboard(mw):
    """Copy results summary to clipboard."""
    if not hasattr(mw, 'last_results') or mw.last_results is None:
        mw.statusBar().showMessage(" No results to copy")
        return

    r = mw.last_results
    p = mw.last_params
    ul = r['uplink']
    dl = r['downlink']
    lines = [
        f"=== COMPLETE LINK BUDGET ===",
        f"Mode: {p.get('link_mode', 'Full Link')}",
        f"Elevation: {p.get('elevation_deg', 45.0):.2f} deg",
        f"Distance: {p.get('distance_km', 38000):.1f} km",
        f"--- UPLINK ---",
        f"EIRP: {ul['gs_eirp_dbw']:.2f} dBW   FSPL: {ul['fspl_db']:.2f} dB",
        f"C/N0: {ul['uplink_cn0_db']:.2f} dB-Hz   Margin: {ul['uplink_margin_db']:.2f} dB",
        f"--- DOWNLINK ---",
        f"EIRP: {dl['sat_eirp_dbw']:.2f} dBW   FSPL: {dl['fspl_db']:.2f} dB",
        f"C/N0: {dl['downlink_cn0_db']:.2f} dB-Hz   Margin: {dl['downlink_margin_db']:.2f} dB",
        f"--- TOTAL ---",
        f"Total C/N0: {r['total_cn0_db']:.2f} dB-Hz",
        f"Total Eb/N0: {r['total_ebn0_db']:.2f} dB",
        f"Total Margin: {r['total_margin_db']:.2f} dB",
    ]
    text = '\n'.join(lines)
    QApplication.clipboard().setText(text)
    mw.statusBar().showMessage(" Results copied to clipboard!")
