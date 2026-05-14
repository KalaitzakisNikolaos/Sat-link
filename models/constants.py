"""
Physical and RF Constants for Satellite Communications
Based on ITU-R standards and scientific literature
"""

import numpy as np

# Physical Constants
C_LIGHT = 299792458.0  # Speed of light in m/s
BOLTZMANN = 1.380649e-23  # Boltzmann constant in J/K
EARTH_RADIUS = 6371.0  # Earth mean radius in km (IUGG)
EARTH_MU = 398600.4418  # Earth gravitational parameter km^3/s^2

# WGS-84 Ellipsoid Parameters (NIMA TR8350.2, 3rd Edition)
EARTH_SEMI_MAJOR = 6378.137  # WGS-84 semi-major axis (equatorial radius) in km
EARTH_SEMI_MINOR = 6356.752314245  # WGS-84 semi-minor axis (polar radius) in km
EARTH_FLATTENING = 1.0 / 298.257223563  # WGS-84 flattening
EARTH_ECCENTRICITY_SQ = 2 * EARTH_FLATTENING - EARTH_FLATTENING**2  # First eccentricity squared

# Earth Rotation Rate (IERS Conventions 2010)
EARTH_ROTATION_RATE = 7.2921159e-5  # rad/s (sidereal)

# J2 Zonal Harmonic Coefficient (EGM-96 / WGS-84)
# Source: NIMA TR8350.2, Vallado "Fundamentals of Astrodynamics" Table 8-1
EARTH_J2 = 1.08263e-3  # Dominant oblateness perturbation

# Atmospheric Drag Reference Parameters (CIRA-72 / US Standard Atmosphere 1976)
# Scale height model: rho = rho0 * exp(-(h - h0) / H)
ATMOSPHERIC_DENSITY_MODEL = {
    # (alt_min_km, alt_max_km): {'rho0': kg/m^3, 'h0': km, 'H': scale_height_km}
    (0, 100):    {'rho0': 1.225, 'h0': 0, 'H': 8.5},
    (100, 200):  {'rho0': 5.297e-7, 'h0': 100, 'H': 27.0},
    (200, 300):  {'rho0': 2.196e-10, 'h0': 200, 'H': 37.5},
    (300, 400):  {'rho0': 7.370e-12, 'h0': 300, 'H': 45.5},
    (400, 500):  {'rho0': 4.297e-13, 'h0': 400, 'H': 53.5},
    (500, 600):  {'rho0': 3.396e-14, 'h0': 500, 'H': 62.0},
    (600, 800):  {'rho0': 3.500e-15, 'h0': 600, 'H': 71.0},
    (800, 1000): {'rho0': 9.518e-17, 'h0': 800, 'H': 88.7},
}

# Frequency Bands (GHz) - ITU Radio Regulations
FREQUENCY_BANDS = {
    'L-band': {'min': 1.0, 'max': 2.0, 'center': 1.5},
    'S-band': {'min': 2.0, 'max': 4.0, 'center': 3.0},
    'C-band': {'min': 4.0, 'max': 8.0, 'center': 6.0},
    'X-band': {'min': 8.0, 'max': 12.0, 'center': 10.0},
    'Ku-band': {'min': 12.0, 'max': 18.0, 'center': 14.0},
    'K-band': {'min': 18.0, 'max': 27.0, 'center': 22.5},
    'Ka-band': {'min': 27.0, 'max': 40.0, 'center': 30.0},
    'Q-band': {'min': 33.0, 'max': 50.0, 'center': 40.0},
    'V-band': {'min': 50.0, 'max': 75.0, 'center': 60.0},
}

# --- Satellite band allocations (ITU-R frequency assignments) ---------------

