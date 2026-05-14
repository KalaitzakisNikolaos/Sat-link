"""
Save/Load module — JSON save and load for parameters.
"""
import json
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QComboBox
from models.base_station import BaseStation
from models.satellite import Satellite as SatelliteConfig


def get_current_parameters_dict(mw):
    """
    Extract current parameters from the main window into a dictionary structure.
    Useful for saving to file or creating a preset.
    """
    return {
        'base_stations': [bs.to_dict() for bs in mw.base_stations],
        'satellite_configs': [sat.to_dict() for sat in mw.satellite_configs],
        'selected_bs1': mw.bs1_combo.currentText(),
        'selected_sat': mw.sat_combo.currentText(),
        'selected_bs2': mw.bs2_combo.currentText(),
        'general': {
            'link_mode': mw.link_mode_combo.currentText(),
            'uplink_freq_ghz': mw.uplink_freq_spin.value(),
            'downlink_freq_ghz': mw.frequency_spin.value(),
            'bandwidth_mhz': mw.bandwidth_spin.value(),
            'uplink_rain_rate': mw.uplink_rain_spin.value(),
            'downlink_rain_rate': mw.rain_spin.value(),
            'modulation': mw.modulation_combo.currentText(),
            'coding': mw.coding_combo.currentText(),
            'pol_loss_db': mw.pol_loss_spin.value(),
            'water_vapor': mw.water_vapor_spin.value(),
            'cloud_lwc': mw.cloud_lwc_spin.value(),
            'rain_height_km': mw.rain_height_spin.value(),
            'pol_tilt_deg': mw.pol_tilt_spin.value(),
        },
        # Legacy compat keys (from hidden widgets) - useful for flat preset structure
        'link_mode': mw.link_mode_combo.currentText(),
        'sat_type': mw.sat_type_combo.currentText(),
        'altitude_km': mw.altitude_spin.value(),
        'gs_lat': mw.gs_lat_spin.value(),
        'gs_lon': mw.gs_lon_spin.value(),
        'sat_lon': mw.sat_lon_spin.value(),
        'sat_lat': mw.sat_lat_spin.value(),
        'bandwidth_mhz': mw.bandwidth_spin.value(),
        'uplink_tx_power_dbw': mw.uplink_tx_power_spin.value(),
        'uplink_antenna_m': mw.uplink_antenna_spin.value(),
        'uplink_freq_ghz': mw.uplink_freq_spin.value(),
        'uplink_rain_rate': mw.uplink_rain_spin.value(),
        'sat_rx_gain_dbi': mw.sat_rx_gain_spin.value(),
        'sat_nf_db': mw.sat_nf_spin.value(),
        'sat_power_dbw': mw.tx_power_spin.value(),
        'sat_tx_gain_dbi': mw.tx_gain_spin.value(),
        'downlink_freq_ghz': mw.frequency_spin.value(),
        'downlink_rain_rate': mw.rain_spin.value(),
        'gs_rx_diameter_m': mw.gs_diameter_spin.value(),
        'lna_temp_k': mw.lna_temp_spin.value(),
        'modulation': mw.modulation_combo.currentText(),
        'coding': mw.coding_combo.currentText(),
        'feed_loss_db': mw.feed_loss_spin.value(),
        'pointing_loss_tx_db': mw.pointing_loss_tx_spin.value(),
        'pointing_loss_rx_db': mw.pointing_loss_rx_spin.value(),
        'pol_loss_db': mw.pol_loss_spin.value(),
        'ibo_db': mw.ibo_spin.value(),
        'obo_db': mw.obo_spin.value(),
        'hpa_type': mw.hpa_type_combo.currentText(),
        'antenna_efficiency': mw.antenna_eff_spin.value(),
        'c_im_db': mw.cim_spin.value(),
    }


