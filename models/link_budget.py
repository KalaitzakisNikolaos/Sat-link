"""Satellite link budget calculations per ITU-R standards.

Covers uplink, downlink, and end-to-end analysis including free-space
loss (P.525), atmospheric/rain attenuation (P.618, P.676, P.838),
antenna gain, system noise, and link margin.
"""

import numpy as np
from scipy.special import erfc
from .constants import (
    C_LIGHT, BOLTZMANN, EARTH_RADIUS, EARTH_MU,
    RAIN_COEFFICIENTS, GEO_ORBIT,
    CLOUD_ATTENUATION, SCINTILLATION_PARAMS,
    REFERENCE_TEMPERATURES,
    SATELLITE_TYPES, MONTE_CARLO_PARAMS, FADE_DYNAMICS_PARAMS,
    ITU_PFD_LIMITS, EIRP_DENSITY_MASKS,
    ADJACENT_SATELLITE_PARAMS,
    MASENG_BAKKEN_PARAMS,
)


# --- Geometry (ITU-R S.1257) ------------------------------------------------

class GeometryCalculator:
    """Orbital geometry for satellite links (LEO/MEO/GEO/HEO).

    Computes slant range, elevation, azimuth, Doppler shift,
    and related quantities per ITU-R S.1257 and P.618.
    """
    
    def __init__(self, orbit_type='GEO'):
        """Set up geometry for *orbit_type* ('LEO', 'MEO', 'GEO', or 'HEO')."""
        self.orbit_type = orbit_type
        self.Re = EARTH_RADIUS  # km
        self.mu = EARTH_MU      # km^3/s^2 (gravitational parameter)
        
        # Get orbit-specific parameters
        if orbit_type in SATELLITE_TYPES:
            orbit_params = SATELLITE_TYPES[orbit_type]
            self.altitude_km = orbit_params['typical_altitude']
            self.Rs = orbit_params['orbital_radius_km']
            self.velocity_km_s = orbit_params['velocity_km_s']
            self.period_minutes = orbit_params['period_minutes']
            self.doppler_max_khz = orbit_params['doppler_shift_max_khz']
            self.handover_required = orbit_params['handover_required']
        else:
            # Default to GEO
            self.altitude_km = GEO_ORBIT['altitude_km']
            self.Rs = GEO_ORBIT['orbital_radius_km']
            self.velocity_km_s = GEO_ORBIT['orbital_velocity_km_s']
            self.period_minutes = GEO_ORBIT['orbital_period_hours'] * 60
            self.doppler_max_khz = 0
            self.handover_required = False
    
    def set_orbit_type(self, orbit_type, altitude_km=None):
        """Switch orbit type, optionally overriding altitude."""
        self.orbit_type = orbit_type
        
        if orbit_type in SATELLITE_TYPES:
            orbit_params = SATELLITE_TYPES[orbit_type]
            if altitude_km is not None:
                self.altitude_km = altitude_km
                self.Rs = self.Re + altitude_km
            else:
                self.altitude_km = orbit_params['typical_altitude']
                self.Rs = orbit_params['orbital_radius_km']
            
            # Calculate velocity from orbital mechanics: v = sqrt(mu/r)
            self.velocity_km_s = np.sqrt(self.mu / self.Rs)
            
            # Calculate period from Kepler's 3rd law: T = 2*pi*sqrt(r^3/mu)
            self.period_minutes = 2 * np.pi * np.sqrt(self.Rs**3 / self.mu) / 60
            
            self.doppler_max_khz = orbit_params['doppler_shift_max_khz']
            self.handover_required = orbit_params['handover_required']
    
    def calculate_orbital_velocity(self, altitude_km=None):
        """Orbital velocity in km/s.  v = sqrt(μ/r)"""
        if altitude_km is None:
            r = self.Rs
        else:
            r = self.Re + altitude_km
        
        return np.sqrt(self.mu / r)
    
    def calculate_orbital_period(self, altitude_km=None):
        """Orbital period in minutes.  T = 2π·√(r³/μ)"""
        if altitude_km is None:
            r = self.Rs
        else:
            r = self.Re + altitude_km
        
        T_seconds = 2 * np.pi * np.sqrt(r**3 / self.mu)
        return T_seconds / 60  # minutes
    
    def calculate_doppler_shift(self, frequency_ghz, elevation_deg, 
                                radial_velocity_km_s=None):
        """Doppler shift in kHz.  Δf = f·(v_r/c).  Returns 0 for GEO."""
        if self.orbit_type == 'GEO':
            return 0.0
        
        if radial_velocity_km_s is None:
            # Maximum radial velocity at horizon
            # v_r = v * cos(elevation)
            el_rad = np.radians(elevation_deg)
            radial_velocity_km_s = self.velocity_km_s * np.cos(el_rad)
        
        # delta_f = f * (v_r / c)
        c_km_s = C_LIGHT / 1000  # km/s
        doppler_hz = frequency_ghz * 1e9 * (radial_velocity_km_s / c_km_s)
        
        return doppler_hz / 1000  # kHz
    
    def calculate_propagation_delay(self, distance_km=None):
        """One-way propagation delay in milliseconds."""
        if distance_km is None:
            distance_km = self.altitude_km
        
        delay_s = (distance_km * 1000) / C_LIGHT
        return delay_s * 1000  # ms
    
    def calculate_round_trip_delay(self, distance_km=None):
        """Round-trip propagation delay in milliseconds."""
        return 2 * self.calculate_propagation_delay(distance_km)
    
    def calculate_central_angle(self, lat_gs_deg, lon_gs_deg, lon_sat_deg, lat_sat_deg=0.0):
        """Central angle (radians) between ground station and sub-satellite point."""
        lat_gs_rad = np.radians(lat_gs_deg)
        lat_sat_rad = np.radians(lat_sat_deg)
        delta_lon_rad = np.radians(lon_gs_deg - lon_sat_deg)
        
        # Haversine-style formula, valid for any orbit type
        gamma = np.arccos(
            np.sin(lat_gs_rad) * np.sin(lat_sat_rad) + 
            np.cos(lat_gs_rad) * np.cos(lat_sat_rad) * np.cos(delta_lon_rad)
        )
        return gamma  # radians
    
    def calculate_slant_range(self, lat_gs_deg, lon_gs_deg, lon_sat_deg,
                              altitude_km=None, lat_sat_deg=0.0):
        """Slant range in km.  d = √(Re² + Rs² − 2·Re·Rs·cos γ)"""
        if altitude_km is None:
            Rs = self.Rs
        else:
            Rs = self.Re + altitude_km
        
        gamma = self.calculate_central_angle(lat_gs_deg, lon_gs_deg, lon_sat_deg, lat_sat_deg)
        
        d = np.sqrt(self.Re**2 + Rs**2 - 2 * self.Re * Rs * np.cos(gamma))
        return d  # km
    
    def calculate_elevation_angle(self, lat_gs_deg, lon_gs_deg, lon_sat_deg,
                                   altitude_km=None, lat_sat_deg=0.0):
        """Elevation angle in degrees (P.618-13 Eq. 2)."""
        if altitude_km is None:
            Rs = self.Rs
        else:
            Rs = self.Re + altitude_km
        
        gamma = self.calculate_central_angle(lat_gs_deg, lon_gs_deg, lon_sat_deg, lat_sat_deg)
        
        if np.sin(gamma) < 1e-10:
            return 90.0  # satellite directly overhead
        
        E = np.arctan((np.cos(gamma) - self.Re/Rs) / np.sin(gamma))
        return np.degrees(E)  # degrees
    
    def calculate_polarization_angle(self, lat_gs_deg, lon_gs_deg, lon_sat_deg):
        """Polarization tilt angle in degrees (P.618-14 Annex 1)."""
        lat_rad = np.radians(lat_gs_deg)
        delta_lon_rad = np.radians(lon_sat_deg - lon_gs_deg)
        
        if np.abs(lat_gs_deg) < 0.1:
            return 0.0  # at equator
        
        tau = np.arctan(np.sin(delta_lon_rad) / np.tan(lat_rad))
        return np.degrees(tau)  # degrees
    
    def calculate_azimuth_angle(self, lat_gs_deg, lon_gs_deg, lon_sat_deg):
        """Azimuth angle in degrees (0–360, North = 0)."""
        lat_rad = np.radians(lat_gs_deg)
        delta_lon_rad = np.radians(lon_sat_deg - lon_gs_deg)
        
        x = np.sin(delta_lon_rad)
        y = np.cos(delta_lon_rad) * np.sin(lat_rad)
        
        azimuth_rad = np.arctan2(x, -y)
        azimuth_deg = np.degrees(azimuth_rad)
        
        # Convert to 0-360 range
        if azimuth_deg < 0:
            azimuth_deg += 360
        
        return azimuth_deg  # degrees


# --- General link budget (base class) --------------------------------------

