"""
Presets module — predefined satellite scenario presets and user preset management.
"""
import os
import json
import logging
from PyQt5.QtWidgets import QComboBox, QInputDialog, QMessageBox, QMenu
from models.constants import SATELLITE_TYPES
from models.base_station import BaseStation
from models.satellite import Satellite as SatelliteConfig
from models.orbit import create_satellite_from_type
from gui.utils.app_paths import get_user_data_dir

# Setup logging
logger = logging.getLogger(__name__)

USER_PRESETS_FILE = "user_presets.json"

# Built-in presets
BUILTIN_PRESETS = {
    'geo_dth': {
        'link_mode': 'Full Link', 'sat_type': 'GEO', 'altitude_km': 35786,
        'gs_lat': 38.0, 'gs_lon': 23.7, 'sat_lon': 13.0, 'sat_lat': 0.0,
        'band': 'Ku-band', 'bandwidth_mhz': 36.0,
        'uplink_tx_power_dbw': 17.0, 'uplink_antenna_m': 3.7,
        'uplink_freq_ghz': 14.0, 'uplink_rain_rate': 0,
        'sat_rx_gain_dbi': 30.0, 'sat_nf_db': 2.0,
        'sat_power_dbw': 12.0, 'sat_tx_gain_dbi': 34.0,
        'downlink_freq_ghz': 11.7, 'downlink_rain_rate': 0,
        'gs_rx_diameter_m': 0.6, 'lna_temp_k': 55,
        'modulation': 'QPSK', 'coding': 'LDPC (R=3/4)',
    },
    'geo_vsat': {
        'link_mode': 'Full Link', 'sat_type': 'GEO', 'altitude_km': 35786,
        'gs_lat': 40.0, 'gs_lon': -3.7, 'sat_lon': -30.0, 'sat_lat': 0.0,
        'band': 'C-band', 'bandwidth_mhz': 36.0,
        'uplink_tx_power_dbw': 7.0, 'uplink_antenna_m': 1.8,
        'uplink_freq_ghz': 6.0, 'uplink_rain_rate': 0,
        'sat_rx_gain_dbi': 28.0, 'sat_nf_db': 2.5,
        'sat_power_dbw': 8.0, 'sat_tx_gain_dbi': 28.0,
        'downlink_freq_ghz': 4.0, 'downlink_rain_rate': 0,
        'gs_rx_diameter_m': 1.8, 'lna_temp_k': 40,
        'modulation': 'QPSK', 'coding': 'LDPC (R=1/2)',
    },
    'geo_ka_hts': {
        'link_mode': 'Full Link', 'sat_type': 'GEO', 'altitude_km': 35786,
        'gs_lat': 48.8, 'gs_lon': 2.3, 'sat_lon': 9.0, 'sat_lat': 0.0,
        'band': 'Ka-band', 'bandwidth_mhz': 250.0,
        'uplink_tx_power_dbw': 13.0, 'uplink_antenna_m': 0.75,
        'uplink_freq_ghz': 30.0, 'uplink_rain_rate': 0,
        'sat_rx_gain_dbi': 42.0, 'sat_nf_db': 3.0,
        'sat_power_dbw': 15.0, 'sat_tx_gain_dbi': 42.0,
        'downlink_freq_ghz': 20.0, 'downlink_rain_rate': 0,
        'gs_rx_diameter_m': 0.75, 'lna_temp_k': 120,
        'modulation': '16APSK', 'coding': 'LDPC (R=3/4)',
    },
    'leo_iot': {
        'link_mode': 'Full Link', 'sat_type': 'LEO', 'altitude_km': 600,
        'gs_lat': 52.5, 'gs_lon': 13.4, 'sat_lon': 13.4, 'sat_lat': 52.5,
        'band': 'L-band', 'bandwidth_mhz': 1.0,
        'uplink_tx_power_dbw': -3.0, 'uplink_antenna_m': 0.5,
        'uplink_freq_ghz': 1.6, 'uplink_rain_rate': 0,
        'sat_rx_gain_dbi': 12.0, 'sat_nf_db': 3.0,
        'sat_power_dbw': 0.0, 'sat_tx_gain_dbi': 12.0,
        'downlink_freq_ghz': 1.5, 'downlink_rain_rate': 0,
        'gs_rx_diameter_m': 0.5, 'lna_temp_k': 100,
        'modulation': 'BPSK', 'coding': 'LDPC (R=1/2)',
    },
    'leo_broadband': {
        'link_mode': 'Full Link', 'sat_type': 'LEO', 'altitude_km': 550,
        'gs_lat': 37.8, 'gs_lon': -122.4, 'sat_lon': -122.4, 'sat_lat': 37.8,
        'band': 'Ku-band', 'bandwidth_mhz': 240.0,
        'uplink_tx_power_dbw': 10.0, 'uplink_antenna_m': 0.5,
        'uplink_freq_ghz': 14.0, 'uplink_rain_rate': 0,
        'sat_rx_gain_dbi': 32.0, 'sat_nf_db': 2.0,
        'sat_power_dbw': 5.0, 'sat_tx_gain_dbi': 32.0,
        'downlink_freq_ghz': 12.0, 'downlink_rain_rate': 0,
        'gs_rx_diameter_m': 0.5, 'lna_temp_k': 75,
        'modulation': '8PSK', 'coding': 'LDPC (R=3/4)',
    },
    'meo_nav': {
        'link_mode': 'Downlink Only', 'sat_type': 'MEO', 'altitude_km': 20200,
        'gs_lat': 39.0, 'gs_lon': -77.0, 'sat_lon': -77.0, 'sat_lat': 39.0,
        'band': 'L-band', 'bandwidth_mhz': 20.0,
        'uplink_tx_power_dbw': 10.0, 'uplink_antenna_m': 1.0,
        'uplink_freq_ghz': 1.6, 'uplink_rain_rate': 0,
        'sat_rx_gain_dbi': 13.0, 'sat_nf_db': 3.0,
        'sat_power_dbw': 6.0, 'sat_tx_gain_dbi': 13.0,
        'downlink_freq_ghz': 1.575, 'downlink_rain_rate': 0,
        'gs_rx_diameter_m': 0.3, 'lna_temp_k': 50,
        'modulation': 'BPSK', 'coding': 'Turbo (R=1/2)',
    },
}

