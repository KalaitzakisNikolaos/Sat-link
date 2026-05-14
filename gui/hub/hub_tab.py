"""Hub tab — creation, refresh, and card building logic."""

from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                              QPushButton, QScrollArea, QFrame, QSplitter)
from PyQt5.QtGui import QFont, QCursor
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QComboBox


def create_hub_tab(mw):
    """Create Hub tab with split view for managing Base Stations and Satellites."""
    tab = QWidget()
    main_layout = QHBoxLayout(tab)
    main_layout.setContentsMargins(8, 8, 8, 8)
    main_layout.setSpacing(12)

    splitter = QSplitter(Qt.Orientation.Horizontal)

    # Left panel: base stations
    bs_panel = QWidget()
    bs_layout = QVBoxLayout(bs_panel)
    bs_layout.setSpacing(8)

    bs_header = QLabel("BASE STATIONS")
    bs_header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
    bs_header.setStyleSheet("color: #6366f1; background: transparent; letter-spacing: 1px;")
    bs_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
    bs_layout.addWidget(bs_header)

    bs_subtitle = QLabel("Ground stations for uplink/downlink")
    bs_subtitle.setStyleSheet("color: #94a3b8; background: transparent; font-size: 9pt;")
    bs_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
    bs_layout.addWidget(bs_subtitle)

    add_bs_btn = QPushButton("  +  Add Base Station")
    add_bs_btn.setFixedHeight(56)
    add_bs_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    add_bs_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent; border: 2px dashed #c7d2fe;
            border-radius: 14px; color: #6366f1; font-size: 12pt; font-weight: 600;
        }
        QPushButton:hover {
            background-color: #eef2ff; border: 2px dashed #6366f1; color: #4338ca;
        }
    """)
    add_bs_btn.clicked.connect(mw._add_base_station_dialog)
    bs_layout.addWidget(add_bs_btn)

    mw.bs_hub_scroll = QScrollArea()
    mw.bs_hub_scroll.setWidgetResizable(True)
    mw.bs_hub_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
    mw.bs_hub_list_widget = QWidget()
    mw.bs_hub_list_widget.setStyleSheet("background: transparent;")
    mw.bs_hub_list_layout = QVBoxLayout(mw.bs_hub_list_widget)
    mw.bs_hub_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    mw.bs_hub_scroll.setWidget(mw.bs_hub_list_widget)
    bs_layout.addWidget(mw.bs_hub_scroll, 1)

    splitter.addWidget(bs_panel)

    # Right panel: satellites
    sat_panel = QWidget()
    sat_layout = QVBoxLayout(sat_panel)
    sat_layout.setSpacing(8)

    sat_header = QLabel("SATELLITES")
    sat_header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
    sat_header.setStyleSheet("color: #f97316; background: transparent; letter-spacing: 1px;")
    sat_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
    sat_layout.addWidget(sat_header)

    sat_subtitle = QLabel("Satellite configurations with transponder")
    sat_subtitle.setStyleSheet("color: #94a3b8; background: transparent; font-size: 9pt;")
    sat_subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
    sat_layout.addWidget(sat_subtitle)

    add_sat_btn = QPushButton("  +  Add Satellite")
    add_sat_btn.setFixedHeight(56)
    add_sat_btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
    add_sat_btn.setStyleSheet("""
        QPushButton {
            background-color: transparent; border: 2px dashed #fed7aa;
            border-radius: 14px; color: #f97316; font-size: 12pt; font-weight: 600;
        }
        QPushButton:hover {
            background-color: #fff7ed; border: 2px dashed #f97316; color: #ea580c;
        }
    """)
    add_sat_btn.clicked.connect(mw._add_satellite_dialog)
    sat_layout.addWidget(add_sat_btn)

    mw.sat_hub_scroll = QScrollArea()
    mw.sat_hub_scroll.setWidgetResizable(True)
    mw.sat_hub_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
    mw.sat_hub_list_widget = QWidget()
    mw.sat_hub_list_widget.setStyleSheet("background: transparent;")
    mw.sat_hub_list_layout = QVBoxLayout(mw.sat_hub_list_widget)
    mw.sat_hub_list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    mw.sat_hub_scroll.setWidget(mw.sat_hub_list_widget)
    sat_layout.addWidget(mw.sat_hub_scroll, 1)

    # Quick load preset (replaces current satellites)
    from models.satellite import Satellite as SatelliteConfig
    
    preset_row = QHBoxLayout()
    preset_row.setContentsMargins(4, 0, 4, 0)
    
    preset_label = QLabel("Quick Load:")
    preset_label.setStyleSheet("color: #64748b; font-weight: 600; font-size: 9pt;")
    preset_row.addWidget(preset_label)
    
    preset_combo = QComboBox()
    preset_combo.addItem("- Select Preset to Replace -")
    preset_combo.addItems(list(SatelliteConfig.PRESETS.keys()))
    preset_combo.setStyleSheet("""
        QComboBox { border: 1px solid #cbd5e1; border-radius: 6px; padding: 4px 8px; color: #334155; }
        QComboBox::drop-down { border: none; }
    """)
    
    def _on_quick_preset(text):
        if text == "- Select Preset to Replace -": return
        if text in SatelliteConfig.PRESETS:
            try:
                # Create new satellite from preset
                p = SatelliteConfig.PRESETS[text]
                new_sat = SatelliteConfig(**p)
                
                # REPLACE existing satellites
                mw.satellite_configs.clear()
                mw.satellite_configs.append(new_sat)
                
                # Refresh UI
                mw._refresh_combos()
                mw._refresh_hub_lists()
                mw._rebuild_3d_visibility_panel()
                
                # Update main calculation if in full link mode
                if hasattr(mw, 'calculate_complete_link'):
                    mw.calculate_complete_link()
                
                mw.statusBar().showMessage(f"Replaced satellites with preset '{text}'")
                
                # Reset combo without triggering signal
                preset_combo.blockSignals(True)
                preset_combo.setCurrentIndex(0)
                preset_combo.blockSignals(False)
                
            except Exception as e:
                mw.statusBar().showMessage(f"Error loading preset: {str(e)}")
    
    preset_combo.currentTextChanged.connect(_on_quick_preset)
    preset_row.addWidget(preset_combo, 1)
    sat_layout.addLayout(preset_row)

    splitter.addWidget(sat_panel)
    splitter.setSizes([500, 500])

    main_layout.addWidget(splitter)

    _refresh_hub_lists(mw)
    return tab


# Refresh & card builders

def _refresh_hub_lists(mw):
    """Refresh both BS and Satellite card lists in the Hub tab."""
    mw._3d_needs_full_rebuild = True
    _refresh_hub_bs_list(mw)
    _refresh_hub_sat_list(mw)


def _refresh_hub_bs_list(mw):
    if not hasattr(mw, 'bs_hub_list_layout'):
        return
    try:
        while mw.bs_hub_list_layout.count():
            child = mw.bs_hub_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        for i, bs in enumerate(mw.base_stations):
            card = _create_bs_card(mw, bs, i)
            mw.bs_hub_list_layout.addWidget(card)
    except RuntimeError:
        return


def _refresh_hub_sat_list(mw):
    if not hasattr(mw, 'sat_hub_list_layout'):
        return
    try:
        while mw.sat_hub_list_layout.count():
            child = mw.sat_hub_list_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        for i, sat in enumerate(mw.satellite_configs):
            card = _create_sat_card(mw, sat, i)
            mw.sat_hub_list_layout.addWidget(card)
    except RuntimeError:
        return


def _create_bs_card(mw, bs, index):
    card = QFrame()
    card.setFrameShape(QFrame.Shape.StyledPanel)
    card.setStyleSheet("""
        QFrame {
            background-color: #ffffff; border: 1px solid #e2e8f0;
            border-left: 4px solid #6366f1; border-radius: 12px; padding: 4px;
        }
        QFrame:hover { border-left: 4px solid #4f46e5; background-color: #f8fafc; }
    """)
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(12, 8, 12, 8)
    card_layout.setSpacing(4)

    name_label = QLabel(f"\U0001f4e1  {bs.name}")
    name_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
    name_label.setStyleSheet("color: #1e293b; background: transparent; border: none;")
    card_layout.addWidget(name_label)

    info = (f"\U0001f4cd {bs.latitude:.4f}\u00b0, {bs.longitude:.4f}\u00b0  |  "
            f"TX: {bs.tx_power_dbw} dBW, D={bs.tx_antenna_diameter_m}m  |  "
            f"RX: D={bs.rx_antenna_diameter_m}m, T_LNA={bs.lna_temp_k}K")
    info_label = QLabel(info)
    info_label.setStyleSheet("color: #64748b; background: transparent; border: none; font-size: 8pt;")
    info_label.setWordWrap(True)
    card_layout.addWidget(info_label)

    btn_row = QHBoxLayout()
    btn_row.addStretch()

    edit_btn = QPushButton("\u270f\ufe0f Edit")
    edit_btn.setFixedHeight(28)
    edit_btn.setStyleSheet("""
        QPushButton { background: #eef2ff; color: #4338ca; border: 1px solid #c7d2fe;
            border-radius: 6px; padding: 2px 12px; font-size: 8pt; font-weight: 600; }
        QPushButton:hover { background: #e0e7ff; }
    """)
    edit_btn.clicked.connect(lambda checked, idx=index: mw._edit_base_station(idx))
    btn_row.addWidget(edit_btn)

    del_btn = QPushButton("\U0001f5d1\ufe0f Delete")
    del_btn.setFixedHeight(28)
    del_btn.setStyleSheet("""
        QPushButton { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca;
            border-radius: 6px; padding: 2px 12px; font-size: 8pt; font-weight: 600; }
        QPushButton:hover { background: #fee2e2; }
    """)
    del_btn.clicked.connect(lambda checked, idx=index: mw._delete_base_station(idx))
    btn_row.addWidget(del_btn)

    card_layout.addLayout(btn_row)
    return card


def _create_sat_card(mw, sat, index):
    card = QFrame()
    card.setFrameShape(QFrame.Shape.StyledPanel)
    card.setStyleSheet("""
        QFrame {
            background-color: #ffffff; border: 1px solid #e2e8f0;
            border-left: 4px solid #f97316; border-radius: 12px; padding: 4px;
        }
        QFrame:hover { border-left: 4px solid #ea580c; background-color: #f8fafc; }
    """)
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(12, 8, 12, 8)
    card_layout.setSpacing(4)

    name_label = QLabel(f"\U0001f6f0\ufe0f  {sat.name}")
    name_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
    name_label.setStyleSheet("color: #1e293b; background: transparent; border: none;")
    card_layout.addWidget(name_label)

    band_name = getattr(sat, 'band', 'N/A')
    ul_freq = getattr(sat, 'uplink_freq_ghz', 0)
    dl_freq = getattr(sat, 'downlink_freq_ghz', 0)
    bw_mhz = getattr(sat, 'bandwidth_mhz', 0)
    band_info = f"\U0001f4e1 {band_name}  |  UL: {ul_freq:.3f} GHz  |  DL: {dl_freq:.3f} GHz  |  BW: {bw_mhz:.0f} MHz"
    band_label = QLabel(band_info)
    band_label.setStyleSheet("color: #7c3aed; background: transparent; border: none; font-size: 8pt; font-weight: 600;")
    card_layout.addWidget(band_label)

    info = (f"{sat.sat_type} @ {sat.longitude:.1f}\u00b0E, {sat.altitude_km:.0f} km  |  "
            f"RX: {sat.rx_gain_dbi} dBi  |  TX: {sat.tx_power_dbw} dBW, {sat.tx_gain_dbi} dBi  |  "
            f"HPA: {sat.hpa_type}")
    info_label = QLabel(info)
    info_label.setStyleSheet("color: #64748b; background: transparent; border: none; font-size: 8pt;")
    info_label.setWordWrap(True)
    card_layout.addWidget(info_label)

    btn_row = QHBoxLayout()
    btn_row.addStretch()

    edit_btn = QPushButton("\u270f\ufe0f Edit")
    edit_btn.setFixedHeight(28)
    edit_btn.setStyleSheet("""
        QPushButton { background: #fff7ed; color: #c2410c; border: 1px solid #fed7aa;
            border-radius: 6px; padding: 2px 12px; font-size: 8pt; font-weight: 600; }
        QPushButton:hover { background: #ffedd5; }
    """)
    edit_btn.clicked.connect(lambda checked, idx=index: mw._edit_satellite(idx))
    btn_row.addWidget(edit_btn)

    del_btn = QPushButton("\U0001f5d1\ufe0f Delete")
    del_btn.setFixedHeight(28)
    del_btn.setStyleSheet("""
        QPushButton { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca;
            border-radius: 6px; padding: 2px 12px; font-size: 8pt; font-weight: 600; }
        QPushButton:hover { background: #fee2e2; }
    """)
    del_btn.clicked.connect(lambda checked, idx=index: mw._delete_satellite(idx))
    btn_row.addWidget(del_btn)

    card_layout.addLayout(btn_row)
    return card