class GeneralLinkBudget:
    """Shared uplink/downlink formulas: FSPL, attenuation, gain, noise, margin."""
    
    def __init__(self, orbit_type='GEO'):
        self.geometry = GeometryCalculator(orbit_type)
        self.frequency_ghz = 14.0
        self.bandwidth_hz = 36e6
        self.distance_km = GEO_ORBIT['altitude_km'] + EARTH_RADIUS
    
    # -- Free-space path loss (P.525) ----------------------------------------

    def calculate_fspl(self, frequency_ghz, distance_km):
        """FSPL in dB (P.525).  20·log(d) + 20·log(f) + 92.45"""
        if distance_km <= 0 or frequency_ghz <= 0:
            return 0.0
        fspl_db = (20 * np.log10(distance_km) + 
                   20 * np.log10(frequency_ghz) + 
                   92.45)
        return fspl_db
    
    # -- Atmospheric / gaseous (P.676-12) ------------------------------------

    def calculate_atmospheric_attenuation(self, frequency_ghz, elevation_deg,
                                         water_vapor_density=7.5):
        """Gaseous attenuation in dB (oxygen + water vapor, P.676-12)."""
        if elevation_deg < 5:
            elevation_deg = 5  # Minimum for this model
        
        f = frequency_ghz
        rho = water_vapor_density
        
        # Oxygen attenuation (simplified ITU-R P.676-12)
        # Static values: h_o = 6.0 km, h_w = 2.0 km
        h_o = 6.0  # km - equivalent height for oxygen
        h_w = 2.0  # km - equivalent height for water vapor
        
        if f <= 54:
            gamma_o = (7.2 * (f**2.9) / (f**2 + 0.34) * 1e-3 +
                      0.62 * f**2.9 / (67 - f)**2 * 1e-3)
        else:
            gamma_o = 0.0
        
        # Water vapor attenuation (simplified)
        if f > 10:
            gamma_w = (0.067 + 3.0 / ((f - 22.3)**2 + 7.3)) * rho * f**2 * 1e-4
        else:
            gamma_w = 0.0
        
        # Total zenith attenuation
        A_zenith = gamma_o * h_o + gamma_w * h_w
        
        # Slant path correction
        sin_E = np.sin(np.radians(elevation_deg))
        A_atm = A_zenith / sin_E
        
        return A_atm
    
    # -- Rain attenuation (P.618, P.838-3) ----------------------------------

    def calculate_rain_attenuation(self, frequency_ghz, elevation_deg, 
                                   rain_rate, polarization_tilt_deg=45,
                                   station_height_km=0,
                                   rain_height_km=3.0):
        """Rain attenuation in dB.  A = γ_R · L_eff · r  (P.618/P.838-3)."""
        if rain_rate <= 0 or frequency_ghz <= 0:
            return 0.0
        
        f = frequency_ghz
        E = np.radians(elevation_deg)
        
        # Get rain coefficients from ITU-R P.838-3
        k_h, k_v, alpha_h, alpha_v = self._get_rain_coefficients(f)
        
        # Polarization-weighted coefficients
        tau = np.radians(polarization_tilt_deg)
        k = (k_h + k_v + (k_h - k_v) * np.cos(E)**2 * np.cos(2*tau)) / 2
        alpha = (k_h*alpha_h + k_v*alpha_v + 
                (k_h*alpha_h - k_v*alpha_v) * np.cos(E)**2 * np.cos(2*tau)) / (2*k)
        
        # Specific attenuation
        gamma_R = k * (rain_rate ** alpha)
        
        # Rain height from USER INPUT (previously hardcoded)
        h_r = rain_height_km
        
        # Slant path length
        h_s = station_height_km
        if elevation_deg >= 5:
            L_s = (h_r - h_s) / np.sin(E)
        else:
            L_s = 2 * (h_r - h_s) / (np.sin(E)**2 + 2*(h_r-h_s)/8500)**0.5
        
        # Horizontal projection
        L_g = L_s * np.cos(E)
        
        # Reduction factor
        r = 1 / (1 + 0.78 * np.sqrt(L_g * gamma_R / f) - 0.38 * (1 - np.exp(-2*L_g)))
        
        # Total rain attenuation
        A_rain = gamma_R * L_s * r
        
        return A_rain
    
    def _get_rain_coefficients(self, frequency_ghz):
        """Interpolate k_h, k_v, alpha_h, alpha_v from P.838-3 table."""
        f = frequency_ghz
        
        # Get arrays from RAIN_COEFFICIENTS
        freq_array = RAIN_COEFFICIENTS['freq_ghz']
        k_h_array = RAIN_COEFFICIENTS['k_h']
        k_v_array = RAIN_COEFFICIENTS['k_v']
        alpha_h_array = RAIN_COEFFICIENTS['alpha_h']
        alpha_v_array = RAIN_COEFFICIENTS['alpha_v']
        
        # Interpolate for the given frequency
        k_h = np.interp(f, freq_array, k_h_array)
        k_v = np.interp(f, freq_array, k_v_array)
        alpha_h = np.interp(f, freq_array, alpha_h_array)
        alpha_v = np.interp(f, freq_array, alpha_v_array)
        
        return (k_h, k_v, alpha_h, alpha_v)
    
    # -- Cloud / fog (P.840-8) -----------------------------------------------

    def calculate_cloud_attenuation(self, frequency_ghz, elevation_deg,
                                    liquid_water_content=0.5):
        """Cloud/fog attenuation in dB (P.840-8)."""
        if liquid_water_content <= 0 or elevation_deg <= 0:
            return 0.0
        
        f = frequency_ghz
        E = np.radians(elevation_deg)
        
        # ITU-R P.840-8: Specific attenuation coefficient at 0°C
        # K_l increases with frequency squared approximately
        # This is the corrected formula that properly scales with frequency
        T = CLOUD_ATTENUATION.get('temperature_k', 273.15)
        theta = 300.0 / T
        
        # Dielectric constants for liquid water (ITU-R P.840-8)
        eps_0 = 77.66 + 103.3 * (theta - 1)
        eps_1 = 0.0671 * eps_0
        eps_2 = 3.52
        
        # Principal and secondary relaxation frequencies
        fp = 20.20 - 146 * (theta - 1) + 316 * (theta - 1)**2  # GHz
        fs = 39.8 * fp  # GHz
        
        # Complex dielectric permittivity
        eps_real = (eps_0 - eps_1) / (1 + (f/fp)**2) + (eps_1 - eps_2) / (1 + (f/fs)**2) + eps_2
        eps_imag = f * (eps_0 - eps_1) / (fp * (1 + (f/fp)**2)) + f * (eps_1 - eps_2) / (fs * (1 + (f/fs)**2))
        
        # Specific attenuation coefficient (dB/km per g/m^3)
        eta_sq = ((2 + eps_real) / eps_imag)**2
        K_l = 0.819 * f / (eps_imag * (1 + eta_sq))
        
        # Cloud attenuation through slant path
        A_cloud = K_l * liquid_water_content / np.sin(E)
        
        return A_cloud
    
    # -- Scintillation (P.618-13 §2.4.1) -------------------------------------

    def calculate_scintillation(self, frequency_ghz, elevation_deg,
                                antenna_diameter_m, antenna_efficiency=0.6):
        """Tropospheric scintillation fade depth in dB (P.618-13)."""
        if elevation_deg <= 4:
            elevation_deg = 4  # Minimum for this model
        
        if antenna_diameter_m <= 0:
            return 0.0
        
        f = frequency_ghz
        E = np.radians(elevation_deg)
        
        # Effective antenna diameter
        D_eff = np.sqrt(antenna_efficiency) * antenna_diameter_m
        
        # Reference scintillation intensity
        # Static value from SCINTILLATION_PARAMS
        sigma_ref = SCINTILLATION_PARAMS.get('sigma_ref', 3.6e-3)
        
        # Antenna averaging factor
        D_lambda = D_eff * f / 0.3  # D/lambda in GHz equivalent
        if D_lambda > 0:
            x = 1.22 * D_lambda**2
            # Compute inner value and ensure non-negative before sqrt
            inner_val = (3.86 * (x**2 + 1)**(11/12) * 
                        np.sin(11/6 * np.arctan(1/x)) - 7.08 * x**(5/6))
            g_D = np.sqrt(max(inner_val, 0.0))
        else:
            g_D = 1.0
        
        # Bounds check to avoid sqrt of negative
        sin_E = max(np.sin(E), 0.05)
        
        # Standard deviation
        sigma = sigma_ref * (f**0.45) * g_D / (sin_E**1.3)
        
        # Fade for 0.01% time
        A_scint = 2.6 * sigma
        
        return A_scint
    
    # -- Total atmospheric loss ----------------------------------------------

    def calculate_total_atmospheric_loss(self, frequency_ghz, elevation_deg,
                                         rain_rate=0, water_vapor=7.5,
                                         cloud_content=0.5, 
                                         antenna_diameter_m=1.0,
                                         station_height_km=0.0,
                                         rain_height_km=3.0,
                                         polarization_tilt_deg=45):
        """Combined atmospheric loss breakdown (gaseous + rain + cloud + scint)."""
        A_gas = self.calculate_atmospheric_attenuation(
            frequency_ghz, elevation_deg, water_vapor)
        
        A_rain = self.calculate_rain_attenuation(
            frequency_ghz, elevation_deg, rain_rate, 
            polarization_tilt_deg=polarization_tilt_deg,
            station_height_km=station_height_km,
            rain_height_km=rain_height_km)
        
        A_cloud = self.calculate_cloud_attenuation(
            frequency_ghz, elevation_deg, cloud_content)
        
        A_scint = self.calculate_scintillation(
            frequency_ghz, elevation_deg, antenna_diameter_m)
        
        # Total (statistical combination for rain and scintillation per ITU-R P.618)
        A_total = A_gas + np.sqrt(A_rain**2 + A_scint**2) + A_cloud
        
        return {
            'gaseous_db': A_gas,
            'rain_db': A_rain,
            'cloud_db': A_cloud,
            'scintillation_db': A_scint,
            'total_db': A_total
        }
    
    # -- Antenna gain (S.580-6) ----------------------------------------------

    def calculate_antenna_gain(self, diameter_m, frequency_ghz, efficiency=0.6):
        """Antenna gain in dBi (S.580-6).  G = 20·lg(D) + 20·lg(f) + 10·lg(η) + 20.4"""
        if diameter_m <= 0 or frequency_ghz <= 0:
            return 0.0
        
        # Aperture efficiency
        eta = efficiency
        
        # Correct constant is 20.4 (not 17.8)
        G_dbi = (20 * np.log10(diameter_m) + 
                20 * np.log10(frequency_ghz) + 
                10 * np.log10(eta) + 20.4)
        
        return G_dbi
    
    def calculate_beamwidth(self, diameter_m, frequency_ghz):
        """3-dB beamwidth in degrees.  θ = 21/(f·D)"""
        if diameter_m <= 0 or frequency_ghz <= 0:
            return 180.0  # omnidirectional
        
        theta_3db = 21.0 / (frequency_ghz * diameter_m)
        return theta_3db  # degrees
    
    def calculate_pointing_loss(self, pointing_error_deg, beamwidth_deg):
        """Pointing loss in dB (S.465-6).  L = 12·(θ_e/θ_3dB)²"""
        if beamwidth_deg <= 0:
            return 0.0
        
        L_pointing = 12.0 * (pointing_error_deg / beamwidth_deg)**2
        return L_pointing
    
    # -- EIRP ----------------------------------------------------------------

    def calculate_eirp(self, tx_power_dbw, antenna_gain_dbi, 
                       feed_loss_db=0.5, pointing_loss_db=0):
        """EIRP in dBW.  P_tx + G_tx − L_feed − L_point"""
        # Static value: feed_loss typically 0.5 dB
        eirp_dbw = tx_power_dbw + antenna_gain_dbi - feed_loss_db - pointing_loss_db
        return eirp_dbw
    
    # -- System noise temperature (P.372) ------------------------------------

    def calculate_system_noise_temperature(self, antenna_noise_temp_k,
                                           receiver_noise_temp_k,
                                           feed_loss_db=0.5):
        """System noise temperature in Kelvin.  T_sys = T_ant + T_line + T_rx/L"""
        T_0 = REFERENCE_TEMPERATURES.get('T0', 290.0)
        
        L = 10**(feed_loss_db / 10)  # Convert to linear
        
        T_line = T_0 * (L - 1)
        T_sys = antenna_noise_temp_k + T_line + receiver_noise_temp_k / L
        
        return T_sys
    
    def calculate_antenna_noise_temperature(self, elevation_deg, 
                                            rain_attenuation_db=0):
        """Antenna noise temperature in Kelvin (sky + ground + rain)."""
        # Sky temperature model (simplified)
        if elevation_deg < 10:
            T_sky = 50 + 280 * (10 - elevation_deg) / 10
        elif elevation_deg < 90:
            T_sky = 10 + 40 * (90 - elevation_deg) / 80
        else:
            T_sky = 10  # Cosmic background
        
        # Rain contribution
        if rain_attenuation_db > 0:
            L_rain = 10**(rain_attenuation_db / 10)
            T_m = REFERENCE_TEMPERATURES.get('Tm_rain', 275.0)
            T_ant = T_sky / L_rain + T_m * (1 - 1/L_rain)
        else:
            T_ant = T_sky
        
        return T_ant
    
    # -- G/T figure of merit (S.1328) ----------------------------------------

    def calculate_gt(self, antenna_gain_dbi, system_noise_temp_k, 
                     feed_loss_db=0.5, pointing_loss_db=0):
        """G/T in dB/K.  G − L_feed − L_point − 10·lg(T_sys)"""
        if system_noise_temp_k <= 0:
            return -100.0  # Invalid
        
        gt_db = (antenna_gain_dbi - feed_loss_db - pointing_loss_db - 
                10 * np.log10(system_noise_temp_k))
        return gt_db
    
    # -- C/N₀, C/N, Eb/N₀, margin -------------------------------------------

    def calculate_cn0(self, eirp_dbw, path_loss_db, gt_db_k):
        """C/N₀ in dB-Hz.  EIRP − L_path + G/T − k"""
        k_db = 10 * np.log10(BOLTZMANN)
        
        cn0_db = eirp_dbw - path_loss_db + gt_db_k - k_db
        return cn0_db
    
    def calculate_cn(self, cn0_db, bandwidth_hz):
        """C/N in dB.  C/N₀ − 10·lg(B)"""
        if bandwidth_hz <= 0:
            return cn0_db
        
        cn_db = cn0_db - 10 * np.log10(bandwidth_hz)
        return cn_db
    
    # -- Eb/N₀ ---------------------------------------------------------------

    def calculate_ebn0(self, cn0_db, bit_rate_bps):
        """Eb/N₀ in dB.  C/N₀ − 10·lg(R_b)"""
        if bit_rate_bps <= 0:
            return cn0_db
        
        ebn0_db = cn0_db - 10 * np.log10(bit_rate_bps)
        return ebn0_db
    
    # -- Link margin ---------------------------------------------------------

    def calculate_link_margin(self, ebn0_db, required_ebn0_db):
        """Link margin in dB.  Positive = link closes."""
        return ebn0_db - required_ebn0_db
    
    # -- BER -----------------------------------------------------------------

    def calculate_ber_qpsk(self, ebn0_db):
        """BER for QPSK.  0.5·erfc(√(Eb/N₀))"""
        ebn0_linear = 10**(ebn0_db / 10)
        ber = 0.5 * erfc(np.sqrt(ebn0_linear))
        return ber
    
    def calculate_ber_8psk(self, ebn0_db):
        """BER for 8-PSK modulation"""
        ebn0_linear = 10**(ebn0_db / 10)
        ber = (2/3) * erfc(np.sqrt(0.5 * ebn0_linear * np.sin(np.pi/8)**2))
        return ber
    
    # -- Channel capacity ----------------------------------------------------

    def calculate_shannon_capacity(self, bandwidth_hz, cn_db):
        """Shannon capacity in bps.  C = B·log₂(1 + S/N)"""
        if bandwidth_hz <= 0:
            return 0.0
        
        snr_linear = 10**(cn_db / 10)
        capacity_bps = bandwidth_hz * np.log2(1 + snr_linear)
        return capacity_bps
    
    # -- Power flux density --------------------------------------------------

    def calculate_pfd(self, eirp_dbw, distance_km):
        """PFD in dBW/m² (ITU RR Art. 21)."""
        if distance_km <= 0:
            return 0.0
        
        distance_m = distance_km * 1000
        spreading_loss = 10 * np.log10(4 * np.pi * distance_m**2)
        pfd = eirp_dbw - spreading_loss
        
        return pfd