SATELLITE_BAND_ALLOCATIONS = {
    'L-band': {
        'name': 'L-band (MSS)',
        # ITU-R Radio Regulations Art.5, footnotes 5.351A, 5.353A
        # Inmarsat, Iridium, Thuraya — Mobile Satellite Service
        'uplink_min_ghz': 1.6265,
        'uplink_max_ghz': 1.6605,
        'uplink_center_ghz': 1.6435,
        'downlink_min_ghz': 1.525,
        'downlink_max_ghz': 1.559,
        'downlink_center_ghz': 1.542,
        'total_bandwidth_mhz': 34.0,
        'typical_transponder_bw_mhz': 4.0,      # Narrow-band mobile channels
        'services': 'MSS (Mobile Satellite Service)',
        'examples': 'Inmarsat, Iridium, Thuraya, GPS L1',
    },
    'S-band': {
        'name': 'S-band (MSS/BSS)',
        # ITU-R Radio Regulations Art.5, Region 1/2/3 allocations
        # Sirius XM, some mobile broadband
        'uplink_min_ghz': 2.655,
        'uplink_max_ghz': 2.690,
        'uplink_center_ghz': 2.6725,
        'downlink_min_ghz': 2.500,
        'downlink_max_ghz': 2.535,
        'downlink_center_ghz': 2.5175,
        'total_bandwidth_mhz': 35.0,
        'typical_transponder_bw_mhz': 15.0,
        'services': 'MSS/BSS (Mobile/Broadcast Satellite Service)',
        'examples': 'Sirius XM, Terrestar, ICO',
    },
    'C-band': {
        'name': 'C-band (FSS)',
        # ITU-R Radio Regulations Art.5, S.1525, S.580-6
        # Standard FSS allocation — most widely used for international trunking
        'uplink_min_ghz': 5.925,
        'uplink_max_ghz': 6.425,
        'uplink_center_ghz': 6.175,
        'downlink_min_ghz': 3.700,
        'downlink_max_ghz': 4.200,
        'downlink_center_ghz': 3.950,
        'total_bandwidth_mhz': 500.0,
        'typical_transponder_bw_mhz': 36.0,     # Standard 36 MHz transponder
        'services': 'FSS (Fixed Satellite Service)',
        'examples': 'Intelsat, AsiaSat, SES — VSAT, TV distribution',
    },
    'X-band': {
        'name': 'X-band (Government/Military)',
        # ITU-R Radio Regulations Art.5 — primarily government/military FSS
        # NATO, WGS (Wideband Global SATCOM)
        'uplink_min_ghz': 7.900,
        'uplink_max_ghz': 8.400,
        'uplink_center_ghz': 8.150,
        'downlink_min_ghz': 7.250,
        'downlink_max_ghz': 7.750,
        'downlink_center_ghz': 7.500,
        'total_bandwidth_mhz': 500.0,
        'typical_transponder_bw_mhz': 36.0,
        'services': 'FSS (Government/Military)',
        'examples': 'WGS, Skynet, XTAR — military tactical communications',
    },
    'Ku-band': {
        'name': 'Ku-band (FSS/BSS)',
        # ITU-R Radio Regulations Art.5, S.1525, BO.1443
        # Dominant band for DTH broadcasting and VSAT
        # Uplink: 14.0–14.5 GHz (FSS Earth-to-space)
        # Downlink: 10.7–12.75 GHz (FSS/BSS space-to-Earth)
        #   Sub-bands: 10.7–11.7 (FSS), 11.7–12.2 (BSS Reg.1&3), 12.2–12.75 (BSS Reg.2)
        'uplink_min_ghz': 14.0,
        'uplink_max_ghz': 14.5,
        'uplink_center_ghz': 14.25,
        'downlink_min_ghz': 10.7,
        'downlink_max_ghz': 12.75,
        'downlink_center_ghz': 11.725,
        'total_bandwidth_mhz': 500.0,           # Uplink allocation
        'typical_transponder_bw_mhz': 36.0,     # Standard 36 MHz (also 27, 54, 72)
        'services': 'FSS/BSS (Fixed/Broadcast Satellite Service)',
        'examples': 'Astra, Hotbird, DirecTV, SES — DTH TV, VSAT',
    },
    'Ka-band': {
        'name': 'Ka-band (FSS/HTS)',
        # ITU-R Radio Regulations Art.5, S.1525
        # High Throughput Satellites (HTS) — spot beam architectures
        # Uplink: 27.5–31.0 GHz (Earth-to-space)
        # Downlink: 17.7–21.2 GHz (space-to-Earth)
        'uplink_min_ghz': 27.5,
        'uplink_max_ghz': 31.0,
        'uplink_center_ghz': 29.25,
        'downlink_min_ghz': 17.7,
        'downlink_max_ghz': 21.2,
        'downlink_center_ghz': 19.45,
        'total_bandwidth_mhz': 3500.0,          # 3.5 GHz total uplink allocation
        'typical_transponder_bw_mhz': 250.0,    # Wideband HTS transponder
        'services': 'FSS/HTS (High Throughput Satellite)',
        'examples': 'ViaSat, Hughes Jupiter, Eutelsat KA-SAT — broadband internet',
    },
    'Q-band': {
        'name': 'Q/V-band (FSS feeder)',
        # ITU-R Radio Regulations Art.5
        # Primarily used for HTS gateway feeder links
        # Uplink (gateway): 42.5–43.5 GHz and 47.2–50.2 GHz
        # Downlink (gateway): 37.5–42.5 GHz
        'uplink_min_ghz': 42.5,
        'uplink_max_ghz': 43.5,
        'uplink_center_ghz': 43.0,
        'downlink_min_ghz': 37.5,
        'downlink_max_ghz': 42.5,
        'downlink_center_ghz': 40.0,
        'total_bandwidth_mhz': 5000.0,          # Wide allocation
        'typical_transponder_bw_mhz': 500.0,    # Very wideband
        'services': 'FSS (Gateway feeder links)',
        'examples': 'HTS gateway feeder links (next-gen broadband)',
    },
    'V-band': {
        'name': 'V-band (FSS/experimental)',
        # ITU-R Radio Regulations Art.5
        # Future allocations for ultra-high-capacity systems
        'uplink_min_ghz': 57.0,
        'uplink_max_ghz': 64.0,
        'uplink_center_ghz': 60.5,
        'downlink_min_ghz': 52.0,
        'downlink_max_ghz': 57.0,
        'downlink_center_ghz': 54.5,
        'total_bandwidth_mhz': 5000.0,
        'typical_transponder_bw_mhz': 500.0,
        'services': 'FSS (Experimental/next-gen)',
        'examples': 'Boeing V-band constellation, future LEO mega-constellations',
    },
}

