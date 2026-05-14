"""Ground station / base station configuration."""

import json


class BaseStation:
    """ground station with TX and RX antennas for uplink/downlink."""

    PRESETS = {
        'Athens GS': {
            'name': 'Athens GS',
            'latitude': 37.9755648,
            'longitude': 23.7348324,
            'height_km': 0.0,
            'tx_power_dbw': 10.0,
            'tx_antenna_diameter_m': 2.4,
            'rx_antenna_diameter_m': 1.2,
            'antenna_efficiency': 0.6,
            'feed_loss_db': 0.5,
            'pointing_loss_tx_db': 0.3,
            'pointing_loss_rx_db': 0.2,
            'lna_temp_k': 50.0,
        },
        'London Teleport': {
            'name': 'London Teleport',
            'latitude': 51.5074,
            'longitude': -0.1278,
            'height_km': 0.01,
            'tx_power_dbw': 15.0,
            'tx_antenna_diameter_m': 3.7,
            'rx_antenna_diameter_m': 3.7,
            'antenna_efficiency': 0.65,
            'feed_loss_db': 0.4,
            'pointing_loss_tx_db': 0.2,
            'pointing_loss_rx_db': 0.15,
            'lna_temp_k': 40.0,
        },
        'VSAT Terminal': {
            'name': 'VSAT Terminal',
            'latitude': 40.0,
            'longitude': 20.0,
            'height_km': 0.0,
            'tx_power_dbw': 4.0,
            'tx_antenna_diameter_m': 1.2,
            'rx_antenna_diameter_m': 1.2,
            'antenna_efficiency': 0.55,
            'feed_loss_db': 0.6,
            'pointing_loss_tx_db': 0.5,
            'pointing_loss_rx_db': 0.3,
            'lna_temp_k': 75.0,
        },
        'Broadcast Uplink': {
            'name': 'Broadcast Uplink',
            'latitude': 48.8566,   # Paris
            'longitude': 2.3522,
            'height_km': 0.05,
            'tx_power_dbw': 20.0,
            'tx_antenna_diameter_m': 9.0,
            'rx_antenna_diameter_m': 4.5,
            'antenna_efficiency': 0.7,
            'feed_loss_db': 0.3,
            'pointing_loss_tx_db': 0.1,
            'pointing_loss_rx_db': 0.1,
            'lna_temp_k': 35.0,
        },
    }

    def __init__(self, name="Default GS", latitude=37.9755648, longitude=23.7348324,
                 height_km=0.0, tx_power_dbw=10.0, tx_antenna_diameter_m=2.4,
                 rx_antenna_diameter_m=1.2, antenna_efficiency=0.6,
                 feed_loss_db=0.5, pointing_loss_tx_db=0.3, pointing_loss_rx_db=0.2,
                 lna_temp_k=50.0):
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.height_km = height_km
        self.tx_power_dbw = tx_power_dbw
        self.tx_antenna_diameter_m = tx_antenna_diameter_m
        self.rx_antenna_diameter_m = rx_antenna_diameter_m
        self.antenna_efficiency = antenna_efficiency
        self.feed_loss_db = feed_loss_db
        self.pointing_loss_tx_db = pointing_loss_tx_db
        self.pointing_loss_rx_db = pointing_loss_rx_db
        self.lna_temp_k = lna_temp_k

    def to_dict(self):
        return {k: getattr(self, k) for k in (
            'name', 'latitude', 'longitude', 'height_km',
            'tx_power_dbw', 'tx_antenna_diameter_m', 'rx_antenna_diameter_m',
            'antenna_efficiency', 'feed_loss_db',
            'pointing_loss_tx_db', 'pointing_loss_rx_db', 'lna_temp_k')}

    @classmethod
    def from_dict(cls, data):
        return cls(**data)

    @classmethod
    def from_preset(cls, preset_name):
        if preset_name not in cls.PRESETS:
            raise ValueError(f"Unknown preset: {preset_name}")
        return cls(**cls.PRESETS[preset_name])

    def __str__(self):
        return f"{self.name} ({self.latitude:.2f}°, {self.longitude:.2f}°)"

    def __repr__(self):
        return f"BaseStation('{self.name}', lat={self.latitude:.4f}, lon={self.longitude:.4f})"