# --- Downlink budget --------------------------------------------------------

class DownlinkBudget(GeneralLinkBudget):
    """Satellite → ground station link budget."""
    
    def __init__(self, orbit_type='GEO'):
        super().__init__(orbit_type)


# --- Uplink budget ----------------------------------------------------------

class UplinkBudget(GeneralLinkBudget):
    """Ground station → satellite link budget."""
    
    def __init__(self, orbit_type='GEO'):
        super().__init__(orbit_type)
    
    def calculate_intermodulation_carrier(self, c_im_db=-30):
        """Intermodulation C/IM in dB (typical −25 to −35)."""
        return c_im_db


# --- Complete link budget ---------------------------------------------------

class LinkBudget(GeneralLinkBudget):
    """End-to-end link budget combining uplink, downlink, and intermod."""
    
    def __init__(self, orbit_type='GEO'):
        super().__init__(orbit_type)
        self.uplink = UplinkBudget(orbit_type)
        self.downlink = DownlinkBudget(orbit_type)
    
    def calculate_combined_cn0(self, cn0_uplink_db, cn0_downlink_db, 
                               c_im_db=30, bandwidth_hz=36e6):
        """Combined C/N₀ via reciprocal sum (S.1328)."""
        # Convert to linear
        cn0_up_linear = 10**(cn0_uplink_db / 10)
        cn0_dn_linear = 10**(cn0_downlink_db / 10)
        
        # Convert C/IM [dB] to C/IM0 [dB-Hz] by adding bandwidth
        # C/IM0 = C/IM + 10*log10(B)
        c_im0_db = c_im_db + 10 * np.log10(bandwidth_hz)
        c_im0_linear = 10**(c_im0_db / 10)
        
        # Reciprocal sum (now all in same units: dB-Hz)
        cn0_total_linear = 1 / (1/cn0_up_linear + 1/cn0_dn_linear + 1/c_im0_linear)
        
        # Convert back to dB
        cn0_total_db = 10 * np.log10(cn0_total_linear)
        
        return cn0_total_db
    
    def calculate_complete_link(self, 
                                gs_tx_power_dbw=20,
                                gs_antenna_diameter_m=2.4,
                                uplink_frequency_ghz=14.0,
                                sat_gt_db=-8,
                                sat_eirp_dbw=40,
                                gs_rx_antenna_diameter_m=2.4,
                                downlink_frequency_ghz=12.0,
                                gs_rx_noise_temp_k=120,
                                lat_gs_deg=40.0,
                                lon_gs_deg=10.0,
                                lon_sat_deg=0.0,
                                rain_rate=25,
                                bit_rate_mbps=10,
                                required_ebn0_db=6.0,
                                c_im_db=-30):
        """Full uplink + downlink budget returning a results dict."""
        # Geometry calculations
        distance_km = self.geometry.calculate_slant_range(
            lat_gs_deg, lon_gs_deg, lon_sat_deg)
        elevation_deg = self.geometry.calculate_elevation_angle(
            lat_gs_deg, lon_gs_deg, lon_sat_deg)
        
        # --- UPLINK (#1-#9) ---
        
        # #1: Ground station EIRP
        gs_tx_gain = self.calculate_antenna_gain(
            gs_antenna_diameter_m, uplink_frequency_ghz)
        gs_eirp = self.calculate_eirp(gs_tx_power_dbw, gs_tx_gain)
        
        # #2: Uplink FSPL
        uplink_fspl = self.calculate_fspl(uplink_frequency_ghz, distance_km)
        
        # #3: Uplink atmospheric losses
        uplink_atm = self.calculate_total_atmospheric_loss(
            uplink_frequency_ghz, elevation_deg, rain_rate,
            antenna_diameter_m=gs_antenna_diameter_m)
        uplink_total_loss = uplink_fspl + uplink_atm['total_db']
        
        # #4: Satellite G/T (given)
        # #5: Uplink C/N0
        uplink_cn0 = self.calculate_cn0(gs_eirp, uplink_total_loss, sat_gt_db)
        
        # #6: Uplink C/N
        uplink_cn = self.calculate_cn(uplink_cn0, 36e6)
        
        # #7: Uplink Eb/N0
        bit_rate_bps = bit_rate_mbps * 1e6
        uplink_ebn0 = self.calculate_ebn0(uplink_cn0, bit_rate_bps)
        
        # #8: Uplink margin
        uplink_margin = self.calculate_link_margin(uplink_ebn0, required_ebn0_db)
        
        # --- DOWNLINK (#10-#17) ---
        
        # #10: Satellite EIRP (given)
        # #11: Downlink FSPL
        downlink_fspl = self.calculate_fspl(downlink_frequency_ghz, distance_km)
        
        # #12: Downlink atmospheric losses
        downlink_atm = self.calculate_total_atmospheric_loss(
            downlink_frequency_ghz, elevation_deg, rain_rate,
            antenna_diameter_m=gs_rx_antenna_diameter_m)
        downlink_total_loss = downlink_fspl + downlink_atm['total_db']
        
        # #13: Ground station G/T
        gs_rx_gain = self.calculate_antenna_gain(
            gs_rx_antenna_diameter_m, downlink_frequency_ghz)
        gs_ant_noise = self.calculate_antenna_noise_temperature(
            elevation_deg, downlink_atm['rain_db'])
        gs_sys_noise = self.calculate_system_noise_temperature(
            gs_ant_noise, gs_rx_noise_temp_k)
        gs_gt = self.calculate_gt(gs_rx_gain, gs_sys_noise)
        
        # #14: Downlink C/N0
        downlink_cn0 = self.calculate_cn0(sat_eirp_dbw, downlink_total_loss, gs_gt)
        
        # #15: Downlink C/N
        downlink_cn = self.calculate_cn(downlink_cn0, 36e6)
        
        # #16: Downlink Eb/N0
        downlink_ebn0 = self.calculate_ebn0(downlink_cn0, bit_rate_bps)
        
        # #17: Downlink margin
        downlink_margin = self.calculate_link_margin(downlink_ebn0, required_ebn0_db)
        
        # --- TOTAL LINK (#18-#21) ---
        
        # #18: Combined C/N0
        # Pass bandwidth for C/IM to C/IM0 conversion
        total_cn0 = self.calculate_combined_cn0(uplink_cn0, downlink_cn0, c_im_db, 
                                                bandwidth_hz=36e6)
        
        # #19: Total C/N
        total_cn = self.calculate_cn(total_cn0, 36e6)
        
        # #20: Total Eb/N0
        total_ebn0 = self.calculate_ebn0(total_cn0, bit_rate_bps)
        
        # #21: Total margin
        total_margin = self.calculate_link_margin(total_ebn0, required_ebn0_db)
        
        # BER calculation
        ber = self.calculate_ber_qpsk(total_ebn0)
        
        # Build results dictionary
        results = {
            # Geometry
            'orbit_type': self.geometry.orbit_type,
            'distance_km': distance_km,
            'elevation_deg': elevation_deg,
            'doppler_khz': self.geometry.calculate_doppler_shift(
                downlink_frequency_ghz, elevation_deg),
            'propagation_delay_ms': self.geometry.calculate_propagation_delay(distance_km),
            
            # Uplink
            'gs_eirp_dbw': gs_eirp,
            'uplink_fspl_db': uplink_fspl,
            'uplink_atm_db': uplink_atm['total_db'],
            'uplink_cn0_db': uplink_cn0,
            'uplink_cn_db': uplink_cn,
            'uplink_ebn0_db': uplink_ebn0,
            'uplink_margin_db': uplink_margin,
            
            # Downlink
            'sat_eirp_dbw': sat_eirp_dbw,
            'downlink_fspl_db': downlink_fspl,
            'downlink_atm_db': downlink_atm['total_db'],
            'gs_gt_db': gs_gt,
            'downlink_cn0_db': downlink_cn0,
            'downlink_cn_db': downlink_cn,
            'downlink_ebn0_db': downlink_ebn0,
            'downlink_margin_db': downlink_margin,
            
            # Total
            'total_cn0_db': total_cn0,
            'total_cn_db': total_cn,
            'total_ebn0_db': total_ebn0,
            'total_margin_db': total_margin,
            'ber': ber,
            
            # Link status
            'link_closes': total_margin > 0,
            'limiting_link': 'uplink' if uplink_cn0 < downlink_cn0 else 'downlink'
        }
        
        return results
    
    def calculate_geometry(self, lat_gs_deg, lon_gs_deg, lon_sat_deg, altitude_km=None):
        """Return dict of slant_range, elevation, azimuth, and polarization angle."""
        return {
            'slant_range_km': self.geometry.calculate_slant_range(
                lat_gs_deg, lon_gs_deg, lon_sat_deg, altitude_km
            ),
            'elevation_deg': self.geometry.calculate_elevation_angle(
                lat_gs_deg, lon_gs_deg, lon_sat_deg, altitude_km
            ),
            'azimuth_deg': self.geometry.calculate_azimuth_angle(
                lat_gs_deg, lon_gs_deg, lon_sat_deg
            ),
            'polarization_angle_deg': self.geometry.calculate_polarization_angle(
                lat_gs_deg, lon_gs_deg, lon_sat_deg
            )
        }
    
    def complete_link_budget(self, params):
        """Full link budget from a parameter dict (used by the GUI)."""
        # Extract parameters with defaults
        gs_tx_power_dbw = params.get('gs_tx_power_dbw', 20)
        gs_antenna_diameter_m = params.get('gs_antenna_diameter_m', 2.4)
        gs_antenna_diameter_m_rx = params.get('gs_antenna_diameter_m_rx', gs_antenna_diameter_m)
        gs_antenna_efficiency = params.get('gs_antenna_efficiency', 0.6)
        uplink_frequency_ghz = params.get('uplink_frequency_ghz', 14.0)
        downlink_frequency_ghz = params.get('downlink_frequency_ghz', 12.0)
        
        sat_power_dbw = params.get('sat_power_dbw', 10)
        sat_antenna_gain_dbi = params.get('sat_antenna_gain_dbi', 35)
        sat_rx_gain_dbi = params.get('sat_rx_gain_dbi', 30)
        sat_noise_figure_db = params.get('sat_noise_figure_db', 2.5)
        
        distance_km = params.get('distance_km', 42000)
        elevation_deg = params.get('elevation_deg', 30)
        bandwidth_hz = params.get('bandwidth_hz', 36e6)
        data_rate_bps = params.get('data_rate_bps', 10e6)
        
        uplink_rain_rate = params.get('uplink_rain_rate', 0)
        downlink_rain_rate = params.get('downlink_rain_rate', 0)
        
        gs_lna_temp_k = params.get('gs_lna_temp_k', 120)
        ebn0_required_db = params.get('ebn0_required_db', 8.0)
        
        # Losses
        gs_feed_loss_db = params.get('gs_feed_loss_db', 0.5)
        gs_pointing_loss_tx_db = params.get('gs_pointing_loss_tx_db',
                                              params.get('gs_pointing_loss_db', 0.3))  # backward compat
        gs_pointing_loss_rx_db = params.get('gs_pointing_loss_rx_db',
                                              params.get('gs_pointing_loss_db', 0.2))  # backward compat
        polarization_loss_db = params.get('polarization_loss_db', 0.2)
        input_backoff_db = params.get('input_backoff_db', 1.0)
        output_backoff_db = params.get('output_backoff_db', 2.5)
        
        # Atmospheric parameters (USER INPUTS - not hardcoded)
        gs_height_km = params.get('gs_height_km', 0.0)              # Station height above sea level
        water_vapor_density = params.get('water_vapor_density', 7.5)  # g/m³ (ITU-R P.836)
        cloud_liquid_water = params.get('cloud_liquid_water', 0.5)   # kg/m² (ITU-R P.840)
        rain_height_km = params.get('rain_height_km', 3.0)          # km (ITU-R P.839)
        polarization_tilt_deg = params.get('polarization_tilt_deg', 45)  # degrees
        
        # --- Uplink (#1-#9) ---
        
        # #1: Ground station antenna gain
        gs_tx_gain = self.calculate_antenna_gain(
            gs_antenna_diameter_m, uplink_frequency_ghz, gs_antenna_efficiency)
        
        # #2: Ground station EIRP (IBO is subtracted here, consistent with OBO handling)
        # IBO reduces effective transmitted power, not path loss
        gs_eirp = self.calculate_eirp(
            gs_tx_power_dbw - input_backoff_db, gs_tx_gain, gs_feed_loss_db, gs_pointing_loss_tx_db)
        
        # #3: Uplink FSPL
        uplink_fspl = self.calculate_fspl(uplink_frequency_ghz, distance_km)
        
        # #4: Atmospheric losses (using all USER INPUT parameters)
        uplink_atm = self.calculate_total_atmospheric_loss(
            uplink_frequency_ghz, elevation_deg, uplink_rain_rate,
            water_vapor=water_vapor_density,
            cloud_content=cloud_liquid_water,
            antenna_diameter_m=gs_antenna_diameter_m,
            station_height_km=gs_height_km,
            rain_height_km=rain_height_km,
            polarization_tilt_deg=polarization_tilt_deg)
        
        # #5: Satellite noise temperature and G/T
        sat_noise_temp_k = 290 * (10**(sat_noise_figure_db/10) - 1)
        sat_ant_temp_k = params.get('sat_antenna_temp_k', 290)
        sat_sys_temp_k = sat_ant_temp_k + sat_noise_temp_k
        sat_gt_db = sat_rx_gain_dbi - 10 * np.log10(sat_sys_temp_k)
        
        # Uplink total path loss (pure propagation losses)
        # L_total = FSPL + A_atm + L_pol (pointing already in EIRP, IBO already subtracted)
        uplink_total_loss = (uplink_fspl + uplink_atm['total_db'] + 
                            polarization_loss_db)
        
        # #5: Uplink C/N0
        uplink_cn0 = self.calculate_cn0(gs_eirp, uplink_total_loss, sat_gt_db)
        
        # #6: Uplink C/N
        uplink_cn = self.calculate_cn(uplink_cn0, bandwidth_hz)
        
        # #7: Uplink Eb/N0
        uplink_ebn0 = self.calculate_ebn0(uplink_cn0, data_rate_bps)
        
        # #8: Uplink margin
        uplink_margin = self.calculate_link_margin(uplink_ebn0, ebn0_required_db)
        
        uplink_results = {
            'gs_eirp_dbw': gs_eirp,
            'gs_tx_gain_dbi': gs_tx_gain,
            'gs_antenna_gain_dbi': gs_tx_gain,  # Alias for compatibility
            'fspl_db': uplink_fspl,
            'atmospheric_atten_db': uplink_atm['gaseous_db'],
            'rain_atten_db': uplink_atm['rain_db'],
            'cloud_atten_db': uplink_atm['cloud_db'],
            'scintillation_db': uplink_atm['scintillation_db'],
            'polarization_loss_db': polarization_loss_db,
            'input_backoff_db': input_backoff_db,
            'total_path_loss_db': uplink_total_loss,
            'sat_gt_db': sat_gt_db,
            'sat_noise_temp_k': sat_sys_temp_k,
            'uplink_cn0_db': uplink_cn0,
            'uplink_cn_db': uplink_cn,
            'uplink_ebn0_db': uplink_ebn0,
            'uplink_margin_db': uplink_margin,
        }
        
        # --- Downlink (#10-#17) ---
        
        # #10: Satellite EIRP
        sat_eirp = sat_power_dbw + sat_antenna_gain_dbi - output_backoff_db
        
        # #11: Downlink FSPL
        downlink_fspl = self.calculate_fspl(downlink_frequency_ghz, distance_km)
        
        # #12: Atmospheric losses (using all USER INPUT parameters)
        downlink_atm = self.calculate_total_atmospheric_loss(
            downlink_frequency_ghz, elevation_deg, downlink_rain_rate,
            water_vapor=water_vapor_density,
            cloud_content=cloud_liquid_water,
            antenna_diameter_m=gs_antenna_diameter_m_rx,
            station_height_km=gs_height_km,
            rain_height_km=rain_height_km,
            polarization_tilt_deg=polarization_tilt_deg)
        
        # #13: Ground station G/T
        gs_rx_gain = self.calculate_antenna_gain(
            gs_antenna_diameter_m_rx, downlink_frequency_ghz, gs_antenna_efficiency)
        gs_ant_noise = self.calculate_antenna_noise_temperature(
            elevation_deg, downlink_atm['rain_db'])
        gs_sys_noise = self.calculate_system_noise_temperature(
            gs_ant_noise, gs_lna_temp_k, gs_feed_loss_db)
        gs_gt = self.calculate_gt(gs_rx_gain, gs_sys_noise, gs_feed_loss_db, gs_pointing_loss_rx_db)
        
        # Downlink total loss 
        # L_total = FSPL + A_atm + L_pol (pointing already in G/T)
        downlink_total_loss = (downlink_fspl + downlink_atm['total_db'] +
                              polarization_loss_db)
        
        # #14: Downlink C/N0
        downlink_cn0 = self.calculate_cn0(sat_eirp, downlink_total_loss, gs_gt)
        
        # #15: Downlink C/N
        downlink_cn = self.calculate_cn(downlink_cn0, bandwidth_hz)
        
        # #16: Downlink Eb/N0
        downlink_ebn0 = self.calculate_ebn0(downlink_cn0, data_rate_bps)
        
        # #17: Downlink margin
        downlink_margin = self.calculate_link_margin(downlink_ebn0, ebn0_required_db)
        
        downlink_results = {
            'sat_eirp_dbw': sat_eirp,
            'gs_antenna_gain_dbi': gs_rx_gain,
            'fspl_db': downlink_fspl,
            'atmospheric_atten_db': downlink_atm['gaseous_db'],
            'rain_atten_db': downlink_atm['rain_db'],
            'cloud_atten_db': downlink_atm['cloud_db'],
            'scintillation_db': downlink_atm['scintillation_db'],
            'polarization_loss_db': polarization_loss_db,
            'output_backoff_db': output_backoff_db,
            'total_path_loss_db': downlink_total_loss,
            'gs_gt_db': gs_gt,
            'system_temp_k': gs_sys_noise,
            'downlink_cn0_db': downlink_cn0,
            'downlink_cn_db': downlink_cn,
            'downlink_ebn0_db': downlink_ebn0,
            'downlink_margin_db': downlink_margin,
        }
        
        # --- Total link (#18-#21) ---
        
        # Get C/IM from params (user input, default 30 dB)
        c_im_db = params.get('c_im_db', 30)
        
        # #18: Combined C/N0
        # Pass bandwidth for C/IM to C/IM0 conversion
        total_cn0 = self.calculate_combined_cn0(uplink_cn0, downlink_cn0, 
                                                c_im_db=c_im_db, bandwidth_hz=bandwidth_hz)
        
        # #19: Total C/N
        total_cn = self.calculate_cn(total_cn0, bandwidth_hz)
        
        # #20: Total Eb/N0
        total_ebn0 = self.calculate_ebn0(total_cn0, data_rate_bps)
        
        # #21: Total margin
        total_margin = self.calculate_link_margin(total_ebn0, ebn0_required_db)
        
        # BER calculation
        ber = self.calculate_ber_qpsk(total_ebn0)
        
        # Add data_rate_mbps to uplink/downlink for display
        uplink_results['data_rate_mbps'] = data_rate_bps / 1e6
        downlink_results['data_rate_mbps'] = data_rate_bps / 1e6
        
        return {
            'uplink': uplink_results,
            'downlink': downlink_results,
            # Top-level keys for backward compatibility with main_advanced.py
            'uplink_cn0_db': uplink_cn0,
            'downlink_cn0_db': downlink_cn0,
            'total_cn0_db': total_cn0,
            'total_cn_db': total_cn,
            'total_ebn0_db': total_ebn0,
            'total_margin_db': total_margin,
            'ber': ber,
            'link_closes': total_margin > 0,
            'limiting_link': 'uplink' if uplink_cn0 < downlink_cn0 else 'downlink',
            'distance_km': distance_km,
            'elevation_deg': elevation_deg,
        }