# --- Satellite types and orbital parameters ---------------------------------

SATELLITE_TYPES = {
    'LEO': {
        'name': 'Low Earth Orbit',
        'altitude_range': (160, 2000),  # km
        'typical_altitude': 550,        # km (Starlink)
        'min_altitude': 160,            # km
        'max_altitude': 2000,           # km
        'period_minutes': 96,           # typical orbital period
        'velocity_km_s': 7.8,           # orbital velocity
        'orbital_radius_km': 6921,      # from Earth center (550 + 6371)
        'examples': 'Starlink, OneWeb, Iridium',
        # Link budget parameters
        'typical_tx_power_dbw': 5.0,    # Lower power than GEO
        'typical_antenna_gain_dbi': 25.0,
        'typical_eirp_dbw': 30.0,
        'doppler_shift_max_khz': 40,    # Max Doppler at Ku-band
        'handover_required': True,
        'coverage_radius_km': 1000,     # Footprint radius
        'propagation_delay_ms': 4,      # Round trip ~8ms
        'free_space_loss_db': 170,      # Typical at 12 GHz
    },
    'MEO': {
        'name': 'Medium Earth Orbit',
        'altitude_range': (2000, 35786),  # km
        'typical_altitude': 20200,        # km (GPS)
        'min_altitude': 2000,             # km
        'max_altitude': 35786,            # km
        'period_minutes': 720,            # 12 hours (GPS)
        'velocity_km_s': 3.87,            # orbital velocity
        'orbital_radius_km': 26571,       # from Earth center
        'examples': 'GPS, Galileo, GLONASS, O3b',
        # Link budget parameters
        'typical_tx_power_dbw': 8.0,
        'typical_antenna_gain_dbi': 28.0,
        'typical_eirp_dbw': 36.0,
        'doppler_shift_max_khz': 5,
        'handover_required': True,
        'coverage_radius_km': 5000,
        'propagation_delay_ms': 70,       # Round trip ~140ms
        'free_space_loss_db': 190,        # Typical at 12 GHz
    },
    'GEO': {
        'name': 'Geostationary Orbit',
        'altitude_range': (35786, 35786),  # km
        'typical_altitude': 35786,         # km
        'min_altitude': 35786,             # km
        'max_altitude': 35786,             # km
        'period_minutes': 1436,            # ~24 hours (sidereal day)
        'velocity_km_s': 3.07,             # orbital velocity
        'orbital_radius_km': 42164,        # from Earth center
        'examples': 'Intelsat, Astra, Hotbird, SES',
        # Link budget parameters
        'typical_tx_power_dbw': 10.0,      # Higher power
        'typical_antenna_gain_dbi': 32.0,
        'typical_eirp_dbw': 42.0,
        'doppler_shift_max_khz': 0,        # No Doppler (stationary)
        'handover_required': False,
        'coverage_radius_km': 15000,       # Large footprint
        'propagation_delay_ms': 240,       # Round trip ~480ms
        'free_space_loss_db': 205,         # Typical at 12 GHz
    },
    'HEO': {
        'name': 'Highly Elliptical Orbit',
        'altitude_range': (1000, 39000),   # km (perigee to apogee)
        'typical_altitude': 20000,         # km (average)
        'min_altitude': 1000,              # km (perigee)
        'max_altitude': 39000,             # km (apogee)
        'period_minutes': 720,             # 12 hours (Molniya)
        'velocity_km_s': 1.6,              # at apogee
        'orbital_radius_km': 26371,        # average from Earth center
        'examples': 'Molniya, Tundra, Sirius XM',
        # Link budget parameters
        'typical_tx_power_dbw': 10.0,
        'typical_antenna_gain_dbi': 30.0,
        'typical_eirp_dbw': 40.0,
        'doppler_shift_max_khz': 15,       # Variable Doppler
        'handover_required': True,
        'coverage_radius_km': 8000,        # At apogee
        'propagation_delay_ms': 130,       # Variable
        'free_space_loss_db': 195,         # At apogee
        # Elliptical orbit specific
        'eccentricity': 0.74,
        'inclination_deg': 63.4,           # Critical inclination
        'argument_of_perigee_deg': 270,
    }
}

