# -*- coding: utf-8 -*-
"""Satellite transponder model.

Models the bent-pipe signal chain (LNA → Mixer → IF Amp → PA)
including cascade noise (Friis), HPA nonlinearity (Saleh/Rapp),
and end-to-end C/N₀ combining.
"""

import numpy as np
from .constants import BOLTZMANN, C_LIGHT


class TransponderStage:
    """Single stage in the transponder chain (gain + noise figure)."""
    
    def __init__(self, name, gain_db=0.0, noise_figure_db=0.0, 
                 bandwidth_hz=36e6, description=""):
        self.name = name
        self.gain_db = gain_db
        self.noise_figure_db = noise_figure_db
        self.bandwidth_hz = bandwidth_hz
        self.description = description
    
    @property
    def gain_linear(self):
        """Gain in linear scale"""
        return 10 ** (self.gain_db / 10)
    
    @property
    def noise_figure_linear(self):
        """Noise figure in linear scale"""
        return 10 ** (self.noise_figure_db / 10)
    
    @property
    def noise_temperature_k(self):
        """Equivalent noise temperature:  Tₑ = T₀·(F − 1)"""
        T0 = 290.0  # Reference temperature (K)
        return T0 * (self.noise_figure_linear - 1)
    
    def __repr__(self):
        return (f"TransponderStage('{self.name}', G={self.gain_db:.1f} dB, "
                f"NF={self.noise_figure_db:.1f} dB, Te={self.noise_temperature_k:.1f} K)")