# --- Monte Carlo simulation -------------------------------------------------

class MonteCarloSimulator:
    """Statistical link availability analysis via Monte Carlo (P.618, P.837)."""
    
    def __init__(self, link_budget_calculator):
        self.link_calc = link_budget_calculator
        self.mc_params = MONTE_CARLO_PARAMS

    def generate_rain_samples(self, n_samples, climate_zone='Temperate'):
        """Random rain rates from a composite dry/wet model (P.837)."""
        dist = self.mc_params['rain_distribution'].get(
            climate_zone, self.mc_params['rain_distribution']['Temperate'])
        
        scale = dist['scale']
        shape = dist['shape']
        
        # ITU-R P.837: fraction of time with rain varies by climate
        # Approximate: Tropical ~5%, Mediterranean ~3%, Temperate ~2%, Polar ~1%
        rain_prob = {'Tropical': 0.05, 'Mediterranean': 0.03, 'Continental': 0.025,
                     'Temperate': 0.02, 'Polar': 0.01}
        p_rain = rain_prob.get(climate_zone, 0.02)
        
        # Generate binary rain/no-rain
        is_raining = np.random.random(n_samples) < p_rain
        
        # Generate rain rates for rainy periods (Weibull distribution per ITU-R P.837)
        rain_rates = np.zeros(n_samples)
        n_rainy = np.sum(is_raining)
        if n_rainy > 0:
            rain_rates[is_raining] = np.random.weibull(shape, n_rainy) * scale
            
        return rain_rates
    
    def run_simulation(self, params, n_simulations=10000, climate_zone='Temperate'):
        """Run Monte Carlo varying rain, cloud, vapor, and IBO."""
        freq_ghz = params.get('downlink_frequency_ghz', 12.0)
        elevation_deg = params.get('elevation_deg', 45.0)
        base_margin = params.get('link_margin_db', 10.0)
        water_vapor = params.get('water_vapor_density', 7.5)
        station_height = params.get('gs_height_km', 0.0)
        rain_height = params.get('rain_height_km', 3.0)
        pol_tilt = params.get('polarization_tilt_deg', 45.0)
        antenna_diameter = params.get('gs_antenna_diameter_m', 1.2)
        cloud_base = params.get('cloud_liquid_water', 0.3)
        
        # IBO parameters for power control uncertainty
        ibo_nominal = params.get('input_backoff_db', 1.0)
        ibo_std = params.get('ibo_uncertainty_db', 0.5)  # ±0.5 dB typical
        
        # Generate random atmospheric conditions
        rain_rates = self.generate_rain_samples(n_simulations, climate_zone)
        
        # Random cloud content (log-normal, correlated with rain)
        cloud_contents = np.random.lognormal(
            mean=np.log(max(cloud_base, 0.01)), sigma=0.5, size=n_simulations)
        cloud_contents = np.where(rain_rates > 5, cloud_contents * 1.5, cloud_contents)
        cloud_contents = np.clip(cloud_contents, 0, 3.0)
        
        # Random water vapor variation (normal, ±20%)
        water_vapors = np.random.normal(water_vapor, water_vapor * 0.2, n_simulations)
        water_vapors = np.clip(water_vapors, 0.5, 30.0)
        
        # Random IBO variation (power control uncertainty / HPA gain drift)
        ibo_variations = np.random.normal(ibo_nominal, ibo_std, n_simulations)
        ibo_variations = np.clip(ibo_variations, 0.0, ibo_nominal + 3 * ibo_std)
        
        # Calculate total attenuation for each sample
        total_attenuations = np.zeros(n_simulations)
        gaseous_att = np.zeros(n_simulations)
        rain_att = np.zeros(n_simulations)
        cloud_att = np.zeros(n_simulations)
        scint_att = np.zeros(n_simulations)
        ibo_excess = np.zeros(n_simulations)  # IBO deviation from nominal
        
        for i in range(n_simulations):
            atm = self.link_calc.calculate_total_atmospheric_loss(
                frequency_ghz=freq_ghz,
                elevation_deg=elevation_deg,
                rain_rate=rain_rates[i],
                water_vapor=water_vapors[i],
                cloud_content=cloud_contents[i],
                antenna_diameter_m=antenna_diameter,
                station_height_km=station_height,
                rain_height_km=rain_height,
                polarization_tilt_deg=pol_tilt
            )
            total_attenuations[i] = atm['total_db']
            gaseous_att[i] = atm['gaseous_db']
            rain_att[i] = atm['rain_db']
            cloud_att[i] = atm['cloud_db']
            scint_att[i] = atm['scintillation_db']
            ibo_excess[i] = ibo_variations[i] - ibo_nominal  # Excess IBO (reduces margin)
        
        # Calculate link margins
        # base_margin is already the clear-sky margin
        # Under rain: margin = base_margin - (excess_attenuation)
        clear_sky_atten = self.link_calc.calculate_total_atmospheric_loss(
            freq_ghz, elevation_deg, rain_rate=0, water_vapor=water_vapor,
            cloud_content=cloud_base, antenna_diameter_m=antenna_diameter,
            station_height_km=station_height, rain_height_km=rain_height,
            polarization_tilt_deg=pol_tilt)['total_db']
        
        excess_attenuations = total_attenuations - clear_sky_atten
        # Include IBO power control uncertainty in margin degradation
        link_margins = base_margin - excess_attenuations - ibo_excess
        
        # Statistics
        outage_mask = link_margins < 0
        availability = (1 - np.mean(outage_mask)) * 100
        
        # Percentiles for CDF
        percentiles = np.arange(0, 100.1, 0.1)
        margin_percentiles = np.percentile(link_margins, percentiles)
        
        # Confidence intervals
        ci_results = {}
        for ci in self.mc_params['confidence_levels']:
            pct = (1 - ci) * 100
            ci_results[ci] = {
                'margin_threshold': np.percentile(link_margins, pct),
                'rain_rate_threshold': np.percentile(rain_rates, 100 - pct),
                'availability_pct': ci * 100,
            }
        
        return {
            'link_margins': link_margins,
            'total_attenuations': total_attenuations,
            'rain_rates': rain_rates,
            'rain_attenuations': rain_att,
            'gaseous_attenuations': gaseous_att,
            'cloud_attenuations': cloud_att,
            'scintillation_attenuations': scint_att,
            'ibo_variations': ibo_variations,
            'ibo_excess': ibo_excess,
            'excess_attenuations': excess_attenuations,
            'availability_pct': availability,
            'mean_margin': np.mean(link_margins),
            'std_margin': np.std(link_margins),
            'min_margin': np.min(link_margins),
            'max_margin': np.max(link_margins),
            'median_margin': np.median(link_margins),
            'margin_percentiles': margin_percentiles,
            'percentiles': percentiles,
            'confidence_intervals': ci_results,
            'n_simulations': n_simulations,
            'outage_samples': np.sum(outage_mask),
            'climate_zone': climate_zone,
            'clear_sky_atten_db': clear_sky_atten,
        }


