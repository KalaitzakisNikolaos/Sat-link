"""Dashboard metric cards and real-time tracking cards.

Every function takes `mw` (the main window instance) as its first parameter.
"""
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                              QFrame)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt
import numpy as np


def create_dashboard_cards(mw):
    """Create dashboard metric cards."""
    dashboard = QWidget()
    dashboard.setFixedHeight(88)
    dashboard.setStyleSheet("background: transparent;")
    layout = QHBoxLayout(dashboard)
    layout.setContentsMargins(4, 4, 4, 4)
    layout.setSpacing(10)

    # Card factory with gradient accent bars
    def make_card(title, value, unit, gradient_start, gradient_end, icon):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
                border-left: 4px solid {gradient_start};
            }}
            QFrame:hover {{
                background-color: #f8fafc;
                border-left: 4px solid {gradient_end};
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 8, 14, 8)
        card_layout.setSpacing(2)

        title_label = QLabel(f"{icon} {title}")
        title_label.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
        title_label.setStyleSheet(
            f"color: #64748b; background: transparent; border: none; letter-spacing: 0.5px;")
        card_layout.addWidget(title_label)

        value_label = QLabel(f"{value} {unit}")
        value_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        value_label.setStyleSheet(
            f"color: {gradient_start}; background: transparent; border: none;")
        value_label.setObjectName("card_value")
        card_layout.addWidget(value_label)

        return card, value_label

    card1, mw.card_margin_label = make_card(
        "TOTAL MARGIN", "--", "dB", "#10b981", "#059669", "")
    card2, mw.card_cn0_label = make_card(
        "TOTAL C/N\u2080", "--", "dB-Hz", "#6366f1", "#4f46e5", "")
    card3, mw.card_ebn0_label = make_card(
        "Eb/N\u2080", "--", "dB", "#f59e0b", "#d97706", "")
    card4, mw.card_availability_label = make_card(
        "AVAILABILITY", "--", "%", "#8b5cf6", "#7c3aed", "")
    card5, mw.card_data_rate_label = make_card(
        "DATA RATE", "--", "Mbps", "#06b6d4", "#0891b2", "")
    card6, mw.card_elevation_label = make_card(
        "ELEVATION", "--", "\u00b0", "#64748b", "#475569", "")

    for card in [card1, card2, card3, card4, card5, card6]:
        layout.addWidget(card)

    return dashboard


def create_tracking_cards(mw):
    """Create real-time satellite tracking dashboard with collapsible arrow toggle."""
    # Outer wrapper: arrow row + cards row
    wrapper = QWidget()
    wrapper.setStyleSheet("background: transparent;")
    wrapper_layout = QVBoxLayout(wrapper)
    wrapper_layout.setContentsMargins(0, 0, 0, 0)
    wrapper_layout.setSpacing(0)

    # Arrow toggle row
    arrow_btn = QLabel("\u25BC")                         # ▼ = expanded
    arrow_btn.setFixedSize(18, 14)
    arrow_btn.setAlignment(Qt.AlignmentFlag.AlignCenter)
    arrow_btn.setCursor(Qt.CursorShape.PointingHandCursor)
    arrow_btn.setStyleSheet(
        "color: #94a3b8; font-size: 9px; background: transparent; border: none; padding: 0px;")
    arrow_btn.setToolTip("Toggle satellite tracking cards")
    arrow_row = QWidget()
    arrow_row.setFixedHeight(14)
    arrow_row.setStyleSheet("background: transparent;")
    ar_layout = QHBoxLayout(arrow_row)
    ar_layout.setContentsMargins(6, 0, 0, 0)
    ar_layout.setSpacing(0)
    ar_layout.addWidget(arrow_btn)
    ar_layout.addStretch()
    wrapper_layout.addWidget(arrow_row)

    # Tracking cards row
    tracking = QWidget()
    tracking.setFixedHeight(88)
    tracking.setStyleSheet("background: transparent;")
    layout = QHBoxLayout(tracking)
    layout.setContentsMargins(4, 4, 4, 4)
    layout.setSpacing(10)

    def make_tracking_card(title, value, unit, gradient_start, gradient_end, icon):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setStyleSheet(f"""
            QFrame {{
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 14px;
                border-left: 4px solid {gradient_start};
            }}
            QFrame:hover {{
                background-color: #f8fafc;
                border-left: 4px solid {gradient_end};
            }}
        """)
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 8, 14, 8)
        card_layout.setSpacing(2)

        title_label = QLabel(f"{icon} {title}")
        title_label.setFont(QFont("Segoe UI", 7, QFont.Weight.DemiBold))
        title_label.setStyleSheet(
            f"color: #64748b; background: transparent; border: none; letter-spacing: 0.5px;")
        card_layout.addWidget(title_label)

        value_label = QLabel(f"{value} {unit}")
        value_label.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        value_label.setStyleSheet(
            f"color: {gradient_start}; background: transparent; border: none;")
        card_layout.addWidget(value_label)

        return card, value_label

    c1, mw.track_distance_label = make_tracking_card(
        "SAT DISTANCE", "--", "km", "#e11d48", "#be123c", "\U0001F6F0")
    c2, mw.track_azimuth_label = make_tracking_card(
        "AZIMUTH", "--", "\u00B0", "#0284c7", "#0369a1", "\U0001F9ED")
    c3, mw.track_elevation_label = make_tracking_card(
        "ELEVATION", "--", "\u00B0", "#16a34a", "#15803d", "\U0001F4D0")
    c4, mw.track_doppler_ul_label = make_tracking_card(
        "UL DOPPLER", "--", "kHz", "#9333ea", "#7e22ce", "\u2B06")
    c4b, mw.track_doppler_dl_label = make_tracking_card(
        "DL DOPPLER", "--", "kHz", "#6d28d9", "#5b21b6", "\u2B07")
    c5, mw.track_velocity_label = make_tracking_card(
        "SAT VELOCITY", "--", "km/s", "#ea580c", "#c2410c", "\u26A1")
    c6, mw.track_lat_lon_label = make_tracking_card(
        "SUB-SAT POINT", "--", "", "#64748b", "#475569", "\U0001F30D")

    for card in [c1, c2, c3, c4, c4b, c5, c6]:
        layout.addWidget(card)

    wrapper_layout.addWidget(tracking)

    # Toggle logic
    def _toggle_tracking(event):
        vis = not tracking.isVisible()
        tracking.setVisible(vis)
        arrow_btn.setText("\u25BC" if vis else "\u25B6")  # ▼ or ▶
        # Adjust wrapper height so collapsed = just the tiny arrow row
        if vis:
            wrapper.setFixedHeight(88 + 14)
        else:
            wrapper.setFixedHeight(14)

    arrow_btn.mousePressEvent = _toggle_tracking
    wrapper.setFixedHeight(88 + 14)  # initial expanded height

    return wrapper