# Modulation Schemes
# Includes required Eb/N0 for BER=10^-6 (uncoded) based on theoretical curves
MODULATION_SCHEMES = {
    'BPSK': {'order': 2, 'efficiency': 1.0, 'name': 'Binary PSK', 'required_ebn0_db': 10.5},
    'QPSK': {'order': 4, 'efficiency': 2.0, 'name': 'Quadrature PSK', 'required_ebn0_db': 10.5},
    '8PSK': {'order': 8, 'efficiency': 3.0, 'name': '8-Phase PSK', 'required_ebn0_db': 14.0},
    '16QAM': {'order': 16, 'efficiency': 4.0, 'name': '16-QAM', 'required_ebn0_db': 14.5},
    '16APSK': {'order': 16, 'efficiency': 4.0, 'name': '16-APSK', 'required_ebn0_db': 13.5},
    '32APSK': {'order': 32, 'efficiency': 5.0, 'name': '32-APSK', 'required_ebn0_db': 16.0},
    '64QAM': {'order': 64, 'efficiency': 6.0, 'name': '64-QAM', 'required_ebn0_db': 18.5},
}

# Coding Schemes and their coding gains (dB)
CODING_SCHEMES = {
    'Uncoded': {'rate': 1.0, 'gain': 0.0},
    'Convolutional (R=1/2)': {'rate': 0.5, 'gain': 5.0},
    'Turbo (R=1/2)': {'rate': 0.5, 'gain': 6.5},
    'Turbo (R=2/3)': {'rate': 0.667, 'gain': 5.5},
    'LDPC (R=1/2)': {'rate': 0.5, 'gain': 6.8},
    'LDPC (R=2/3)': {'rate': 0.667, 'gain': 6.0},
    'LDPC (R=3/4)': {'rate': 0.75, 'gain': 5.5},
    'LDPC (R=5/6)': {'rate': 0.833, 'gain': 4.8},
}

# Rain Climate Zones (ITU-R P.618)
RAIN_ZONES = {
    'A': {'name': 'Tropical', 'rain_rate': 95},  # mm/h for 0.01%
    'B': {'name': 'Mediterranean', 'rain_rate': 65},
    'C': {'name': 'Continental Subtropical', 'rain_rate': 55},
    'D': {'name': 'Temperate', 'rain_rate': 42},
    'E': {'name': 'Polar', 'rain_rate': 22},
}

# Rain Attenuation Coefficients (ITU-R P.838-3)
# Regression coefficients for specific attenuation γ_R = k * R^α
# Horizontal and Vertical polarization values
RAIN_COEFFICIENTS = {
    'freq_ghz': np.array([
        1, 2, 4, 6, 7, 8, 10, 12, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100
    ]),
    # Horizontal polarization
    'k_h': np.array([
        0.0000387, 0.000154, 0.000650, 0.00175, 0.00301, 0.00454, 0.0101,
        0.0188, 0.0367, 0.0751, 0.124, 0.187, 0.263, 0.350, 0.442, 0.536,
        0.707, 0.851, 0.975, 1.06, 1.12
    ]),
    'alpha_h': np.array([
        0.912, 0.963, 1.121, 1.308, 1.332, 1.327, 1.276, 1.217, 1.154,
        1.099, 1.061, 1.021, 0.979, 0.939, 0.903, 0.873, 0.826, 0.793,
        0.769, 0.753, 0.743
    ]),
    # Vertical polarization
    'k_v': np.array([
        0.0000352, 0.000138, 0.000591, 0.00155, 0.00265, 0.00395, 0.00887,
        0.0168, 0.0335, 0.0691, 0.113, 0.167, 0.233, 0.310, 0.393, 0.479,
        0.642, 0.784, 0.906, 0.999, 1.06
    ]),
    'alpha_v': np.array([
        0.880, 0.923, 1.075, 1.265, 1.312, 1.310, 1.264, 1.200, 1.128,
        1.065, 1.030, 1.000, 0.963, 0.929, 0.897, 0.868, 0.824, 0.793,
        0.769, 0.754, 0.744
    ]),
}

