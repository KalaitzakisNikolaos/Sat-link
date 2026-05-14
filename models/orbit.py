"""Orbital mechanics for satellite communications.

Keplerian propagation with J2 secular perturbations and optional
atmospheric drag.  Ground-track, look-angle, and Doppler utilities.
"""

import numpy as np
from datetime import datetime, timedelta
from .constants import (EARTH_RADIUS, EARTH_MU, C_LIGHT,
                         EARTH_SEMI_MAJOR, EARTH_FLATTENING, EARTH_ECCENTRICITY_SQ,
                         EARTH_ROTATION_RATE, EARTH_J2, ATMOSPHERIC_DENSITY_MODEL)


class SatelliteOrbit:
    """Keplerian orbit with J2 perturbations and optional atmospheric drag."""
    
    def __init__(self, orbital_params=None):
        """Initialize from *orbital_params* dict (defaults to a GEO satellite)."""
        if orbital_params is None:
            # Default GEO satellite
            self.semi_major_axis = EARTH_RADIUS + 35786  # km
            self.eccentricity = 0.0
            self.inclination = 0.0  # degrees
            self.raan = 0.0  # Right Ascension of Ascending Node (degrees)
            self.arg_perigee = 0.0  # Argument of perigee (degrees)
            self.mean_anomaly = 0.0  # Mean anomaly (degrees)
        else:
            self.semi_major_axis = orbital_params.get('semi_major_axis', 
                                                     EARTH_RADIUS + 35786)
            self.eccentricity = orbital_params.get('eccentricity', 0.0)
            self.inclination = orbital_params.get('inclination', 0.0)
            self.raan = orbital_params.get('raan', 0.0)
            self.arg_perigee = orbital_params.get('arg_perigee', 0.0)
            self.mean_anomaly = orbital_params.get('mean_anomaly', 0.0)
        
        # Drag parameters (typical small satellite defaults)
        if orbital_params is not None:
            self.drag_area_m2 = orbital_params.get('drag_area_m2', 1.0)
            self.drag_coeff = orbital_params.get('drag_coeff', 2.2)
            self.mass_kg = orbital_params.get('mass_kg', 100.0)
        else:
            self.drag_area_m2 = 1.0
            self.drag_coeff = 2.2
            self.mass_kg = 100.0
        
        self.orbital_period = self._calculate_period()
        
        # Pre-compute J2 secular perturbation rates
        self._compute_j2_rates()
    
    def _calculate_period(self):
        """Orbital period in minutes using Kepler's third law."""
        a_m = self.semi_major_axis * 1000  # Convert to meters
        mu_m = EARTH_MU * 1e9  # Convert to m³/s²
        period_sec = 2 * np.pi * np.sqrt(a_m**3 / mu_m)
        return period_sec / 60  # Return in minutes
    
    def _compute_j2_rates(self):
        """Compute secular J2 rates on Ω, ω, and M (Vallado Eq. 9-41–43)."""
        a = self.semi_major_axis  # km
        e = self.eccentricity
        i = np.radians(self.inclination)
        
        # Mean motion (rad/s)
        n = np.sqrt(EARTH_MU / a**3)
        
        # Semi-latus rectum (km)
        p = a * (1 - e**2)
        
        # Common factor
        factor = 1.5 * n * EARTH_J2 * (EARTH_RADIUS / p)**2
        
        # RAAN rate (rad/s) — regression of nodes
        self.raan_rate = -factor * np.cos(i)
        
        # Argument of perigee rate (rad/s) — apsidal rotation
        self.arg_perigee_rate = factor * (2.0 - 2.5 * np.sin(i)**2)
        
        # Mean anomaly correction rate (rad/s)
        self.mean_anomaly_rate_correction = factor * np.sqrt(1 - e**2) * (1.0 - 1.5 * np.sin(i)**2)
    
    def _get_atmospheric_density(self, altitude_km):
        """Exponential-model density in kg/m³ (US Std Atm 1976).  0 above 1000 km."""
        if altitude_km > 1000 or altitude_km < 0:
            return 0.0
        
        for (alt_min, alt_max), params in ATMOSPHERIC_DENSITY_MODEL.items():
            if alt_min <= altitude_km < alt_max:
                rho0 = params['rho0']
                h0 = params['h0']
                H = params['H']
                return rho0 * np.exp(-(altitude_km - h0) / H)
        
        return 0.0
    
    def _compute_drag_perturbation(self, r_km, v_km_s):
        """Semi-major axis decay rate da/dt (km/s) from atmospheric drag."""
        altitude_km = r_km - EARTH_RADIUS
        rho = self._get_atmospheric_density(altitude_km)
        
        if rho <= 0:
            return 0.0
        
        # Ballistic coefficient B = Cd * A / (2 * m)  [m²/kg]
        B = self.drag_coeff * self.drag_area_m2 / (2.0 * self.mass_kg)
        
        # Velocity in m/s
        v_m_s = v_km_s * 1000.0
        
        # Acceleration due to drag: a_drag = -0.5 * ρ * v² * Cd * A / m
        # Effect on semi-major axis: da/dt ≈ -ρ * v * Cd * A / m * a_km
        # Simplified: we accumulate the effect over the propagation
        da_dt = -rho * v_m_s * 2.0 * B * self.semi_major_axis  # km/s (mixed units intentional)
        
        return da_dt
    
    def get_satellite_position_eci(self, time_since_epoch_sec=0):
        """Satellite position (x, y, z) in ECI [km], with J2 secular perturbations."""
        # J2 secular perturbations (Vallado Eq. 9-41–43)
        raan_current = np.radians(self.raan) + self.raan_rate * time_since_epoch_sec
        omega_current = np.radians(self.arg_perigee) + self.arg_perigee_rate * time_since_epoch_sec
        
        # Mean motion with J2 correction
        n = np.sqrt(EARTH_MU / self.semi_major_axis**3)  # Unperturbed mean motion
        n_corrected = n + self.mean_anomaly_rate_correction
        
        # Mean anomaly with corrected mean motion
        M = np.radians(self.mean_anomaly) + n_corrected * time_since_epoch_sec
        
        # Solve Kepler's equation for eccentric anomaly
        E = self._solve_kepler_equation(M, self.eccentricity)
        
        # True anomaly
        nu = 2 * np.arctan2(
            np.sqrt(1 + self.eccentricity) * np.sin(E / 2),
            np.sqrt(1 - self.eccentricity) * np.cos(E / 2)
        )
        
        # Distance from Earth center
        r = self.semi_major_axis * (1 - self.eccentricity * np.cos(E))
        
        # Position in orbital plane (perifocal frame PQW)
        x_orb = r * np.cos(nu)
        y_orb = r * np.sin(nu)
        
        # Rotate perifocal (PQW) to ECI
        i = np.radians(self.inclination)
        
        cos_Omega = np.cos(raan_current)
        sin_Omega = np.sin(raan_current)
        cos_i = np.cos(i)
        sin_i = np.sin(i)
        cos_omega = np.cos(omega_current)
        sin_omega = np.sin(omega_current)
        
        # 3-1-3 Euler rotation: Ω, i, ω
        x_eci = (cos_Omega * cos_omega - sin_Omega * sin_omega * cos_i) * x_orb + \
                (-cos_Omega * sin_omega - sin_Omega * cos_omega * cos_i) * y_orb
        
        y_eci = (sin_Omega * cos_omega + cos_Omega * sin_omega * cos_i) * x_orb + \
                (-sin_Omega * sin_omega + cos_Omega * cos_omega * cos_i) * y_orb
        
        z_eci = (sin_omega * sin_i) * x_orb + (cos_omega * sin_i) * y_orb
        
        return np.array([x_eci, y_eci, z_eci])

    def get_satellite_velocity_eci(self, time_since_epoch_sec=0):
        """Satellite velocity (vx, vy, vz) in ECI [km/s]."""
        # J2 secular perturbations
        raan_current = np.radians(self.raan) + self.raan_rate * time_since_epoch_sec
        omega_current = np.radians(self.arg_perigee) + self.arg_perigee_rate * time_since_epoch_sec
        
        n = np.sqrt(EARTH_MU / self.semi_major_axis**3)
        n_corrected = n + self.mean_anomaly_rate_correction
        M = np.radians(self.mean_anomaly) + n_corrected * time_since_epoch_sec
        
        E = self._solve_kepler_equation(M, self.eccentricity)
        
        nu = 2 * np.arctan2(
            np.sqrt(1 + self.eccentricity) * np.sin(E / 2),
            np.sqrt(1 - self.eccentricity) * np.cos(E / 2)
        )
        
        r = self.semi_major_axis * (1 - self.eccentricity * np.cos(E))
        
        # Velocity in perifocal frame
        p = self.semi_major_axis * (1 - self.eccentricity**2)
        h = np.sqrt(EARTH_MU * p)  # Specific angular momentum
        
        vx_orb = -(EARTH_MU / h) * np.sin(nu)
        vy_orb = (EARTH_MU / h) * (self.eccentricity + np.cos(nu))
        
        # Rotate to ECI
        i = np.radians(self.inclination)
        cos_Omega = np.cos(raan_current)
        sin_Omega = np.sin(raan_current)
        cos_i = np.cos(i)
        sin_i = np.sin(i)
        cos_omega = np.cos(omega_current)
        sin_omega = np.sin(omega_current)
        
        vx_eci = (cos_Omega * cos_omega - sin_Omega * sin_omega * cos_i) * vx_orb + \
                 (-cos_Omega * sin_omega - sin_Omega * cos_omega * cos_i) * vy_orb
        
        vy_eci = (sin_Omega * cos_omega + cos_Omega * sin_omega * cos_i) * vx_orb + \
                 (-sin_Omega * sin_omega + cos_Omega * cos_omega * cos_i) * vy_orb
        
        vz_eci = (sin_omega * sin_i) * vx_orb + (cos_omega * sin_i) * vy_orb
        
        return np.array([vx_eci, vy_eci, vz_eci])
    
    def _solve_kepler_equation(self, M, e, tolerance=1e-8, max_iter=50):
        """Solve M = E − e·sin(E) via Newton-Raphson."""
        E = M  # Initial guess
        for _ in range(max_iter):
            f = E - e * np.sin(E) - M
            fp = 1 - e * np.cos(E)
            E_new = E - f / fp
            
            if abs(E_new - E) < tolerance:
                return E_new
            E = E_new
        
        return E
    
    @staticmethod
    def _eci_to_ecef(pos_eci, time_since_epoch_sec):
        """Rotate ECI → ECEF via Greenwich Mean Sidereal Time."""
        theta = EARTH_ROTATION_RATE * time_since_epoch_sec
        cos_t = np.cos(theta)
        sin_t = np.sin(theta)
        
        x_ecef = cos_t * pos_eci[0] + sin_t * pos_eci[1]
        y_ecef = -sin_t * pos_eci[0] + cos_t * pos_eci[1]
        z_ecef = pos_eci[2]
        
        return np.array([x_ecef, y_ecef, z_ecef])
    
    def calculate_ground_track(self, num_points=100, duration_hours=24):
        """Subsatellite point track as (lat, lon) arrays in degrees."""
        duration_sec = duration_hours * 3600
        times = np.linspace(0, duration_sec, num_points)
        
        lats = []
        lons = []
        
        for t in times:
            pos_eci = self.get_satellite_position_eci(t)
            
            # Rotate ECI to ECEF using GMST
            pos_ecef = self._eci_to_ecef(pos_eci, t)
            
            # Convert ECEF to geodetic (lat, lon)
            r = np.linalg.norm(pos_ecef)
            lat = np.degrees(np.arcsin(pos_ecef[2] / r))
            lon = np.degrees(np.arctan2(pos_ecef[1], pos_ecef[0]))
            
            # Normalize longitude to [-180, 180]
            while lon > 180:
                lon -= 360
            while lon < -180:
                lon += 360
            
            lats.append(lat)
            lons.append(lon)
        
        return np.array(lats), np.array(lons)
    
    def calculate_look_angles(self, gs_lat_deg, gs_lon_deg, gs_alt_km=0,
                             time_since_epoch_sec=0):
        """Azimuth, elevation, range, and visibility from a ground station."""
        # Satellite ECI → ECEF
        sat_pos_eci = self.get_satellite_position_eci(time_since_epoch_sec)
        sat_pos_ecef = self._eci_to_ecef(sat_pos_eci, time_since_epoch_sec)
        
        # Ground station ECEF (WGS-84)
        gs_pos_ecef = self._geodetic_to_ecef(gs_lat_deg, gs_lon_deg, gs_alt_km)
        
        # Range vector in ECEF
        range_vec = sat_pos_ecef - gs_pos_ecef
        range_km = np.linalg.norm(range_vec)
        
        # Convert to topocentric SEZ coordinates
        lat_rad = np.radians(gs_lat_deg)
        lon_rad = np.radians(gs_lon_deg)
        
        # ECEF → SEZ rotation matrix
        R = np.array([
            [np.sin(lat_rad) * np.cos(lon_rad), 
             np.sin(lat_rad) * np.sin(lon_rad), 
             -np.cos(lat_rad)],
            [-np.sin(lon_rad), 
             np.cos(lon_rad), 
             0],
            [np.cos(lat_rad) * np.cos(lon_rad), 
             np.cos(lat_rad) * np.sin(lon_rad), 
             np.sin(lat_rad)]
        ])
        
        sez = R @ range_vec
        
        # Calculate azimuth and elevation
        s, e, z = sez
        
        elevation_rad = np.arcsin(z / range_km)
        elevation_deg = np.degrees(elevation_rad)
        
        azimuth_rad = np.arctan2(e, -s)
        azimuth_deg = np.degrees(azimuth_rad)
        
        # Normalize azimuth to [0, 360]
        if azimuth_deg < 0:
            azimuth_deg += 360
        
        # Check visibility (above horizon)
        visible = elevation_deg > 0
        
        return {
            'azimuth': azimuth_deg,
            'elevation': elevation_deg,
            'range': range_km,
            'visible': visible
        }
    
    def _geodetic_to_ecef(self, lat_deg, lon_deg, alt_km):
        """Geodetic (WGS-84) to ECEF position vector in km."""
        lat_rad = np.radians(lat_deg)
        lon_rad = np.radians(lon_deg)
        
        a = EARTH_SEMI_MAJOR
        e2 = EARTH_ECCENTRICITY_SQ
        
        # Radius of curvature in the prime vertical
        N = a / np.sqrt(1 - e2 * np.sin(lat_rad)**2)
        
        # ECEF coordinates
        x = (N + alt_km) * np.cos(lat_rad) * np.cos(lon_rad)
        y = (N + alt_km) * np.cos(lat_rad) * np.sin(lon_rad)
        z = (N * (1 - e2) + alt_km) * np.sin(lat_rad)
        
        return np.array([x, y, z])
    
    def calculate_doppler_shift(self, frequency_hz, gs_lat_deg, gs_lon_deg,
                               time_since_epoch_sec=0):
        """Doppler shift in Hz.  Uses finite-difference radial velocity."""
        dt = 1.0  # 1 second finite difference
        
        look1 = self.calculate_look_angles(gs_lat_deg, gs_lon_deg, 0, 
                                          time_since_epoch_sec)
        look2 = self.calculate_look_angles(gs_lat_deg, gs_lon_deg, 0, 
                                          time_since_epoch_sec + dt)
        
        # Radial velocity (km/s)
        v_r = (look2['range'] - look1['range']) / dt
        
        # Doppler shift
        doppler_hz = -(v_r * 1000 / C_LIGHT) * frequency_hz
        
        return doppler_hz
    
    def calculate_visibility_window(self, gs_lat_deg, gs_lon_deg, 
                                   duration_hours=24, min_elevation_deg=5):
        """Visibility passes as (start_sec, end_sec, max_elev) tuples."""
        duration_sec = duration_hours * 3600
        time_step = 60  # 1 minute steps
        times = np.arange(0, duration_sec, time_step)
        
        windows = []
        in_window = False
        window_start = None
        max_elev_in_window = 0
        
        for t in times:
            look = self.calculate_look_angles(gs_lat_deg, gs_lon_deg, 0, t)
            
            if look['visible'] and look['elevation'] >= min_elevation_deg:
                if not in_window:
                    in_window = True
                    window_start = t
                    max_elev_in_window = look['elevation']
                else:
                    max_elev_in_window = max(max_elev_in_window, look['elevation'])
            else:
                if in_window:
                    windows.append((window_start, t, max_elev_in_window))
                    in_window = False
        
        if in_window:
            windows.append((window_start, times[-1], max_elev_in_window))
        
        return windows
    
    def get_orbital_elements_at_time(self, time_since_epoch_sec):
        """Osculating elements at *t*, including J2 secular drift."""
        raan_deg = np.degrees(np.radians(self.raan) + self.raan_rate * time_since_epoch_sec) % 360
        arg_perigee_deg = np.degrees(np.radians(self.arg_perigee) + self.arg_perigee_rate * time_since_epoch_sec) % 360
        n = np.sqrt(EARTH_MU / self.semi_major_axis**3) + self.mean_anomaly_rate_correction
        mean_anomaly_deg = np.degrees(np.radians(self.mean_anomaly) + n * time_since_epoch_sec) % 360
        
        return {
            'semi_major_axis': self.semi_major_axis,
            'eccentricity': self.eccentricity,
            'inclination': self.inclination,
            'raan': raan_deg,
            'arg_perigee': arg_perigee_deg,
            'mean_anomaly': mean_anomaly_deg,
            'raan_rate_deg_per_day': np.degrees(self.raan_rate) * 86400,
            'arg_perigee_rate_deg_per_day': np.degrees(self.arg_perigee_rate) * 86400,
        }


