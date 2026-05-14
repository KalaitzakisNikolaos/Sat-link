"""Base Station and Satellite CRUD dialogs."""

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
                              QLabel, QPushButton, QComboBox, QDoubleSpinBox,
                              QGroupBox, QScrollArea, QWidget, QMessageBox)
from models.base_station import BaseStation
from models.satellite import Satellite as SatelliteConfig
from models.transponder import SatelliteTransponder
from models.constants import SATELLITE_TYPES, SATELLITE_BAND_ALLOCATIONS


# Base station dialogs

def add_base_station_dialog(mw):
    dialog = _create_bs_dialog(mw)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        data = dialog.get_values()
        bs = BaseStation(**data)
        mw.base_stations.append(bs)
        mw._refresh_combos()
        mw._refresh_hub_lists()
        mw._rebuild_3d_visibility_panel()
        mw.statusBar().showMessage(f"Base Station '{bs.name}' added")


def edit_base_station(mw, index):
    if 0 <= index < len(mw.base_stations):
        bs = mw.base_stations[index]
        dialog = _create_bs_dialog(mw, bs)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_values()
            for key, val in data.items():
                setattr(bs, key, val)
            mw._refresh_combos()
            mw._refresh_hub_lists()
            mw._rebuild_3d_visibility_panel()
            mw.statusBar().showMessage(f"Base Station '{bs.name}' updated")