# --- Professional link budget constants -------------------------------------

# GEO Orbital Parameters (ITU-R S.1257)
GEO_ORBIT = {
    'altitude_km': 35786.0,          # GEO altitude
    'orbital_radius_km': 42164.0,    # From Earth center
    'orbital_period_hours': 23.934,  # Sidereal day
    'orbital_velocity_km_s': 3.0746, # Orbital velocity
}

# ITU-R P.839-4: Rain Height Model
# Mean annual rain height above mean sea level
RAIN_HEIGHT_MODEL = {
    # Latitude ranges for rain height calculation
    # h_R = h_0 + 0.36 km for latitude <= 36°
    # h_R = h_0 + 0.36 - 0.075*(lat-36) for latitude > 36°
    'h0_tropical': 5.0,      # km, 0-23° latitude
    'h0_subtropical': 4.5,   # km, 23-45° latitude  
    'h0_temperate': 3.5,     # km, 45-60° latitude
    'h0_polar': 2.5,         # km, >60° latitude
    # Default value for user input
    'default_km': 3.0,       # km, mid-latitude default
}

# ITU-R P.840-8: Cloud and Fog Attenuation
CLOUD_ATTENUATION = {
    # Liquid water content (g/m³) for different cloud types
    'stratus': 0.30,
    'stratocumulus': 0.25,
    'cumulus': 0.50,
    'cumulonimbus': 2.00,
    'fog_light': 0.05,
    'fog_moderate': 0.25,
    'fog_thick': 0.50,
    # Specific attenuation coefficient Kl (dB/km)/(g/m³) at various frequencies
    'Kl_10ghz': 0.0543,
    'Kl_20ghz': 0.287,
    'Kl_30ghz': 0.614,
    'Kl_40ghz': 0.952,
}

# ITU-R P.618-14: Scintillation Parameters
SCINTILLATION_PARAMS = {
    'Nwet_standard': 42.0,    # Wet term of refractivity (ITU-R P.453)
    'href_m': 1000.0,         # Reference height (m)
    'Deff_factor': 1.22,      # Effective antenna diameter factor
    'sigma_ref': 3.6e-3,      # Reference standard deviation (dB) at 1 GHz
}

# ITU-R P.676-12: Gaseous Attenuation - Water Vapor Lines
WATER_VAPOR_LINES = {
    # Primary absorption line at 22.235 GHz
    'f0_primary': 22.235,     # GHz
    'f0_secondary': 183.31,   # GHz
    # Scale heights
    'ho_dry': 6.0,            # km - dry atmosphere
    'hw_wet': 2.0,            # km - wet atmosphere (water vapor)
}

# Reference Temperatures (ITU-R P.372, P.618)
REFERENCE_TEMPERATURES = {
    'T0': 290.0,              # Standard reference temperature (K)
    'Tm_rain': 275.0,         # Mean rain temperature (K)
    'Tsky_clear_low': 5.0,    # Clear sky at low freq (K)
    'Tsky_clear_high': 30.0,  # Clear sky at high freq (K)
    'Tground': 290.0,         # Ground temperature (K)
    'Tcosmic': 2.7,           # Cosmic background (K)
}

# HPA (High Power Amplifier) Characteristics
HPA_CHARACTERISTICS = {
    'sspa_backoff_typical': 3.0,   # dB - Solid State PA
    'twta_backoff_typical': 6.0,   # dB - Traveling Wave Tube
    'klystron_backoff': 4.0,       # dB
    'linearizer_improvement': 2.0, # dB improvement with linearizer
}

