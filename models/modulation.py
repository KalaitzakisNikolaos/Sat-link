"""
Modulation and Coding Schemes for Satellite Communications
Implements theoretical BER curves and performance calculations
References:
- Digital Communications by John G. Proakis
- DVB-S2/S2X standards (ETSI EN 302 307)
"""

import numpy as np
from scipy.special import erfc, erfcinv


class ModulationPerformance:
    """
    Calculate theoretical BER curves for various modulation schemes
    """
    
    @staticmethod
    def ber_bpsk(ebn0_db):
        """
        Theoretical BER for BPSK (Binary Phase Shift Keying)
        Formula: BER = Q(sqrt(2*Eb/N0)) = 0.5 * erfc(sqrt(Eb/N0))
        """
        ebn0_linear = 10**(ebn0_db / 10)
        ber = 0.5 * erfc(np.sqrt(ebn0_linear))
        return ber
    
    @staticmethod
    def ber_qpsk(ebn0_db):
        """
        Theoretical BER for QPSK (Quadrature Phase Shift Keying)
        Same as BPSK due to orthogonality
        """
        return ModulationPerformance.ber_bpsk(ebn0_db)
    
    @staticmethod
    def ber_8psk(ebn0_db):
        """
        Approximate BER for 8PSK
        Formula: BER ≈ (1/3) * erfc(sqrt(3*Eb/N0) * sin(π/8))
        """
        ebn0_linear = 10**(ebn0_db / 10)
        ber = (1/3) * erfc(np.sqrt(3 * ebn0_linear) * np.sin(np.pi / 8))
        return ber
    
    @staticmethod
    def ber_16qam(ebn0_db):
        """
        Approximate BER for 16-QAM
        Formula: BER ≈ (3/8) * erfc(sqrt(0.4 * Eb/N0))
        """
        ebn0_linear = 10**(ebn0_db / 10)
        ber = (3/8) * erfc(np.sqrt(0.4 * ebn0_linear))
        return ber
    
    @staticmethod
    def ber_16apsk(ebn0_db, r=2.85):
        """
        Approximate BER for 16-APSK
        r is the radius ratio (typical: 2.85 for DVB-S2)
        More complex, using approximation
        """
        ebn0_linear = 10**(ebn0_db / 10)
        # Simplified approximation (actual calculation is complex)
        ber = 0.4 * erfc(np.sqrt(0.35 * ebn0_linear))
        return ber
    
    @staticmethod
    def ber_32apsk(ebn0_db, r1=2.84, r2=5.27):
        """
        Approximate BER for 32-APSK
        r1, r2 are radius ratios (typical for DVB-S2)
        """
        ebn0_linear = 10**(ebn0_db / 10)
        # Simplified approximation
        ber = 0.45 * erfc(np.sqrt(0.28 * ebn0_linear))
        return ber
    
    @staticmethod
    def ber_64qam(ebn0_db):
        """
        Approximate BER for 64-QAM
        BER ≈ (7/24) * erfc(sqrt(1/7 * Eb/N0))
        """
        ebn0_linear = 10**(ebn0_db / 10)
        ber = (7/24) * erfc(np.sqrt((1.0/7.0) * ebn0_linear))
        return ber
    
    @staticmethod
    def get_ber_curve(modulation, ebn0_range_db):
        """
        Get BER curve for specified modulation
        
        Args:
            modulation: String like 'BPSK', 'QPSK', '8PSK', etc.
            ebn0_range_db: Array of Eb/N0 values in dB
        
        Returns:
            Array of BER values
        """
        ber_functions = {
            'BPSK': ModulationPerformance.ber_bpsk,
            'QPSK': ModulationPerformance.ber_qpsk,
            '8PSK': ModulationPerformance.ber_8psk,
            '16QAM': ModulationPerformance.ber_16qam,
            '16APSK': ModulationPerformance.ber_16apsk,
            '32APSK': ModulationPerformance.ber_32apsk,
            '64QAM': ModulationPerformance.ber_64qam,
        }
        
        if modulation not in ber_functions:
            # Default to QPSK
            modulation = 'QPSK'
        
        ber_func = ber_functions[modulation]
        ber = ber_func(ebn0_range_db)
        
        return ber
    
    @staticmethod
    def required_ebn0_for_ber(modulation, target_ber=1e-6):
        """
        Calculate required Eb/N0 for target BER
        Uses binary search
        """
        # Search range
        ebn0_min = -5
        ebn0_max = 30
        tolerance = 0.01
        
        while (ebn0_max - ebn0_min) > tolerance:
            ebn0_mid = (ebn0_min + ebn0_max) / 2
            ber = ModulationPerformance.get_ber_curve(modulation, np.array([ebn0_mid]))[0]
            
            if ber > target_ber:
                ebn0_min = ebn0_mid
            else:
                ebn0_max = ebn0_mid
        
        return (ebn0_min + ebn0_max) / 2
    
    @staticmethod
    def generate_constellation(modulation, num_symbols=1000, add_noise=False, noise_power=0.1):
        """
        Generate constellation diagram points
        
        Returns:
            (I, Q) arrays for in-phase and quadrature components
        """
        np.random.seed(42)  # For reproducibility
        
        if modulation == 'BPSK':
            # BPSK: two points on real axis
            symbols = np.random.choice([-1.0, 1.0], num_symbols)
            I = symbols.astype(float)
            Q = np.zeros(num_symbols, dtype=float)
            
        elif modulation == 'QPSK':
            # QPSK: four points at 45°, 135°, 225°, 315°
            phase = np.random.choice([np.pi/4, 3*np.pi/4, 5*np.pi/4, 7*np.pi/4], 
                                    num_symbols)
            I = np.cos(phase)
            Q = np.sin(phase)
            
        elif modulation == '8PSK':
            # 8PSK: eight points equally spaced
            phase = np.random.choice(np.linspace(0, 2*np.pi, 9)[:-1], num_symbols)
            I = np.cos(phase)
            Q = np.sin(phase)
            
        elif modulation == '16QAM':
            # 16-QAM: 4x4 grid
            levels = [-3, -1, 1, 3]
            I = np.random.choice(levels, num_symbols) / np.sqrt(10)
            Q = np.random.choice(levels, num_symbols) / np.sqrt(10)
            
        elif modulation == '16APSK':
            # 16-APSK: Two rings (4+12)
            # Inner ring: 4 symbols
            # Outer ring: 12 symbols
            ring = np.random.choice([0, 1], num_symbols, p=[0.25, 0.75])
            
            I = np.zeros(num_symbols)
            Q = np.zeros(num_symbols)
            
            for i in range(num_symbols):
                if ring[i] == 0:
                    # Inner ring
                    phase = np.random.choice([np.pi/4, 3*np.pi/4, 5*np.pi/4, 7*np.pi/4])
                    r = 1.0
                else:
                    # Outer ring
                    phase = np.random.choice(np.linspace(0, 2*np.pi, 13)[:-1])
                    r = 2.85
                
                I[i] = r * np.cos(phase)
                Q[i] = r * np.sin(phase)
            
            # Normalize
            norm = np.sqrt(np.mean(I**2 + Q**2))
            I /= norm
            Q /= norm
            
        elif modulation == '32APSK':
            # 32-APSK: Three rings (4+12+16)
            ring = np.random.choice([0, 1, 2], num_symbols, p=[0.125, 0.375, 0.5])
            
            I = np.zeros(num_symbols)
            Q = np.zeros(num_symbols)
            
            for i in range(num_symbols):
                if ring[i] == 0:
                    phase = np.random.choice([np.pi/4, 3*np.pi/4, 5*np.pi/4, 7*np.pi/4])
                    r = 1.0
                elif ring[i] == 1:
                    phase = np.random.choice(np.linspace(0, 2*np.pi, 13)[:-1])
                    r = 2.84
                else:
                    phase = np.random.choice(np.linspace(0, 2*np.pi, 17)[:-1])
                    r = 5.27
                
                I[i] = r * np.cos(phase)
                Q[i] = r * np.sin(phase)
            
            norm = np.sqrt(np.mean(I**2 + Q**2))
            I /= norm
            Q /= norm
            
        elif modulation == '64QAM':
            # 64-QAM: 8x8 grid
            levels = [-7, -5, -3, -1, 1, 3, 5, 7]
            I = np.random.choice(levels, num_symbols) / np.sqrt(42)
            Q = np.random.choice(levels, num_symbols) / np.sqrt(42)
            
        else:
            # Default to QPSK
            phase = np.random.choice([np.pi/4, 3*np.pi/4, 5*np.pi/4, 7*np.pi/4], 
                                    num_symbols)
            I = np.cos(phase)
            Q = np.sin(phase)
        
        # Add noise only if requested (callers typically add their own noise)
        if add_noise:
            I += np.random.normal(0, noise_power, num_symbols)
            Q += np.random.normal(0, noise_power, num_symbols)
        
        return I, Q