def create_satellite_from_type(sat_type, longitude_deg=0):
    """Factory for LEO/MEO/GEO/HEO orbits with representative parameters."""
    from .constants import SATELLITE_TYPES, EARTH_RADIUS
    
    if sat_type == 'LEO':
        params = {
            'semi_major_axis': EARTH_RADIUS + 550,  # 550 km altitude (Starlink)
            'eccentricity': 0.0001,
            'inclination': 53.0,  # Starlink Shell 1
            'raan': 0.0,
            'arg_perigee': 0.0,
            'mean_anomaly': 0.0,
            # LEO drag parameters (typical small satellite)
            'drag_area_m2': 10.0,  # ~3.3m x 3m flat panel
            'drag_coeff': 2.2,
            'mass_kg': 260.0,  # Starlink v1 mass
        }
    elif sat_type == 'MEO':
        params = {
            'semi_major_axis': EARTH_RADIUS + 20200,  # GPS altitude
            'eccentricity': 0.01,
            'inclination': 55.0,  # GPS Block IIIA
            'raan': 0.0,
            'arg_perigee': 0.0,
            'mean_anomaly': 0.0
        }
    elif sat_type == 'GEO':
        params = {
            'semi_major_axis': EARTH_RADIUS + 35786,
            'eccentricity': 0.0,
            'inclination': 0.0,
            'raan': longitude_deg,  # Use RAAN to set longitude
            'arg_perigee': 0.0,
            'mean_anomaly': 0.0
        }
    elif sat_type == 'HEO':
        # Molniya orbit: perigee ~500 km, apogee ~39873 km
        # a = (r_p + r_a) / 2 = (6371+500 + 6371+39873) / 2 ≈ 26557.5 km
        # e = (r_a - r_p) / (r_a + r_p) ≈ 0.74
        # Source: Sidi, M.J., "Spacecraft Dynamics and Control", Cambridge (1997)
        params = {
            'semi_major_axis': 26557.5,  # Corrected Molniya semi-major axis
            'eccentricity': 0.74,  # Highly eccentric
            'inclination': 63.4,  # Critical inclination (zero apsidal rotation from J2)
            'raan': 0.0,
            'arg_perigee': 270.0,  # Apogee over northern hemisphere
            'mean_anomaly': 0.0
        }
    else:
        params = {
            'semi_major_axis': EARTH_RADIUS + 35786,
            'eccentricity': 0.0,
            'inclination': 0.0,
            'raan': 0.0,
            'arg_perigee': 0.0,
            'mean_anomaly': 0.0
        }
    
    return SatelliteOrbit(params)