class SatelliteTransponder:
    """Complete satellite bent-pipe transponder model."""
    
    # Standard transponder configurations
    PRESETS = {
        'C-band_standard': {
            'name': 'C-band Standard (36 MHz)',
            'uplink_freq_ghz': 6.0,
            'downlink_freq_ghz': 4.0,
            'bandwidth_mhz': 36,
            'saturated_power_dbw': 8.5,
            'lna_gain_db': 25.0,
            'lna_nf_db': 1.5,
            'mixer_gain_db': -6.0,
            'mixer_nf_db': 8.0,
            'if_gain_db': 30.0,
            'if_nf_db': 3.0,
            'pa_gain_db': 15.0,
            'pa_nf_db': 10.0,
            'rx_antenna_gain_dbi': 30.0,
            'tx_antenna_gain_dbi': 32.0,
        },
        'Ku-band_standard': {
            'name': 'Ku-band Standard (36 MHz)',
            'uplink_freq_ghz': 14.0,
            'downlink_freq_ghz': 12.0,
            'bandwidth_mhz': 36,
            'saturated_power_dbw': 10.0,
            'lna_gain_db': 30.0,
            'lna_nf_db': 1.2,
            'mixer_gain_db': -6.0,
            'mixer_nf_db': 8.0,
            'if_gain_db': 30.0,
            'if_nf_db': 3.0,
            'pa_gain_db': 20.0,
            'pa_nf_db': 12.0,
            'rx_antenna_gain_dbi': 32.0,
            'tx_antenna_gain_dbi': 35.0,
        },
        'Ka-band_hts': {
            'name': 'Ka-band HTS (250 MHz)',
            'uplink_freq_ghz': 30.0,
            'downlink_freq_ghz': 20.0,
            'bandwidth_mhz': 250,
            'saturated_power_dbw': 12.0,
            'lna_gain_db': 35.0,
            'lna_nf_db': 2.0,
            'mixer_gain_db': -8.0,
            'mixer_nf_db': 10.0,
            'if_gain_db': 35.0,
            'if_nf_db': 3.5,
            'pa_gain_db': 25.0,
            'pa_nf_db': 14.0,
            'rx_antenna_gain_dbi': 35.0,
            'tx_antenna_gain_dbi': 38.0,
        },
    }
    
    def __init__(self, preset=None):
        # Default transponder chain
        self.stages = []
        
        # Frequency plan
        self.uplink_freq_ghz = 14.0
        self.downlink_freq_ghz = 12.0
        self.lo_freq_ghz = 2.0  # LO = f_up - f_down (for Ku-band)
        
        # Transponder-level parameters
        self.bandwidth_mhz = 36.0
        self.saturated_power_dbw = 10.0  # Saturated TWTA/SSPA output
        self.input_backoff_db = 1.0
        self.output_backoff_db = 2.5
        
        # Antenna parameters
        self.rx_antenna_gain_dbi = 32.0
        self.tx_antenna_gain_dbi = 35.0
        
        # Load preset if specified
        if preset and preset in self.PRESETS:
            self._load_preset(preset)
        else:
            self._build_default_chain()
    
    def _load_preset(self, preset_name):
        """Load a preset transponder configuration."""
        p = self.PRESETS[preset_name]
        
        self.uplink_freq_ghz = p['uplink_freq_ghz']
        self.downlink_freq_ghz = p['downlink_freq_ghz']
        self.lo_freq_ghz = abs(p['uplink_freq_ghz'] - p['downlink_freq_ghz'])
        self.bandwidth_mhz = p['bandwidth_mhz']
        self.saturated_power_dbw = p['saturated_power_dbw']
        self.rx_antenna_gain_dbi = p['rx_antenna_gain_dbi']
        self.tx_antenna_gain_dbi = p['tx_antenna_gain_dbi']
        
        self.stages = [
            TransponderStage('LNA', p['lna_gain_db'], p['lna_nf_db'],
                           p['bandwidth_mhz'] * 1e6,
                           'Low Noise Amplifier - First stage amplification'),
            TransponderStage('Mixer', p['mixer_gain_db'], p['mixer_nf_db'],
                           p['bandwidth_mhz'] * 1e6,
                           f'Frequency Converter (LO = {self.lo_freq_ghz:.1f} GHz)'),
            TransponderStage('IF_Amp', p['if_gain_db'], p['if_nf_db'],
                           p['bandwidth_mhz'] * 1e6,
                           'Intermediate Frequency Amplifier'),
            TransponderStage('PA', p['pa_gain_db'], p['pa_nf_db'],
                           p['bandwidth_mhz'] * 1e6,
                           'Power Amplifier (TWTA/SSPA)'),
        ]
    
    def _build_default_chain(self):
        """Build default Ku-band transponder chain."""
        self.lo_freq_ghz = abs(self.uplink_freq_ghz - self.downlink_freq_ghz)
        bw_hz = self.bandwidth_mhz * 1e6
        
        self.stages = [
            TransponderStage('LNA', 30.0, 1.2, bw_hz,
                           'Low Noise Amplifier - First stage amplification'),
            TransponderStage('Mixer', -6.0, 8.0, bw_hz,
                           f'Frequency Converter (LO = {self.lo_freq_ghz:.1f} GHz)'),
            TransponderStage('IF_Amp', 30.0, 3.0, bw_hz,
                           'Intermediate Frequency Amplifier'),
            TransponderStage('PA', 20.0, 12.0, bw_hz,
                           'Power Amplifier (TWTA/SSPA)'),
        ]
    
    def set_stage_params(self, stage_name, gain_db=None, noise_figure_db=None):
        """Update gain or noise figure for a named stage."""
        for stage in self.stages:
            if stage.name == stage_name:
                if gain_db is not None:
                    stage.gain_db = gain_db
                if noise_figure_db is not None:
                    stage.noise_figure_db = noise_figure_db
                return
    
    def set_frequency_plan(self, uplink_ghz, downlink_ghz):
        """Set uplink/downlink frequencies and derive LO."""
        self.uplink_freq_ghz = uplink_ghz
        self.downlink_freq_ghz = downlink_ghz
        self.lo_freq_ghz = abs(uplink_ghz - downlink_ghz)
        
        # Update mixer description
        for stage in self.stages:
            if stage.name == 'Mixer':
                stage.description = f'Frequency Converter (LO = {self.lo_freq_ghz:.1f} GHz)'
    
    # -- Cascade noise (Friis) -----------------------------------------------

    def calculate_cascade_noise_temperature(self):
        """Total system noise temperature via Friis cascade formula (K)."""
        if not self.stages:
            return 290.0  # Default
        
        T_total = self.stages[0].noise_temperature_k
        cumulative_gain = self.stages[0].gain_linear
        
        for i in range(1, len(self.stages)):
            T_total += self.stages[i].noise_temperature_k / cumulative_gain
            cumulative_gain *= self.stages[i].gain_linear
        
        return T_total
    
    def calculate_cascade_noise_figure(self):
        """Total cascade noise figure in dB (Friis, NF form)."""
        if not self.stages:
            return 0.0
        
        F_total = self.stages[0].noise_figure_linear
        cumulative_gain = self.stages[0].gain_linear
        
        for i in range(1, len(self.stages)):
            F_total += (self.stages[i].noise_figure_linear - 1) / cumulative_gain
            cumulative_gain *= self.stages[i].gain_linear
        
        return 10 * np.log10(F_total)
    
    def calculate_total_gain(self):
        """Total transponder gain in dB (sum of all stages)."""
        return sum(stage.gain_db for stage in self.stages)
    
    @property
    def bandwidth_hz(self):
        """Bandwidth in Hz."""
        return self.bandwidth_mhz * 1e6
    
    # -- Transponder performance ---------------------------------------------

    def calculate_operating_point(self, input_power_dbw):
        """Operating-point dict: output power, backoff, compression."""
        total_gain = self.calculate_total_gain()
        
        # Output power without saturation
        output_power_linear = input_power_dbw + total_gain
        
        # Apply saturation (PA clips at P_sat - OBO)
        max_output = self.saturated_power_dbw - self.output_backoff_db
        actual_output = min(output_power_linear, max_output)
        
        # Operating point relative to saturation
        backoff_from_sat = self.saturated_power_dbw - actual_output
        
        # Drive level
        input_at_saturation = self.saturated_power_dbw - total_gain
        input_backoff = input_at_saturation - input_power_dbw
        
        return {
            'input_power_dbw': input_power_dbw,
            'output_power_dbw': actual_output,
            'saturated_power_dbw': self.saturated_power_dbw,
            'total_gain_db': total_gain,
            'input_backoff_db': max(0, input_backoff),
            'output_backoff_db': backoff_from_sat,
            'is_saturated': output_power_linear >= self.saturated_power_dbw,
            'compression_db': max(0, output_power_linear - actual_output),
        }
    
    def calculate_satellite_gt(self):
        """Satellite G/T in dB/K (receive side)."""
        T_sys = self.calculate_cascade_noise_temperature()
        gt_db = self.rx_antenna_gain_dbi - 10 * np.log10(T_sys)
        return gt_db
    
    def calculate_satellite_eirp(self):
        """Satellite downlink EIRP in dBW."""
        p_out = self.saturated_power_dbw - self.output_backoff_db
        eirp = p_out + self.tx_antenna_gain_dbi
        return eirp
    
    def calculate_cn0_at_transponder(self, uplink_eirp_dbw, uplink_path_loss_db):
        """Uplink C/N₀ at transponder input in dB-Hz."""
        gt_sat = self.calculate_satellite_gt()
        k_db = 10 * np.log10(BOLTZMANN)  # -228.6 dBW/K/Hz
        
        cn0_up = uplink_eirp_dbw - uplink_path_loss_db + gt_sat - k_db
        return cn0_up
    
    # -- Total C/N₀ ----------------------------------------------------------

    @staticmethod
    def calculate_total_cn0(cn0_uplink_db, cn0_downlink_db, c_im_db=None,
                            bandwidth_hz=36e6):
        """End-to-end C/N₀ via reciprocal sum, optionally including C/IM."""
        # Convert to linear
        cn0_up_lin = 10 ** (cn0_uplink_db / 10)
        cn0_dn_lin = 10 ** (cn0_downlink_db / 10)
        
        # Reciprocal sum: 1/(C/N₀)_total = 1/(C/N₀)_up + 1/(C/N₀)_down
        reciprocal_sum = 1.0 / cn0_up_lin + 1.0 / cn0_dn_lin
        
        # Add intermodulation if specified
        if c_im_db is not None:
            # Convert C/IM [dB] to C/IM₀ [dB-Hz]
            c_im0_db = c_im_db + 10 * np.log10(bandwidth_hz)
            c_im0_lin = 10 ** (c_im0_db / 10)
            reciprocal_sum += 1.0 / c_im0_lin
        
        cn0_total_lin = 1.0 / reciprocal_sum
        cn0_total_db = 10 * np.log10(cn0_total_lin)
        
        return cn0_total_db
    
    def get_chain_summary(self):
        """Transponder parameter summary as a dict."""
        stage_details = []
        cumulative_gain_db = 0
        
        for stage in self.stages:
            cumulative_gain_db += stage.gain_db
            stage_details.append({
                'name': stage.name,
                'description': stage.description,
                'gain_db': stage.gain_db,
                'noise_figure_db': stage.noise_figure_db,
                'noise_temp_k': stage.noise_temperature_k,
                'cumulative_gain_db': cumulative_gain_db,
            })
        
        return {
            # Frequency plan
            'uplink_freq_ghz': self.uplink_freq_ghz,
            'downlink_freq_ghz': self.downlink_freq_ghz,
            'lo_freq_ghz': self.lo_freq_ghz,
            'bandwidth_mhz': self.bandwidth_mhz,
            
            # Antenna
            'rx_antenna_gain_dbi': self.rx_antenna_gain_dbi,
            'tx_antenna_gain_dbi': self.tx_antenna_gain_dbi,
            
            # Power
            'saturated_power_dbw': self.saturated_power_dbw,
            'output_power_dbw': self.saturated_power_dbw - self.output_backoff_db,
            'input_backoff_db': self.input_backoff_db,
            'output_backoff_db': self.output_backoff_db,
            
            # Performance
            'total_gain_db': self.calculate_total_gain(),
            'cascade_noise_figure_db': self.calculate_cascade_noise_figure(),
            'cascade_noise_temp_k': self.calculate_cascade_noise_temperature(),
            'satellite_gt_db_k': self.calculate_satellite_gt(),
            'satellite_eirp_dbw': self.calculate_satellite_eirp(),
            
            # Per-stage
            'stages': stage_details,
        }
    
    # -- HPA nonlinear models (Saleh / Rapp / Linearized) --------------------
    
    # Default Saleh model parameters (typical TWTA)
    SALEH_PARAMS = {
        'alpha_a': 2.1587,   # AM/AM amplitude gain parameter
        'beta_a': 1.1517,    # AM/AM saturation parameter
        'alpha_phi': 4.0033, # AM/PM phase shift parameter (rad)
        'beta_phi': 9.1040,  # AM/PM saturation parameter
    }
    
    # Default Rapp model parameter
    RAPP_SMOOTHNESS = 2.0  # p=2 typical for SSPA (higher = sharper saturation)
    
    # HPA type: 'TWTA', 'SSPA', or 'Linearized'
    HPA_TYPES = ['TWTA', 'SSPA', 'Linearized']
    
    def __init__(self, preset=None):
        # Default transponder chain
        self.stages = []
        
        # Frequency plan
        self.uplink_freq_ghz = 14.0
        self.downlink_freq_ghz = 12.0
        self.lo_freq_ghz = 2.0  # LO = f_up - f_down (for Ku-band)
        
        # Transponder-level parameters
        self.bandwidth_mhz = 36.0
        self.saturated_power_dbw = 10.0  # Saturated TWTA/SSPA output
        self.input_backoff_db = 1.0
        self.output_backoff_db = 2.5
        
        # HPA type (determines nonlinear model)
        self.hpa_type = 'TWTA'  # 'TWTA', 'SSPA', or 'Linearized'
        self.rapp_p = self.RAPP_SMOOTHNESS
        self.saleh_alpha_a = self.SALEH_PARAMS['alpha_a']
        self.saleh_beta_a = self.SALEH_PARAMS['beta_a']
        self.saleh_alpha_phi = self.SALEH_PARAMS['alpha_phi']
        self.saleh_beta_phi = self.SALEH_PARAMS['beta_phi']
        
        # Antenna parameters
        self.rx_antenna_gain_dbi = 32.0
        self.tx_antenna_gain_dbi = 35.0
        
        # Load preset if specified
        if preset and preset in self.PRESETS:
            self._load_preset(preset)
        else:
            self._build_default_chain()
    
    def calculate_obo_from_ibo(self, ibo_db=None):
        """Output back-off (dB) from input back-off using current HPA model."""
        if ibo_db is None:
            ibo_db = self.input_backoff_db
            
        ibo_db = max(ibo_db, 0.001)  # Avoid exactly 0 dB
        
        # IBO (dB) = P_in_sat / P_in → ibo_linear = 10^(IBO/10)
        ibo_linear = 10 ** (ibo_db / 10.0)
        
        # Normalized input amplitude: r = sqrt(P_in / P_in_sat) = 1/sqrt(ibo_linear)
        r_in = 1.0 / np.sqrt(ibo_linear)
        
        if self.hpa_type == 'TWTA':
            # Saleh AM/AM: g(r) = alpha_a * r / (1 + beta_a * r²)
            r_out = self.saleh_alpha_a * r_in / (1.0 + self.saleh_beta_a * r_in**2)
            r_out_sat = self.saleh_alpha_a * 1.0 / (1.0 + self.saleh_beta_a * 1.0**2)  # at saturation (r=1)
            
        elif self.hpa_type == 'SSPA':
            # Rapp model: g(r) = r / (1 + (r)^(2p))^(1/(2p))
            p = self.rapp_p
            r_out = r_in / (1.0 + r_in**(2*p))**(1.0/(2*p))
            r_out_sat = 1.0 / (1.0 + 1.0)**(1.0/(2*p))  # at saturation (r=1)
            
        elif self.hpa_type == 'Linearized':
            # Ideal linearized TWTA: OBO ≈ IBO (near-perfect pre-distortion)
            return max(0.0, ibo_db - 0.1)  # Tiny residual compression
        else:
            return ibo_db  # Fallback
        
        # OBO = 10*log10(P_out_sat / P_out) = 10*log10((r_out_sat / r_out)²)
        if r_out < 1e-12:
            return 20.0  # Very deep backoff
        
        obo_linear = (r_out_sat / r_out) ** 2
        obo_db = 10.0 * np.log10(max(obo_linear, 1.0))
        
        return obo_db
    
    def calculate_am_pm(self, ibo_db=None):
        """AM/PM phase distortion in degrees at the current operating point."""
        if ibo_db is None:
            ibo_db = self.input_backoff_db
            
        if self.hpa_type == 'SSPA':
            return 0.0  # SSPA has negligible AM/PM
        
        if self.hpa_type == 'Linearized':
            return 0.0  # Pre-distortion corrects AM/PM
        
        # TWTA Saleh AM/PM
        ibo_linear = 10 ** (max(ibo_db, 0.001) / 10.0)
        r_in = 1.0 / np.sqrt(ibo_linear)
        
        phase_rad = self.saleh_alpha_phi * r_in**2 / (1.0 + self.saleh_beta_phi * r_in**2)
        phase_deg = np.degrees(phase_rad)
        
        return phase_deg
    
    def calculate_cim_from_ibo(self, ibo_db=None, num_carriers=1):
        """C/IM in dB from input back-off and carrier count."""
        if ibo_db is None:
            ibo_db = self.input_backoff_db
        
        if self.hpa_type == 'Linearized':
            # Pre-distorted: C/IM greatly improved
            base_cim = 2.0 * ibo_db + 35.0  # High baseline from linearization
        elif self.hpa_type == 'TWTA':
            # TWTA: sharper nonlinearity, worse C/IM
            # Empirical: C/IM ≈ 2*IBO + 10 dB (typical TWTA)
            base_cim = 2.0 * ibo_db + 10.0
        else:
            # SSPA: softer saturation, better C/IM than TWTA
            # Empirical: C/IM ≈ 2*IBO + 15 dB (typical SSPA)
            base_cim = 2.0 * ibo_db + 15.0
        
        # Multi-carrier degradation
        if num_carriers > 1:
            n = num_carriers
            # Number of 3rd-order intermod products falling on a carrier
            intermod_count = n * (n - 1) / 2.0
            base_cim -= 10.0 * np.log10(max(intermod_count, 1.0))
        
        return max(base_cim, 5.0)  # Floor at 5 dB
    
    def calculate_npr(self, ibo_db=None, num_carriers=1, uplink_cn_db=20.0):
        """Noise Power Ratio (NPR) in dB for multi-carrier operation."""
        if ibo_db is None:
            ibo_db = self.input_backoff_db
        
        c_im_db = self.calculate_cim_from_ibo(ibo_db, num_carriers)
        
        # NPR = -10*log10(1/cn_lin + 1/cim_lin)
        cn_lin = 10 ** (uplink_cn_db / 10.0)
        cim_lin = 10 ** (c_im_db / 10.0)
        
        npr_lin = 1.0 / (1.0/cn_lin + 1.0/cim_lin)
        npr_db = 10.0 * np.log10(npr_lin)
        
        return npr_db
    
    def find_optimal_ibo(self, uplink_cn_db=20.0, num_carriers=1, ibo_range=None):
        """Find IBO that maximizes NPR (optimum linearity/power trade-off)."""
        if ibo_range is None:
            ibo_range = np.linspace(0.0, 15.0, 300)
        
        npr_values = np.array([self.calculate_npr(ibo, num_carriers, uplink_cn_db) 
                               for ibo in ibo_range])
        obo_values = np.array([self.calculate_obo_from_ibo(ibo) for ibo in ibo_range])
        cim_values = np.array([self.calculate_cim_from_ibo(ibo, num_carriers) 
                               for ibo in ibo_range])
        
        # Effective output = P_sat - OBO (more output is better for link budget)
        # But we also need good intermod performance
        # NPR combines both effects
        optimal_idx = np.argmax(npr_values)
        
        return {
            'ibo_range_db': ibo_range,
            'obo_values_db': obo_values,
            'cim_values_db': cim_values,
            'npr_values_db': npr_values,
            'optimal_ibo_db': ibo_range[optimal_idx],
            'optimal_obo_db': obo_values[optimal_idx],
            'optimal_npr_db': npr_values[optimal_idx],
            'optimal_cim_db': cim_values[optimal_idx],
        }
    
    def get_hpa_characteristics(self, ibo_db=None):
        """Comprehensive HPA operating-point parameters dict."""
        if ibo_db is None:
            ibo_db = self.input_backoff_db
        
        obo = self.calculate_obo_from_ibo(ibo_db)
        am_pm = self.calculate_am_pm(ibo_db)
        c_im = self.calculate_cim_from_ibo(ibo_db)
        
        # Power efficiency: P_out / P_dc ∝ (P_sat - OBO) 
        # Higher OBO = lower efficiency
        efficiency_factor = 10 ** (-obo / 10.0)  # Fraction of P_sat being used
        
        return {
            'hpa_type': self.hpa_type,
            'ibo_db': ibo_db,
            'obo_db': obo,
            'am_pm_deg': am_pm,
            'c_im_db': c_im,
            'output_power_dbw': self.saturated_power_dbw - obo,
            'power_efficiency_pct': efficiency_factor * 100,
            'compression_db': max(0, ibo_db - obo),
        }
    
    def get_transfer_curve(self, input_range_dbw=None):
        """AM/AM and AM/PM transfer curves over a range of input powers."""
        if input_range_dbw is None:
            # Generate from -40 dBW to +10 dBW
            input_range_dbw = np.linspace(-40, 10, 200)
        
        total_gain = self.calculate_total_gain()
        p_sat = self.saturated_power_dbw
        
        # Input power at saturation
        p_in_sat_dbw = p_sat - total_gain
        
        # Linear output (no saturation)
        output_linear = input_range_dbw + total_gain
        
        # Apply HPA nonlinear model
        output_saturated = np.zeros_like(output_linear)
        am_pm_phase = np.zeros_like(output_linear)
        
        for i, p_in in enumerate(input_range_dbw):
            # IBO at this input level
            ibo_at_point = max(p_in_sat_dbw - p_in, 0.001)
            ibo_linear = 10 ** (ibo_at_point / 10.0)
            r_in = 1.0 / np.sqrt(max(ibo_linear, 1e-12))
            
            # Clamp input amplitude for stability
            r_in = min(r_in, 3.0) 
            
            if self.hpa_type == 'TWTA':
                # Saleh AM/AM
                r_out = self.saleh_alpha_a * r_in / (1.0 + self.saleh_beta_a * r_in**2)
                r_out_sat = self.saleh_alpha_a / (1.0 + self.saleh_beta_a)
                
                # Saleh AM/PM
                am_pm_phase[i] = np.degrees(
                    self.saleh_alpha_phi * r_in**2 / (1.0 + self.saleh_beta_phi * r_in**2))
                
            elif self.hpa_type == 'SSPA':
                # Rapp model
                p = self.rapp_p
                r_out = r_in / (1.0 + r_in**(2*p))**(1.0/(2*p))
                r_out_sat = 1.0 / (1.0 + 1.0)**(1.0/(2*p))
                am_pm_phase[i] = 0.0  # SSPA: negligible AM/PM
                
            else:  # Linearized
                r_out = min(r_in, 1.0)  # Perfect linear until saturation
                r_out_sat = 1.0
                am_pm_phase[i] = 0.0
            
            # Convert back to dBW
            if r_out_sat > 0 and r_out > 0:
                obo_at_point = (r_out_sat / r_out) ** 2
                output_saturated[i] = p_sat - 10.0 * np.log10(max(obo_at_point, 1.0))
            else:
                output_saturated[i] = p_sat - 40
        
        # Find 1-dB compression point
        compression = output_linear - output_saturated
        valid_compression = np.where(compression > 0, compression, 100)
        p1db_idx = np.argmin(np.abs(valid_compression - 1.0))
        
        return {
            'input_dbw': input_range_dbw,
            'output_linear_dbw': output_linear,
            'output_saturated_dbw': output_saturated,
            'am_pm_degrees': am_pm_phase,
            'saturation_power_dbw': p_sat,
            'p1db_input_dbw': input_range_dbw[p1db_idx],
            'p1db_output_dbw': output_saturated[p1db_idx],
            'total_gain_db': total_gain,
            'hpa_type': self.hpa_type,
        }