# --- Fade dynamics (P.1623-1) -----------------------------------------------

class FadeDynamicsAnalyzer:
    """Rain fade time-series synthesis and duration statistics (P.1623-1)."""
    
    def __init__(self, link_budget_calculator):
        self.link_calc = link_budget_calculator
        self.fd_params = FADE_DYNAMICS_PARAMS
    
    def generate_fade_time_series(self, duration_hours=24, sample_interval_sec=1,
                                   freq_ghz=12.0, elevation_deg=45.0,
                                   rain_rate_001=42.0, station_height_km=0.0,
                                   rain_height_km=3.0, pol_tilt_deg=45.0):
        """Synthesize a rain fade time series via Markov chain (P.1623-1)."""
        n_samples = int(duration_hours * 3600 / sample_interval_sec)
        time_seconds = np.arange(n_samples) * sample_interval_sec
        
        # Generate exponentially correlated Gaussian noise
        # ITU-R P.1623-1: correlation time ~60 seconds for rain
        tau_c = self.fd_params['fade_slope']['correlation_time']
        rho = np.exp(-sample_interval_sec / tau_c)
        
        # AR(1) process for correlated noise
        noise = np.zeros(n_samples)
        noise[0] = np.random.normal()
        for i in range(1, n_samples):
            noise[i] = rho * noise[i-1] + np.sqrt(1 - rho**2) * np.random.normal()
        
        # Transform Gaussian to rain rate via ITU-R P.837 statistics
        # P(R > r) = P0 * exp(-r / r_scale)  (simplified exponential model)
        # Map quantiles: Phi(noise) → P(R > r)
        from scipy.stats import norm
        probabilities = norm.cdf(noise)
        
        # Map probability to rain rate using inverse exponential distribution
        # Scale so that at 0.01% exceedance → rain_rate_001
        r_scale = rain_rate_001 / (-np.log(0.0001))  # Scale parameter
        rain_rates = np.zeros(n_samples)
        
        # Only ~2-5% of time has rain
        rain_threshold = 0.97  # 3% rain probability
        rainy = probabilities > rain_threshold
        rain_probs = (probabilities[rainy] - rain_threshold) / (1 - rain_threshold)
        rain_rates[rainy] = -r_scale * np.log(1 - rain_probs * 0.9999 + 1e-10)
        rain_rates = np.clip(rain_rates, 0, 200)
        
        # Calculate fade attenuation for each sample
        attenuations = np.zeros(n_samples)
        for i in range(n_samples):
            if rain_rates[i] > 0.1:
                attenuations[i] = self.link_calc.calculate_rain_attenuation(
                    freq_ghz, elevation_deg, rain_rates[i],
                    polarization_tilt_deg=pol_tilt_deg,
                    station_height_km=station_height_km,
                    rain_height_km=rain_height_km)
        
        return {
            'time_seconds': time_seconds,
            'time_hours': time_seconds / 3600,
            'rain_rates': rain_rates,
            'attenuations_db': attenuations,
            'duration_hours': duration_hours,
            'sample_interval_sec': sample_interval_sec,
        }
    
    def analyze_fade_events(self, attenuations_db, margin_db, sample_interval_sec=1):
        """Detect individual fade events and compute duration statistics."""
        # Identify outage periods (attenuation > margin)
        in_outage = attenuations_db > margin_db
        
        # Find fade event start/end indices
        transitions = np.diff(in_outage.astype(int))
        starts = np.where(transitions == 1)[0] + 1
        ends = np.where(transitions == -1)[0] + 1
        
        # Handle edge cases
        if in_outage[0]:
            starts = np.concatenate([[0], starts])
        if in_outage[-1]:
            ends = np.concatenate([ends, [len(in_outage)]])
        
        # Ensure equal lengths
        n_events = min(len(starts), len(ends))
        starts = starts[:n_events]
        ends = ends[:n_events]
        
        # Calculate event durations
        durations_sec = (ends - starts) * sample_interval_sec
        
        # Peak attenuation per event
        peak_attens = np.array([np.max(attenuations_db[s:e]) for s, e in zip(starts, ends)]) if n_events > 0 else np.array([])
        
        # Fade duration distribution (ITU-R P.1623-1)
        duration_bins = np.array(self.fd_params['duration_bins'])
        duration_hist = np.zeros(len(duration_bins))
        for i, threshold in enumerate(duration_bins):
            duration_hist[i] = np.sum(durations_sec >= threshold) if n_events > 0 else 0
        
        total_time = len(attenuations_db) * sample_interval_sec
        total_outage = np.sum(in_outage) * sample_interval_sec
        availability = (1 - total_outage / total_time) * 100
        
        return {
            'n_events': n_events,
            'durations_sec': durations_sec,
            'peak_attenuations_db': peak_attens,
            'mean_duration_sec': np.mean(durations_sec) if n_events > 0 else 0,
            'max_duration_sec': np.max(durations_sec) if n_events > 0 else 0,
            'min_duration_sec': np.min(durations_sec) if n_events > 0 else 0,
            'total_outage_sec': total_outage,
            'availability_pct': availability,
            'duration_bins': duration_bins,
            'duration_exceedance': duration_hist,
            'outage_fraction': total_outage / total_time,
        }
    
    def compute_fade_exceedance(self, freq_ghz=12.0, elevation_deg=45.0,
                                 rain_rate_001=42.0, station_height_km=0.0,
                                 rain_height_km=3.0, pol_tilt_deg=45.0):
        """Fade depth vs. percentage of time exceeded (P.618-14 §2.2.1.1)."""
        # ITU-R P.618-14: time percentages from 0.001% to 50%
        percentages = np.array([50, 30, 20, 10, 5, 3, 2, 1, 0.5, 0.3, 0.2, 
                                0.1, 0.05, 0.03, 0.02, 0.01, 0.005, 0.003, 0.001])
        
        # Rain rate scaling: R(p) = R(0.01) * (p/0.01)^(-0.655 + 0.033*ln(p) - ...)
        # Simplified ITU-R P.837 scaling from 0.01% reference
        attn_001 = self.link_calc.calculate_rain_attenuation(
            freq_ghz, elevation_deg, rain_rate_001,
            polarization_tilt_deg=pol_tilt_deg,
            station_height_km=station_height_km,
            rain_height_km=rain_height_km)
        
        # ITU-R P.618-14 Eq. (10): scaling from A(0.01%)
        fade_depths = []
        for p in percentages:
            if p >= 1:
                # Low fade regime
                C0 = 0.12
                beta = 0.55 if p >= 5 else 0.7
                ratio = C0 * (p / 0.01)**(-((0.655 + 0.033 * np.log(p) - 
                         0.045 * np.log(attn_001 + 0.001) - beta * (1 - p) * 
                         np.sin(np.radians(elevation_deg)))))
            else:
                # ITU-R P.618 Eq. (10) for p < 1%
                beta_val = 0.0
                if p < 1 and attn_001 >= 0.01:
                    beta_val = -0.005 * (np.log10(p) + 2)
                    
                C1 = 0.12 + 0.4 * (1 - np.cos(2 * np.arctan(
                    1e-7 * (rain_rate_001**0.7) * (freq_ghz**0.19))))
                ratio = C1 * (p / 0.01) ** (-(0.655 + 0.033 * np.log(p) - 
                         0.045 * np.log(attn_001 + 0.001) + beta_val))
            
            fade_db = attn_001 * max(ratio, 0)
            fade_depths.append(fade_db)
        
        return {
            'percentages': percentages,
            'fade_depths_db': np.array(fade_depths),
            'attenuation_001_pct': attn_001,
        }