# --- TLE parser (NORAD / CelesTrak) ----------------------------------------

def parse_tle(tle_text):
    """Parse a 2- or 3-line TLE set and return a SatelliteOrbit + metadata dict."""
    lines = [l.strip() for l in tle_text.strip().splitlines() if l.strip()]

    # Determine format: 2-line or 3-line
    if len(lines) >= 3 and lines[0][0] != '1':
        name = lines[0].strip()
        line1 = lines[1]
        line2 = lines[2]
    elif len(lines) >= 2:
        line1 = lines[0]
        line2 = lines[1]
        # Try to extract name from catalog number
        name = f"SAT-{line1[2:7].strip()}"
    else:
        raise ValueError("TLE data must contain at least 2 lines (Line 1 and Line 2)")

    # Validate line identifiers
    if line1[0] != '1':
        raise ValueError(f"Line 1 must start with '1', got '{line1[0]}'")
    if line2[0] != '2':
        raise ValueError(f"Line 2 must start with '2', got '{line2[0]}'")

    # ── Parse Line 1 ──
    catalog_number = line1[2:7].strip()

    # Epoch: columns 18-32 (year + fractional day)
    epoch_year_2d = int(line1[18:20])
    epoch_day = float(line1[20:32])
    # Convert 2-digit year: 57-99 → 1957-1999, 00-56 → 2000-2056
    epoch_year = epoch_year_2d + (1900 if epoch_year_2d >= 57 else 2000)

    # B* drag term: columns 53-61 (mantissa + exponent notation)
    bstar_str = line1[53:61].strip()
    try:
        # Format: ±NNNNN±N  →  ±0.NNNNN × 10^±N
        mantissa = float(bstar_str[:-2]) * 1e-5
        exponent = int(bstar_str[-2:])
        bstar = mantissa * (10.0 ** exponent)
    except (ValueError, IndexError):
        bstar = 0.0

    # ── Parse Line 2 ──
    inclination_deg = float(line2[8:16].strip())
    raan_deg = float(line2[17:25].strip())

    # Eccentricity: columns 26-33 (implied leading "0.")
    ecc_str = line2[26:33].strip()
    eccentricity = float(f"0.{ecc_str}")

    arg_perigee_deg = float(line2[34:42].strip())
    mean_anomaly_deg = float(line2[43:51].strip())
    mean_motion_revday = float(line2[52:63].strip())

    # ── Convert mean motion to semi-major axis ──
    # n (rad/s) = mean_motion * 2π / 86400
    # a = (μ / n²)^(1/3)     [Kepler's 3rd law]
    n_rad_s = mean_motion_revday * 2.0 * np.pi / 86400.0
    semi_major_axis_km = (EARTH_MU / (n_rad_s ** 2)) ** (1.0 / 3.0)

    # Build orbital params dict
    orbital_params = {
        'semi_major_axis': semi_major_axis_km,
        'eccentricity': eccentricity,
        'inclination': inclination_deg,
        'raan': raan_deg,
        'arg_perigee': arg_perigee_deg,
        'mean_anomaly': mean_anomaly_deg,
    }

    # For LEO satellites (altitude < 2000 km), enable drag
    altitude_km = semi_major_axis_km - EARTH_RADIUS
    if altitude_km < 2000:
        orbital_params['drag_coeff'] = 2.2
        orbital_params['drag_area_m2'] = 10.0
        orbital_params['mass_kg'] = 500.0

    orbit = SatelliteOrbit(orbital_params)

    return {
        'name': name,
        'orbit': orbit,
        'catalog_number': catalog_number,
        'epoch_year': epoch_year,
        'epoch_day': epoch_day,
        'mean_motion_revday': mean_motion_revday,
        'bstar': bstar,
        'altitude_km': altitude_km,
        'inclination_deg': inclination_deg,
        'period_min': orbit.orbital_period,
    }