# DVB-S2/S2X Eb/N0 Requirements (ITU-R S.1328, ETSI EN 302 307)
MODCOD_REQUIREMENTS = {
    # Format: 'modulation_coding': {'ebn0_required': dB, 'spectral_eff': bits/s/Hz}
    'QPSK_1/4': {'ebn0_required': -2.35, 'spectral_eff': 0.49},
    'QPSK_1/3': {'ebn0_required': -1.24, 'spectral_eff': 0.66},
    'QPSK_2/5': {'ebn0_required': -0.30, 'spectral_eff': 0.79},
    'QPSK_1/2': {'ebn0_required': 1.00, 'spectral_eff': 0.99},
    'QPSK_3/5': {'ebn0_required': 2.23, 'spectral_eff': 1.19},
    'QPSK_2/3': {'ebn0_required': 3.10, 'spectral_eff': 1.32},
    'QPSK_3/4': {'ebn0_required': 4.03, 'spectral_eff': 1.49},
    'QPSK_4/5': {'ebn0_required': 4.68, 'spectral_eff': 1.59},
    'QPSK_5/6': {'ebn0_required': 5.18, 'spectral_eff': 1.65},
    '8PSK_3/5': {'ebn0_required': 5.50, 'spectral_eff': 1.78},
    '8PSK_2/3': {'ebn0_required': 6.62, 'spectral_eff': 1.98},
    '8PSK_3/4': {'ebn0_required': 7.91, 'spectral_eff': 2.23},
    '16APSK_2/3': {'ebn0_required': 8.97, 'spectral_eff': 2.64},
    '16APSK_3/4': {'ebn0_required': 10.21, 'spectral_eff': 2.97},
    '16APSK_4/5': {'ebn0_required': 11.03, 'spectral_eff': 3.17},
    '16APSK_5/6': {'ebn0_required': 11.61, 'spectral_eff': 3.30},
    '32APSK_3/4': {'ebn0_required': 12.73, 'spectral_eff': 3.70},
    '32APSK_4/5': {'ebn0_required': 13.64, 'spectral_eff': 3.95},
    '32APSK_5/6': {'ebn0_required': 14.28, 'spectral_eff': 4.12},
}

# --- Monte Carlo simulation parameters --------------------------------------

MONTE_CARLO_PARAMS = {
    'default_n_simulations': 10000,        # Number of Monte Carlo runs
    'confidence_levels': [0.90, 0.95, 0.99, 0.999],  # Confidence intervals
    
    # ITU-R P.837-7: Rain rate distribution parameters (log-normal)
    # Rayleigh scale parameters for different climate zones
    'rain_distribution': {
        'Tropical':     {'scale': 12.0, 'shape': 2.0, 'p001': 95},   # mm/h at 0.01%
        'Mediterranean':{'scale': 8.0,  'shape': 1.8, 'p001': 65},
        'Continental':  {'scale': 6.0,  'shape': 1.5, 'p001': 55},
        'Temperate':    {'scale': 4.5,  'shape': 1.3, 'p001': 42},
        'Polar':        {'scale': 2.0,  'shape': 1.0, 'p001': 22},
    },
    
    # Parameter variation ranges (% of nominal) for sensitivity
    'variation_ranges': {
        'tx_power_db': 0.5,           # ±0.5 dB
        'antenna_gain_db': 0.3,       # ±0.3 dB (pointing jitter)
        'atmospheric_loss_db': 1.0,   # ±1.0 dB (seasonal variation)
        'noise_temp_pct': 10.0,       # ±10% of system noise temp
        'elevation_deg': 0.5,         # ±0.5° (tracking error)
    },
}

# --- Fade dynamics parameters (P.1623-1) ------------------------------------

FADE_DYNAMICS_PARAMS = {
    # ITU-R P.1623-1: Fade duration parameters
    # Probability that fade duration > D seconds given fade > A dB
    # P(d > D | a > A) = 1 / (1 + (D/D0)^(beta))
    'D0_coefficients': {
        # D0 = a * A^b (seconds) — varies with frequency
        # Source: ITU-R P.1623-1 Table 1
        'a': 200.0,       # Duration scale factor
        'b': -0.78,       # Attenuation exponent
    },
    'beta': 0.89,          # Shape parameter for duration distribution
    
    # Fade slope (rate of change of attenuation)
    # ITU-R P.1623-1 Section 2.3
    'fade_slope': {
        'sigma_zeta': 0.1,    # Standard deviation of fade slope (dB/s)
        'correlation_time': 60.0,  # Decorrelation time (seconds)
    },
    
    # Availability targets for SLA
    'availability_targets': {
        'broadcast_standard': 99.5,    # % — standard broadcast
        'broadcast_premium': 99.9,     # % — premium broadcast
        'telecom_standard': 99.95,     # % — standard telecom
        'telecom_premium': 99.99,      # % — premium telecom/military
        'scientific_grade': 99.999,    # % — deep space / scientific
    },
    
    # Fade duration bins (seconds) for histogram
    'duration_bins': [1, 2, 5, 10, 20, 30, 60, 120, 300, 600, 1800, 3600],
}

# --- Maseng-Bakken rain fade synthesizer (P.1853-2) -------------------------