BUILTIN_DISPLAY_NAMES = {
    'geo_dth': 'GEO DTH Broadcasting',
    'geo_vsat': 'GEO VSAT Enterprise',
    'geo_ka_hts': 'GEO Ka-band HTS',
    'leo_iot': 'LEO IoT/M2M',
    'leo_broadband': 'LEO Broadband',
    'meo_nav': 'MEO Navigation',
}


def _get_user_presets_path():
    """Get path to user presets file"""
    return os.path.join(get_user_data_dir(), USER_PRESETS_FILE)


def load_user_presets():
    """Load user presets from JSON file"""
    path = _get_user_presets_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load user presets: {e}")
        return {}


def save_user_presets_to_disk(presets):
    """Save user presets dict to JSON file"""
    path = _get_user_presets_path()
    try:
        with open(path, 'w') as f:
            json.dump(presets, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save user presets: {e}")


def get_all_presets():
    """Return merged dictionary of builtin and user presets."""
    user_presets = load_user_presets()
    # User presets override builtin ones if names clash (though UI should prevent name reuse ideally)
    return {**BUILTIN_PRESETS, **user_presets}


def save_current_as_preset(mw):
    """Save current configuration as a new named preset."""
    from gui.utils.save_load import get_current_parameters_dict

    name, ok = QInputDialog.getText(mw, "Save Preset", "Enter name for new preset:")
    if not ok or not name.strip():
        return

    preset_name = name.strip()
    
    # Get current params
    params = get_current_parameters_dict(mw)
    
    # Convert complex structure to flat preset structure simplified for reuse
    # Note: Presets traditionally store 'general' keys flatly. 
    # We will try to map the detailed save structure back to a flat structure 
    # compatible with load_preset logic below.
    
    flat_preset = {}
    general = params.get('general', {})
    
    # Copy general fields
    flat_preset.update(general)
    
    # Add vital fields often used in presets
    flat_preset['link_mode'] = general.get('link_mode', 'Full Link')
    flat_preset['sat_type'] = mw.sat_type_combo.currentText()
    flat_preset['altitude_km'] = mw.altitude_spin.value()
    flat_preset['gs_lat'] = mw.gs_lat_spin.value()
    flat_preset['gs_lon'] = mw.gs_lon_spin.value()
    flat_preset['sat_lon'] = mw.sat_lon_spin.value()
    flat_preset['sat_lat'] = mw.sat_lat_spin.value()
    
    # Store sat/bs specific info if needed (presets usually imply generic templates)
    # But user might want to save current specific hardware
    flat_preset['uplink_tx_power_dbw'] = mw.uplink_tx_power_spin.value()
    flat_preset['uplink_antenna_m'] = mw.uplink_antenna_spin.value()
    flat_preset['sat_rx_gain_dbi'] = mw.sat_rx_gain_spin.value()
    flat_preset['sat_nf_db'] = mw.sat_nf_spin.value()
    flat_preset['sat_power_dbw'] = mw.tx_power_spin.value()
    flat_preset['sat_tx_gain_dbi'] = mw.tx_gain_spin.value()
    flat_preset['gs_rx_diameter_m'] = mw.gs_diameter_spin.value()
    flat_preset['lna_temp_k'] = mw.lna_temp_spin.value()
    
    # Hub items (stations/sats) are usually part of the full save, 
    # but for "Preset" we might want to just snapshot the active link.
    # We will also store the full station/sat list if useful, but load_preset 
    # currently focuses on applying settings to active widgets.
    # Let's keep it simple: Snapshot the active link settings.
    
    # Save to user presets
    user_presets = load_user_presets()
    user_presets[preset_name] = flat_preset
    save_user_presets_to_disk(user_presets)
    
    QMessageBox.information(mw, "Preset Saved", f"Preset '{preset_name}' saved successfully!")
    
    # Refresh menu
    from gui.panels.header import rebuild_presets_menu
    rebuild_presets_menu(mw)


def delete_user_preset(mw, preset_name):
    """Delete a user preset."""
    user_presets = load_user_presets()
    if preset_name in user_presets:
        del user_presets[preset_name]
        save_user_presets_to_disk(user_presets)
        QMessageBox.information(mw, "Preset Deleted", f"Preset '{preset_name}' deleted successfully.")
        
        # Refresh menu
        from gui.panels.header import rebuild_presets_menu
        rebuild_presets_menu(mw)


def load_preset(mw, preset_name, is_user_preset=False):
    """Load a predefined scenario preset"""
    all_presets = get_all_presets()
    
    if preset_name not in all_presets:
        QMessageBox.warning(mw, "Load Error", f"Preset '{preset_name}' not found.")
        return

    preset = all_presets[preset_name]
    mw._block_all_signals(True)

    spinner_map = {
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
    }

    # Apply values
    for key, value in preset.items():
        widget = spinner_map.get(key)
        if widget:
            if isinstance(widget, QComboBox):
                # Check if item exists before setting
                if widget.findText(str(value)) >= 0:
                    widget.setCurrentText(str(value))
            else:
                widget.setValue(float(value))

    mw._block_all_signals(False)

    # Update satellite object if type changed
    sat_type = preset.get('sat_type', 'GEO')
    if sat_type in SATELLITE_TYPES:
        mw.satellite = create_satellite_from_type(sat_type)

    # Add preset as BaseStation and SatelliteConfig in the Hub tab
    if is_user_preset:
        display_name = preset_name
    else:
        display_name = BUILTIN_DISPLAY_NAMES.get(preset_name, preset_name)

    # Clear previous selections so only the preset remains
    mw.base_stations.clear()
    mw.satellite_configs.clear()

    # Create BaseStation from preset
    bs_name = f"{display_name} GS"
    bs_data = {
        'name': bs_name,
        'latitude': float(preset.get('gs_lat', 0.0)),
        'longitude': float(preset.get('gs_lon', 0.0)),
        'height_km': 0.0,
        'tx_power_dbw': float(preset.get('uplink_tx_power_dbw', 10.0)),
        'tx_antenna_diameter_m': float(preset.get('uplink_antenna_m', 2.4)),
        'rx_antenna_diameter_m': float(preset.get('gs_rx_diameter_m', 1.2)),
        'antenna_efficiency': 0.6,
        'feed_loss_db': 0.5,
        'pointing_loss_tx_db': 0.3,
        'pointing_loss_rx_db': 0.2,
        'lna_temp_k': float(preset.get('lna_temp_k', 50.0)),
    }
    mw.base_stations.append(BaseStation(**bs_data))

    # Create SatelliteConfig from preset
    sat_name = display_name if is_user_preset else display_name.replace("GEO ", "").replace("LEO ", "").replace("MEO ", "") + " Sat"
    sat_data = {
        'name': sat_name,
        'sat_type': preset.get('sat_type', 'GEO'),
        'altitude_km': float(preset.get('altitude_km', 35786)),
        'latitude': float(preset.get('sat_lat', 0.0)),
        'longitude': float(preset.get('sat_lon', 0.0)),
        'band': preset.get('band', 'Ku-band'),
        'uplink_freq_ghz': float(preset.get('uplink_freq_ghz', 14.0)),
        'downlink_freq_ghz': float(preset.get('downlink_freq_ghz', 12.0)),
        'bandwidth_mhz': float(preset.get('bandwidth_mhz', 36.0)),
        'rx_gain_dbi': float(preset.get('sat_rx_gain_dbi', 30.0)),
        'noise_figure_db': float(preset.get('sat_nf_db', 2.0)),
        'tx_power_dbw': float(preset.get('sat_power_dbw', 10.0)),
        'tx_gain_dbi': float(preset.get('sat_tx_gain_dbi', 32.0)),
    }
    mw.satellite_configs.append(SatelliteConfig(**sat_data))

    # Refresh UI
    mw._refresh_combos()
    if hasattr(mw, 'bs_hub_list_layout'):
        mw._refresh_hub_lists()

    # Select the newly created/updated items
    bs_idx = mw.bs1_combo.findText(bs_name)
    if bs_idx >= 0:
        mw.bs1_combo.setCurrentIndex(bs_idx)
        mw.bs2_combo.setCurrentIndex(bs_idx)
        
    sat_idx = mw.sat_combo.findText(sat_name)
    if sat_idx >= 0:
        mw.sat_combo.setCurrentIndex(sat_idx)

    mw.calculate_complete_link()
    mw.statusBar().showMessage(f" Preset loaded: {display_name}")
    QMessageBox.information(mw, "Preset Loaded", f"Successfully loaded preset: {display_name}")