# --- Maseng-Bakken rain fade synthesizer (P.1853-2) ------------------------

class MasengBakkenSimulator:
    """Stochastic rain fade time-series synthesizer (Maseng-Bakken / P.1853-2)."""
    
    def __init__(self, link_budget_calculator):
        self.link_calc = link_budget_calculator
        self.params = MASENG_BAKKEN_PARAMS
    
    def _get_beta(self, freq_ghz):
        """Get correlation time constant β for frequency."""
        betas = self.params['beta_seconds']
        if freq_ghz < 6:
            return betas['C-band']
        elif freq_ghz < 18:
            return betas['Ku-band']
        elif freq_ghz < 32:
            return betas['Ka-band']
        elif freq_ghz < 45:
            return betas['Q-band']
        else:
            return betas['V-band']
    
    def _get_climate_params(self, climate_zone='K'):
        """Get lognormal rain parameters for climate zone."""
        zones = self.params['climate_zones']
        return zones.get(climate_zone, zones['K'])
    
    def synthesize(self, duration_hours=6, dt=1.0,
                   freq_ghz=12.0, elevation_deg=30.0,
                   rain_rate_001=42.0, climate_zone='K',
                   station_height_km=0.0, rain_height_km=3.0,
                   pol_tilt_deg=45.0, link_margin_db=10.0,
                   seed=None, force_rain_prob=None):
        """Synthesize a rain fade time series and compute outage statistics."""
        if seed is not None:
            np.random.seed(seed)
        
        n_samples = int(duration_hours * 3600 / dt)
        time_sec = np.arange(n_samples) * dt
        
        # ── Step 1: Get Maseng-Bakken parameters ──
        beta = self._get_beta(freq_ghz)
        climate = self._get_climate_params(climate_zone)
        sigma_ln = climate['sigma_ln']
        
        # Correlation coefficient for AR(1)
        rho = np.exp(-dt / beta)
        
        # ── Step 2: Generate correlated Gaussian process x(t) ──
        # x(t+dt) = rho * x(t) + sqrt(1 - rho^2) * w(t)
        x = np.zeros(n_samples)
        x[0] = np.random.normal(0, 1)
        innovation_scale = np.sqrt(1 - rho ** 2)
        
        white_noise = np.random.normal(0, 1, n_samples)
        for i in range(1, n_samples):
            x[i] = rho * x[i - 1] + innovation_scale * white_noise[i]
        
        # ── Step 3: Non-linear transform to rain attenuation ──
        # A(t) = A_001 * 10^(sigma_ln * Φ^-1(U(x(t))) / 20)
        # Simplified: use threshold to model rain on/off
        
        # Compute baseline attenuation A_001 from link budget
        A_001 = self.link_calc.calculate_rain_attenuation(
            freq_ghz, elevation_deg, rain_rate_001,
            polarization_tilt_deg=pol_tilt_deg,
            station_height_km=station_height_km,
            rain_height_km=rain_height_km)
        
        if A_001 <= 0:
            A_001 = 1.0  # Fallback
        
        # Rain occurrence threshold
        if force_rain_prob is not None:
            # Inverse CDF (ppf) of (1 - prob) gives the threshold
            import scipy.stats as stats
            rain_threshold = stats.norm.ppf(1.0 - force_rain_prob)
        else:
            rain_threshold = 1.88  # Gaussian quantile for ~97th percentile (3% rain)
        
        # Map Gaussian process to attenuation
        attenuation = np.zeros(n_samples)
        rain_rate = np.zeros(n_samples)
        
        rainy_mask = x > rain_threshold
        if np.any(rainy_mask):
            # Map exceedance above threshold to fade depth
            # Uses lognormal mapping: fade grows exponentially with x
            excess = x[rainy_mask] - rain_threshold
            # A = A_001 * 10^(sigma_ln * excess / 10)
            attenuation[rainy_mask] = A_001 * np.power(10, sigma_ln * excess / 10.0)
            attenuation = np.clip(attenuation, 0, A_001 * 10)  # Cap at 10x baseline
            
            # Corresponding rain rates (inverse of attenuation model)
            rain_rate[rainy_mask] = rain_rate_001 * np.power(
                np.clip(attenuation[rainy_mask] / max(A_001, 0.01), 0.01, 100), 0.8)
        
        # ── Step 4: Fade slope (dA/dt) ──
        fade_slope = np.gradient(attenuation, dt)
        
        # ── Step 5: Event detection with hysteresis ──
        events = self._detect_events(attenuation, link_margin_db, dt)
        
        # ── Step 6: Statistics ──
        total_outage_sec = np.sum(attenuation > link_margin_db) * dt
        availability = 100.0 * (1.0 - total_outage_sec / (duration_hours * 3600))
        
        # CCDF of attenuation
        ccdf_thresholds = np.linspace(0, np.max(attenuation) * 1.1 + 0.1, 200)
        ccdf_values = np.array([
            100.0 * np.mean(attenuation > th) for th in ccdf_thresholds])
        
        # Fade duration CDF
        if len(events['durations_sec']) > 0:
            sorted_dur = np.sort(events['durations_sec'])
            dur_cdf = np.arange(1, len(sorted_dur) + 1) / len(sorted_dur)
        else:
            sorted_dur = np.array([0])
            dur_cdf = np.array([0])
        
        return {
            'time_sec': time_sec,
            'time_hours': time_sec / 3600.0,
            'attenuation_db': attenuation,
            'rain_rate_mmh': rain_rate,
            'fade_slope_dbps': fade_slope,
            'gaussian_process': x,
            'A_001_db': A_001,
            'beta_sec': beta,
            'link_margin_db': link_margin_db,
            'events': events,
            'availability_pct': availability,
            'total_outage_sec': total_outage_sec,
            'max_attenuation_db': float(np.max(attenuation)),
            'mean_attenuation_rain_db': float(
                np.mean(attenuation[attenuation > 0.01])) if np.any(attenuation > 0.01) else 0.0,
            'ccdf_thresholds': ccdf_thresholds,
            'ccdf_values': ccdf_values,
            'fade_dur_sorted': sorted_dur,
            'fade_dur_cdf': dur_cdf,
            'params': {
                'freq_ghz': freq_ghz,
                'elevation_deg': elevation_deg,
                'rain_rate_001': rain_rate_001,
                'climate_zone': climate_zone,
                'duration_hours': duration_hours,
                'dt': dt,
                'beta': beta,
            },
        }
    
    def _detect_events(self, attenuation, margin_db, dt,
                       hysteresis_db=0.5):
        """Detect fade events with hysteresis to avoid chattering."""
        n = len(attenuation)
        upper = margin_db + hysteresis_db / 2
        lower = margin_db - hysteresis_db / 2
        
        in_event = False
        event_starts = []
        event_ends = []
        event_peaks = []
        current_peak = 0.0
        
        for i in range(n):
            if not in_event:
                if attenuation[i] > upper:
                    in_event = True
                    event_starts.append(i)
                    current_peak = attenuation[i]
            else:
                current_peak = max(current_peak, attenuation[i])
                if attenuation[i] < lower:
                    in_event = False
                    event_ends.append(i)
                    event_peaks.append(current_peak)
        
        # Close open event at end
        if in_event:
            event_ends.append(n - 1)
            event_peaks.append(current_peak)
        
        durations = np.array([(e - s) * dt for s, e in zip(event_starts, event_ends)])
        
        return {
            'n_events': len(event_starts),
            'starts': np.array(event_starts),
            'ends': np.array(event_ends),
            'peaks_db': np.array(event_peaks),
            'durations_sec': durations,
            'mean_duration_sec': float(np.mean(durations)) if len(durations) > 0 else 0.0,
            'max_duration_sec': float(np.max(durations)) if len(durations) > 0 else 0.0,
            'total_outage_sec': float(np.sum(durations)),
        }