def update_dashboard_cards(mw, results, params):
    """Update dashboard metric cards with current results."""
    link_mode = params.get('link_mode', 'Full Link')

    if link_mode == 'Uplink Only':
        margin = results['uplink']['uplink_margin_db']
        cn0 = results['uplink']['uplink_cn0_db']
        ebn0 = results['uplink']['uplink_ebn0_db']
    elif link_mode == 'Downlink Only':
        margin = results['downlink']['downlink_margin_db']
        cn0 = results['downlink']['downlink_cn0_db']
        ebn0 = results['downlink']['downlink_ebn0_db']
    else:
        margin = results['total_margin_db']
        cn0 = results['total_cn0_db']
        ebn0 = results['total_ebn0_db']

    margin_color = "#4CAF50" if margin > 3 else "#FF9800" if margin > 0 else "#f44336"
    mw.card_margin_label.setText(f"{margin:.1f} dB")
    mw.card_margin_label.setStyleSheet(
        f"color: {margin_color}; background: transparent; border: none; "
        f"font-size: 13pt; font-weight: bold;")

    mw.card_cn0_label.setText(f"{cn0:.1f} dB-Hz")
    mw.card_ebn0_label.setText(f"{ebn0:.1f} dB")

    # Availability estimate (simplified from rain margin)
    if margin > 5:
        avail = 99.99
    elif margin > 3:
        avail = 99.9
    elif margin > 1:
        avail = 99.5
    elif margin > 0:
        avail = 99.0
    else:
        avail = max(0, 95.0 + margin * 2)
    mw.card_availability_label.setText(f"{avail:.2f} %")

    # Data rate
    data_rate_mbps = params.get('data_rate_bps', 0) / 1e6
    mw.card_data_rate_label.setText(f"{data_rate_mbps:.1f} Mbps")

    # Elevation
    elevation = params.get('elevation_deg', 0)
    mw.card_elevation_label.setText(f"{elevation:.1f}\u00b0")