def save_parameters(mw):
    """Save current parameters to a JSON file"""
    filepath, _ = QFileDialog.getSaveFileName(
        mw, "Save Parameters",
        f"link_params_{__import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        "JSON Files (*.json)")
    if not filepath:
        return

    save_data = get_current_parameters_dict(mw)

    try:
        with open(filepath, 'w') as f:
            json.dump(save_data, f, indent=2)
        mw.statusBar().showMessage(f" Parameters saved to: {filepath}")
        QMessageBox.information(mw, "Success", "Parameters saved successfully.")
    except Exception as e:
        QMessageBox.warning(mw, "Save Error", str(e))


def load_parameters(mw):
    """Load parameters from a JSON file"""
    filepath, _ = QFileDialog.getOpenFileName(
        mw, "Load Parameters", "", "JSON Files (*.json)")
    if not filepath:
        return

    try:
        with open(filepath, 'r') as f:
            params = json.load(f)

        if 'base_stations' in params:
            # New format: load objects
            mw.base_stations = [BaseStation.from_dict(d) for d in params['base_stations']]
            mw.satellite_configs = [SatelliteConfig.from_dict(d) for d in params['satellite_configs']]
            mw._refresh_combos()
            mw._refresh_hub_lists()

            gen = params.get('general', {})
            mw._rebuild_3d_visibility_panel()

            if 'selected_bs1' in params:
                idx = mw.bs1_combo.findText(params['selected_bs1'])
                if idx >= 0:
                    mw.bs1_combo.setCurrentIndex(idx)
            if 'selected_sat' in params:
                idx = mw.sat_combo.findText(params['selected_sat'])
                if idx >= 0:
                    mw.sat_combo.setCurrentIndex(idx)
            if 'selected_bs2' in params:
                idx = mw.bs2_combo.findText(params['selected_bs2'])
                if idx >= 0:
                    mw.bs2_combo.setCurrentIndex(idx)

            if 'link_mode' in gen:
                mw.link_mode_combo.setCurrentText(gen['link_mode'])
            if 'uplink_freq_ghz' in gen:
                mw.uplink_freq_spin.setValue(gen['uplink_freq_ghz'])
            if 'downlink_freq_ghz' in gen:
                mw.frequency_spin.setValue(gen['downlink_freq_ghz'])
            if 'bandwidth_mhz' in gen:
                mw.bandwidth_spin.setValue(gen['bandwidth_mhz'])
            if 'uplink_rain_rate' in gen:
                mw.uplink_rain_spin.setValue(gen['uplink_rain_rate'])
            if 'downlink_rain_rate' in gen:
                mw.rain_spin.setValue(gen['downlink_rain_rate'])
            if 'modulation' in gen:
                mw.modulation_combo.setCurrentText(gen['modulation'])
            if 'coding' in gen:
                mw.coding_combo.setCurrentText(gen['coding'])
            if 'pol_loss_db' in gen:
                mw.pol_loss_spin.setValue(gen['pol_loss_db'])
            if 'water_vapor' in gen:
                mw.water_vapor_spin.setValue(gen['water_vapor'])
            if 'cloud_lwc' in gen:
                mw.cloud_lwc_spin.setValue(gen['cloud_lwc'])
            if 'rain_height_km' in gen:
                mw.rain_height_spin.setValue(gen['rain_height_km'])
            if 'pol_tilt_deg' in gen:
                mw.pol_tilt_spin.setValue(gen['pol_tilt_deg'])
        else:
            # Legacy format
            mw._block_all_signals(True)

            _load_legacy_widgets(mw, params)

            mw._block_all_signals(False)

        mw.calculate_complete_link()
        mw.statusBar().showMessage(f" Parameters loaded from: {filepath}")
        QMessageBox.information(mw, "Success", "Parameters loaded successfully.")
    except Exception as e:
        QMessageBox.warning(mw, "Load Error", str(e))


def _load_legacy_widgets(mw, params):
    """Load legacy format parameters into hidden widgets"""
    widget_map = {
        'link_mode': mw.link_mode_combo,
        'sat_type': mw.sat_type_combo,
        'altitude_km': mw.altitude_spin,
        'gs_lat': mw.gs_lat_spin,
        'gs_lon': mw.gs_lon_spin,
        'sat_lon': mw.sat_lon_spin,
        'sat_lat': mw.sat_lat_spin,
        'bandwidth_mhz': mw.bandwidth_spin,
        'uplink_tx_power_dbw': mw.uplink_tx_power_spin,
        'uplink_antenna_m': mw.uplink_antenna_spin,
        'uplink_freq_ghz': mw.uplink_freq_spin,
        'uplink_rain_rate': mw.uplink_rain_spin,
        'sat_rx_gain_dbi': mw.sat_rx_gain_spin,
        'sat_nf_db': mw.sat_nf_spin,
        'sat_power_dbw': mw.tx_power_spin,
        'sat_tx_gain_dbi': mw.tx_gain_spin,
        'downlink_freq_ghz': mw.frequency_spin,
        'downlink_rain_rate': mw.rain_spin,
        'gs_rx_diameter_m': mw.gs_diameter_spin,
        'lna_temp_k': mw.lna_temp_spin,
        'modulation': mw.modulation_combo,
        'coding': mw.coding_combo,
        'feed_loss_db': mw.feed_loss_spin,
        'pointing_loss_tx_db': mw.pointing_loss_tx_spin,
        'pointing_loss_rx_db': mw.pointing_loss_rx_spin,
        'pol_loss_db': mw.pol_loss_spin,
        'ibo_db': mw.ibo_spin,
        'obo_db': mw.obo_spin,
        'hpa_type': mw.hpa_type_combo,
        'antenna_efficiency': mw.antenna_eff_spin,
        'c_im_db': mw.cim_spin,
    }

    for key, widget in widget_map.items():
        if key in params:
            if isinstance(widget, QComboBox):
                widget.setCurrentText(str(params[key]))
            else:
                widget.setValue(params[key])

    # Special case: pointing_loss_db sets both TX and RX
    if 'pointing_loss_db' in params:
        mw.pointing_loss_tx_spin.setValue(params['pointing_loss_db'])
        mw.pointing_loss_rx_spin.setValue(params['pointing_loss_db'])