# --- Regulatory compliance (ITU RR Art. 21/22) -----------------------------

class RegulatoryComplianceChecker:
    """PFD limits and EIRP density masks per ITU Radio Regulations."""
    
    def __init__(self, link_budget_calculator=None):
        self.link_calc = link_budget_calculator
        self.pfd_limits = ITU_PFD_LIMITS
        self.eirp_masks = EIRP_DENSITY_MASKS
    
    def get_pfd_limit(self, freq_ghz, elevation_deg, is_gso=True):
        """ITU PFD limit for the given frequency and elevation (Art. 21 Table 21-4)."""
        sin2_elev = np.sin(np.radians(elevation_deg))**2
        
        if is_gso:
            limits = self.pfd_limits['gso_limits']
            for (f_min, f_max), limit_data in limits.items():
                if f_min <= freq_ghz <= f_max:
                    pfd_low = limit_data['pfd_low']
                    pfd_high = limit_data['pfd_high']
                    pfd_limit = pfd_low + (pfd_high - pfd_low) * sin2_elev
                    return {
                        'pfd_limit_dbw_m2_4khz': pfd_limit,
                        'band_name': limit_data['name'],
                        'pfd_low': pfd_low,
                        'pfd_high': pfd_high,
                        'freq_range': (f_min, f_max),
                        'is_gso': True,
                    }
        else:
            limits = self.pfd_limits['ngso_limits']
            for (f_min, f_max), limit_data in limits.items():
                if f_min <= freq_ghz <= f_max:
                    return {
                        'pfd_limit_dbw_m2_4khz': limit_data['pfd_limit'],
                        'band_name': limit_data['name'],
                        'freq_range': (f_min, f_max),
                        'is_gso': False,
                    }
        
        return {
            'pfd_limit_dbw_m2_4khz': -150.0,
            'band_name': f'Default ({freq_ghz:.1f} GHz)',
            'freq_range': (freq_ghz - 0.5, freq_ghz + 0.5),
            'is_gso': is_gso,
        }
    
    def calculate_pfd_per_4khz(self, eirp_dbw, distance_km, bandwidth_hz):
        """PFD per 4 kHz reference bandwidth in dBW/m²/4kHz."""
        if distance_km <= 0 or bandwidth_hz <= 0:
            return -999
        
        distance_m = distance_km * 1000
        spreading_loss = 10 * np.log10(4 * np.pi * distance_m**2)
        bw_normalization = 10 * np.log10(bandwidth_hz / 4000)
        
        pfd_4khz = eirp_dbw - spreading_loss - bw_normalization
        return pfd_4khz
    
    def check_compliance(self, eirp_dbw, distance_km, bandwidth_hz,
                          freq_ghz, elevation_deg, is_gso=True):
        """Full PFD compliance check returning status, margin, and details."""
        # Calculate actual PFD/4kHz
        pfd_actual = self.calculate_pfd_per_4khz(eirp_dbw, distance_km, bandwidth_hz)
        
        # Get ITU limit
        limit_info = self.get_pfd_limit(freq_ghz, elevation_deg, is_gso)
        pfd_limit = limit_info['pfd_limit_dbw_m2_4khz']
        
        # Margin (positive = compliant)
        margin = pfd_limit - pfd_actual
        
        return {
            'compliant': margin >= 0,
            'pfd_actual_dbw_m2_4khz': pfd_actual,
            'pfd_limit_dbw_m2_4khz': pfd_limit,
            'margin_db': margin,
            'band_name': limit_info['band_name'],
            'freq_ghz': freq_ghz,
            'elevation_deg': elevation_deg,
            'eirp_dbw': eirp_dbw,
            'distance_km': distance_km,
            'is_gso': is_gso,
        }
    
    def compute_pfd_vs_elevation(self, eirp_dbw, distance_km, bandwidth_hz,
                                   freq_ghz, is_gso=True):
        """PFD and limits across all elevation angles (for plotting)."""
        elevations = np.linspace(5, 90, 86)
        pfd_actuals = np.zeros_like(elevations)
        pfd_limits = np.zeros_like(elevations)
        margins = np.zeros_like(elevations)
        
        for i, elev in enumerate(elevations):
            pfd_actuals[i] = self.calculate_pfd_per_4khz(eirp_dbw, distance_km, bandwidth_hz)
            limit = self.get_pfd_limit(freq_ghz, elev, is_gso)
            pfd_limits[i] = limit['pfd_limit_dbw_m2_4khz']
            margins[i] = pfd_limits[i] - pfd_actuals[i]
        
        return {
            'elevations': elevations,
            'pfd_actuals': pfd_actuals,
            'pfd_limits': pfd_limits,
            'margins': margins,
            'band_name': self.get_pfd_limit(freq_ghz, 45, is_gso)['band_name'],
        }
    
    def compute_eirp_density_mask(self, mask_type='standard_earth_station'):
        """Off-axis EIRP density envelope per S.524-9."""
        mask_data = self.eirp_masks.get(mask_type, self.eirp_masks['standard_earth_station'])
        segments = mask_data['segments']
        
        theta_full = np.linspace(0.5, 180, 1000)
        eirp_limit = np.zeros_like(theta_full)
        
        for i, theta in enumerate(theta_full):
            for seg in segments:
                if seg['theta_min'] <= theta < seg['theta_max']:
                    if seg['B'] > 0:
                        eirp_limit[i] = seg['A'] - seg['B'] * np.log10(max(theta, 0.1))
                    else:
                        eirp_limit[i] = seg['A']
                    break
        
        return {
            'theta_deg': theta_full,
            'eirp_limit_dbw_40khz': eirp_limit,
            'mask_type': mask_type,
        }


