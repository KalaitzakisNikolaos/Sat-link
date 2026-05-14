"""Satellite beam pattern and EIRP contour calculations."""

import numpy as np
from .constants import EARTH_RADIUS, SATELLITE_TYPES, FREQUENCY_BANDS


# typical beam specs by coverage type
_BEAM_TYPES = {
    'Global':         {'diameter_km': 13000, 'gain_dBi': 19},
    'Hemispheric':    {'diameter_km': 8000,  'gain_dBi': 24},
    'Regional':       {'diameter_km': 3000,  'gain_dBi': 32},
    'Zone':           {'diameter_km': 1500,  'gain_dBi': 36},
    'Spot':           {'diameter_km': 600,   'gain_dBi': 42},
    'High-Gain Spot': {'diameter_km': 200,   'gain_dBi': 48},
}

# typical EIRP (dBW) by orbit type and band
_EIRP_TABLE = {
    'LEO': {'L': 30, 'S': 35, 'C': 40, 'X': 42, 'Ku': 45, 'Ka': 48},
    'MEO': {'L': 35, 'S': 40, 'C': 45, 'X': 48, 'Ku': 50, 'Ka': 52},
    'GEO': {'L': 40, 'S': 45, 'C': 48, 'X': 50, 'Ku': 52, 'Ka': 55},
    'HEO': {'L': 38, 'S': 43, 'C': 46, 'X': 48, 'Ku': 51, 'Ka': 53},
}


class BeamPattern:
    """antenna beam pattern calculator for a given sat type / freq band."""

    # keep as class attr so external code can still read it
    BEAM_TYPES = _BEAM_TYPES

    def __init__(self, satellite_type, frequency_band, beam_type='Regional'):
        self.satellite_type = satellite_type
        self.frequency_band = frequency_band
        self.beam_type = beam_type
        self.altitude_km = SATELLITE_TYPES[satellite_type]['typical_altitude']
        freq_data = FREQUENCY_BANDS[frequency_band]
        self.frequency_ghz = freq_data['center']
        self.wavelength_m = 0.3 / self.frequency_ghz   # c / f

    def calculate_beamwidth(self, antenna_diameter_m):
        """3dB beamwidth in degrees: 70*lambda/D"""
        return 70 * self.wavelength_m / antenna_diameter_m

    def calculate_antenna_gain(self, antenna_diameter_m, efficiency=0.65):
        """peak gain in dBi"""
        g = efficiency * (np.pi * antenna_diameter_m / self.wavelength_m) ** 2
        return 10 * np.log10(g)

    def beam_pattern_2d(self, theta_deg, beamwidth_deg):
        """gaussian beam envelope, returns values in 0..1"""
        r = theta_deg / beamwidth_deg
        return np.exp(-2.77 * r**2)

    def calculate_footprint(self, beam_center_lat, beam_center_lon,
                            beam_diameter_km, num_points=100):
        """returns (lats, lons) arrays tracing the -3dB contour on the ground"""
        ang = np.degrees(beam_diameter_km / (2 * EARTH_RADIUS))
        theta = np.linspace(0, 2*np.pi, num_points)
        lats = beam_center_lat + ang * np.sin(theta)
        lons = beam_center_lon + ang * np.cos(theta) / np.cos(np.radians(beam_center_lat))
        return lats, lons

    def calculate_eirp_contours(self, center_lat, center_lon,
                                peak_eirp_dbw, num_contours=5,
                                grid_res=200):
        """EIRP map and contour levels over a lat/lon grid around beam center"""
        info = _BEAM_TYPES.get(self.beam_type, _BEAM_TYPES['Regional'])
        diam_km = info['diameter_km']

        # beamwidth from footprint size at orbit altitude
        bw = np.degrees(2 * np.arcsin(diam_km / (2 * (EARTH_RADIUS + self.altitude_km))))

        lat_ext = bw * 1.5
        lon_ext = lat_ext / np.cos(np.radians(center_lat))
        lats = np.linspace(center_lat - lat_ext, center_lat + lat_ext, grid_res)
        lons = np.linspace(center_lon - lon_ext, center_lon + lon_ext, grid_res)
        lon_g, lat_g = np.meshgrid(lons, lats)

        dlat = lat_g - center_lat
        dlon = (lon_g - center_lon) * np.cos(np.radians(center_lat))
        dist = np.sqrt(dlat**2 + dlon**2)

        pattern = self.beam_pattern_2d(dist, bw)
        eirp = peak_eirp_dbw + 10 * np.log10(pattern + 1e-10)

        levels = np.linspace(peak_eirp_dbw - 12, peak_eirp_dbw, num_contours)

        return {
            'lats': lats, 'lons': lons,
            'lat_grid': lat_g, 'lon_grid': lon_g,
            'eirp_grid': eirp,
            'contour_levels': levels,
            'peak_eirp': peak_eirp_dbw,
            'beam_center': (center_lat, center_lon),
            'beam_diameter_km': diam_km,
            'beamwidth_deg': bw,
        }

    def calculate_multispot_beams(self, beam_centers, peak_eirp_dbw):
        return [self.calculate_eirp_contours(lat, lon, peak_eirp_dbw)
                for lat, lon in beam_centers]

    def estimate_peak_eirp(self, transmit_power_dbw, antenna_diameter_m):
        """Ptx + Gtx"""
        return transmit_power_dbw + self.calculate_antenna_gain(antenna_diameter_m)

    def get_typical_eirp(self):
        band = self.frequency_band.split('-')[0] if '-' in self.frequency_band else self.frequency_band
        return _EIRP_TABLE.get(self.satellite_type, {}).get(band, 50.0)