MASENG_BAKKEN_PARAMS = {
    # Time constant β (seconds) — controls autocorrelation of rain process
    # β = 2π / (2 * d_eff / v_wind)  where d_eff ~ rain cell diameter
    # Source: ITU-R P.1853-2 Table 1, Matricciani (1996) Section 3
    'beta_seconds': {
        'C-band':   200.0,    # 4 GHz — longer correlation (larger rain cells effective)
        'Ku-band':  120.0,    # 12 GHz — medium correlation
        'Ka-band':   90.0,    # 20-30 GHz — shorter correlation
        'Q-band':    60.0,    # 40 GHz — fast fluctuations
        'V-band':    45.0,    # 50 GHz — very fast
    },

    # Default β if frequency not in lookup
    'beta_default': 100.0,

    # Lognormal rain rate distribution parameters by ITU-R P.837 climate zone
    # R(p) = R_0.01 * (p/0.01)^(-alpha)  approximate power-law tail
    # m = mean of ln(R), sigma = std of ln(R)
    # Source: ITU-R P.837-7, Crane (1996) Table 3.2
    'climate_zones': {
        'A':  {'R001': 8,   'm_ln': 0.80,  'sigma_ln': 1.10, 'name': 'Polar/Tundra'},
        'B':  {'R001': 12,  'm_ln': 1.05,  'sigma_ln': 1.15, 'name': 'Polar/Temperate'},
        'C':  {'R001': 15,  'm_ln': 1.20,  'sigma_ln': 1.18, 'name': 'Temperate'},
        'D':  {'R001': 19,  'm_ln': 1.32,  'sigma_ln': 1.20, 'name': 'Dry Temperate'},
        'E':  {'R001': 22,  'm_ln': 1.40,  'sigma_ln': 1.22, 'name': 'Continental'},
        'F':  {'R001': 28,  'm_ln': 1.50,  'sigma_ln': 1.25, 'name': 'Maritime Temperate'},
        'G':  {'R001': 30,  'm_ln': 1.55,  'sigma_ln': 1.28, 'name': 'Subtropical Wet'},
        'H':  {'R001': 32,  'm_ln': 1.58,  'sigma_ln': 1.30, 'name': 'Subtropical Moderate'},
        'J':  {'R001': 35,  'm_ln': 1.62,  'sigma_ln': 1.32, 'name': 'Mediterranean'},
        'K':  {'R001': 42,  'm_ln': 1.72,  'sigma_ln': 1.35, 'name': 'Temperate Maritime'},
        'L':  {'R001': 60,  'm_ln': 1.90,  'sigma_ln': 1.38, 'name': 'Subtropical Humid'},
        'M':  {'R001': 63,  'm_ln': 1.95,  'sigma_ln': 1.40, 'name': 'Tropical Wet-Dry'},
        'N':  {'R001': 95,  'm_ln': 2.20,  'sigma_ln': 1.45, 'name': 'Maritime Tropical'},
        'P':  {'R001': 145, 'm_ln': 2.55,  'sigma_ln': 1.50, 'name': 'Equatorial Heavy'},
        'Q':  {'R001': 115, 'm_ln': 2.40,  'sigma_ln': 1.48, 'name': 'Tropical Moderate'},
    },

    # Default simulation parameters
    'default_duration_hours': 6,
    'default_sample_interval_sec': 1,

    # Animation display parameters
    'window_width_sec': 600,       # Sliding window width for animation (10 min)
    'animation_interval_ms': 100,  # QTimer interval for animation
}

# --- ITU regulatory compliance (PFD limits, EIRP masks) --------------------

ITU_PFD_LIMITS = {
    # ITU Radio Regulations Article 21, Table 21-4
    # PFD limits at Earth's surface (dBW/m²/4kHz) for GSO satellites
    # Varies with elevation angle (0-90°)
    'gso_limits': {
        # Format: (freq_min_ghz, freq_max_ghz): {'pfd_low': at 0°, 'pfd_high': at 90°}
        # PFD limit = pfd_low + (pfd_high - pfd_low) * sin²(elevation)
        (3.4, 4.2):   {'pfd_low': -152.0, 'pfd_high': -152.0, 'name': 'C-band (3.4-4.2 GHz)'},
        (4.5, 4.8):   {'pfd_low': -152.0, 'pfd_high': -148.0, 'name': 'C-band ext (4.5-4.8 GHz)'},
        (10.7, 11.7): {'pfd_low': -150.0, 'pfd_high': -138.0, 'name': 'Ku-band low (10.7-11.7 GHz)'},
        (11.7, 12.2): {'pfd_low': -148.0, 'pfd_high': -138.0, 'name': 'Ku-band mid (11.7-12.2 GHz)'},
        (12.2, 12.75):{'pfd_low': -148.0, 'pfd_high': -138.0, 'name': 'Ku-band high (12.2-12.75 GHz)'},
        (17.7, 19.7): {'pfd_low': -150.0, 'pfd_high': -138.0, 'name': 'Ka-band (17.7-19.7 GHz)'},
        (37.5, 42.5): {'pfd_low': -120.0, 'pfd_high': -105.0, 'name': 'Q/V-band (37.5-42.5 GHz)'},
    },
    
    # Non-GSO satellite PFD limits (ITU-R S.1428, Article 22)
    'ngso_limits': {
        (10.7, 12.75): {'pfd_limit': -138.0, 'name': 'Ku-band NGSO'},
        (17.8, 18.6):  {'pfd_limit': -115.0, 'name': 'Ka-band NGSO'},
        (19.7, 20.2):  {'pfd_limit': -115.0, 'name': 'Ka-band NGSO ext'},
    },
}

