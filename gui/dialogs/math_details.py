"""
Math details dialog module — shows detailed mathematical calculations for the link budget.
Visuals updated to include rendered LaTeX equations via matplotlib.
"""
import io
import base64
import numpy as np
import matplotlib
# Use Agg backend for headless rendering
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QPushButton, QTextBrowser, QMessageBox, QApplication, QProgressDialog
from PyQt5.QtCore import Qt
from models.constants import MODULATION_SCHEMES


def render_equation(tex, dpi=120):
    """
    Render a LaTeX equation to a base64 encoded PNG image using matplotlib.
    """
    try:
        # Create a figure with transparent background
        fig = plt.figure(figsize=(0.1, 0.1), dpi=dpi)  # minimal size, bbox_inches='tight' will expand
        
        # Add text - usetex=False uses mathtext which is faster and doesn't require ext latex
        text = fig.text(0.5, 0.5, f"${tex}$", fontsize=14, ha='center', va='center', color='#333333')
        
        # Save to buffer
        buf = io.BytesIO()
        plt.axis('off')
        
        # rendering
        plt.savefig(buf, format='png', bbox_inches='tight', pad_inches=0.1, transparent=True)
        plt.close(fig)
        
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        print(f"Error rendering equation: {e}")
        return ""


def show_math_details_dialog(mw):
    """Display detailed mathematical calculations for current link budget"""
    if not hasattr(mw, 'last_results') or mw.last_results is None:
        QMessageBox.warning(mw, "No Data", "Please run a calculation first.")
        return

    # Show progress dialog because rendering images takes a few seconds
    progress = QProgressDialog("Generating detailed report...", "Cancel", 0, 100, mw)
    progress.setWindowModality(Qt.WindowModality.WindowModal)
    progress.setMinimumDuration(0)
    progress.setValue(10)
    QApplication.processEvents()

    results = mw.last_results
    params = mw.last_params
    uplink = results.get('uplink', {})
    downlink = results.get('downlink', {})
    link_mode = params.get('link_mode', 'Full Link')

    slant_range = results.get('distance_km', params.get('distance_km', 42000))

    if link_mode == 'Uplink Only':
        title = "UPLINK Mathematical Details"
    elif link_mode == 'Downlink Only':
        title = "DOWNLINK Mathematical Details"
    else:
        title = "Detailed Link Budget Calculations"

    # Calculate beamwidths
    gs_tx_beamwidth = (21.0 / (params.get('uplink_frequency_ghz', 14.0) * params.get('gs_antenna_diameter_m', 2.4))
                       if params.get('gs_antenna_diameter_m', 2.4) > 0 else 0)
    gs_rx_beamwidth = (21.0 / (params.get('downlink_frequency_ghz', 12.0) * params.get('gs_antenna_diameter_m_rx', 1.2))
                       if params.get('gs_antenna_diameter_m_rx', 1.2) > 0 else 0)

    # C/IM0 calculation
    bandwidth_hz = params.get('bandwidth_hz', 36e6)
    c_im_db = params.get('c_im_db', 30)
    c_im0_db = c_im_db + 10 * np.log10(bandwidth_hz)

    progress.setValue(30)
    
    math_text = _build_html(
        title, link_mode, params, results, uplink, downlink,
        slant_range, gs_tx_beamwidth, gs_rx_beamwidth,
        bandwidth_hz, c_im_db, c_im0_db
    )
    
    progress.setValue(100)
    progress.close()

    # Create dialog with scroll area
    dialog = QDialog(mw)
    dialog.setWindowTitle("Mathematical Details - High Precision Report")
    dialog.setMinimumSize(900, 800)
    dialog.setStyleSheet("background-color: #f8f9fa;")

    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(0, 0, 0, 0)

    text_browser = QTextBrowser()
    text_browser.setHtml(math_text)
    text_browser.setOpenExternalLinks(True)
    text_browser.setStyleSheet("border: none;")
    layout.addWidget(text_browser)

    close_btn = QPushButton("Close Report")
    close_btn.setStyleSheet("""
        QPushButton {
            background-color: #3b82f6;
            color: white;
            padding: 10px 20px;
            font-size: 14px;
            font-weight: bold;
            border-radius: 6px;
            margin: 10px;
        }
        QPushButton:hover {
            background-color: #2563eb;
        }
    """)
    close_btn.clicked.connect(dialog.close)
    layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    dialog.exec()


