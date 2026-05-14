"""
Satellite configuration model.

Encapsulates all parameters related to a satellite including
orbital position, antenna gains, and transponder chain configuration.
"""

import json


class Satellite:
    """Represents a satellite configuration with orbital and transponder parameters.

    Stores all static satellite parameters for link budget calculations.
    This is separate from SatelliteOrbit (in orbit.py) which handles dynamics.
    """

    # Preset satellite configurations
    PRESETS = {
        'Hotbird 13E': {
            'name': 'Hotbird 13E',
            'sat_type': 'GEO',
            'altitude_km': 35786,
            'latitude': 0.0,
            'longitude': 13.0,
            'band': 'Ku-band',
            'uplink_freq_ghz': 14.25,
            'downlink_freq_ghz': 11.725,
            'bandwidth_mhz': 36.0,
            'rx_gain_dbi': 30.0,
            'noise_figure_db': 2.0,
            'tx_power_dbw': 10.0,
            'tx_gain_dbi': 32.0,
            'transponder_preset': 'Ku-band_standard',
            'hpa_type': 'TWTA',
            'input_backoff_db': 1.0,
            'lna_gain_db': 30.0,
            'lna_nf_db': 1.2,
            'mixer_gain_db': -6.0,
            'mixer_nf_db': 8.0,
            'if_gain_db': 30.0,
            'pa_gain_db': 20.0,
            'pa_psat_dbw': 10.0,
        },
        'Astra 19.2E': {
            'name': 'Astra 19.2E',
            'sat_type': 'GEO',
            'altitude_km': 35786,
            'latitude': 0.0,
            'longitude': 19.2,
            'band': 'Ku-band',
            'uplink_freq_ghz': 14.25,
            'downlink_freq_ghz': 11.725,
            'bandwidth_mhz': 36.0,
            'rx_gain_dbi': 32.0,
            'noise_figure_db': 1.8,
            'tx_power_dbw': 12.0,
            'tx_gain_dbi': 34.0,
            'transponder_preset': 'Ku-band_standard',
            'hpa_type': 'TWTA',
            'input_backoff_db': 1.0,
            'lna_gain_db': 32.0,
            'lna_nf_db': 1.0,
            'mixer_gain_db': -6.0,
            'mixer_nf_db': 7.0,
            'if_gain_db': 30.0,
            'pa_gain_db': 22.0,
            'pa_psat_dbw': 12.0,
        },
        'Eutelsat 7E': {
            'name': 'Eutelsat 7E',
            'sat_type': 'GEO',
            'altitude_km': 35786,
            'latitude': 0.0,
            'longitude': 7.0,
            'band': 'Ku-band',
            'uplink_freq_ghz': 14.25,
            'downlink_freq_ghz': 11.725,
            'bandwidth_mhz': 36.0,
            'rx_gain_dbi': 31.0,
            'noise_figure_db': 2.0,
            'tx_power_dbw': 11.0,
            'tx_gain_dbi': 33.0,
            'transponder_preset': 'Ku-band_standard',
            'hpa_type': 'TWTA',
            'input_backoff_db': 1.0,
            'lna_gain_db': 30.0,
            'lna_nf_db': 1.2,
            'mixer_gain_db': -6.0,
            'mixer_nf_db': 8.0,
            'if_gain_db': 30.0,
            'pa_gain_db': 20.0,
            'pa_psat_dbw': 11.0,
        },
        'LEO IoT Sat': {
            'name': 'LEO IoT Sat',
            'sat_type': 'LEO',
            'altitude_km': 600,
            'latitude': 0.0,
            'longitude': 0.0,
            'band': 'L-band',
            'uplink_freq_ghz': 1.6435,
            'downlink_freq_ghz': 1.542,
            'bandwidth_mhz': 4.0,
            'rx_gain_dbi': 8.0,
            'noise_figure_db': 3.0,
            'tx_power_dbw': 0.0,
            'tx_gain_dbi': 6.0,
            'transponder_preset': 'L-band_mobile',
            'hpa_type': 'SSPA',
            'input_backoff_db': 3.0,
            'lna_gain_db': 25.0,
            'lna_nf_db': 2.5,
            'mixer_gain_db': -8.0,
            'mixer_nf_db': 10.0,
            'if_gain_db': 25.0,
            'pa_gain_db': 15.0,
            'pa_psat_dbw': 2.0,
        },
        'LEO Broadband': {
            'name': 'LEO Broadband',
            'sat_type': 'LEO',
            'altitude_km': 550,
            'latitude': 0.0,
            'longitude': 0.0,
            'band': 'Ku-band',
            'uplink_freq_ghz': 14.25,
            'downlink_freq_ghz': 11.725,
            'bandwidth_mhz': 36.0,
            'rx_gain_dbi': 32.0,
            'noise_figure_db': 2.0,
            'tx_power_dbw': 5.0,
            'tx_gain_dbi': 32.0,
            'transponder_preset': 'Ku-band_standard',
            'hpa_type': 'SSPA',
            'input_backoff_db': 2.0,
            'lna_gain_db': 28.0,
            'lna_nf_db': 1.5,
            'mixer_gain_db': -6.0,
            'mixer_nf_db': 8.0,
            'if_gain_db': 28.0,
            'pa_gain_db': 18.0,
            'pa_psat_dbw': 5.0,
        },
        'MEO Navigation': {
            'name': 'MEO Navigation',
            'sat_type': 'MEO',
            'altitude_km': 20200,
            'latitude': 0.0,
            'longitude': 0.0,
            'band': 'L-band',
            'uplink_freq_ghz': 1.6435,
            'downlink_freq_ghz': 1.542,
            'bandwidth_mhz': 4.0,
            'rx_gain_dbi': 13.0,
            'noise_figure_db': 3.0,
            'tx_power_dbw': 6.0,
            'tx_gain_dbi': 13.0,
            'transponder_preset': 'L-band_mobile',
            'hpa_type': 'SSPA',
            'input_backoff_db': 2.0,
            'lna_gain_db': 22.0,
            'lna_nf_db': 2.0,
            'mixer_gain_db': -7.0,
            'mixer_nf_db': 9.0,
            'if_gain_db': 25.0,
            'pa_gain_db': 16.0,
            'pa_psat_dbw': 6.0,
        },
    }

    def __init__(self, name="Default Sat", sat_type="GEO", altitude_km=35786,
                 latitude=0.0, longitude=13.0,
                 band="Ku-band", uplink_freq_ghz=14.25,
                 downlink_freq_ghz=11.725, bandwidth_mhz=36.0,
                 rx_gain_dbi=30.0,
                 noise_figure_db=2.0, tx_power_dbw=10.0, tx_gain_dbi=32.0,
                 transponder_preset="Ku-band_standard", hpa_type="TWTA",
                 input_backoff_db=1.0, lna_gain_db=30.0, lna_nf_db=1.2,
                 mixer_gain_db=-6.0, mixer_nf_db=8.0, if_gain_db=30.0,
                 pa_gain_db=20.0, pa_psat_dbw=10.0):
        """Initialize a Satellite.

        Args:
            name: Unique identifier for this satellite
            sat_type: Satellite orbit type (GEO, LEO, MEO, HEO)
            altitude_km: Orbital altitude in km
            latitude: Sub-satellite point latitude (0 for GEO)
            longitude: Orbital longitude position in degrees
            band: Frequency band (L-band, S-band, C-band, X-band, Ku-band, Ka-band, Q-band, V-band)
            uplink_freq_ghz: Uplink center frequency in GHz (ITU-R allocated)
            downlink_freq_ghz: Downlink center frequency in GHz (ITU-R allocated)
            bandwidth_mhz: Transponder bandwidth in MHz
            rx_gain_dbi: Satellite receive antenna gain in dBi
            noise_figure_db: Satellite receiver noise figure in dB
            tx_power_dbw: Satellite transmit power in dBW
            tx_gain_dbi: Satellite transmit antenna gain in dBi
            transponder_preset: Transponder preset name
            hpa_type: HPA type (TWTA, SSPA, Linearized)
            input_backoff_db: Input backoff in dB
            lna_gain_db: LNA gain in dB
            lna_nf_db: LNA noise figure in dB
            mixer_gain_db: Mixer gain in dB (typically negative)
            mixer_nf_db: Mixer noise figure in dB
            if_gain_db: IF amplifier gain in dB
            pa_gain_db: Power amplifier gain in dB
            pa_psat_dbw: PA saturated output power in dBW
        """
        self.name = name
        self.sat_type = sat_type
        self.altitude_km = altitude_km
        self.latitude = latitude
        self.longitude = longitude
        self.band = band
        self.uplink_freq_ghz = uplink_freq_ghz
        self.downlink_freq_ghz = downlink_freq_ghz
        self.bandwidth_mhz = bandwidth_mhz
        self.rx_gain_dbi = rx_gain_dbi
        self.noise_figure_db = noise_figure_db
        self.tx_power_dbw = tx_power_dbw
        self.tx_gain_dbi = tx_gain_dbi
        self.transponder_preset = transponder_preset
        self.hpa_type = hpa_type
        self.input_backoff_db = input_backoff_db
        self.lna_gain_db = lna_gain_db
        self.lna_nf_db = lna_nf_db
        self.mixer_gain_db = mixer_gain_db
        self.mixer_nf_db = mixer_nf_db
        self.if_gain_db = if_gain_db
        self.pa_gain_db = pa_gain_db
        self.pa_psat_dbw = pa_psat_dbw

    def to_dict(self):
        """Serialize to dictionary."""
        return {
            'name': self.name,
            'sat_type': self.sat_type,
            'altitude_km': self.altitude_km,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'band': self.band,
            'uplink_freq_ghz': self.uplink_freq_ghz,
            'downlink_freq_ghz': self.downlink_freq_ghz,
            'bandwidth_mhz': self.bandwidth_mhz,
            'rx_gain_dbi': self.rx_gain_dbi,
            'noise_figure_db': self.noise_figure_db,
            'tx_power_dbw': self.tx_power_dbw,
            'tx_gain_dbi': self.tx_gain_dbi,
            'transponder_preset': self.transponder_preset,
            'hpa_type': self.hpa_type,
            'input_backoff_db': self.input_backoff_db,
            'lna_gain_db': self.lna_gain_db,
            'lna_nf_db': self.lna_nf_db,
            'mixer_gain_db': self.mixer_gain_db,
            'mixer_nf_db': self.mixer_nf_db,
            'if_gain_db': self.if_gain_db,
            'pa_gain_db': self.pa_gain_db,
            'pa_psat_dbw': self.pa_psat_dbw,
        }

    @classmethod
    def from_dict(cls, data):
        """Deserialize from dictionary."""
        return cls(**data)

    @classmethod
    def from_preset(cls, preset_name):
        """Create a Satellite from a preset configuration."""
        if preset_name in cls.PRESETS:
            return cls(**cls.PRESETS[preset_name])
        raise ValueError(f"Unknown preset: {preset_name}")

    def __str__(self):
        return f"{self.name} ({self.sat_type} @ {self.longitude:.1f}°E, {self.altitude_km:.0f} km)"

    def __repr__(self):
        return (f"Satellite(name='{self.name}', type={self.sat_type}, "
                f"alt={self.altitude_km}km, lon={self.longitude}°)")