# EIRP Density Masks (ITU-R S.524-9)
EIRP_DENSITY_MASKS = {
    # Off-axis EIRP density limits for satellite earth stations
    # EIRP_density = A - B*log10(theta) dBW/40kHz
    'standard_earth_station': {
        # For 2° < θ < 7°:  33 - 25*log10(θ)
        # For 7° ≤ θ < 9.2°: 12
        # For 9.2° ≤ θ < 48°: 36 - 25*log10(θ)  
        # For θ ≥ 48°:        -6
        'segments': [
            {'theta_min': 2.0, 'theta_max': 7.0, 'A': 33.0, 'B': 25.0},
            {'theta_min': 7.0, 'theta_max': 9.2, 'A': 12.0, 'B': 0.0},
            {'theta_min': 9.2, 'theta_max': 48.0, 'A': 36.0, 'B': 25.0},
            {'theta_min': 48.0, 'theta_max': 180.0, 'A': -6.0, 'B': 0.0},
        ],
    },
    
    # Satellite downlink EIRP density mask (ITU-R S.728)
    'satellite_downlink': {
        'segments': [
            {'theta_min': 0.0, 'theta_max': 1.0, 'A': 0.0, 'B': 0.0},  # On-axis
            {'theta_min': 1.0, 'theta_max': 7.0, 'A': 29.0, 'B': 25.0},
            {'theta_min': 7.0, 'theta_max': 9.2, 'A': 8.0, 'B': 0.0},
            {'theta_min': 9.2, 'theta_max': 48.0, 'A': 32.0, 'B': 25.0},
            {'theta_min': 48.0, 'theta_max': 180.0, 'A': -10.0, 'B': 0.0},
        ],
    },
}

# --- Adjacent satellite interference (ASI) parameters ----------------------

ADJACENT_SATELLITE_PARAMS = {
    # Typical GEO orbital spacing (degrees) — ITU coordination arc
    'typical_spacings_deg': [2.0, 3.0, 4.0, 6.0, 9.0],

    # Typical interfering satellite EIRP per band (dBW)
    # Based on real satellite fleet data (SES, Intelsat, Eutelsat filings)
    'interferer_eirp_dbw': {
        'C-band':  38.0,   # Typical C-band transponder EIRP
        'Ku-band': 52.0,   # Typical Ku-band DTH / VSAT EIRP
        'Ka-band': 56.0,   # Typical Ka-band HTS spot-beam EIRP
    },

    # ITU-R S.465-6 / S.580-6 Reference Antenna Pattern Parameters
    # Used for off-axis gain calculation of the ground station antenna
    #   Region 1: G(θ) = Gmax - 2.5e-3 * (D/λ * θ)²    for 0 ≤ θ ≤ θ_m
    #   Region 2: G(θ) = G1                               for θ_m < θ ≤ θ_r
    #   Region 3: G(θ) = 32 - 25*log10(θ)                 for θ_r < θ ≤ 48°
    #   Region 4: G(θ) = -10 dBi                           for θ > 48°
    # where:
    #   G1 = 2 + 15*log10(D/λ)
    #   θ_m = 20*λ/D * sqrt(Gmax - G1)
    #   θ_r = 15.85 * (D/λ)^(-0.6)
    'antenna_pattern': {
        'floor_dbi': -10.0,           # Far-out sidelobe floor (dBi)
        'sidelobe_envelope_A': 32.0,  # Envelope constant (dBi)
        'sidelobe_envelope_B': 25.0,  # Envelope slope (dB/decade)
        'transition_angle_deg': 48.0, # Angle beyond which floor applies
    },

    # Number of interfering satellites to model (east + west neighbors)
    'default_num_interferers': 2,      # 1 east + 1 west neighbor

    # Topocentric angular offset correction factor
    # Accounts for the fact that earth-station sees slightly different
    # angular separation than the geocentric orbital spacing
    'topocentric_correction': True,
}