def _build_html(title, link_mode, params, results, uplink, downlink,
                slant_range, gs_tx_beamwidth, gs_rx_beamwidth,
                bandwidth_hz, c_im_db, c_im0_db):
    """Build the full HTML content for the math details dialog with rendered equations."""

    # Updated CSS styles
    css = """
    <style>
        body { font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8f9fa; color: #1f2937; margin: 0; padding: 20px; }
        .container { max_width: 850px; margin: 0 auto; background: white; padding: 40px; border-radius: 12px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06); }
        h1 { color: #111827; font-size: 24px; text-align: center; margin-bottom: 5px; border-bottom: 2px solid #e5e7eb; padding-bottom: 15px; }
        .subtitle { text-align: center; color: #6b7280; font-size: 14px; margin-bottom: 30px; font-style: italic; }
        h2 { color: #2563eb; font-size: 18px; margin-top: 30px; margin-bottom: 15px; border-left: 4px solid #2563eb; padding-left: 10px; background: #eff6ff; padding-top: 5px; padding-bottom: 5px; border-radius: 0 4px 4px 0; }
        
        .card { border: 1px solid #e5e7eb; border-radius: 8px; margin-bottom: 15px; overflow: hidden; break-inside: avoid; }
        .card-header { background-color: #f3f4f6; padding: 8px 15px; font-weight: 600; color: #374151; font-size: 14px; border-bottom: 1px solid #e5e7eb; }
        .card-body { padding: 15px; }
        
        .equation-box { text-align: center; margin: 10px 0; padding: 10px; background-color: #ffffff; }
        .equation-img { max-width: 100%; height: auto; }
        
        .calculation-row { margin-top: 8px; font-family: Consolas, monospace; font-size: 13px; color: #4b5563; background: #f9fafb; padding: 8px; border-radius: 4px; border-left: 3px solid #d1d5db; }
        .result-highlight { color: #059669; font-weight: bold; }
        .param-highlight { color: #2563eb; }
        
        table.params-table { width: 100%; border-collapse: collapse; font-size: 13px; }
        table.params-table td { padding: 6px 10px; border-bottom: 1px solid #f3f4f6; }
        table.params-table tr:last-child td { border-bottom: none; }
        .label-col { color: #6b7280; width: 50%; }
        .symbol-col { font-family: serif; font-style: italic; color: #374151; width: 15%; text-align: center; }
        .value-col { font-weight: 600; color: #111827; text-align: right; }
        
        .footer { margin-top: 40px; text-align: center; font-size: 12px; color: #9ca3af; border-top: 1px solid #e5e7eb; padding-top: 20px; }
    </style>
    """

    # --- Render Equations ---
    # Geometry
    eq_gamma = render_equation(r"\gamma = \arccos(\sin(\phi_{gs})\sin(\phi_{sat}) + \cos(\phi_{gs})\cos(\phi_{sat})\cos(\lambda_{gs} - \lambda_{sat}))")
    eq_d = render_equation(r"d = \sqrt{(R_e + h)^2 + R_e^2 - 2R_e(R_e+h)\cos(\gamma)}") # Using law of cosines / slant range formula
    # Simplified slant range for display:
    eq_d_simple = render_equation(r"d = \sqrt{R_e^2 + (R_e+h)^2 - 2R_e(R_e+h)\cos(\gamma_{central})}") 
    # Or proper look angle formula
    eq_d_itu = render_equation(r"d = \sqrt{(R_e+h)^2 + R_e^2 - 2R_e(R_e+h)\cos(\gamma)}") 

    eq_beamwidth = render_equation(r"\theta_{3dB} \approx \frac{21}{f_{GHz} \cdot D_{m}}")
    
    # Uplink
    eq_gtx = render_equation(r"G_{tx} = 20\log_{10}(D) + 20\log_{10}(f) + 10\log_{10}(\eta) + 20.4")
    eq_eirp = render_equation(r"EIRP = P_{tx} - IBO + G_{tx} - L_{feed} - L_{point}")
    eq_fspl = render_equation(r"FSPL = 20\log_{10}(d) + 20\log_{10}(f) + 92.45")
    eq_ltotal = render_equation(r"L_{total} = FSPL + A_{gas} + \sqrt{A_{rain}^2 + A_{scint}^2} + A_{cloud} + L_{pol}")
    eq_gt = render_equation(r"G/T = G_{rx} - 10\log_{10}(T_{sys})")
    eq_cn0 = render_equation(r"C/N_0 = EIRP - L_{total} + G/T + 228.6")
    
    # Combined
    eq_cn0_total = render_equation(r"\frac{1}{(C/N_0)_{total}} = \frac{1}{(C/N_0)_{up}} + \frac{1}{(C/N_0)_{dn}} + \frac{1}{(C/IM_0)}")
    eq_margin = render_equation(r"Margin = (E_b/N_0)_{total} - (E_b/N_0)_{req}")
    eq_ber = render_equation(r"BER \approx 0.5 \cdot \text{erfc}\left(\sqrt{E_b/N_0}\right)")

    # --- Content Building ---
    
    content = f"""
    <html>
    <head>{css}</head>
    <body>
    <div class="container">
        <h1>{title}</h1>
        <div class="subtitle">Calculation Standards: ITU-R S.1328, P.525, P.618-14, P.676-12</div>
        
        <h2>1. System Parameters</h2>
        <div class="card">
            <div class="card-header">Input Configuration</div>
            <div class="card-body">
                <table class="params-table">
                    <tr><td class="label-col">Ground Station Location</td><td class="symbol-col">(\u03c6, \u03bb)</td><td class="value-col">{params.get('lat_gs', 0):.2f}\u00b0, {params.get('lon_gs', 0):.2f}\u00b0</td></tr>
                     <tr><td class="label-col">Satellite Location</td><td class="symbol-col">(\u03c6, \u03bb)</td><td class="value-col">{params.get('lat_sat', 0):.2f}\u00b0, {params.get('lon_sat', 0):.2f}\u00b0</td></tr>
                    <tr><td class="label-col">Uplink Frequency</td><td class="symbol-col">f_up</td><td class="value-col">{params.get('uplink_frequency_ghz', 14):.2f} GHz</td></tr>
                    <tr><td class="label-col">Downlink Frequency</td><td class="symbol-col">f_dn</td><td class="value-col">{params.get('downlink_frequency_ghz', 12):.2f} GHz</td></tr>
                    <tr><td class="label-col">Bandwidth</td><td class="symbol-col">B</td><td class="value-col">{bandwidth_hz/1e6:.1f} MHz</td></tr>
                    <tr><td class="label-col">Modulation</td><td class="symbol-col">MOD</td><td class="value-col">{params.get('modulation', 'QPSK')}</td></tr>
                </table>
            </div>
        </div>

        <h2>2. Geometry Calculations</h2>
        <div class="card">
            <div class="card-header">Step 1: Central Angle & Slant Range</div>
            <div class="card-body">
                <div class="equation-box"><img src="{eq_d_itu}" class="equation-img"></div>
                <div class="calculation-row">
                    d = {slant_range:.1f} km (Elevation: {params.get('elevation_deg', 0):.1f}\u00b0)
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">Step 2: Antenna Beamwidth (ITU-R S.1528)</div>
            <div class="card-body">
                <div class="equation-box"><img src="{eq_beamwidth}" class="equation-img"></div>
                <div class="calculation-row">
                    TX Beamwidth = 21 / ({params.get('uplink_frequency_ghz', 14):.1f} * {params.get('gs_antenna_diameter_m', 2.4):.1f}) = <span class="result-highlight">{gs_tx_beamwidth:.2f}\u00b0</span>
                </div>
            </div>
        </div>

        <h2>3. Uplink Budget</h2>
        <div class="card">
            <div class="card-header">Step 3: Ground Station EIRP</div>
            <div class="card-body">
                <div class="equation-box"><img src="{eq_gtx}" class="equation-img"></div>
                <div class="equation-box"><img src="{eq_eirp}" class="equation-img"></div>
                <div class="calculation-row">
                    G_tx = {uplink.get('gs_tx_gain_dbi', 0):.2f} dBi<br>
                    EIRP = {params.get('gs_tx_power_dbw', 0):.1f} (P_tx) - {params.get('input_backoff_db', 0):.1f} (IBO) + {uplink.get('gs_tx_gain_dbi', 0):.2f} (G_tx) - Losses<br>
                    EIRP = <span class="result-highlight">{uplink.get('gs_eirp_dbw', 0):.2f} dBW</span>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">Step 4: Path Losses (Free Space + Atmospheric)</div>
            <div class="card-body">
                <div class="equation-box"><img src="{eq_fspl}" class="equation-img"></div>
                <div class="equation-box"><img src="{eq_ltotal}" class="equation-img"></div>
                <div class="calculation-row">
                    FSPL = {uplink.get('fspl_db', 0):.2f} dB<br>
                    Atmospheric = {uplink.get('atmospheric_atten_db', 0):.2f} dB (Gas) + {uplink.get('rain_atten_db', 0):.2f} dB (Rain) + {uplink.get('cloud_atten_db', 0):.2f} dB (Cloud)<br>
                    Total Loss = <span class="result-highlight">{uplink.get('total_path_loss_db', 0):.2f} dB</span>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">Step 5: Uplink C/N0</div>
            <div class="card-body">
                <div class="equation-box"><img src="{eq_cn0}" class="equation-img"></div>
                <div class="calculation-row">
                    C/N0 = {uplink.get('gs_eirp_dbw', 0):.2f} - {uplink.get('total_path_loss_db', 0):.2f} + {uplink.get('sat_gt_db', 0):.2f} + 228.6<br>
                    C/N0 = <span class="result-highlight">{uplink.get('uplink_cn0_db', 0):.2f} dB-Hz</span>
                </div>
            </div>
        </div>

        <h2>4. Downlink Budget</h2>
        <div class="card">
            <div class="card-header">Step 6: Satellite EIRP & Path Loss</div>
            <div class="card-body">
                <div class="calculation-row">
                    Satellite EIRP = <span class="result-highlight">{downlink.get('sat_eirp_dbw', 0):.2f} dBW</span><br>
                    Total Downlink Loss = <span class="result-highlight">{downlink.get('total_path_loss_db', 0):.2f} dB</span>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">Step 7: Ground Station G/T</div>
            <div class="card-body">
                <div class="equation-box"><img src="{eq_gt}" class="equation-img"></div>
                 <div class="calculation-row">
                    T_sys = {downlink.get('system_temp_k', 0):.0f} K<br>
                    G/T = {downlink.get('gs_antenna_gain_dbi', 0):.2f} - Losses - 10log({downlink.get('system_temp_k', 0):.0f})<br>
                    G/T = <span class="result-highlight">{downlink.get('gs_gt_db', 0):.2f} dB/K</span>
                </div>
            </div>
        </div>

        <div class="card">
            <div class="card-header">Step 8: Downlink C/N0</div>
            <div class="card-body">
                 <div class="calculation-row">
                    C/N0 = {downlink.get('sat_eirp_dbw', 0):.2f} - {downlink.get('total_path_loss_db', 0):.2f} + {downlink.get('gs_gt_db', 0):.2f} + 228.6<br>
                    C/N0 = <span class="result-highlight">{downlink.get('downlink_cn0_db', 0):.2f} dB-Hz</span>
                </div>
            </div>
        </div>

        <h2>5. Total Link Performance</h2>
        <div class="card">
            <div class="card-header">Step 9: Combined C/N0 and Margin</div>
            <div class="card-body">
                <div class="equation-box"><img src="{eq_cn0_total}" class="equation-img"></div>
                <div class="calculation-row">
                    (C/N0)_up = {uplink.get('uplink_cn0_db', 0):.2f} dB-Hz<br>
                    (C/N0)_dn = {downlink.get('downlink_cn0_db', 0):.2f} dB-Hz<br>
                    (C/IM0) = {c_im0_db:.2f} dB-Hz<br>
                    <hr>
                    Total C/N0 = <span class="result-highlight">{results.get('total_cn0_db', 0):.2f} dB-Hz</span>
                </div>
            </div>
        </div>

        <div class="card" style="border-left: 5px solid #059669;">
            <div class="card-header" style="background-color: #ecfdf5; color: #065f46;">Step 10: Final Margin & BER</div>
            <div class="card-body">
                <div class="equation-box"><img src="{eq_margin}" class="equation-img"></div>
                <div class="equation-box"><img src="{eq_ber}" class="equation-img"></div>
                <div class="calculation-row" style="font-size: 14px; background: #d1fae5; color: #064e3b;">
                    Total Eb/N0 = <span style="font-weight:bold;">{results.get('total_ebn0_db', 0):.2f} dB</span><br>
                    Required Eb/N0 = {params.get('ebn0_required_db', 0):.2f} dB<br>
                    <br>
                    <span style="font-size: 18px;">LINK MARGIN = {results.get('total_margin_db', 0):.2f} dB</span>
                </div>
            </div>
        </div>

        <div class="footer">
            Generated by Satellite Link Budget Tool \u2022 ITU-R Compliant Models
        </div>
    </div>
    </body>
    </html>
    """
    return content