# --- Interference analysis (S.1323, S.465-6) -------------------------------

class InterferenceCalculator:
    """Adjacent-satellite interference (ASI) analysis per ITU-R S.465-6/S.1323."""

    def __init__(self, link_budget_calculator=None):
        self.link_calc = link_budget_calculator
        self.asi_params = ADJACENT_SATELLITE_PARAMS

    # -- ITU-R S.465-6 reference antenna pattern -----------------------------
    def itu_s465_gain(self, theta_deg, antenna_diameter_m, frequency_ghz):
        """Off-axis gain in dBi per ITU-R S.465-6."""
        theta = np.atleast_1d(np.asarray(theta_deg, dtype=float))
        wavelength_m = C_LIGHT / (frequency_ghz * 1e9)
        d_over_lambda = antenna_diameter_m / wavelength_m

        # Peak gain  (η ≈ 0.65)
        efficiency = 0.65
        g_max = 10 * np.log10(efficiency * (np.pi * d_over_lambda) ** 2)

        # First-sidelobe plateau
        g1 = 2.0 + 15.0 * np.log10(d_over_lambda)

        # Transition angles
        theta_m = (20.0 / d_over_lambda) * np.sqrt(max(g_max - g1, 0))
        theta_r = 15.85 * d_over_lambda ** (-0.6)

        ap = self.asi_params['antenna_pattern']

        gain = np.empty_like(theta)
        for i, th in enumerate(theta):
            th = abs(th)
            if th < 1e-6:
                gain[i] = g_max
            elif th <= theta_m:
                gain[i] = g_max - 2.5e-3 * (d_over_lambda * th) ** 2
            elif th <= max(theta_r, theta_m):
                gain[i] = g1
            elif th <= ap['transition_angle_deg']:
                gain[i] = ap['sidelobe_envelope_A'] - ap['sidelobe_envelope_B'] * np.log10(th)
            else:
                gain[i] = ap['floor_dbi']

        return gain.item() if gain.size == 1 else gain

    # -- Single-entry C/I ----------------------------------------------------
    def calculate_asi_ci(self, params, orbital_spacing_deg,
                         interferer_eirp_dbw=None):
        """C/I for a single adjacent-satellite interferer."""
        freq_ghz = params.get('downlink_frequency_ghz', 12.0)
        ant_diam = params.get('gs_antenna_diameter_m_rx',
                              params.get('gs_antenna_diameter_m', 1.2))

        # Wanted satellite EIRP
        wanted_eirp = (params.get('sat_power_dbw', 10)
                       + params.get('sat_antenna_gain_dbi', 35)
                       - params.get('output_backoff_db', 2.5))

        # Interfering satellite EIRP
        if interferer_eirp_dbw is None:
            band = self._detect_band(freq_ghz)
            interferer_eirp_dbw = self.asi_params['interferer_eirp_dbw'].get(band, wanted_eirp)

        # Receive antenna on-axis and off-axis gain
        g_rx_on = self.itu_s465_gain(0.0, ant_diam, freq_ghz)
        g_rx_off = self.itu_s465_gain(orbital_spacing_deg, ant_diam, freq_ghz)

        # Discrimination: the difference in receive gain
        discrimination = g_rx_on - g_rx_off        # positive, dB

        # C/I (single entry)
        c_i = (wanted_eirp - interferer_eirp_dbw) + discrimination

        return {
            'c_i_db': c_i,
            'wanted_eirp_dbw': wanted_eirp,
            'interferer_eirp_dbw': interferer_eirp_dbw,
            'g_rx_on_dbi': g_rx_on,
            'g_rx_off_dbi': g_rx_off,
            'discrimination_db': discrimination,
            'orbital_spacing_deg': orbital_spacing_deg,
        }

    # -- Aggregate C/I -------------------------------------------------------
    def calculate_aggregate_ci(self, params, orbital_spacing_deg,
                               num_interferers=2):
        """Aggregate C/I from multiple adjacent satellites (power sum)."""
        entries = []
        ci_linear_sum = 0.0
        for k in range(1, num_interferers + 1):
            # Alternate east / west: spacing × ceil(k/2)
            spacing = orbital_spacing_deg * ((k + 1) // 2)
            entry = self.calculate_asi_ci(params, spacing)
            entries.append(entry)
            ci_linear_sum += 10 ** (-entry['c_i_db'] / 10)

        aggregate_ci = -10 * np.log10(ci_linear_sum) if ci_linear_sum > 0 else 99.0

        return {
            'aggregate_ci_db': aggregate_ci,
            'entries': entries,
            'num_interferers': num_interferers,
            'orbital_spacing_deg': orbital_spacing_deg,
        }

    # -- Combined C/(N+I) ----------------------------------------------------
    def calculate_total_cnir(self, cn_db, ci_db):
        """C/(N+I) in dB.  1/C(N+I) = 1/CN + 1/CI"""
        cn_lin = 10 ** (cn_db / 10)
        ci_lin = 10 ** (ci_db / 10)
        cnir_lin = 1.0 / (1.0 / cn_lin + 1.0 / ci_lin)
        return 10 * np.log10(cnir_lin)

    # -- Sweep C/I vs. spacing -----------------------------------------------
    def sweep_orbital_spacing(self, params, spacing_range=None,
                              num_interferers=2):
        """C/I and C/(N+I) across a range of orbital spacings."""
        if spacing_range is None:
            spacing_range = np.arange(1.0, 10.5, 0.5)

        ci_values = np.zeros_like(spacing_range)
        for i, sp in enumerate(spacing_range):
            agg = self.calculate_aggregate_ci(params, sp, num_interferers)
            ci_values[i] = agg['aggregate_ci_db']

        return {
            'spacings_deg': spacing_range,
            'ci_db': ci_values,
        }

    # -- helpers -------------------------------------------------------------
    @staticmethod
    def _detect_band(freq_ghz):
        """Map frequency to band name used in ASI params."""
        if freq_ghz < 8:
            return 'C-band'
        elif freq_ghz < 18:
            return 'Ku-band'
        else:
            return 'Ka-band'