def delete_base_station(mw, index):
    if 0 <= index < len(mw.base_stations):
        bs = mw.base_stations[index]
        reply = QMessageBox.question(mw, "Delete Base Station",
            f"Delete '{bs.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            mw.base_stations.pop(index)
            mw._refresh_combos()
            mw._refresh_hub_lists()
            mw._rebuild_3d_visibility_panel()
            mw.statusBar().showMessage(f"Base Station '{bs.name}' deleted")


# Satellite dialogs

def add_satellite_dialog(mw):
    dialog = _create_sat_dialog(mw)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        data = dialog.get_values()
        sat = SatelliteConfig(**data)
        mw.satellite_configs.append(sat)
        mw._refresh_combos()
        mw._refresh_hub_lists()
        mw._rebuild_3d_visibility_panel()
        mw.statusBar().showMessage(f"Satellite '{sat.name}' added")


def edit_satellite(mw, index):
    if 0 <= index < len(mw.satellite_configs):
        sat = mw.satellite_configs[index]
        dialog = _create_sat_dialog(mw, sat)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_values()
            for key, val in data.items():
                setattr(sat, key, val)
            mw._refresh_combos()
            mw._refresh_hub_lists()
            mw._rebuild_3d_visibility_panel()
            mw._sync_from_selection()
            mw.calculate_complete_link()
            mw.statusBar().showMessage(f"Satellite '{sat.name}' updated")


def delete_satellite(mw, index):
    if 0 <= index < len(mw.satellite_configs):
        sat = mw.satellite_configs[index]
        reply = QMessageBox.question(mw, "Delete Satellite",
            f"Delete '{sat.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            mw.satellite_configs.pop(index)
            mw._refresh_combos()
            mw._refresh_hub_lists()
            mw._rebuild_3d_visibility_panel()
            mw.statusBar().showMessage(f"Satellite '{sat.name}' deleted")


# Dialog builders

def _create_bs_dialog(mw, bs=None):
    dialog = QDialog(mw)
    dialog.setWindowTitle("Edit Base Station" if bs else "Add Base Station")
    dialog.setMinimumWidth(440)
    dlg_layout = QVBoxLayout(dialog)

    form = QGridLayout()
    row = 0

    form.addWidget(QLabel("Name:"), row, 0)
    name_edit = QComboBox()
    name_edit.setEditable(True)
    name_edit.addItems(list(BaseStation.PRESETS.keys()))
    name_edit.setCurrentText(bs.name if bs else "")
    name_edit.setToolTip("Type a name or select a preset")
    form.addWidget(name_edit, row, 1)

    load_preset_btn = QPushButton("Load Preset")
    load_preset_btn.setFixedHeight(28)
    form.addWidget(load_preset_btn, row, 2)
    row += 1

    def _make_spin(min_v, max_v, val, suffix="", decimals=2, step=1.0):
        s = QDoubleSpinBox()
        s.setRange(min_v, max_v)
        s.setValue(val)
        s.setSuffix(suffix)
        s.setDecimals(decimals)
        s.setSingleStep(step)
        return s

    fields = {}
    params = [
        ("Latitude:", "latitude", -90, 90, bs.latitude if bs else 37.9755648, "\u00b0", 7),
        ("Longitude:", "longitude", -180, 180, bs.longitude if bs else 23.7348324, "\u00b0", 7),
        ("Height (ASL):", "height_km", 0, 5, bs.height_km if bs else 0.0, " km", 2),
        ("TX Power:", "tx_power_dbw", -10, 30, bs.tx_power_dbw if bs else 10.0, " dBW", 1),
        ("TX Antenna \u00d8:", "tx_antenna_diameter_m", 0.3, 15, bs.tx_antenna_diameter_m if bs else 2.4, " m", 2),
        ("RX Antenna \u00d8:", "rx_antenna_diameter_m", 0.3, 30, bs.rx_antenna_diameter_m if bs else 1.2, " m", 2),
        ("Antenna Eff.:", "antenna_efficiency", 0.3, 0.9, bs.antenna_efficiency if bs else 0.6, "", 2),
        ("Feed Loss:", "feed_loss_db", 0, 5, bs.feed_loss_db if bs else 0.5, " dB", 1),
        ("TX Pointing Loss:", "pointing_loss_tx_db", 0, 3, bs.pointing_loss_tx_db if bs else 0.3, " dB", 1),
        ("RX Pointing Loss:", "pointing_loss_rx_db", 0, 3, bs.pointing_loss_rx_db if bs else 0.2, " dB", 1),
        ("LNA Temp:", "lna_temp_k", 10, 500, bs.lna_temp_k if bs else 50.0, " K", 0),
    ]

    for label_text, key, mn, mx, val, suffix, dec in params:
        form.addWidget(QLabel(label_text), row, 0)
        spin = _make_spin(mn, mx, val, suffix, dec)
        fields[key] = spin
        form.addWidget(spin, row, 1, 1, 2)
        row += 1

    def _load_preset():
        preset_name = name_edit.currentText()
        if preset_name in BaseStation.PRESETS:
            p = BaseStation.PRESETS[preset_name]
            for key, spin in fields.items():
                if key in p:
                    spin.setValue(p[key])

    load_preset_btn.clicked.connect(_load_preset)
    dlg_layout.addLayout(form)

    btn_row = QHBoxLayout()
    ok_btn = QPushButton("Save")
    ok_btn.setProperty("variant", "success")
    ok_btn.clicked.connect(dialog.accept)
    btn_row.addWidget(ok_btn)
    cancel_btn = QPushButton("Cancel")
    cancel_btn.setProperty("variant", "outline")
    cancel_btn.clicked.connect(dialog.reject)
    btn_row.addWidget(cancel_btn)
    dlg_layout.addLayout(btn_row)

    def get_values():
        result = {'name': name_edit.currentText()}
        for key, spin in fields.items():
            result[key] = spin.value()
        return result

    dialog.get_values = get_values
    return dialog


def _create_sat_dialog(mw, sat=None):
    dialog = QDialog(mw)
    dialog.setWindowTitle("Edit Satellite" if sat else "Add Satellite")
    dialog.setMinimumWidth(520)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll_widget = QWidget()
    dlg_layout = QVBoxLayout(scroll_widget)

    form = QGridLayout()
    row = 0

    form.addWidget(QLabel("Name:"), row, 0)
    name_edit = QComboBox()
    name_edit.setEditable(True)
    name_edit.addItems(list(SatelliteConfig.PRESETS.keys()))
    name_edit.setCurrentText(sat.name if sat else "")
    form.addWidget(name_edit, row, 1)

    load_preset_btn = QPushButton("Load Preset")
    load_preset_btn.setFixedHeight(28)
    form.addWidget(load_preset_btn, row, 2)
    row += 1

    form.addWidget(QLabel("Type:"), row, 0)
    type_combo = QComboBox()
    type_combo.addItems(list(SATELLITE_TYPES.keys()))
    type_combo.setCurrentText(sat.sat_type if sat else "GEO")
    form.addWidget(type_combo, row, 1, 1, 2)
    row += 1

    band_header = QLabel("\u2500\u2500 Frequency Band (ITU-R) \u2500\u2500")
    band_header.setStyleSheet("color: #7c3aed; font-weight: bold; font-size: 9pt; border: none; background: transparent;")
    form.addWidget(band_header, row, 0, 1, 3)
    row += 1

    form.addWidget(QLabel("Band:"), row, 0)
    band_combo = QComboBox()
    band_combo.addItems(list(SATELLITE_BAND_ALLOCATIONS.keys()))
    current_band = getattr(sat, 'band', 'Ku-band') if sat else 'Ku-band'
    band_combo.setCurrentText(current_band)
    form.addWidget(band_combo, row, 1, 1, 2)
    row += 1

    def _make_spin(min_v, max_v, val, suffix="", decimals=1, step=1.0):
        s = QDoubleSpinBox()
        s.setRange(min_v, max_v)
        s.setValue(val)
        s.setSuffix(suffix)
        s.setDecimals(decimals)
        s.setSingleStep(step)
        return s

    form.addWidget(QLabel("Uplink Freq:"), row, 0)
    ul_freq_spin = _make_spin(0.5, 100.0, getattr(sat, 'uplink_freq_ghz', 14.25) if sat else 14.25, " GHz", 3, 0.1)
    form.addWidget(ul_freq_spin, row, 1, 1, 2)
    row += 1

    form.addWidget(QLabel("Downlink Freq:"), row, 0)
    dl_freq_spin = _make_spin(0.5, 100.0, getattr(sat, 'downlink_freq_ghz', 11.725) if sat else 11.725, " GHz", 3, 0.1)
    form.addWidget(dl_freq_spin, row, 1, 1, 2)
    row += 1

    form.addWidget(QLabel("Bandwidth:"), row, 0)
    bw_spin = _make_spin(0.1, 5000.0, getattr(sat, 'bandwidth_mhz', 36.0) if sat else 36.0, " MHz", 1, 1.0)
    form.addWidget(bw_spin, row, 1, 1, 2)
    row += 1

    band_info_label = QLabel("")
    band_info_label.setStyleSheet("color: #64748b; background: transparent; border: none; font-size: 7pt;")
    band_info_label.setWordWrap(True)
    form.addWidget(band_info_label, row, 0, 1, 3)
    row += 1

    def _on_band_changed(band_name):
        if band_name in SATELLITE_BAND_ALLOCATIONS:
            alloc = SATELLITE_BAND_ALLOCATIONS[band_name]
            ul_freq_spin.setValue(alloc['uplink_center_ghz'])
            dl_freq_spin.setValue(alloc['downlink_center_ghz'])
            bw_spin.setValue(alloc['typical_transponder_bw_mhz'])
            band_info_label.setText(
                f"ITU-R: UL {alloc['uplink_min_ghz']:.3f}\u2013{alloc['uplink_max_ghz']:.3f} GHz  |  "
                f"DL {alloc['downlink_min_ghz']:.3f}\u2013{alloc['downlink_max_ghz']:.3f} GHz  |  "
                f"{alloc['services']}")

    band_combo.currentTextChanged.connect(_on_band_changed)
    _on_band_changed(band_combo.currentText())
    if sat:
        ul_freq_spin.setValue(getattr(sat, 'uplink_freq_ghz', 14.25))
        dl_freq_spin.setValue(getattr(sat, 'downlink_freq_ghz', 11.725))
        bw_spin.setValue(getattr(sat, 'bandwidth_mhz', 36.0))

    sep2 = QLabel("\u2500\u2500 Transponder & HPA \u2500\u2500")
    sep2.setStyleSheet("color: #f97316; font-weight: bold; font-size: 9pt; border: none; background: transparent;")
    form.addWidget(sep2, row, 0, 1, 3)
    row += 1

    form.addWidget(QLabel("Transponder:"), row, 0)
    transp_combo = QComboBox()
    transp_combo.addItems(list(SatelliteTransponder.PRESETS.keys()))
    transp_combo.setCurrentText(sat.transponder_preset if sat else "Ku-band_standard")
    form.addWidget(transp_combo, row, 1, 1, 2)
    row += 1

    form.addWidget(QLabel("HPA Type:"), row, 0)
    hpa_combo = QComboBox()
    hpa_combo.addItems(['TWTA', 'SSPA', 'Linearized'])
    hpa_combo.setCurrentText(sat.hpa_type if sat else "TWTA")
    form.addWidget(hpa_combo, row, 1, 1, 2)
    row += 1

    fields = {}
    params = [
        ("Altitude:", "altitude_km", 160, 50000, sat.altitude_km if sat else 35786, " km", 0),
        ("Latitude:", "latitude", -90, 90, sat.latitude if sat else 0.0, "\u00b0", 2),
        ("Longitude:", "longitude", -180, 180, sat.longitude if sat else 13.0, "\u00b0", 1),
        ("RX Gain:", "rx_gain_dbi", 0, 50, sat.rx_gain_dbi if sat else 30.0, " dBi", 1),
        ("Noise Figure:", "noise_figure_db", 0.5, 10, sat.noise_figure_db if sat else 2.0, " dB", 1),
        ("TX Power:", "tx_power_dbw", -10, 50, sat.tx_power_dbw if sat else 10.0, " dBW", 1),
        ("TX Gain:", "tx_gain_dbi", 0, 60, sat.tx_gain_dbi if sat else 32.0, " dBi", 1),
        ("IBO:", "input_backoff_db", 0, 15, sat.input_backoff_db if sat else 1.0, " dB", 1),
        ("LNA Gain:", "lna_gain_db", 10, 50, sat.lna_gain_db if sat else 30.0, " dB", 0),
        ("LNA NF:", "lna_nf_db", 0.3, 5, sat.lna_nf_db if sat else 1.2, " dB", 1),
        ("Mixer Gain:", "mixer_gain_db", -15, 5, sat.mixer_gain_db if sat else -6.0, " dB", 0),
        ("Mixer NF:", "mixer_nf_db", 3, 15, sat.mixer_nf_db if sat else 8.0, " dB", 1),
        ("IF Amp Gain:", "if_gain_db", 10, 50, sat.if_gain_db if sat else 30.0, " dB", 0),
        ("PA Gain:", "pa_gain_db", 5, 40, sat.pa_gain_db if sat else 20.0, " dB", 0),
        ("PA P_sat:", "pa_psat_dbw", -5, 25, sat.pa_psat_dbw if sat else 10.0, " dBW", 0),
    ]

    for label_text, key, mn, mx, val, suffix, dec in params:
        form.addWidget(QLabel(label_text), row, 0)
        spin = _make_spin(mn, mx, val, suffix, dec)
        fields[key] = spin
        form.addWidget(spin, row, 1, 1, 2)
        row += 1

    def _load_preset():
        preset_name = name_edit.currentText()
        if preset_name in SatelliteConfig.PRESETS:
            p = SatelliteConfig.PRESETS[preset_name]
            type_combo.setCurrentText(p.get('sat_type', 'GEO'))
            transp_combo.setCurrentText(p.get('transponder_preset', 'Ku-band_standard'))
            hpa_combo.setCurrentText(p.get('hpa_type', 'TWTA'))
            if 'band' in p:
                band_combo.blockSignals(True)
                band_combo.setCurrentText(p['band'])
                band_combo.blockSignals(False)
                _on_band_changed(p['band'])
            if 'uplink_freq_ghz' in p:
                ul_freq_spin.setValue(p['uplink_freq_ghz'])
            if 'downlink_freq_ghz' in p:
                dl_freq_spin.setValue(p['downlink_freq_ghz'])
            if 'bandwidth_mhz' in p:
                bw_spin.setValue(p['bandwidth_mhz'])
            for key, spin in fields.items():
                if key in p:
                    spin.setValue(p[key])

    load_preset_btn.clicked.connect(_load_preset)

    def _on_type_changed(new_type):
        dialog_orbit_defaults = {
            'GEO': {'altitude_km': 35786, 'latitude': 0.0, 'uplink_freq_ghz': 14.0, 'downlink_freq_ghz': 12.0,
                     'bandwidth_mhz': 36.0, 'rx_gain_dbi': 30.0, 'noise_figure_db': 2.0,
                     'tx_power_dbw': 10.0, 'tx_gain_dbi': 32.0, 'input_backoff_db': 1.0,
                     'hpa_type': 'TWTA', 'transponder_preset': 'Ku-band_standard', 'band': 'Ku-band'},
            'LEO': {'altitude_km': 550, 'latitude': 0.0, 'uplink_freq_ghz': 14.0, 'downlink_freq_ghz': 12.0,
                     'bandwidth_mhz': 240.0, 'rx_gain_dbi': 32.0, 'noise_figure_db': 2.0,
                     'tx_power_dbw': 5.0, 'tx_gain_dbi': 32.0, 'input_backoff_db': 2.0,
                     'hpa_type': 'SSPA', 'transponder_preset': 'Ku-band_standard', 'band': 'Ku-band'},
            'MEO': {'altitude_km': 20200, 'latitude': 0.0, 'uplink_freq_ghz': 1.6, 'downlink_freq_ghz': 1.575,
                     'bandwidth_mhz': 20.0, 'rx_gain_dbi': 13.0, 'noise_figure_db': 3.0,
                     'tx_power_dbw': 8.0, 'tx_gain_dbi': 13.0, 'input_backoff_db': 2.0,
                     'hpa_type': 'SSPA', 'transponder_preset': 'C-band_standard', 'band': 'L-band'},
            'HEO': {'altitude_km': 20000, 'latitude': 63.4, 'uplink_freq_ghz': 14.0, 'downlink_freq_ghz': 12.0,
                     'bandwidth_mhz': 36.0, 'rx_gain_dbi': 30.0, 'noise_figure_db': 2.5,
                     'tx_power_dbw': 10.0, 'tx_gain_dbi': 30.0, 'input_backoff_db': 1.0,
                     'hpa_type': 'TWTA', 'transponder_preset': 'Ku-band_standard', 'band': 'Ku-band'},
        }
        defaults = dialog_orbit_defaults.get(new_type)
        if not defaults:
            return
        for key, spin in fields.items():
            if key in defaults:
                spin.setValue(defaults[key])
        ul_freq_spin.setValue(defaults['uplink_freq_ghz'])
        dl_freq_spin.setValue(defaults['downlink_freq_ghz'])
        bw_spin.setValue(defaults['bandwidth_mhz'])
        hpa_combo.setCurrentText(defaults['hpa_type'])
        transp_combo.setCurrentText(defaults['transponder_preset'])
        band_combo.blockSignals(True)
        band_combo.setCurrentText(defaults['band'])
        band_combo.blockSignals(False)

    type_combo.currentTextChanged.connect(_on_type_changed)

    dlg_layout.addLayout(form)

    btn_row = QHBoxLayout()
    ok_btn = QPushButton("Save")
    ok_btn.setProperty("variant", "success")
    ok_btn.clicked.connect(dialog.accept)
    btn_row.addWidget(ok_btn)
    cancel_btn = QPushButton("Cancel")
    cancel_btn.setProperty("variant", "outline")
    cancel_btn.clicked.connect(dialog.reject)
    btn_row.addWidget(cancel_btn)
    dlg_layout.addLayout(btn_row)

    scroll.setWidget(scroll_widget)
    outer_layout = QVBoxLayout(dialog)
    outer_layout.addWidget(scroll)

    def get_values():
        result = {
            'name': name_edit.currentText(),
            'sat_type': type_combo.currentText(),
            'band': band_combo.currentText(),
            'uplink_freq_ghz': ul_freq_spin.value(),
            'downlink_freq_ghz': dl_freq_spin.value(),
            'bandwidth_mhz': bw_spin.value(),
            'transponder_preset': transp_combo.currentText(),
            'hpa_type': hpa_combo.currentText(),
        }
        for key, spin in fields.items():
            result[key] = spin.value()
        return result

    dialog.get_values = get_values
    return dialog