class ChannelCoding:
    """
    Channel coding performance calculations
    """
    
    @staticmethod
    def apply_coding_gain(uncoded_ebn0_db, coding_scheme='LDPC (R=3/4)'):
        """
        Apply coding gain to Eb/N0
        
        Args:
            uncoded_ebn0_db: Required Eb/N0 without coding
            coding_scheme: Coding scheme name
        
        Returns:
            Required Eb/N0 with coding (dB)
        """
        from .constants import CODING_SCHEMES
        
        if coding_scheme in CODING_SCHEMES:
            gain = CODING_SCHEMES[coding_scheme]['gain']
            return uncoded_ebn0_db - gain
        else:
            return uncoded_ebn0_db
    
    @staticmethod
    def calculate_throughput(symbol_rate_sps, modulation, coding_rate):
        """
        Calculate effective throughput
        
        Formula: Throughput = R_s * log2(M) * R_c
        where:
        - R_s is symbol rate
        - M is modulation order
        - R_c is coding rate
        """
        from .constants import MODULATION_SCHEMES
        
        if modulation in MODULATION_SCHEMES:
            bits_per_symbol = MODULATION_SCHEMES[modulation]['efficiency']
        else:
            bits_per_symbol = 2.0  # Default to QPSK
        
        throughput_bps = symbol_rate_sps * bits_per_symbol * coding_rate
        
        return throughput_bps