def update_tracking_cards(mw):
    """Compute and display satellite-to-ground tracking data."""
    from models.orbit import create_satellite_from_type

    try:
        if mw.satellite is None:
            sat_type = mw.sat_type_combo.currentText()
            mw.satellite = create_satellite_from_type(sat_type)

        gs_lat = mw.gs_lat_spin.value()
        gs_lon = mw.gs_lon_spin.value()
        ul_freq_ghz = mw.uplink_freq_spin.value()
        dl_freq_ghz = mw.frequency_spin.value()
        ul_freq_hz = ul_freq_ghz * 1e9
        dl_freq_hz = dl_freq_ghz * 1e9
        t = mw.current_time

        # Look angles
        look = mw.satellite.calculate_look_angles(gs_lat, gs_lon, 0, t)
        distance_km = look['range']
        azimuth_deg = look['azimuth']
        elevation_deg = look['elevation']
        visible = look['visible']

        # Doppler shift
        doppler_ul_hz = mw.satellite.calculate_doppler_shift(ul_freq_hz, gs_lat, gs_lon, t)
        doppler_dl_hz = mw.satellite.calculate_doppler_shift(dl_freq_hz, gs_lat, gs_lon, t)
        doppler_ul_khz = doppler_ul_hz / 1e3
        doppler_dl_khz = doppler_dl_hz / 1e3

        # Satellite velocity magnitude
        vel = mw.satellite.get_satellite_velocity_eci(t)
        vel_mag = np.linalg.norm(vel)

        # Sub-satellite point
        pos_eci = mw.satellite.get_satellite_position_eci(t)
        pos_ecef = mw.satellite._eci_to_ecef(pos_eci, t)
        r = np.linalg.norm(pos_ecef)
        sub_lat = np.degrees(np.arcsin(pos_ecef[2] / r))
        sub_lon = np.degrees(np.arctan2(pos_ecef[1], pos_ecef[0]))

        # Format distance
        if distance_km > 10000:
            dist_text = f"{distance_km/1000:.1f} \u00d710\u00b3 km"
        else:
            dist_text = f"{distance_km:.1f} km"

        if visible and elevation_deg >= 5:
            dist_color = "#10b981"
        elif visible:
            dist_color = "#f59e0b"
        else:
            dist_color = "#ef4444"

        mw.track_distance_label.setText(dist_text)
        mw.track_distance_label.setStyleSheet(
            f"color: {dist_color}; background: transparent; border: none; "
            f"font-size: 13pt; font-weight: bold;")

        mw.track_azimuth_label.setText(f"{azimuth_deg:.1f}\u00b0")

        el_color = ("#10b981" if elevation_deg > 10
                     else "#f59e0b" if elevation_deg > 0
                     else "#ef4444")
        mw.track_elevation_label.setText(f"{elevation_deg:.1f}\u00b0")
        mw.track_elevation_label.setStyleSheet(
            f"color: {el_color}; background: transparent; border: none; "
            f"font-size: 13pt; font-weight: bold;")

        mw.track_doppler_ul_label.setText(f"{doppler_ul_khz:+.2f} kHz")
        mw.track_doppler_dl_label.setText(f"{doppler_dl_khz:+.2f} kHz")
        mw.track_velocity_label.setText(f"{vel_mag:.2f} km/s")
        mw.track_lat_lon_label.setText(f"{sub_lat:.1f}\u00b0, {sub_lon:.1f}\u00b0")

    except Exception:
        pass  # Silently skip if satellite not yet initialized
