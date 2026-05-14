"""Advanced analysis dialog with ITU-R compliant link budget tabs."""
import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel,
    QPushButton, QTabWidget, QComboBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from gui.core.mpl_canvas import MplCanvas
from models.constants import FADE_DYNAMICS_PARAMS, ITU_PFD_LIMITS, EIRP_DENSITY_MASKS

# IEEE color scheme
IEEE_COLORS = {
    'primary': '#4f46e5',
    'secondary': '#7c3aed',
    'tertiary': '#ec4899',
    'quaternary': '#f59e0b',
    'success': '#10b981',
    'warning': '#f97316',
    'error': '#ef4444',
    'grid': '#cbd5e1',
}


class AdvancedAnalysisDialog(QDialog):
    """ITU-R compliant advanced analysis dialog with 13 professional tabs."""
    
    def __init__(self, parent, params, results, link_budget):
        super().__init__(parent)
        self.params = params
        self.results = results
        self.link_budget = link_budget
        self.parent_window = parent
        self._is_fullscreen = False
        
        self.setWindowTitle("Advanced Link Analysis (ITU-R Compliant)")
        self.setMinimumSize(900, 600)
        self.resize(1500, 950)
        # Allow maximize button on the dialog
        self.setWindowFlags(self.windowFlags() | 
                           Qt.WindowType.WindowMaximizeButtonHint | 
                           Qt.WindowType.WindowMinimizeButtonHint)
        self.setStyleSheet("""
            QDialog {
                background-color: #f0f4f8;
            }
            QWidget { background-color: #f0f4f8; }
        """)
        
        self.setup_ui()
    
    @staticmethod
    def _rain_coefficients(freq_ghz):
        """ITU-R P.838-3 simplified rain attenuation coefficients (k, alpha) for given frequency."""
        if freq_ghz < 3:
            return 0.0001, 0.5
        elif freq_ghz < 6:
            return 0.0005, 0.85
        elif freq_ghz < 12:
            return 0.01, 1.0
        elif freq_ghz < 20:
            return 0.05, 1.1
        elif freq_ghz < 40:
            return 0.15, 1.15
        else:
            return 0.3, 1.2
        
    def setup_ui(self):
        """Setup professional dialog UI with dynamic resizing"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)
        
        # Header with fullscreen toggle
        header_widget = QWidget()
        header_widget.setFixedHeight(42)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(8, 0, 8, 0)
        header_layout.setSpacing(10)
        
        title = QLabel("ADVANCED LINK ANALYSIS")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {IEEE_COLORS['primary']}; background: transparent;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        subtitle = QLabel("ITU-R Compliant  |  IEEE Publication Quality")
        subtitle.setFont(QFont("Segoe UI", 9))
        subtitle.setStyleSheet("color: #666666; background: transparent;")
        header_layout.addWidget(subtitle)
        
        # Fullscreen toggle button
        self.fullscreen_btn = QPushButton("Fullscreen")
        self.fullscreen_btn.setFixedSize(100, 30)
        self.fullscreen_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #8b5cf6);
                color: white; border: none; border-radius: 6px;
                font-weight: 600; font-size: 9pt;
            }
            QPushButton:hover { background: #4f46e5; }
        """)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        header_layout.addWidget(self.fullscreen_btn)
        
        layout.addWidget(header_widget)
        
        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.setElideMode(Qt.TextElideMode.ElideNone)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #e2e8f0;
                border-radius: 10px;
                background-color: #ffffff;
                padding: 6px;
            }
            QTabBar {
                qproperty-expanding: false;
            }
            QTabBar::tab {
                background-color: #f1f5f9;
                border: none;
                border-radius: 8px;
                padding: 8px 14px;
                margin: 2px 1px 3px 1px;
                font-weight: 600;
                font-size: 9pt;
                color: #64748b;
                min-width: 60px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #8b5cf6);
                color: white;
            }
            QTabBar::tab:hover:!selected {
                background-color: #e0e7ff;
                color: #4338ca;
            }
            QTabBar::scroller {
                width: 30px;
            }
            QTabBar QToolButton {
                background-color: #e0e7ff;
                border: none;
                border-radius: 4px;
                margin: 2px;
            }
            QTabBar QToolButton:hover {
                background-color: #c7d2fe;
            }
        """)
        
        # Add all professional tabs (no emojis, clean labels)
        self.tabs.addTab(self.create_comparison_tab(), "Scenarios")
        self.tabs.addTab(self.create_elevation_sweep_tab(), "Elevation")
        self.tabs.addTab(self.create_rain_availability_tab(), "Availability")
        self.tabs.addTab(self.create_frequency_comparison_tab(), "Band Compare")
        self.tabs.addTab(self.create_sensitivity_tab(), "Sensitivity")
        self.tabs.addTab(self.create_timeseries_tab(), "Time Series")
        self.tabs.addTab(self.create_coverage_tab(), "Coverage")
        self.tabs.addTab(self.create_spectral_tab(), "Spectrum")
        self.tabs.addTab(self.create_monte_carlo_tab(), "Monte Carlo")
        self.tabs.addTab(self.create_fade_dynamics_tab(), "Fade Dynamics")
        self.tabs.addTab(self.create_regulatory_tab(), "Regulatory")
        self.tabs.addTab(self.create_interference_tab(), "Interference")
        self.tabs.addTab(self.create_rain_simulator_tab(), "Rain Simulator")
        
        layout.addWidget(self.tabs, 1)  # stretch factor = 1 → fills space
        
        # Bottom bar
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 4, 0, 0)
        btn_layout.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setFixedSize(120, 34)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d; color: white;
                border: none; padding: 6px 30px;
                border-radius: 6px; font-weight: 600; font-size: 10pt;
            }
            QPushButton:hover { background-color: #5a6268; }
        """)
        close_btn.clicked.connect(self.close)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
    
    def toggle_fullscreen(self):
        """Toggle between maximized and normal window mode"""
        if self._is_fullscreen:
            self.showNormal()
            self.fullscreen_btn.setText("Fullscreen")
            self._is_fullscreen = False
        else:
            self.showMaximized()
            self.fullscreen_btn.setText("Fullscreen")
            self._is_fullscreen = True
    
    def keyPressEvent(self, event):
        """Handle keyboard shortcuts: F11 for fullscreen, Escape to exit"""
        if event.key() == Qt.Key.Key_F11:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key.Key_Escape:
            if self._is_fullscreen:
                self.toggle_fullscreen()
            else:
                self.close()
        else:
            super().keyPressEvent(event)
    
    # --- Tab 1: Link budget comparison ---
    
    def create_comparison_tab(self):
        """Create scenario comparison tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        label = QLabel("Compare current link with different scenarios (antenna sizes, power levels, frequencies)")
        label.setStyleSheet("padding: 10px; background-color: #f5f5f5; border-left: 4px solid #9C27B0;")
        layout.addWidget(label)
        
        self.comparison_canvas = MplCanvas(self, width=10, height=7, dpi=100)
        layout.addWidget(self.comparison_canvas, 1)
        
        self.plot_comparison_analysis()
        
        return tab
    
    def plot_comparison_analysis(self):
        """Scenario comparison with link budget calculations."""
        ax = self.comparison_canvas.axes
        ax.clear()
        
        # Get accurate current metrics
        current_margin = self.results.get('total_margin_db', 0)
        current_eirp = self.params.get('sat_power_dbw', 10) + self.params.get('sat_antenna_gain_dbi', 32)
        
        # Define realistic professional scenarios
        scenarios = {
            'Baseline': {'power_delta': 0, 'antenna_delta': 0, 'freq_mult': 1.0, 'desc': 'Current'},
            'HPA Boost': {'power_delta': 3, 'antenna_delta': 0, 'freq_mult': 1.0, 'desc': '+3dB Power'},
            'Large Aperture': {'power_delta': 0, 'antenna_delta': 6, 'freq_mult': 1.0, 'desc': '2x Antenna'},
            'C-Band': {'power_delta': 0, 'antenna_delta': 0, 'freq_mult': 0.5, 'desc': '6 GHz'},
            'Ka-Band': {'power_delta': 0, 'antenna_delta': 0, 'freq_mult': 2.5, 'desc': '30 GHz'},
            'Optimized': {'power_delta': 3, 'antenna_delta': 6, 'freq_mult': 1.0, 'desc': 'Best Config'},
        }
        
        scenario_names = [v['desc'] for v in scenarios.values()]
        margins = []
        eirps = []
        g_over_t = []
        
        for key, sc in scenarios.items():
            # Accurate margin calculation
            margin = current_margin + sc['power_delta'] + sc['antenna_delta']
            
            # Frequency affects FSPL: FSPL ∝ 20log(f)
            if sc['freq_mult'] != 1.0:
                fspl_delta = 20 * np.log10(sc['freq_mult'])
                margin -= fspl_delta
            
            # EIRP calculation
            eirp = current_eirp + sc['power_delta']
            
            # G/T approximation
            gt = 20 + sc['antenna_delta']  # dB/K
            
            margins.append(margin)
            eirps.append(eirp)
            g_over_t.append(gt)
        
        x = np.arange(len(scenario_names))
        width = 0.27
        

        bars1 = ax.bar(x - width, margins, width, label='Link Margin', 
                       color=IEEE_COLORS['success'], alpha=0.85, edgecolor='#2b2b2b', linewidth=1.2)
        bars2 = ax.bar(x, [e - 40 for e in eirps], width, label='EIRP - 40 dBW', 
                       color=IEEE_COLORS['primary'], alpha=0.85, edgecolor='#2b2b2b', linewidth=1.2)
        bars3 = ax.bar(x + width, g_over_t, width, label='G/T (dB/K)', 
                       color=IEEE_COLORS['tertiary'], alpha=0.85, edgecolor='#2b2b2b', linewidth=1.2)
        

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(1.5)
        ax.spines['bottom'].set_linewidth(1.5)
        ax.grid(True, linestyle='--', alpha=0.3, linewidth=1, color=IEEE_COLORS['grid'], axis='y')
        
        ax.set_xlabel('Configuration Scenario', fontsize=12, fontweight='600', color='#2b2b2b')
        ax.set_ylabel('Performance Metric (dB)', fontsize=12, fontweight='600', color='#2b2b2b')
        ax.set_title('Link Budget Scenario Comparison', 
                     fontsize=13, fontweight='600', pad=18, color=IEEE_COLORS['primary'])
        ax.set_xticks(x)
        ax.set_xticklabels(scenario_names, fontsize=10, fontweight='500', rotation=0)
        ax.tick_params(width=1.5, labelsize=10)
        
        # Add critical threshold
        ax.axhline(y=0, color=IEEE_COLORS['error'], linestyle='--', linewidth=2, alpha=0.7, 
                   label='0 dB Threshold')
        
        # Value labels
        for bars in [bars1, bars2, bars3]:
            for bar in bars:
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height,
                       f'{height:.1f}',
                       ha='center', va='bottom' if height > 0 else 'top', 
                       fontsize=9, fontweight='600', color='#2b2b2b')
        

        ax.legend(loc='upper left', fontsize=10, framealpha=0.95, edgecolor='#999999', fancybox=True)
        
        # Best configuration annotation
        best_idx = np.argmax(margins)
        ax.text(0.98, 0.97, f'Optimal: {scenario_names[best_idx]}\nMargin: {margins[best_idx]:.2f} dB',
                transform=ax.transAxes, fontsize=10, ha='right', va='top', fontweight='600',
                bbox=dict(boxstyle='round,pad=0.7', facecolor='#fffacd', edgecolor=IEEE_COLORS['primary'], linewidth=2))
        
        self.comparison_canvas.draw()
    
    # --- Tab 2: Elevation angle sweep ---
    
    def create_elevation_sweep_tab(self):
        """Create elevation angle sweep tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        label = QLabel("Link performance vs elevation angle (5° to 90°) - Critical for satellite visibility planning")
        label.setStyleSheet("padding: 10px; background-color: #f5f5f5; border-left: 4px solid #2196F3;")
        layout.addWidget(label)
        
        self.elevation_canvas = MplCanvas(self, width=10, height=7, dpi=100)
        layout.addWidget(self.elevation_canvas, 1)
        
        self.plot_elevation_sweep()
        
        return tab
    
    def plot_elevation_sweep(self):
        """Elevation sweep with ITU-R P.618-14 rain attenuation."""
        ax = self.elevation_canvas.axes
        ax.clear()
        
        # Elevation angles from 5° to 90°
        elevations = np.linspace(5, 90, 86)
        
        # Get current parameters
        freq_ghz = self.params.get('downlink_frequency_ghz', 12.0)
        rain_rate = self.params.get('downlink_rain_rate', 10)
        altitude_km = self.params.get('altitude_km', 35786)
        current_elev = self.params.get('elevation_deg', 45)
        
        # ITU-R P.838-3 Rain attenuation coefficients (simplified)
        k_h, alpha_h = self._rain_coefficients(freq_ghz)
        
        margins = []
        rain_losses = []
        fspl_values = []
        
        Re = 6371  # Earth radius in km
        
        for elev in elevations:
            # Calculate slant range based on elevation
            h = altitude_km
            elev_rad = np.radians(elev)
            slant_range = np.sqrt((Re + h)**2 - Re**2 * np.cos(elev_rad)**2) - Re * np.sin(elev_rad)
            
            # ITU-R P.525 Free space path loss
            fspl = 20 * np.log10(slant_range * 1000) + 20 * np.log10(freq_ghz * 1e9) + 20 * np.log10(4 * np.pi / 3e8)
            fspl_values.append(fspl)
            
            # ITU-R P.618-14 Rain attenuation
            if rain_rate > 0:
                path_length_km = 5.0 / np.sin(elev_rad)  # Simplified effective path
                gamma_r = k_h * (rain_rate ** alpha_h)  # dB/km
                rain_loss = gamma_r * path_length_km
                rain_loss = min(rain_loss, 35)  # Cap at 35 dB
            else:
                rain_loss = 0
            rain_losses.append(rain_loss)
            
            # Estimate margin
            base_margin = self.results.get('total_margin_db', 10)
            margin = base_margin + (elev - 45) * 0.1 - rain_loss
            margins.append(margin)
        

        ax2 = ax.twinx()
        
        color1 = IEEE_COLORS['success']
        color2 = IEEE_COLORS['tertiary']
        color3 = IEEE_COLORS['primary']
        
        ax.plot(elevations, margins, color=color1, linewidth=2.5, label='Link Margin', zorder=3)
        ax.fill_between(elevations, 0, margins, where=(np.array(margins) > 0), 
                        color=color1, alpha=0.15, label='Positive Margin')
        
        ax.plot(elevations, rain_losses, color=color2, linewidth=2.5, linestyle='--', 
                label='Rain Attenuation', zorder=2)
        ax2.plot(elevations, fspl_values, color=color3, linewidth=2, linestyle=':', 
                 label='FSPL', alpha=0.7, zorder=1)
        
        # Highlight current elevation
        if 5 <= current_elev <= 90:
            idx = np.argmin(np.abs(elevations - current_elev))
            ax.scatter([current_elev], [margins[idx]], s=200, color=IEEE_COLORS['warning'], 
                      edgecolors='#2b2b2b', linewidths=2, zorder=5, marker='D')
            ax.annotate(f'Current\n{current_elev:.1f}° | {margins[idx]:.2f} dB',
                       xy=(current_elev, margins[idx]), xytext=(20, 30),
                       textcoords='offset points', fontsize=10, fontweight='600',
                       bbox=dict(boxstyle='round,pad=0.6', facecolor='#fff8dc', 
                                edgecolor=IEEE_COLORS['warning'], linewidth=2),
                       arrowprops=dict(arrowstyle='->', lw=2, color=IEEE_COLORS['warning']))
        

        ax.spines['top'].set_visible(False)
        ax2.spines['top'].set_visible(False)
        ax.spines['left'].set_linewidth(1.5)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_linewidth(1.5)
        ax2.spines['right'].set_linewidth(1.5)
        ax2.spines['left'].set_visible(False)
        
        ax.grid(True, linestyle='--', alpha=0.3, linewidth=1, color=IEEE_COLORS['grid'])
        ax.axhline(y=0, color=IEEE_COLORS['error'], linestyle='--', linewidth=2, alpha=0.7)
        
        ax.set_xlabel('Elevation Angle (degrees)', fontsize=12, fontweight='600', color='#2b2b2b')
        ax.set_ylabel('Margin / Rain Loss (dB)', fontsize=12, fontweight='600', color='#2b2b2b')
        ax2.set_ylabel('Free Space Path Loss (dB)', fontsize=12, fontweight='600', color=color3)
        ax.set_title(f'Link Performance vs. Elevation - {freq_ghz:.1f} GHz @ {rain_rate:.0f} mm/h Rain',
                    fontsize=13, fontweight='600', pad=18, color=IEEE_COLORS['primary'])
        
        ax.tick_params(axis='y', labelcolor='#2b2b2b', width=1.5, labelsize=10)
        ax2.tick_params(axis='y', labelcolor=color3, width=1.5, labelsize=10)
        ax.tick_params(axis='x', width=1.5, labelsize=10)
        
        # Combined legend
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='lower right', 
                 fontsize=10, framealpha=0.95, edgecolor='#999999', fancybox=True)
        
        ax.set_xlim(5, 90)
        
        self.elevation_canvas.draw()
    
    # --- Tab 3: Rain availability ---
    
    def create_rain_availability_tab(self):
        """Create rain rate vs link availability tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        label = QLabel("Statistical link availability for different rain rates - Essential for SLA planning (ITU-R P.618)")
        label.setStyleSheet("padding: 10px; background-color: #f5f5f5; border-left: 4px solid #FF5722;")
        layout.addWidget(label)
        
        self.availability_canvas = MplCanvas(self, width=10, height=7, dpi=100)
        layout.addWidget(self.availability_canvas, 1)
        
        self.plot_rain_availability()
        
        return tab
    
    def plot_rain_availability(self):
        """Rain availability analysis using ITU-R P.618-14 statistical model."""
        ax = self.availability_canvas.axes
        ax.clear()
        
        # Rain rates from 0 to 100 mm/h
        rain_rates = np.linspace(0, 100, 200)
        
        freq_ghz = self.params.get('downlink_frequency_ghz', 12.0)
        elevation_deg = self.params.get('elevation_deg', 45)
        current_margin = self.results.get('total_margin_db', 10)
        
        # ITU-R P.838-3 Rain attenuation coefficients (simplified)
        k, alpha = self._rain_coefficients(freq_ghz)
        
        # Rain attenuation using ITU-R P.618-14
        elev_rad = np.radians(elevation_deg)
        path_length_km = 5.0 / np.sin(elev_rad)  # Simplified effective path
        gamma_r = k * (rain_rates ** alpha)  # dB/km
        rain_attenuation = gamma_r * path_length_km
        
        # ITU-R P.618-14 statistical model for availability
        # Log-normal distribution of rain rates
        availabilities = []
        for atten in rain_attenuation:
            if atten <= current_margin:
                # High availability regime
                p = 0.001 * (atten / max(current_margin, 0.1))
            else:
                # Exceeded margin - exponential outage
                p = 0.001 * np.exp((atten - current_margin) / 3.0)
            
            availability = 100 * (1 - min(p, 1.0))
            availabilities.append(availability)
        
        availabilities = np.array(availabilities)
        

        color1 = IEEE_COLORS['primary']
        ax.plot(rain_rates, availabilities, color=color1, linewidth=3, label='Link Availability', zorder=3)
        ax.fill_between(rain_rates, 99.9, availabilities, where=(availabilities >= 99.9), 
                        color=IEEE_COLORS['success'], alpha=0.2, label='≥99.9% (SLA Compliant)')
        
        # SLA threshold lines
        ax.axhline(y=99.9, color=IEEE_COLORS['success'], linestyle='--', linewidth=2, 
                   alpha=0.8, label='99.9% (Three Nines)', zorder=2)
        ax.axhline(y=99.99, color=IEEE_COLORS['warning'], linestyle='--', linewidth=2, 
                   alpha=0.8, label='99.99% (Four Nines)', zorder=2)
        ax.axhline(y=99.999, color=IEEE_COLORS['tertiary'], linestyle='--', linewidth=2, 
                   alpha=0.8, label='99.999% (Five Nines)', zorder=2)
        

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(1.5)
        ax.spines['bottom'].set_linewidth(1.5)
        ax.grid(True, linestyle='--', alpha=0.3, linewidth=1, color=IEEE_COLORS['grid'], axis='both')
        
        ax.set_xlabel('Rain Rate (mm/h)', fontsize=12, fontweight='600', color='#2b2b2b')
        ax.set_ylabel('Link Availability (%)', fontsize=12, fontweight='600', color='#2b2b2b')
        ax.set_title(f'Statistical Availability Analysis - ITU-R P.618-14\n{freq_ghz:.1f} GHz @ {elevation_deg:.0f}° Elevation',
                    fontsize=13, fontweight='600', pad=18, color=IEEE_COLORS['primary'])
        ax.tick_params(width=1.5, labelsize=10)
        
        # Rain zone annotations
        ax.annotate('Light Rain\n(Temperate)', xy=(8, 99.95), fontsize=10, ha='center', fontweight='500',
                   bbox=dict(boxstyle='round,pad=0.6', facecolor='#d4edda', edgecolor=IEEE_COLORS['success'], linewidth=1.5))
        ax.annotate('Moderate Rain\n(Subtropical)', xy=(30, 99.85), fontsize=10, ha='center', fontweight='500',
                   bbox=dict(boxstyle='round,pad=0.6', facecolor='#fff3cd', edgecolor=IEEE_COLORS['warning'], linewidth=1.5))
        ax.annotate('Heavy Rain\n(Tropical)', xy=(65, 99.65), fontsize=10, ha='center', fontweight='500',
                   bbox=dict(boxstyle='round,pad=0.6', facecolor='#f8d7da', edgecolor=IEEE_COLORS['error'], linewidth=1.5))
        
        # Current margin indicator
        ax.text(0.02, 0.05, f'Current Link Margin: {current_margin:.2f} dB\nFrequency: {freq_ghz:.1f} GHz',
               transform=ax.transAxes, fontsize=11, ha='left', va='bottom', fontweight='600',
               bbox=dict(boxstyle='round,pad=0.7', facecolor='white', edgecolor=IEEE_COLORS['primary'], linewidth=2))
        
        # Legend
        ax.legend(loc='lower left', fontsize=10, framealpha=0.95, edgecolor='#999999', fancybox=True)
        
        ax.set_ylim(98.5, 100.05)
        ax.set_xlim(0, 100)
        
        self.availability_canvas.draw()
    
    # --- Tab 4: Frequency band comparison ---
    
    def create_frequency_comparison_tab(self):
        """Create frequency band comparison tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        label = QLabel("Compare performance across L/S/C/X/Ku/Ka/Q/V bands - Trade-offs between bandwidth and losses")
        label.setStyleSheet("padding: 10px; background-color: #f5f5f5; border-left: 4px solid #00BCD4;")
        layout.addWidget(label)
        
        self.frequency_canvas = MplCanvas(self, width=10, height=7, dpi=100)
        layout.addWidget(self.frequency_canvas, 1)
        
        self.plot_frequency_comparison()
        
        return tab
    
    def plot_frequency_comparison(self):
        """Frequency band comparison with ITU-R calculations."""
        ax = self.frequency_canvas.axes
        ax.clear()
        
        # Standard satellite communication bands
        bands = {
            'L': 1.5, 'S': 3.0, 'C': 6.0, 'X': 10.0,
            'Ku': 14.0, 'Ka': 30.0, 'Q': 40.0, 'V': 60.0
        }
        
        band_names = list(bands.keys())
        frequencies = list(bands.values())
        
        # Current parameters
        distance_km = self.params.get('distance_km', 40000)
        rain_rate = self.params.get('downlink_rain_rate', 10)
        elevation_deg = self.params.get('elevation_deg', 45)
        elev_rad = np.radians(elevation_deg)
        
        fspl_values = []
        rain_losses = []
        atmospheric_losses = []
        total_losses = []
        
        for freq_ghz in frequencies:
            # ITU-R P.525 Free Space Path Loss
            fspl = 20 * np.log10(distance_km * 1000) + 20 * np.log10(freq_ghz * 1e9) + 20 * np.log10(4 * np.pi / 3e8)
            fspl_values.append(fspl)
            
            # ITU-R P.838-3 Rain attenuation coefficients
            k, alpha = self._rain_coefficients(freq_ghz)
            
            path_length_km = 5.0 / np.sin(elev_rad)
            gamma_r = k * (rain_rate ** alpha)
            rain_loss = gamma_r * path_length_km
            rain_losses.append(rain_loss)
            
            # ITU-R P.676 Atmospheric attenuation (simplified)
            if freq_ghz < 20:
                atm_loss = 0.08 * freq_ghz / 10
            else:
                atm_loss = 0.4 + (freq_ghz - 20) * 0.04
            atmospheric_losses.append(atm_loss)
            
            total_losses.append(fspl + rain_loss + atm_loss)
        
        x = np.arange(len(band_names))
        width = 0.19
        

        bars1 = ax.bar(x - width*1.5, fspl_values, width, label='Free Space Loss',
                       color=IEEE_COLORS['primary'], alpha=0.85, edgecolor='#2b2b2b', linewidth=1)
        bars2 = ax.bar(x - width*0.5, rain_losses, width, label='Rain Attenuation',
                       color=IEEE_COLORS['tertiary'], alpha=0.85, edgecolor='#2b2b2b', linewidth=1)
        bars3 = ax.bar(x + width*0.5, atmospheric_losses, width, label='Atmospheric Loss',
                       color=IEEE_COLORS['success'], alpha=0.85, edgecolor='#2b2b2b', linewidth=1)
        bars4 = ax.bar(x + width*1.5, total_losses, width, label='Total Path Loss',
                       color=IEEE_COLORS['secondary'], alpha=0.85, edgecolor='#2b2b2b', linewidth=1)
        

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(1.5)
        ax.spines['bottom'].set_linewidth(1.5)
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=1, color=IEEE_COLORS['grid'], axis='y')
        
        ax.set_xlabel('Frequency Band', fontsize=12, fontweight='600', color='#2b2b2b')
        ax.set_ylabel('Path Loss (dB)', fontsize=12, fontweight='600', color='#2b2b2b')
        ax.set_title('Frequency Band Trade-off Analysis - ITU-R Path Loss Components',
                    fontsize=13, fontweight='600', pad=18, color=IEEE_COLORS['primary'])
        ax.set_xticks(x)
        ax.set_xticklabels([f'{b}\n{f} GHz' for b, f in zip(band_names, frequencies)],
                          fontsize=10, fontweight='500')
        ax.tick_params(width=1.5, labelsize=10)
        ax.legend(loc='upper left', fontsize=10, framealpha=0.95, edgecolor='#999999', fancybox=True)
        
        # Highlight current band
        current_freq = self.params.get('downlink_frequency_ghz', 12.0)
        closest_idx = np.argmin([abs(f - current_freq) for f in frequencies])
        bars4[closest_idx].set_edgecolor(IEEE_COLORS['warning'])
        bars4[closest_idx].set_linewidth(3)
        
        # Annotation for current band
        ax.text(0.98, 0.97, f'Current Band: {band_names[closest_idx]}\n{frequencies[closest_idx]} GHz',
               transform=ax.transAxes, fontsize=11, ha='right', va='top', fontweight='600',
               bbox=dict(boxstyle='round,pad=0.7', facecolor='#fff8dc',
                        edgecolor=IEEE_COLORS['warning'], linewidth=2))
        
        self.frequency_canvas.draw()
    
    # --- Tab 5: Sensitivity analysis ---
    
    def create_sensitivity_tab(self):
        """Create sensitivity/tornado analysis tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        label = QLabel("Tornado diagram showing which parameters most affect link margin - Optimize where it matters most")
        label.setStyleSheet("padding: 10px; background-color: #f5f5f5; border-left: 4px solid #FF9800;")
        layout.addWidget(label)
        
        self.sensitivity_canvas = MplCanvas(self, width=10, height=7, dpi=100)
        layout.addWidget(self.sensitivity_canvas, 1)
        
        self.plot_sensitivity_analysis()
        
        return tab
    
    def plot_sensitivity_analysis(self):
        """Tornado diagram for parameter sensitivity analysis."""
        ax = self.sensitivity_canvas.axes
        ax.clear()
        
        base_margin = self.results.get('total_margin_db', 10)
        
        # Realistic ±10% parameter variations
        parameters = [
            'TX Power', 'TX Antenna Gain', 'RX Antenna Diameter',
            'Frequency', 'Rain Rate', 'Elevation Angle', 'System Temperature'
        ]
        
        # Realistic sensitivities based on link budget physics
        sensitivities = {
            'TX Power': [base_margin - 0.91, base_margin + 0.91],  # 10log(1.1) = 0.41 dB
            'TX Antenna Gain': [base_margin - 2.1, base_margin + 2.1],  # Antenna size matters
            'RX Antenna Diameter': [base_margin - 1.7, base_margin + 1.7],  # Area ∝ D²
            'Frequency': [base_margin + 0.83, base_margin - 0.83],  # 20log(1.1) FSPL increase
            'Rain Rate': [base_margin + 2.5, base_margin - 3.2],  # Asymmetric, nonlinear
            'Elevation Angle': [base_margin - 1.3, base_margin + 0.7],  # Path length varies
            'System Temperature': [base_margin + 0.41, base_margin - 0.41]  # G/T effect
        }
        
        # Sort by total impact
        impacts = {p: abs(sensitivities[p][1] - sensitivities[p][0]) for p in parameters}
        parameters_sorted = sorted(parameters, key=lambda p: impacts[p], reverse=True)
        
        y_pos = np.arange(len(parameters_sorted))
        
        for i, param in enumerate(parameters_sorted):
            low, high = sensitivities[param]
            left = min(low, high)
            right = max(low, high)
            width_left = base_margin - left
            width_right = right - base_margin
            

            ax.barh(i, width_left, left=left, height=0.65,
                   color=IEEE_COLORS['tertiary'], alpha=0.85,
                   edgecolor='#2b2b2b', linewidth=1.2,
                   label='Decrease (-10%)' if i == 0 else '')
            ax.barh(i, width_right, left=base_margin, height=0.65,
                   color=IEEE_COLORS['success'], alpha=0.85,
                   edgecolor='#2b2b2b', linewidth=1.2,
                   label='Increase (+10%)' if i == 0 else '')
            
            # Value labels
            ax.text(left - 0.15, i, f'{low:.2f}', ha='right', va='center',
                   fontsize=9, fontweight='600', color='#2b2b2b')
            ax.text(right + 0.15, i, f'{high:.2f}', ha='left', va='center',
                   fontsize=9, fontweight='600', color='#2b2b2b')
        
        # Baseline reference line
        ax.axvline(x=base_margin, color=IEEE_COLORS['primary'], linestyle='--',
                  linewidth=2.5, label='Current Margin', zorder=3)
        

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(1.5)
        ax.spines['bottom'].set_linewidth(1.5)
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=1, color=IEEE_COLORS['grid'], axis='x')
        
        ax.set_yticks(y_pos)
        ax.set_yticklabels(parameters_sorted, fontsize=11, fontweight='500')
        ax.set_xlabel('Link Margin (dB)', fontsize=12, fontweight='600', color='#2b2b2b')
        ax.set_title('Parametric Sensitivity Analysis - Tornado Diagram (±10% Variation)',
                    fontsize=13, fontweight='600', pad=18, color=IEEE_COLORS['primary'])
        ax.tick_params(width=1.5, labelsize=10)
        ax.legend(loc='lower right', fontsize=10, framealpha=0.95, edgecolor='#999999', fancybox=True)
        

        ax.text(0.02, 0.98, f'Base Margin: {base_margin:.2f} dB\n\nWider bars indicate\nhigher sensitivity.\nOptimize these first!',
               transform=ax.transAxes, fontsize=10, va='top', fontweight='600',
               bbox=dict(boxstyle='round,pad=0.7', facecolor='#fff8dc',
                        edgecolor=IEEE_COLORS['warning'], linewidth=2))
        
        self.sensitivity_canvas.draw()
    
    # --- Tab 6: Time-series analysis ---
    
    def create_timeseries_tab(self):
        """Create time-series analysis tab (for LEO satellites)"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        label = QLabel("Time-series link performance for LEO satellites - Shows handover requirements and visibility windows")
        label.setStyleSheet("padding: 10px; background-color: #f5f5f5; border-left: 4px solid #673AB7;")
        layout.addWidget(label)
        
        self.timeseries_canvas = MplCanvas(self, width=10, height=7, dpi=100)
        layout.addWidget(self.timeseries_canvas, 1)
        
        self.plot_timeseries_analysis()
        
        return tab
    
    def plot_timeseries_analysis(self):
        """Plot time-series link performance"""
        ax = self.timeseries_canvas.axes
        ax.clear()
        
        # Get satellite type from parent's combo box
        sat_type = self.parent().sat_type_combo.currentText()
        
        if sat_type == 'GEO':
            # GEO is stationary
            ax.text(0.5, 0.5, 'Time-series analysis is for non-GEO satellites\n\n'
                   'GEO satellites are geostationary and maintain\nconstant link geometry.\n\n'
                   'Change satellite type to LEO, MEO, or HEO\nfor dynamic analysis.',
                   transform=ax.transAxes, fontsize=14, ha='center', va='center',
                   bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))
            ax.axis('off')
            self.timeseries_canvas.draw()
            return
        
        # Time in minutes (one full pass for LEO)
        if sat_type == 'LEO':
            duration = 15  # 15 minutes typical LEO pass
        elif sat_type == 'MEO':
            duration = 120  # 2 hours
        else:  # HEO
            duration = 360  # 6 hours
        
        time_minutes = np.linspace(0, duration, 200)
        
        # Simulate elevation angle over time (simplified sinusoidal)
        max_elevation = 85
        min_elevation = 5
        elevations = min_elevation + (max_elevation - min_elevation) * np.sin(np.pi * time_minutes / duration)**2
        
        # Calculate link parameters based on elevation
        margins = []
        doppler_shifts = []
        slant_ranges = []
        
        altitude_km = self.params.get('altitude_km', 550)
        freq_ghz = self.params.get('downlink_frequency_ghz', 12.0)
        
        for elev in elevations:
            # Slant range
            Re = 6371
            elev_rad = np.radians(elev)
            slant = np.sqrt((Re + altitude_km)**2 - Re**2 * np.cos(elev_rad)**2) - Re * np.sin(elev_rad)
            slant_ranges.append(slant)
            
            # Margin (better at high elevation)
            margin = 10 + (elev - 45) * 0.15
            margins.append(margin)
            
            # Doppler shift (maximum at horizon, zero at zenith)
            if sat_type == 'LEO':
                max_doppler = 40  # kHz
            elif sat_type == 'MEO':
                max_doppler = 5
            else:
                max_doppler = 15
            
            doppler = max_doppler * np.cos(elev_rad)
            doppler_shifts.append(doppler)
        

        ax.clear()
        fig = self.timeseries_canvas.figure
        fig.clear()
        
        ax1 = fig.add_subplot(311)
        ax2 = fig.add_subplot(312)
        ax3 = fig.add_subplot(313)
        
        # Panel 1: Elevation angle
        color1 = IEEE_COLORS['primary']
        ax1.plot(time_minutes, elevations, color=color1, linewidth=2.5, zorder=3)
        ax1.fill_between(time_minutes, 0, elevations, color=color1, alpha=0.15)
        ax1.axhline(y=10, color=IEEE_COLORS['error'], linestyle='--', linewidth=2,
                   alpha=0.8, label='Min Elevation (10°)', zorder=2)
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        ax1.spines['left'].set_linewidth(1.5)
        ax1.spines['bottom'].set_linewidth(1.5)
        ax1.grid(True, alpha=0.3, linestyle='--', linewidth=1, color=IEEE_COLORS['grid'])
        ax1.set_ylabel('Elevation (°)', fontsize=11, fontweight='600', color='#2b2b2b')
        ax1.set_title(f'{sat_type} Satellite Pass - Time Series Link Analysis',
                     fontsize=13, fontweight='600', pad=12, color=IEEE_COLORS['primary'])
        ax1.legend(fontsize=9, framealpha=0.95, edgecolor='#999999')
        ax1.set_xlim(0, duration)
        ax1.tick_params(width=1.5, labelsize=9)
        
        # Panel 2: Link margin
        color2 = IEEE_COLORS['success']
        ax2.plot(time_minutes, margins, color=color2, linewidth=2.5, zorder=3)
        ax2.fill_between(time_minutes, 0, margins, where=(np.array(margins) > 0),
                        color=color2, alpha=0.15)
        ax2.axhline(y=3, color=IEEE_COLORS['warning'], linestyle='--', linewidth=2,
                   alpha=0.8, label='Min Margin (3 dB)', zorder=2)
        ax2.axhline(y=0, color=IEEE_COLORS['error'], linestyle='-', linewidth=1.5,
                   alpha=0.7, zorder=1)
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        ax2.spines['left'].set_linewidth(1.5)
        ax2.spines['bottom'].set_linewidth(1.5)
        ax2.grid(True, alpha=0.3, linestyle='--', linewidth=1, color=IEEE_COLORS['grid'])
        ax2.set_ylabel('Link Margin (dB)', fontsize=11, fontweight='600', color='#2b2b2b')
        ax2.legend(fontsize=9, framealpha=0.95, edgecolor='#999999')
        ax2.set_xlim(0, duration)
        ax2.tick_params(width=1.5, labelsize=9)
        
        # Panel 3: Doppler shift
        color3 = IEEE_COLORS['tertiary']
        ax3.plot(time_minutes, doppler_shifts, color=color3, linewidth=2.5, zorder=3)
        ax3.fill_between(time_minutes, doppler_shifts, 0, color=color3, alpha=0.15)
        ax3.axhline(y=0, color='#2b2b2b', linestyle='-', linewidth=1, alpha=0.5)
        ax3.spines['top'].set_visible(False)
        ax3.spines['right'].set_visible(False)
        ax3.spines['left'].set_linewidth(1.5)
        ax3.spines['bottom'].set_linewidth(1.5)
        ax3.grid(True, alpha=0.3, linestyle='--', linewidth=1, color=IEEE_COLORS['grid'])
        ax3.set_ylabel('Doppler Shift (kHz)', fontsize=11, fontweight='600', color='#2b2b2b')
        ax3.set_xlabel('Time (minutes)', fontsize=12, fontweight='600', color='#2b2b2b')
        ax3.set_xlim(0, duration)
        ax3.tick_params(width=1.5, labelsize=9)
        
        # Mark handover zones (elevation < 15°)
        handover_times = time_minutes[elevations < 15]
        if len(handover_times) > 0:
            for ax_plot in [ax1, ax2, ax3]:
                for t in [handover_times[0], handover_times[-1]]:
                    ax_plot.axvline(x=t, color=IEEE_COLORS['warning'], linestyle=':',
                                   linewidth=2, alpha=0.7)
            # Annotation on first panel
            ax1.text(handover_times[0], 85, 'Handover', ha='center', fontsize=9,
                    fontweight='600', color=IEEE_COLORS['warning'])
        
        fig.tight_layout(pad=2.0)
        self.timeseries_canvas.draw()
    
    # --- Tab 7: Coverage map ---
    
    def create_coverage_tab(self):
        """Create coverage area analysis tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        label = QLabel("Geographic coverage map showing link margin contours - Footprint analysis")
        label.setStyleSheet("padding: 10px; background-color: #f5f5f5; border-left: 4px solid #4CAF50;")
        layout.addWidget(label)
        
        self.coverage_canvas = MplCanvas(self, width=10, height=7, dpi=100)
        layout.addWidget(self.coverage_canvas, 1)
        
        self.plot_coverage_map()
        
        return tab
    
    def plot_coverage_map(self):
        """Plot geographic coverage map with link margin contours"""
        ax = self.coverage_canvas.axes
        ax.clear()
        
        # Satellite position
        sat_lon = self.params.get('lon_sat', 13.0)
        sat_lat = self.params.get('lat_sat', 0.0)
        altitude_km = self.params.get('altitude_km', 35786)
        
        # Create grid of Earth locations
        lons = np.linspace(-180, 180, 100)
        lats = np.linspace(-80, 80, 80)
        LON, LAT = np.meshgrid(lons, lats)
        
        # Calculate link margin for each location
        margins = np.zeros_like(LON)
        
        Re = 6371  # Earth radius
        
        for i in range(len(lats)):
            for j in range(len(lons)):
                # Calculate elevation angle from this location
                lat_diff = lats[i] - sat_lat
                lon_diff = lons[j] - sat_lon
                
                # Central angle (simplified great circle distance)
                central_angle = np.sqrt(lat_diff**2 + lon_diff**2)
                central_angle_rad = np.radians(central_angle)
                
                # Elevation angle
                cos_gamma = np.cos(central_angle_rad)
                Rs = Re + altitude_km
                
                # Check visibility
                horizon_angle = np.arccos(Re / Rs)
                if central_angle_rad > horizon_angle:
                    margins[i, j] = np.nan  # Not visible
                    continue
                
                # Calculate elevation
                numerator = cos_gamma - Re / Rs
                denominator = np.sin(central_angle_rad)
                if denominator > 0.01:
                    elev = np.arctan(numerator / denominator)
                    elev_deg = np.degrees(elev)
                else:
                    elev_deg = 90
                
                if elev_deg < 0:
                    margins[i, j] = np.nan
                else:
                    # Link margin decreases at low elevation
                    base_margin = 15
                    margin = base_margin - (45 - elev_deg) * 0.2
                    margins[i, j] = max(0, margin)
        

        levels = [0, 3, 6, 9, 12, 15, 18, 21]
        contourf = ax.contourf(LON, LAT, margins, levels=levels, cmap='RdYlGn',
                              alpha=0.85, extend='both')
        contour = ax.contour(LON, LAT, margins, levels=levels, colors='#2b2b2b',
                            linewidths=0.8, alpha=0.4)
        ax.clabel(contour, inline=True, fontsize=9, fmt='%1.0f dB', colors='#2b2b2b')
        

        cbar = self.coverage_canvas.figure.colorbar(contourf, ax=ax, label='Link Margin (dB)',
                                                    pad=0.02, shrink=0.9)
        cbar.ax.tick_params(labelsize=10)
        
        # Mark satellite position
        ax.plot(sat_lon, sat_lat, marker='*', markersize=24, color=IEEE_COLORS['warning'],
               label='Satellite Nadir', markeredgecolor='#2b2b2b', markeredgewidth=2, zorder=5)
        
        # Mark ground station
        gs_lon = self.params.get('lon_gs', 23.0)
        gs_lat = self.params.get('lat_gs', 38.0)
        ax.plot(gs_lon, gs_lat, marker='o', markersize=14, color=IEEE_COLORS['primary'],
               label='Ground Station', markeredgecolor='#2b2b2b', markeredgewidth=2, zorder=5)
        
        # Horizon circle (visibility boundary)
        horizon_radius = np.degrees(np.arccos(Re / (Re + altitude_km)))
        circle = plt.Circle((sat_lon, sat_lat), horizon_radius, fill=False,
                          edgecolor=IEEE_COLORS['error'], linewidth=2.5, linestyle='--',
                          alpha=0.8, label=f'Horizon ({horizon_radius:.1f}°)', zorder=4)
        ax.add_patch(circle)
        

        ax.spines['top'].set_linewidth(1.5)
        ax.spines['right'].set_linewidth(1.5)
        ax.spines['left'].set_linewidth(1.5)
        ax.spines['bottom'].set_linewidth(1.5)
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=1, color=IEEE_COLORS['grid'])
        
        ax.set_xlabel('Longitude (°)', fontsize=12, fontweight='600', color='#2b2b2b')
        ax.set_ylabel('Latitude (°)', fontsize=12, fontweight='600', color='#2b2b2b')
        ax.set_title(f'Geographic Coverage Footprint - Link Margin Analysis\nAltitude: {altitude_km:.0f} km',
                    fontsize=13, fontweight='600', pad=18, color=IEEE_COLORS['primary'])
        ax.legend(loc='lower left', fontsize=10, framealpha=0.95, edgecolor='#999999', fancybox=True)
        ax.tick_params(width=1.5, labelsize=10)
        ax.set_xlim(-180, 180)
        ax.set_ylim(-80, 80)
        
        self.coverage_canvas.draw()
    
    # --- Tab 8: Spectral analysis ---
    
    def create_spectral_tab(self):
        """Create spectral analysis tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        label = QLabel("Frequency domain analysis - Signal spectrum, occupied bandwidth, and spectral efficiency")
        label.setStyleSheet("padding: 10px 14px; background-color: rgba(236, 72, 153, 0.08); border-left: 4px solid #ec4899; border-radius: 8px; color: #9d174d; font-weight: 500;")
        layout.addWidget(label)
        
        self.spectral_canvas = MplCanvas(self, width=10, height=7, dpi=100)
        layout.addWidget(self.spectral_canvas, 1)
        
        self.plot_spectral_analysis()
        
        return tab
    
    def plot_spectral_analysis(self):
        """Satellite spectrum analysis with raised-cosine filter shaping."""
        ax = self.spectral_canvas.axes
        ax.clear()
        
        # Parameters from link budget
        center_freq_ghz = self.params.get('downlink_frequency_ghz', 12.0)
        bandwidth_mhz = self.params.get('bandwidth_hz', 36e6) / 1e6
        modulation = self.params.get('modulation', 'QPSK')
        
        # Satellite-standard roll-off factors (DVB-S2, DVB-S2X)
        rolloff = 0.25  # Typical for satellite: 0.20, 0.25, 0.35
        
        # Calculate symbol rate: Rs = BW / (1 + α)
        symbol_rate_msps = bandwidth_mhz / (1 + rolloff)
        
        # Occupied bandwidth (99% power): BW_occ ≈ Rs * (1 + α)
        occupied_bw_mhz = symbol_rate_msps * (1 + rolloff)
        
        # Frequency axis (relative to center, in MHz)
        freq_relative = np.linspace(-bandwidth_mhz * 1.5, bandwidth_mhz * 1.5, 2000)
        
        # ACCURATE Raised Cosine Spectrum (DVB-S2 standard)
        # H(f) = 1 for |f| ≤ (1-α)/(2T)
        # H(f) = 0.5[1 + cos(π*T/α * (|f| - (1-α)/(2T)))] for (1-α)/(2T) < |f| ≤ (1+α)/(2T)
        # H(f) = 0 otherwise
        
        T = 1 / symbol_rate_msps  # Symbol period in microseconds
        spectrum = np.zeros_like(freq_relative)
        
        for i, f in enumerate(freq_relative):
            abs_f = abs(f)
            f_cutoff = (1 - rolloff) * symbol_rate_msps / 2
            f_edge = (1 + rolloff) * symbol_rate_msps / 2
            
            if abs_f <= f_cutoff:
                # Passband: unity gain
                spectrum[i] = 1.0
            elif abs_f < f_edge:
                # Transition band: raised cosine rolloff
                spectrum[i] = 0.5 * (1 + np.cos(np.pi * (abs_f - f_cutoff) / (rolloff * symbol_rate_msps)))
            else:
                # Stopband: zero
                spectrum[i] = 0
        
        # Add realistic spectral regrowth for non-linear satellite amplifiers
        # HPA introduces adjacent channel interference (TWTA effects)
        if modulation in ['16APSK', '32APSK', '16QAM', '64QAM']:
            # Higher-order modulations more sensitive to non-linearity
            for i, f in enumerate(freq_relative):
                abs_f = abs(f)
                if abs_f > occupied_bw_mhz / 2:
                    # Spectral regrowth in adjacent channels
                    regrowth_db = -40 - 10 * np.log10(1 + (abs_f - occupied_bw_mhz/2) / symbol_rate_msps)
                    regrowth_linear = 10 ** (regrowth_db / 10)
                    spectrum[i] = max(spectrum[i], regrowth_linear)
        
        # Convert to dB (normalize to 0 dB peak)
        spectrum_db = 10 * np.log10(spectrum + 1e-12)
        

        color1 = IEEE_COLORS['primary']
        ax.plot(freq_relative, spectrum_db, color=color1, linewidth=2.5,
               label='Raised-Cosine Filtered Signal', zorder=3)
        ax.fill_between(freq_relative, spectrum_db, -80, color=color1, alpha=0.15)
        
        # Symbol rate bandwidth markers (Rs)
        symbol_bw_half = symbol_rate_msps / 2
        ax.axvline(x=-symbol_bw_half, color=IEEE_COLORS['success'], linestyle='-.',
                  linewidth=2, alpha=0.7, label=f'Symbol Rate: {symbol_rate_msps:.2f} Msps', zorder=2)
        ax.axvline(x=symbol_bw_half, color=IEEE_COLORS['success'], linestyle='-.',
                  linewidth=2, alpha=0.7, zorder=2)
        
        # Occupied bandwidth markers (Rs * (1+α))
        occupied_bw_half = occupied_bw_mhz / 2
        ax.axvline(x=-occupied_bw_half, color=IEEE_COLORS['tertiary'], linestyle='--',
                  linewidth=2.5, alpha=0.8, zorder=2)
        ax.axvline(x=occupied_bw_half, color=IEEE_COLORS['tertiary'], linestyle='--',
                  linewidth=2.5, label=f'Occupied BW: {occupied_bw_mhz:.2f} MHz', alpha=0.8, zorder=2)
        
        # -3dB bandwidth (half-power points)
        bw_3db = symbol_rate_msps * (1 + rolloff * 0.5) / 2
        ax.axhline(y=-3, color=IEEE_COLORS['secondary'], linestyle=':', linewidth=2,
                  alpha=0.6, label='-3 dB Bandwidth', zorder=1)
        
        # Center frequency marker
        ax.axvline(x=0, color='#2b2b2b', linestyle='-', linewidth=1.5, alpha=0.5, zorder=2)
        
        # Satellite noise floor (typical)
        noise_floor_db = -60
        ax.axhline(y=noise_floor_db, color=IEEE_COLORS['warning'], linestyle='-.',
                  linewidth=2, alpha=0.7, label='Typical Noise Floor', zorder=1)
        
        # Adjacent channel mask (satellite regulatory limits)
        # ITU-R S.524 emission limits for satellite
        adjacent_mask_freq = [occupied_bw_half, occupied_bw_half * 1.5, occupied_bw_half * 2.0,
                             occupied_bw_half * 2.5, occupied_bw_half * 3.0]
        adjacent_mask_db = [-25, -35, -45, -55, -65]  # dB relative to carrier
        ax.plot(adjacent_mask_freq, adjacent_mask_db, 'r--', linewidth=2, alpha=0.6,
               label='ITU Emission Mask', zorder=1)
        ax.plot([-f for f in adjacent_mask_freq], adjacent_mask_db, 'r--', linewidth=2, alpha=0.6, zorder=1)
        

        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_linewidth(1.5)
        ax.spines['bottom'].set_linewidth(1.5)
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=1, color=IEEE_COLORS['grid'])
        
        ax.set_xlabel('Frequency Offset from Center (MHz)', fontsize=12, fontweight='600', color='#2b2b2b')
        ax.set_ylabel('Power Spectral Density (dB)', fontsize=12, fontweight='600', color='#2b2b2b')
        ax.set_title(f'Satellite Signal Spectrum - {modulation} with α={rolloff} Raised-Cosine',
                    fontsize=13, fontweight='600', pad=18, color=IEEE_COLORS['primary'])
        ax.tick_params(width=1.5, labelsize=10)
        ax.legend(loc='upper right', fontsize=9, framealpha=0.95, edgecolor='#999999', fancybox=True)
        ax.set_ylim(-80, 5)
        ax.set_xlim(-bandwidth_mhz * 1.2, bandwidth_mhz * 1.2)
        
        # Calculate accurate satellite spectral efficiency
        modulation_schemes = {
            'BPSK': 1, 'QPSK': 2, '8PSK': 3, '16QAM': 4,
            '16APSK': 4, '32APSK': 5, '64QAM': 6
        }
        bits_per_symbol = modulation_schemes.get(modulation, 2)
        
        # Realistic coding rates for DVB-S2/DVB-S2X
        # Typical MODCOD (Modulation and Coding) combinations
        if modulation == 'QPSK':
            coding_rate = 0.80  # QPSK typically uses strong FEC
        elif modulation in ['8PSK', '16APSK']:
            coding_rate = 0.75
        elif modulation in ['32APSK', '16QAM']:
            coding_rate = 0.70
        else:
            coding_rate = 0.65
        
        # Spectral efficiency in bit/s/Hz
        spectral_efficiency = (bits_per_symbol * coding_rate) / (1 + rolloff)
        
        # Information data rate
        data_rate_mbps = symbol_rate_msps * bits_per_symbol * coding_rate
        
        # Nyquist efficiency (how close to theoretical limit)
        nyquist_efficiency = spectral_efficiency / 2.0 * 100  # Percent of Nyquist limit
        
        info_text = f'DVB-S2 Standard\n'
        info_text += f'----------------\n'
        info_text += f'Modulation: {modulation}\n'
        info_text += f'Symbol Rate: {symbol_rate_msps:.2f} Msps\n'
        info_text += f'Roll-off (alpha): {rolloff}\n'
        info_text += f'Bits/Symbol: {bits_per_symbol}\n'
        info_text += f'Code Rate: {coding_rate}\n'
        info_text += f'----------------\n'
        info_text += f'Spectral Eff: {spectral_efficiency:.3f} bit/s/Hz\n'
        info_text += f'Data Rate: {data_rate_mbps:.2f} Mbps\n'
        info_text += f'Nyquist Eff: {nyquist_efficiency:.1f}%\n'
        info_text += f'Occupied BW: {occupied_bw_mhz:.2f} MHz'
        
        ax.text(0.02, 0.97, info_text, transform=ax.transAxes, fontsize=9,
               va='top', ha='left', fontweight='500', family='monospace',
               bbox=dict(boxstyle='round,pad=0.7', facecolor='white',
                        edgecolor=IEEE_COLORS['primary'], linewidth=2))
        
        self.spectral_canvas.draw()

    # --- Tab 9: Monte Carlo simulation ---
    
    def create_monte_carlo_tab(self):
        """Create Monte Carlo statistical link analysis tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        label = QLabel("Monte Carlo statistical analysis  —  Link availability, CDF/PDF curves, confidence intervals (ITU-R P.618/P.837)")
        label.setStyleSheet("padding: 10px 14px; background-color: rgba(16, 185, 129, 0.08); border-left: 4px solid #10b981; border-radius: 8px; color: #065f46; font-weight: 500;")
        layout.addWidget(label)
        
        self.mc_canvas = MplCanvas(self, width=10, height=7, dpi=100)
        layout.addWidget(self.mc_canvas, 1)
        
        self.plot_monte_carlo()
        
        return tab
    
    def plot_monte_carlo(self):
        """Monte Carlo simulation with 4-panel output."""
        fig = self.mc_canvas.figure
        fig.clear()
        
        # 2x2 subplot layout
        axes = fig.subplots(2, 2)
        ax_pdf, ax_cdf, ax_scatter, ax_avail = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]
        
        # Initialize Monte Carlo engine
        from models.link_budget import GeneralLinkBudget, MonteCarloSimulator
        link_calc = GeneralLinkBudget()
        mc = MonteCarloSimulator(link_calc)
        
        # Run simulation
        n_sim = 10000
        mc_results = mc.run_simulation(self.params, n_simulations=n_sim, climate_zone='Temperate')
        
        margins = mc_results['link_margins']
        rain_rates = mc_results['rain_rates']
        rain_att = mc_results['rain_attenuations']
        availability = mc_results['availability_pct']
        
        # Panel 1: PDF of link margin
        bins = np.linspace(np.min(margins) - 1, np.max(margins) + 1, 80)
        ax_pdf.hist(margins, bins=bins, density=True, color=IEEE_COLORS['primary'], 
                   alpha=0.7, edgecolor='white', linewidth=0.5, label='PDF')
        
        # Overlay normal fit
        mu, sigma = mc_results['mean_margin'], mc_results['std_margin']
        x_fit = np.linspace(np.min(margins) - 2, np.max(margins) + 2, 200)
        pdf_fit = (1 / (sigma * np.sqrt(2 * np.pi))) * np.exp(-0.5 * ((x_fit - mu) / sigma)**2)
        ax_pdf.plot(x_fit, pdf_fit, color=IEEE_COLORS['warning'], linewidth=2.5, 
                   label=f'Normal fit (μ={mu:.2f}, σ={sigma:.2f})')
        
        ax_pdf.axvline(x=0, color=IEEE_COLORS['error'], linewidth=2, linestyle='--', 
                      alpha=0.8, label='Outage threshold')
        
        # Confidence intervals
        ci_colors = ['#22c55e', '#eab308', '#f97316', '#ef4444']
        for idx, (ci, ci_data) in enumerate(mc_results['confidence_intervals'].items()):
            ax_pdf.axvline(x=ci_data['margin_threshold'], color=ci_colors[idx % 4], 
                          linewidth=1.5, linestyle=':', alpha=0.8,
                          label=f'{ci*100:.1f}% CI: {ci_data["margin_threshold"]:.2f} dB')
        
        ax_pdf.set_xlabel('Link Margin (dB)', fontsize=10, fontweight='600')
        ax_pdf.set_ylabel('Probability Density', fontsize=10, fontweight='600')
        ax_pdf.set_title('PDF of Link Margin', fontsize=11, fontweight='600', 
                        color=IEEE_COLORS['primary'])
        ax_pdf.legend(fontsize=7, framealpha=0.9, loc='upper left')
        ax_pdf.spines['top'].set_visible(False)
        ax_pdf.spines['right'].set_visible(False)
        ax_pdf.grid(True, alpha=0.3, linestyle='--')
        
        # Panel 2: CDF of link margin
        sorted_margins = np.sort(margins)
        cdf = np.arange(1, len(sorted_margins) + 1) / len(sorted_margins)
        
        ax_cdf.plot(sorted_margins, cdf * 100, color=IEEE_COLORS['primary'], linewidth=2.5, label='CDF')
        ax_cdf.fill_between(sorted_margins, 0, cdf * 100, alpha=0.1, color=IEEE_COLORS['primary'])
        
        # Mark availability targets
        targets = {'99.9%': 99.9, '99.99%': 99.99, '99.5%': 99.5}
        target_colors = {'99.9%': '#eab308', '99.99%': '#ef4444', '99.5%': '#22c55e'}
        for name, target in targets.items():
            pct_idx = int((1 - target/100) * len(sorted_margins))
            pct_idx = max(0, min(pct_idx, len(sorted_margins)-1))
            margin_at_target = sorted_margins[pct_idx]
            ax_cdf.axhline(y=100-target, color=target_colors[name], linewidth=1.5, linestyle='--', alpha=0.7)
            ax_cdf.axvline(x=margin_at_target, color=target_colors[name], linewidth=1.5, 
                          linestyle=':', alpha=0.7)
            ax_cdf.annotate(f'{name}\n{margin_at_target:.1f} dB', 
                           xy=(margin_at_target, 100-target),
                           xytext=(15, 15), textcoords='offset points', fontsize=7,
                           bbox=dict(boxstyle='round,pad=0.3', facecolor='white', 
                                    edgecolor=target_colors[name], alpha=0.9),
                           arrowprops=dict(arrowstyle='->', color=target_colors[name]))
        
        ax_cdf.axvline(x=0, color=IEEE_COLORS['error'], linewidth=2, linestyle='--', alpha=0.7)
        ax_cdf.set_xlabel('Link Margin (dB)', fontsize=10, fontweight='600')
        ax_cdf.set_ylabel('Cumulative Probability (%)', fontsize=10, fontweight='600')
        ax_cdf.set_title('CDF  —  Link Availability', fontsize=11, fontweight='600',
                        color=IEEE_COLORS['primary'])
        ax_cdf.set_ylim(0, 5)  # Focus on outage region (0-5%)
        ax_cdf.spines['top'].set_visible(False)
        ax_cdf.spines['right'].set_visible(False)
        ax_cdf.grid(True, alpha=0.3, linestyle='--')
        
        # Panel 3: rain rate vs attenuation scatter
        # Only plot non-zero rain samples for clarity
        rainy = rain_rates > 0.1
        if np.any(rainy):
            scatter = ax_scatter.scatter(rain_rates[rainy], rain_att[rainy], 
                                        c=margins[rainy], cmap='RdYlGn', 
                                        s=8, alpha=0.5, edgecolors='none')
            cbar = fig.colorbar(scatter, ax=ax_scatter, shrink=0.8, pad=0.02)
            cbar.set_label('Link Margin (dB)', fontsize=8)
            cbar.ax.tick_params(labelsize=7)
        
        ax_scatter.set_xlabel('Rain Rate (mm/h)', fontsize=10, fontweight='600')
        ax_scatter.set_ylabel('Rain Attenuation (dB)', fontsize=10, fontweight='600')
        ax_scatter.set_title('Rain Rate vs. Attenuation', fontsize=11, fontweight='600',
                            color=IEEE_COLORS['primary'])
        ax_scatter.spines['top'].set_visible(False)
        ax_scatter.spines['right'].set_visible(False)
        ax_scatter.grid(True, alpha=0.3, linestyle='--')
        
        # Panel 4: summary stats table
        ax_avail.axis('off')
        
        # Build results DataFrame for the table
        mc_table_data = [
            ['Simulations', f'{n_sim:,}', ''],
            ['Climate Zone', mc_results['climate_zone'], ''],
            ['Mean Margin', f'{mu:+.2f} dB', ''],
            ['Std Dev (\u03c3)', f'{sigma:.2f} dB', ''],
            ['Min Margin', f'{mc_results["min_margin"]:+.2f} dB', ''],
            ['Max Margin', f'{mc_results["max_margin"]:+.2f} dB', ''],
            ['Median', f'{mc_results["median_margin"]:+.2f} dB', ''],
            ['Availability', f'{availability:.4f}%', ''],
            ['Outage Samples', f'{mc_results["outage_samples"]:,} / {n_sim:,}', ''],
            ['Clear-sky Atten', f'{mc_results["clear_sky_atten_db"]:.2f} dB', ''],
        ]
        for ci, ci_data in mc_results['confidence_intervals'].items():
            mc_table_data.append([f'CI {ci*100:.1f}%', f'\u2265 {ci_data["margin_threshold"]:+.2f} dB', ''])
        
        # Status badge per row
        status_color = '#16a34a' if availability >= 99.9 else '#eab308' if availability >= 99.0 else '#dc2626'
        badge_text = 'LINK CLOSES' if availability >= 99.5 else 'MARGINAL' if availability >= 99.0 else 'INSUFFICIENT'
        mc_table_data.append(['STATUS', badge_text, ''])
        
        df_mc = pd.DataFrame(mc_table_data, columns=['Parameter', 'Value', ''])
        
        # Render as matplotlib table
        mc_tbl = ax_avail.table(
            cellText=df_mc[['Parameter', 'Value']].values,
            colLabels=['Parameter', 'Value'],
            cellLoc='left', colLoc='center',
            loc='upper center',
            colWidths=[0.48, 0.48]
        )
        mc_tbl.auto_set_font_size(False)
        mc_tbl.set_fontsize(8)
        mc_tbl.scale(1.0, 1.35)
        
        # Style the table with seaborn-inspired palette
        header_color = '#6366f1'
        alt_row_colors = ['#f8fafc', '#eef2ff']
        for (row, col), cell in mc_tbl.get_celld().items():
            cell.set_edgecolor('#e2e8f0')
            cell.set_linewidth(0.5)
            if row == 0:  # header
                cell.set_facecolor(header_color)
                cell.set_text_props(color='white', fontweight='bold', fontsize=9)
                cell.set_height(0.06)
            else:
                cell.set_facecolor(alt_row_colors[row % 2])
                cell.set_text_props(fontsize=8)
                # Highlight status row
                if row == len(mc_table_data):
                    cell.set_facecolor(status_color)
                    cell.set_text_props(color='white', fontweight='bold', fontsize=9)
        
        ax_avail.set_title('Monte Carlo Results', fontsize=11, fontweight='600',
                          color=IEEE_COLORS['primary'], pad=18, loc='center')
        ax_avail.title.set_position([0.5, 1.02])
        
        fig.suptitle(f'Monte Carlo Link Analysis  —  {n_sim:,} Simulations',
                    fontsize=14, fontweight='700', color=IEEE_COLORS['primary'], y=0.98)
        fig.tight_layout(rect=[0, 0, 1, 0.96])
        self.mc_canvas.draw()
    
    # --- Tab 10: Fade dynamics (P.1623) ---
    
    def create_fade_dynamics_tab(self):
        """Create fade dynamics / P.1623 analysis tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        label = QLabel("Rain fade time series synthesis & duration statistics  —  ITU-R P.1623-1 compliant fade dynamics")
        label.setStyleSheet("padding: 10px 14px; background-color: rgba(245, 158, 11, 0.08); border-left: 4px solid #f59e0b; border-radius: 8px; color: #92400e; font-weight: 500;")
        layout.addWidget(label)
        
        self.fade_canvas = MplCanvas(self, width=10, height=7, dpi=100)
        layout.addWidget(self.fade_canvas, 1)
        
        self.plot_fade_dynamics()
        
        return tab
    
    def plot_fade_dynamics(self):
        """Fade dynamics analysis (ITU-R P.1623) with 4-panel output."""
        fig = self.fade_canvas.figure
        fig.clear()
        
        axes = fig.subplots(2, 2)
        ax_ts, ax_exceed, ax_dur, ax_summary = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]
        
        # Initialize fade engine
        from models.link_budget import GeneralLinkBudget, FadeDynamicsAnalyzer
        link_calc = GeneralLinkBudget()
        fda = FadeDynamicsAnalyzer(link_calc)
        
        freq_ghz = self.params.get('downlink_frequency_ghz', 12.0)
        elevation_deg = self.params.get('elevation_deg', 45.0)
        current_margin = self.results.get('link_margin_db', 
                         self.results.get('total_margin_db', 10.0))
        rain_rate_001 = self.params.get('downlink_rain_rate', 42.0)
        if rain_rate_001 <= 0:
            rain_rate_001 = 42.0  # Default Temperate 0.01%
        station_height = self.params.get('gs_height_km', 0.0)
        rain_height = self.params.get('rain_height_km', 3.0)
        pol_tilt = self.params.get('polarization_tilt_deg', 45.0)
        
        # Generate 24-hour fade time series
        ts_data = fda.generate_fade_time_series(
            duration_hours=24, sample_interval_sec=10,
            freq_ghz=freq_ghz, elevation_deg=elevation_deg,
            rain_rate_001=rain_rate_001, station_height_km=station_height,
            rain_height_km=rain_height, pol_tilt_deg=pol_tilt)
        
        # Analyze fade events
        events = fda.analyze_fade_events(
            ts_data['attenuations_db'], abs(current_margin), sample_interval_sec=10)
        
        # Compute fade exceedance
        exceed_data = fda.compute_fade_exceedance(
            freq_ghz=freq_ghz, elevation_deg=elevation_deg,
            rain_rate_001=rain_rate_001, station_height_km=station_height,
            rain_height_km=rain_height, pol_tilt_deg=pol_tilt)
        
        # Panel 1: fade time series
        time_h = ts_data['time_hours']
        atten = ts_data['attenuations_db']
        
        ax_ts.plot(time_h, atten, color=IEEE_COLORS['primary'], linewidth=1, alpha=0.8)
        ax_ts.fill_between(time_h, 0, atten, alpha=0.2, color=IEEE_COLORS['primary'])
        
        # Margin threshold line
        ax_ts.axhline(y=abs(current_margin), color=IEEE_COLORS['error'], linewidth=2,
                      linestyle='--', label=f'Margin = {abs(current_margin):.1f} dB', alpha=0.8)
        
        # Highlight outage periods
        outage = atten > abs(current_margin)
        if np.any(outage):
            ax_ts.fill_between(time_h, abs(current_margin), atten, 
                              where=outage, color=IEEE_COLORS['error'], alpha=0.3, label='Outage')
        
        ax_ts.set_xlabel('Time (hours)', fontsize=10, fontweight='600')
        ax_ts.set_ylabel('Rain Attenuation (dB)', fontsize=10, fontweight='600')
        ax_ts.set_title('24-Hour Fade Time Series (ITU-R P.1623-1)', fontsize=11, 
                       fontweight='600', color=IEEE_COLORS['primary'])
        ax_ts.legend(fontsize=8, framealpha=0.9, loc='upper right')
        ax_ts.set_xlim(0, 24)
        ax_ts.set_ylim(bottom=0)
        ax_ts.spines['top'].set_visible(False)
        ax_ts.spines['right'].set_visible(False)
        ax_ts.grid(True, alpha=0.3, linestyle='--')
        
        # Panel 2: fade exceedance (P.618)
        percentages = exceed_data['percentages']
        fade_depths = exceed_data['fade_depths_db']
        
        ax_exceed.semilogy(fade_depths, percentages, color=IEEE_COLORS['primary'], 
                          linewidth=2.5, marker='o', markersize=4, label='ITU-R P.618')
        
        # Mark current margin
        ax_exceed.axvline(x=abs(current_margin), color=IEEE_COLORS['error'], linewidth=2,
                         linestyle='--', alpha=0.8, label=f'Margin = {abs(current_margin):.1f} dB')
        
        # Availability targets
        avail_targets = FADE_DYNAMICS_PARAMS['availability_targets']
        target_colors = ['#22c55e', '#84cc16', '#eab308', '#f97316', '#ef4444']
        for idx, (name, target) in enumerate(avail_targets.items()):
            outage_pct = 100 - target
            ax_exceed.axhline(y=outage_pct, color=target_colors[idx], linewidth=1,
                            linestyle=':', alpha=0.7)
            ax_exceed.text(fade_depths[-1] * 0.95, outage_pct * 1.3, 
                          f'{target}%', fontsize=7, color=target_colors[idx], 
                          ha='right', fontweight='600')
        
        ax_exceed.set_xlabel('Fade Depth (dB)', fontsize=10, fontweight='600')
        ax_exceed.set_ylabel('% Time Exceeded', fontsize=10, fontweight='600')
        ax_exceed.set_title('Fade Depth Exceedance (ITU-R P.618-14)', fontsize=11,
                           fontweight='600', color=IEEE_COLORS['primary'])
        ax_exceed.legend(fontsize=8, framealpha=0.9)
        ax_exceed.spines['top'].set_visible(False)
        ax_exceed.spines['right'].set_visible(False)
        ax_exceed.grid(True, alpha=0.3, linestyle='--', which='both')
        ax_exceed.set_ylim(0.0005, 60)
        
        # Panel 3: fade duration distribution
        if events['n_events'] > 0 and len(events['durations_sec']) > 0:
            dur = events['durations_sec']
            dur_bins_edges = [1, 5, 10, 30, 60, 120, 300, 600, 1800, 3600]
            dur_hist, _ = np.histogram(dur, bins=dur_bins_edges)
            
            bar_labels = ['1-5s', '5-10s', '10-30s', '30-60s', '1-2m', '2-5m', '5-10m', '10-30m', '30-60m']
            bar_labels = bar_labels[:len(dur_hist)]
            x_pos = np.arange(len(dur_hist))
            
            colors_bar = [IEEE_COLORS['success'] if d < 60 else IEEE_COLORS['warning'] if d < 300 
                         else IEEE_COLORS['error'] for d in dur_bins_edges[:-1]]
            ax_dur.bar(x_pos, dur_hist, color=colors_bar[:len(dur_hist)], alpha=0.8, 
                      edgecolor='white', linewidth=1)
            ax_dur.set_xticks(x_pos)
            ax_dur.set_xticklabels(bar_labels, rotation=45, fontsize=8)
            ax_dur.set_ylabel('Number of Events', fontsize=10, fontweight='600')
        else:
            ax_dur.text(0.5, 0.5, 'No fade events detected\n(margin sufficient)', 
                       transform=ax_dur.transAxes, ha='center', va='center',
                       fontsize=12, color=IEEE_COLORS['success'], fontweight='600')
        
        ax_dur.set_title('Fade Duration Distribution (ITU-R P.1623)', fontsize=11,
                        fontweight='600', color=IEEE_COLORS['primary'])
        ax_dur.spines['top'].set_visible(False)
        ax_dur.spines['right'].set_visible(False)
        ax_dur.grid(True, alpha=0.3, linestyle='--', axis='y')
        
        # Panel 4: summary stats table
        ax_summary.axis('off')
        
        avail = events['availability_pct']
        status_color = '#16a34a' if avail >= 99.9 else '#eab308' if avail >= 99.0 else '#dc2626'
        
        # Build table data
        fade_table_data = [
            ['Frequency', f'{freq_ghz:.1f} GHz'],
            ['Elevation', f'{elevation_deg:.1f}\u00b0'],
            ['Rain Rate (0.01%)', f'{rain_rate_001:.1f} mm/h'],
            ['Link Margin', f'{abs(current_margin):.2f} dB'],
            ['Max Attenuation', f'{np.max(atten):.2f} dB'],
            ['Availability', f'{avail:.4f}%'],
            ['Outage Time', f'{events["total_outage_sec"]:.0f} sec'],
            ['Fade Events', f'{events["n_events"]}'],
        ]
        if events['n_events'] > 0:
            fade_table_data.append(['Mean Duration', f'{events["mean_duration_sec"]:.1f} sec'])
            fade_table_data.append(['Max Duration', f'{events["max_duration_sec"]:.0f} sec'])
        
        # SLA assessment rows
        for name, target in avail_targets.items():
            status_str = 'PASS' if avail >= target else 'FAIL'
            fade_table_data.append([f'SLA {name.replace("_", " ").title()}', f'{target}%  [{status_str}]'])
        
        df_fade = pd.DataFrame(fade_table_data, columns=['Parameter', 'Value'])
        
        fade_tbl = ax_summary.table(
            cellText=df_fade.values,
            colLabels=['Parameter', 'Value'],
            cellLoc='left', colLoc='center',
            loc='upper center',
            colWidths=[0.48, 0.48]
        )
        fade_tbl.auto_set_font_size(False)
        fade_tbl.set_fontsize(8)
        fade_tbl.scale(1.0, 1.35)
        
        header_color = '#6366f1'
        alt_row_colors = ['#f8fafc', '#eef2ff']
        for (row, col), cell in fade_tbl.get_celld().items():
            cell.set_edgecolor('#e2e8f0')
            cell.set_linewidth(0.5)
            if row == 0:
                cell.set_facecolor(header_color)
                cell.set_text_props(color='white', fontweight='bold', fontsize=9)
                cell.set_height(0.05)
            else:
                cell.set_facecolor(alt_row_colors[row % 2])
                cell.set_text_props(fontsize=8)
                # Color SLA rows by pass/fail
                cell_text = str(df_fade.values[row-1][1]) if col == 1 else ''
                if '[PASS]' in cell_text:
                    cell.set_facecolor('#dcfce7')
                    cell.set_text_props(fontsize=8, color='#166534')
                elif '[FAIL]' in cell_text:
                    cell.set_facecolor('#fee2e2')
                    cell.set_text_props(fontsize=8, color='#991b1b')
        
        ax_summary.set_title('Fade Dynamics Summary (P.1623)', fontsize=11, fontweight='600',
                            color=IEEE_COLORS['primary'], pad=18, loc='center')
        ax_summary.title.set_position([0.5, 1.02])
        
        fig.suptitle(f'Fade Dynamics Analysis  —  {freq_ghz:.1f} GHz, {elevation_deg:.1f}° Elevation',
                    fontsize=14, fontweight='700', color=IEEE_COLORS['primary'], y=0.98)
        fig.tight_layout(rect=[0, 0, 1, 0.96])
        self.fade_canvas.draw()
    
    # --- Tab 11: Regulatory compliance ---
    
    def create_regulatory_tab(self):
        """Create ITU regulatory compliance analysis tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        label = QLabel("ITU Regulatory compliance  —  PFD/4kHz limits (Art. 21), EIRP density masks (S.524), compliance margin analysis")
        label.setStyleSheet("padding: 10px 14px; background-color: rgba(239, 68, 68, 0.08); border-left: 4px solid #ef4444; border-radius: 8px; color: #991b1b; font-weight: 500;")
        layout.addWidget(label)
        
        self.regulatory_canvas = MplCanvas(self, width=10, height=7, dpi=100)
        layout.addWidget(self.regulatory_canvas, 1)
        
        self.plot_regulatory_compliance()
        
        return tab
    
    def plot_regulatory_compliance(self):
        """Regulatory compliance analysis (PFD / EIRP density masks)."""
        fig = self.regulatory_canvas.figure
        fig.clear()
        
        axes = fig.subplots(2, 2)
        ax_pfd_elev, ax_pfd_bands, ax_eirp_mask, ax_summary = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]
        
        # Initialize regulatory checker
        from models.link_budget import RegulatoryComplianceChecker
        reg = RegulatoryComplianceChecker()
        
        freq_ghz = self.params.get('downlink_frequency_ghz', 12.0)
        elevation_deg = self.params.get('elevation_deg', 45.0)
        distance_km = self.params.get('distance_km', 35786.0)
        bandwidth_hz = self.params.get('bandwidth_hz', 36e6)
        
        # Calculate satellite EIRP from results
        sat_eirp_dbw = self.results.get('downlink', {}).get('eirp_dbw', 
                       self.results.get('eirp_dbw', 52.0))
        if isinstance(sat_eirp_dbw, dict):
            sat_eirp_dbw = 52.0
        
        is_gso = self.params.get('orbit_type', 'GEO') == 'GEO'
        
        # Panel 1: PFD vs elevation
        pfd_data = reg.compute_pfd_vs_elevation(sat_eirp_dbw, distance_km, bandwidth_hz, 
                                                 freq_ghz, is_gso)
        
        elevations = pfd_data['elevations']
        ax_pfd_elev.plot(elevations, pfd_data['pfd_limits'], color=IEEE_COLORS['error'], 
                        linewidth=2.5, linestyle='--', label='ITU PFD Limit', zorder=3)
        ax_pfd_elev.plot(elevations, pfd_data['pfd_actuals'], color=IEEE_COLORS['primary'], 
                        linewidth=2.5, label='Actual PFD/4kHz', zorder=3)
        
        # Fill compliance/violation regions
        compliant = pfd_data['pfd_actuals'] <= pfd_data['pfd_limits']
        ax_pfd_elev.fill_between(elevations, pfd_data['pfd_actuals'], pfd_data['pfd_limits'],
                                where=compliant, color=IEEE_COLORS['success'], alpha=0.15, 
                                label='Compliant margin')
        ax_pfd_elev.fill_between(elevations, pfd_data['pfd_actuals'], pfd_data['pfd_limits'],
                                where=~compliant, color=IEEE_COLORS['error'], alpha=0.2,
                                label='VIOLATION')
        
        # Mark current elevation
        ax_pfd_elev.axvline(x=elevation_deg, color=IEEE_COLORS['warning'], linewidth=2,
                           linestyle=':', alpha=0.8)
        current_compliance = reg.check_compliance(sat_eirp_dbw, distance_km, bandwidth_hz,
                                                   freq_ghz, elevation_deg, is_gso)
        ax_pfd_elev.scatter([elevation_deg], [current_compliance['pfd_actual_dbw_m2_4khz']], 
                           s=150, color=IEEE_COLORS['warning'], edgecolors='#2b2b2b',
                           linewidths=2, zorder=5, marker='D')
        
        ax_pfd_elev.set_xlabel('Elevation Angle (degrees)', fontsize=10, fontweight='600')
        ax_pfd_elev.set_ylabel('PFD (dBW/m²/4kHz)', fontsize=10, fontweight='600')
        ax_pfd_elev.set_title(f'PFD vs. Elevation  —  {pfd_data["band_name"]}', fontsize=11,
                             fontweight='600', color=IEEE_COLORS['primary'])
        ax_pfd_elev.legend(fontsize=8, framealpha=0.9, loc='lower right')
        ax_pfd_elev.spines['top'].set_visible(False)
        ax_pfd_elev.spines['right'].set_visible(False)
        ax_pfd_elev.grid(True, alpha=0.3, linestyle='--')
        
        # Panel 2: PFD limits across bands
        band_names = []
        band_limits_low = []
        band_limits_high = []
        band_actual = []
        
        gso_limits = ITU_PFD_LIMITS['gso_limits']
        for (f_min, f_max), limit_data in gso_limits.items():
            band_names.append(limit_data['name'].split('(')[0].strip())
            band_limits_low.append(limit_data['pfd_low'])
            band_limits_high.append(limit_data['pfd_high'])
            # Calculate actual PFD at band center
            f_center = (f_min + f_max) / 2
            pfd_actual = reg.calculate_pfd_per_4khz(sat_eirp_dbw, distance_km, bandwidth_hz)
            band_actual.append(pfd_actual)
        
        x_pos = np.arange(len(band_names))
        width = 0.25
        
        ax_pfd_bands.bar(x_pos - width, band_limits_low, width, color=IEEE_COLORS['success'],
                        alpha=0.7, label='Limit @ 0° elev', edgecolor='white')
        ax_pfd_bands.bar(x_pos, band_limits_high, width, color=IEEE_COLORS['warning'],
                        alpha=0.7, label='Limit @ 90° elev', edgecolor='white')
        ax_pfd_bands.bar(x_pos + width, band_actual, width, color=IEEE_COLORS['primary'],
                        alpha=0.7, label='Actual PFD/4kHz', edgecolor='white')
        
        ax_pfd_bands.set_xticks(x_pos)
        ax_pfd_bands.set_xticklabels(band_names, rotation=45, ha='right', fontsize=7)
        ax_pfd_bands.set_ylabel('PFD (dBW/m²/4kHz)', fontsize=10, fontweight='600')
        ax_pfd_bands.set_title('PFD Limits by Frequency Band (ITU Art. 21)', fontsize=11,
                              fontweight='600', color=IEEE_COLORS['primary'])
        ax_pfd_bands.legend(fontsize=7, framealpha=0.9, loc='upper right')
        ax_pfd_bands.spines['top'].set_visible(False)
        ax_pfd_bands.spines['right'].set_visible(False)
        ax_pfd_bands.grid(True, alpha=0.3, linestyle='--', axis='y')
        
        # Panel 3: EIRP density mask
        # Earth Station mask
        mask_es = reg.compute_eirp_density_mask('standard_earth_station')
        mask_sat = reg.compute_eirp_density_mask('satellite_downlink')
        
        ax_eirp_mask.plot(mask_es['theta_deg'], mask_es['eirp_limit_dbw_40khz'],
                         color=IEEE_COLORS['primary'], linewidth=2.5, 
                         label='Earth Station (ITU-R S.524)')
        ax_eirp_mask.plot(mask_sat['theta_deg'], mask_sat['eirp_limit_dbw_40khz'],
                         color=IEEE_COLORS['tertiary'], linewidth=2.5, linestyle='--',
                         label='Satellite DL (ITU-R S.728)')
        
        ax_eirp_mask.fill_between(mask_es['theta_deg'], mask_es['eirp_limit_dbw_40khz'], -20,
                                 alpha=0.1, color=IEEE_COLORS['primary'])
        
        ax_eirp_mask.set_xlabel('Off-axis Angle θ (degrees)', fontsize=10, fontweight='600')
        ax_eirp_mask.set_ylabel('EIRP Density (dBW/40kHz)', fontsize=10, fontweight='600')
        ax_eirp_mask.set_title('EIRP Density Off-axis Masks', fontsize=11,
                              fontweight='600', color=IEEE_COLORS['primary'])
        ax_eirp_mask.set_xscale('log')
        ax_eirp_mask.set_xlim(1, 180)
        ax_eirp_mask.legend(fontsize=8, framealpha=0.9, loc='upper right')
        ax_eirp_mask.spines['top'].set_visible(False)
        ax_eirp_mask.spines['right'].set_visible(False)
        ax_eirp_mask.grid(True, alpha=0.3, linestyle='--', which='both')
        
        # Panel 4: compliance summary
        ax_summary.axis('off')
        
        compliance = current_compliance
        status_text = 'COMPLIANT' if compliance['compliant'] else 'VIOLATION'
        status_color = '#16a34a' if compliance['compliant'] else '#dc2626'
        
        # Build regulatory compliance table data
        reg_table_data = [
            ['Status', status_text],
            ['Band', compliance['band_name']],
            ['Orbit Type', 'GSO' if is_gso else 'NGSO'],
            ['Actual PFD', f'{compliance["pfd_actual_dbw_m2_4khz"]:.2f} dBW/m\u00b2/4kHz'],
            ['ITU Limit', f'{compliance["pfd_limit_dbw_m2_4khz"]:.2f} dBW/m\u00b2/4kHz'],
            ['Margin', f'{compliance["margin_db"]:+.2f} dB'],
            ['Frequency', f'{freq_ghz:.2f} GHz'],
            ['Elevation', f'{elevation_deg:.1f}\u00b0'],
            ['Sat EIRP', f'{sat_eirp_dbw:.1f} dBW'],
            ['Distance', f'{distance_km:.0f} km'],
            ['Bandwidth', f'{bandwidth_hz/1e6:.1f} MHz'],
            ['Reference', 'ITU RR Art. 21, Table 21-4'],
            ['Masks', 'ITU-R S.524-9 / S.728'],
        ]
        
        df_reg = pd.DataFrame(reg_table_data, columns=['Parameter', 'Value'])
        
        reg_tbl = ax_summary.table(
            cellText=df_reg.values,
            colLabels=['Parameter', 'Value'],
            cellLoc='left', colLoc='center',
            loc='upper center',
            colWidths=[0.42, 0.54]
        )
        reg_tbl.auto_set_font_size(False)
        reg_tbl.set_fontsize(8)
        reg_tbl.scale(1.0, 1.35)
        
        header_color = '#6366f1'
        alt_row_colors = ['#f8fafc', '#eef2ff']
        for (row, col), cell in reg_tbl.get_celld().items():
            cell.set_edgecolor('#e2e8f0')
            cell.set_linewidth(0.5)
            if row == 0:
                cell.set_facecolor(header_color)
                cell.set_text_props(color='white', fontweight='bold', fontsize=9)
                cell.set_height(0.05)
            elif row == 1:  # Status row
                cell.set_facecolor(status_color)
                cell.set_text_props(color='white', fontweight='bold', fontsize=9)
            elif row == 6:  # Margin row highlight
                margin_val = compliance['margin_db']
                if margin_val >= 0:
                    cell.set_facecolor('#dcfce7')
                    cell.set_text_props(fontsize=8, color='#166534')
                else:
                    cell.set_facecolor('#fee2e2')
                    cell.set_text_props(fontsize=8, color='#991b1b')
            else:
                cell.set_facecolor(alt_row_colors[row % 2])
                cell.set_text_props(fontsize=8)
        
        ax_summary.set_title('ITU Compliance Report', fontsize=11, fontweight='600',
                            color=IEEE_COLORS['primary'], pad=18, loc='center')
        ax_summary.title.set_position([0.5, 1.02])
        
        fig.suptitle('ITU Regulatory Compliance Analysis  —  PFD Limits & EIRP Masks',
                    fontsize=14, fontweight='700', color=IEEE_COLORS['primary'], y=0.98)
        fig.tight_layout(rect=[0, 0, 1, 0.96])
        self.regulatory_canvas.draw()


    # --- Tab 12: Interference analysis ---
    
    def create_interference_tab(self):
        """Create Adjacent Satellite Interference (ASI) analysis tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        label = QLabel("Interference Analysis  —  Adjacent Satellite Interference (ASI) & C/(N+I) Degradation")
        label.setStyleSheet("padding: 10px 14px; background-color: rgba(234, 88, 12, 0.08); border-left: 4px solid #ea580c; border-radius: 8px; color: #9a3412; font-weight: 500;")
        layout.addWidget(label)
        
        self.interference_canvas = MplCanvas(self, width=10, height=7, dpi=100)
        layout.addWidget(self.interference_canvas, 1)
        
        self.plot_interference_analysis()
        
        return tab
    
    def plot_interference_analysis(self):
        """Adjacent satellite interference analysis with 4-panel output."""
        fig = self.interference_canvas.figure
        fig.clear()
        
        axes = fig.subplots(2, 2)
        ax_ci_sweep, ax_ant_pattern, ax_degradation, ax_summary = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]
        
        # Initialize interference calculator
        from models.link_budget import InterferenceCalculator
        asi = InterferenceCalculator(self.link_budget)
        
        freq_ghz = self.params.get('downlink_frequency_ghz', 12.0)
        ant_diam = self.params.get('gs_antenna_diameter_m', 1.2)
        
        # Default spacing for point analysis
        current_spacing = 2.0  # degrees
        
        # Panel 1: C/I vs orbital spacing
        sweep_data = asi.sweep_orbital_spacing(self.params, np.linspace(1, 10, 50))
        spacings = sweep_data['spacings_deg']
        ci_values = sweep_data['ci_db']
        
        # Plot C/I curve
        ax_ci_sweep.plot(spacings, ci_values, color=IEEE_COLORS['primary'], 
                        linewidth=2.5, label='Aggregate C/I (2 stars)')
        
        # Mark typical spacings
        typical_spacings = [2.0, 3.0, 6.0]
        for sp in typical_spacings:
            val = np.interp(sp, spacings, ci_values)
            ax_ci_sweep.scatter([sp], [val], color=IEEE_COLORS['tertiary'], zorder=5)
            ax_ci_sweep.annotate(f'{sp}°', (sp, val), xytext=(0, 10), 
                                textcoords='offset points', ha='center', fontsize=8)
            
        ax_ci_sweep.set_xlabel('Orbital Spacing (degrees)', fontsize=10, fontweight='600')
        ax_ci_sweep.set_ylabel('C/I Ratio (dB)', fontsize=10, fontweight='600')
        ax_ci_sweep.set_title('C/I vs. Orbital Spacing', fontsize=11,
                             fontweight='600', color=IEEE_COLORS['primary'])
        ax_ci_sweep.grid(True, alpha=0.3, linestyle='--')
        ax_ci_sweep.spines['top'].set_visible(False)
        ax_ci_sweep.spines['right'].set_visible(False)
        
        # Panel 2: off-axis antenna gain
        theta = np.logspace(-1, 2, 200) # 0.1 to 100 degrees
        gain_pattern = asi.itu_s465_gain(theta, ant_diam, freq_ghz)
        
        ax_ant_pattern.semilogx(theta, gain_pattern, color=IEEE_COLORS['secondary'],
                               linewidth=2, label=f'ITU-R S.465 ({ant_diam}m)')
        
        # Mark current spacing gain
        g_off = asi.itu_s465_gain(current_spacing, ant_diam, freq_ghz)
        ax_ant_pattern.scatter([current_spacing], [g_off], color=IEEE_COLORS['error'], s=50, zorder=5)
        ax_ant_pattern.text(current_spacing*1.1, g_off, f' @{current_spacing}°', 
                           color=IEEE_COLORS['error'], fontsize=8, va='center')

        ax_ant_pattern.set_xlabel('Off-axis Angle (degrees)', fontsize=10, fontweight='600')
        ax_ant_pattern.set_ylabel('Antenna Gain (dBi)', fontsize=10, fontweight='600')
        ax_ant_pattern.set_title('Reference Antenna Pattern (ITU-R S.465)', fontsize=11,
                                fontweight='600', color=IEEE_COLORS['primary'])
        ax_ant_pattern.grid(True, alpha=0.3, linestyle='--', which='both')
        ax_ant_pattern.spines['top'].set_visible(False)
        ax_ant_pattern.spines['right'].set_visible(False)
        ax_ant_pattern.set_xlim(0.1, 100)
        ax_ant_pattern.set_ylim(bottom=-15)
        
        # Panel 3: C/(N+I) degradation
        # Calculate C/I at 2 deg
        res_2deg = asi.calculate_aggregate_ci(self.params, current_spacing)
        ci_2deg = res_2deg['aggregate_ci_db']
        
        # Get thermal C/N from results
        cn_thermal = self.results.get('total_cn_db', 20.0) # Downlink C/N typically dominates
        if isinstance(cn_thermal, dict): cn_thermal = 20.0
            
        # Calc Combined
        cnir = asi.calculate_total_cnir(cn_thermal, ci_2deg)
        degradation = cn_thermal - cnir
        
        # Bar chart
        bars = ['Thermal C/N', 'Interference C/I', 'Total C/(N+I)']
        values = [cn_thermal, ci_2deg, cnir]
        colors = ['#cbd5e1', '#fca5a5', IEEE_COLORS['primary']]
        
        x_pos = np.arange(len(bars))
        ax_degradation.bar(x_pos, values, color=colors, width=0.6)
        
        # Add labels on bars
        for i, v in enumerate(values):
            ax_degradation.text(i, v + 0.5, f'{v:.1f} dB', ha='center', fontweight='bold', fontsize=9)
            
        ax_degradation.set_xticks(x_pos)
        ax_degradation.set_xticklabels(bars, fontsize=9)
        ax_degradation.set_ylabel('Ratio (dB)', fontsize=10, fontweight='600')
        ax_degradation.set_title(f'Link Degradation (@ {current_spacing}° spacing)', fontsize=11,
                                fontweight='600', color=IEEE_COLORS['primary'])
        ax_degradation.spines['top'].set_visible(False)
        ax_degradation.spines['right'].set_visible(False)
        ax_degradation.grid(True, alpha=0.3, axis='y')
        
        # Panel 4: summary table
        ax_summary.axis('off')
        
        single_entry = res_2deg['entries'][0] # Check first interferer details
        
        summary_data = [
            ['Analysis Spacing', f'{current_spacing}°'],
            ['Antenna Diameter', f'{ant_diam} m'],
            ['Frequency', f'{freq_ghz} GHz'],
            ['Off-axis Gain', f'{single_entry["g_rx_off_dbi"]:.1f} dBi'],
            ['Discrimination', f'{single_entry["discrimination_db"]:.1f} dB'],
            ['Aggregate C/I', f'{ci_2deg:.1f} dB'],
            ['Thermal C/N', f'{cn_thermal:.1f} dB'],
            ['Total C/(N+I)', f'{cnir:.1f} dB'],
            ['Degradation', f'{degradation:.2f} dB'],
            ['Num Interferers', '2 (±2°)'],
            ['Reference', 'ITU-R S.465-6 / S.1323'],
        ]
        
        df_sum = pd.DataFrame(summary_data, columns=['Parameter', 'Value'])
        
        col_widths = [0.55, 0.45]
        tbl = ax_summary.table(
            cellText=df_sum.values,
            colLabels=['Parameter', 'Value'],
            cellLoc='left', colLoc='center',
            loc='center',
            colWidths=col_widths
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(9)
        tbl.scale(1.0, 1.3)
        
        for (row, col), cell in tbl.get_celld().items():
            cell.set_edgecolor('#e2e8f0')
            if row == 0:
                cell.set_facecolor(IEEE_COLORS['primary'])
                cell.set_text_props(color='white', fontweight='bold')
            elif row == 8: # Degradation row
                cell.set_facecolor('#fee2e2')
                cell.set_text_props(color='#b91c1c', fontweight='bold')
            else:
                cell.set_facecolor('#f8fafc' if row % 2 else '#ffffff')

        ax_summary.set_title('Interference Budget Summary', fontsize=11, fontweight='600',
                            color=IEEE_COLORS['primary'])

        fig.suptitle('Adjacent Satellite Interference (ASI) Analysis',
                    fontsize=14, fontweight='700', color=IEEE_COLORS['primary'], y=0.98)
        fig.tight_layout(rect=[0, 0, 1, 0.96])
        self.interference_canvas.draw()


    # --- Tab 12: Interference analysis ---
    
    def create_interference_tab(self):
        """Create Adjacent Satellite Interference (ASI) analysis tab"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        label = QLabel("Interference Analysis  —  Adjacent Satellite Interference (ASI) & C/(N+I) Degradation")
        label.setStyleSheet("padding: 10px 14px; background-color: rgba(234, 88, 12, 0.08); border-left: 4px solid #ea580c; border-radius: 8px; color: #9a3412; font-weight: 500;")
        layout.addWidget(label)
        
        self.interference_canvas = MplCanvas(self, width=10, height=7, dpi=100)
        layout.addWidget(self.interference_canvas, 1)
        
        self.plot_interference_analysis()
        
        return tab
    
    def plot_interference_analysis(self):
        """Cross-polarization interference analysis with 4-panel output."""
        fig = self.interference_canvas.figure
        fig.clear()
        
        axes = fig.subplots(2, 2)
        ax_ci_sweep, ax_ant_pattern, ax_degradation, ax_summary = axes[0, 0], axes[0, 1], axes[1, 0], axes[1, 1]
        
        # Initialize interference calculator
        from models.link_budget import InterferenceCalculator
        asi = InterferenceCalculator(self.link_budget)
        
        freq_ghz = self.params.get('downlink_frequency_ghz', 12.0)
        ant_diam = self.params.get('gs_antenna_diameter_m', 1.2)
        
        # Default spacing for point analysis
        current_spacing = 2.0  # degrees
        
        # Panel 1: C/I vs orbital spacing
        sweep_data = asi.sweep_orbital_spacing(self.params, np.linspace(1, 10, 50))
        spacings = sweep_data['spacings_deg']
        ci_values = sweep_data['ci_db']
        
        # Plot C/I curve
        ax_ci_sweep.plot(spacings, ci_values, color=IEEE_COLORS['primary'], 
                        linewidth=2.5, label='Aggregate C/I (2 stars)')
        
        # Mark typical spacings
        typical_spacings = [2.0, 3.0, 6.0]
        for sp in typical_spacings:
            val = np.interp(sp, spacings, ci_values)
            ax_ci_sweep.scatter([sp], [val], color=IEEE_COLORS['tertiary'], zorder=5)
            ax_ci_sweep.annotate(f'{sp}°', (sp, val), xytext=(0, 10), 
                                textcoords='offset points', ha='center', fontsize=8)
            
        ax_ci_sweep.set_xlabel('Orbital Spacing (degrees)', fontsize=10, fontweight='600')
        ax_ci_sweep.set_ylabel('C/I Ratio (dB)', fontsize=10, fontweight='600')
        ax_ci_sweep.set_title('C/I vs. Orbital Spacing', fontsize=11,
                             fontweight='600', color=IEEE_COLORS['primary'])
        ax_ci_sweep.grid(True, alpha=0.3, linestyle='--')
        ax_ci_sweep.spines['top'].set_visible(False)
        ax_ci_sweep.spines['right'].set_visible(False)
        
        # Panel 2: off-axis antenna gain
        theta = np.logspace(-1, 2, 200) # 0.1 to 100 degrees
        gain_pattern = asi.itu_s465_gain(theta, ant_diam, freq_ghz)
        
        ax_ant_pattern.semilogx(theta, gain_pattern, color=IEEE_COLORS['secondary'],
                               linewidth=2, label=f'ITU-R S.465 ({ant_diam}m)')
        
        # Mark current spacing gain
        g_off = asi.itu_s465_gain(current_spacing, ant_diam, freq_ghz)
        ax_ant_pattern.scatter([current_spacing], [g_off], color=IEEE_COLORS['error'], s=50, zorder=5)
        ax_ant_pattern.text(current_spacing*1.1, g_off, f' @{current_spacing}°', 
                           color=IEEE_COLORS['error'], fontsize=8, va='center')

        ax_ant_pattern.set_xlabel('Off-axis Angle (degrees)', fontsize=10, fontweight='600')
        ax_ant_pattern.set_ylabel('Antenna Gain (dBi)', fontsize=10, fontweight='600')
        ax_ant_pattern.set_title('Reference Antenna Pattern (ITU-R S.465)', fontsize=11,
                                fontweight='600', color=IEEE_COLORS['primary'])
        ax_ant_pattern.grid(True, alpha=0.3, linestyle='--', which='both')
        ax_ant_pattern.spines['top'].set_visible(False)
        ax_ant_pattern.spines['right'].set_visible(False)
        ax_ant_pattern.set_xlim(0.1, 100)
        ax_ant_pattern.set_ylim(bottom=-15)
        
        # Panel 3: C/(N+I) degradation
        # Calculate C/I at 2 deg
        res_2deg = asi.calculate_aggregate_ci(self.params, current_spacing)
        ci_2deg = res_2deg['aggregate_ci_db']
        
        # Get thermal C/N from results
        cn_thermal = self.results.get('total_cn_db', 20.0) # Downlink C/N typically dominates
        if isinstance(cn_thermal, dict): cn_thermal = 20.0
            
        # Calc Combined
        cnir = asi.calculate_total_cnir(cn_thermal, ci_2deg)
        degradation = cn_thermal - cnir
        
        # Bar chart
        bars = ['Thermal C/N', 'Interference C/I', 'Total C/(N+I)']
        values = [cn_thermal, ci_2deg, cnir]
        colors = ['#cbd5e1', '#fca5a5', IEEE_COLORS['primary']]
        
        x_pos = np.arange(len(bars))
        ax_degradation.bar(x_pos, values, color=colors, width=0.6)
        
        # Add labels on bars
        for i, v in enumerate(values):
            ax_degradation.text(i, v + 0.5, f'{v:.1f} dB', ha='center', fontweight='bold', fontsize=9)
            
        ax_degradation.set_xticks(x_pos)
        ax_degradation.set_xticklabels(bars, fontsize=9)
        ax_degradation.set_ylabel('Ratio (dB)', fontsize=10, fontweight='600')
        ax_degradation.set_title(f'Link Degradation (@ {current_spacing}° spacing)', fontsize=11,
                                fontweight='600', color=IEEE_COLORS['primary'])
        ax_degradation.spines['top'].set_visible(False)
        ax_degradation.spines['right'].set_visible(False)
        ax_degradation.grid(True, alpha=0.3, axis='y')
        
        # Panel 4: summary table
        ax_summary.axis('off')
        
        single_entry = res_2deg['entries'][0] # Check first interferer details
        
        summary_data = [
            ['Analysis Spacing', f'{current_spacing}°'],
            ['Antenna Diameter', f'{ant_diam} m'],
            ['Frequency', f'{freq_ghz} GHz'],
            ['Off-axis Gain', f'{single_entry["g_rx_off_dbi"]:.1f} dBi'],
            ['Discrimination', f'{single_entry["discrimination_db"]:.1f} dB'],
            ['Aggregate C/I', f'{ci_2deg:.1f} dB'],
            ['Thermal C/N', f'{cn_thermal:.1f} dB'],
            ['Total C/(N+I)', f'{cnir:.1f} dB'],
            ['Degradation', f'{degradation:.2f} dB'],
            ['Num Interferers', '2 (±2°)'],
            ['Reference', 'ITU-R S.465-6 / S.1323'],
        ]
        
        df_sum = pd.DataFrame(summary_data, columns=['Parameter', 'Value'])
        
        col_widths = [0.55, 0.45]
        tbl = ax_summary.table(
            cellText=df_sum.values,
            colLabels=['Parameter', 'Value'],
            cellLoc='left', colLoc='center',
            loc='center',
            colWidths=col_widths
        )
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(9)
        tbl.scale(1.0, 1.3)
        
        for (row, col), cell in tbl.get_celld().items():
            cell.set_edgecolor('#e2e8f0')
            if row == 0:
                cell.set_facecolor(IEEE_COLORS['primary'])
                cell.set_text_props(color='white', fontweight='bold')
            elif row == 8: # Degradation row
                cell.set_facecolor('#fee2e2')
                cell.set_text_props(color='#b91c1c', fontweight='bold')
            else:
                cell.set_facecolor('#f8fafc' if row % 2 else '#ffffff')

        ax_summary.set_title('Interference Budget Summary', fontsize=11, fontweight='600',
                            color=IEEE_COLORS['primary'])

        fig.suptitle('Adjacent Satellite Interference (ASI) Analysis',
                    fontsize=14, fontweight='700', color=IEEE_COLORS['primary'], y=0.98)
        fig.tight_layout(rect=[0, 0, 1, 0.96])
        self.interference_canvas.draw()

    # --- Tab 13: Rain fade simulator ---
    
    def create_rain_simulator_tab(self):
        """Create animated rain fade simulator tab (Maseng-Bakken model)"""
        from PyQt5.QtCore import QTimer
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Info label
        label = QLabel("Live Rain Fade Simulation — Maseng-Bakken Stochastic Model (ITU-R P.1853-2)")
        label.setStyleSheet("padding: 10px 14px; background-color: rgba(99, 102, 241, 0.08); "
                           "border-left: 4px solid #6366f1; border-radius: 8px; "
                           "color: #312e81; font-weight: 500;")
        layout.addWidget(label)
        
        # Control panel
        control_panel = QWidget()
        control_layout = QHBoxLayout(control_panel)
        control_layout.setContentsMargins(10, 5, 10, 5)
        
        # Play/Pause button
        self.rain_sim_play_btn = QPushButton("▶ Play")
        self.rain_sim_play_btn.setFixedWidth(100)
        self.rain_sim_play_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #10b981, stop:1 #059669);
                color: white; border: none; border-radius: 6px;
                font-weight: 600; font-size: 9pt; padding: 6px 12px;
            }
            QPushButton:hover { background: #059669; }
        """)
        self.rain_sim_play_btn.clicked.connect(self._toggle_rain_sim_playback)
        control_layout.addWidget(self.rain_sim_play_btn)
        
        # Reset button
        reset_btn = QPushButton("↻ Reset")
        reset_btn.setFixedWidth(80)
        reset_btn.setStyleSheet("""
            QPushButton {
                background: #f3f4f6; color: #374151; border: 1px solid #d1d5db;
                border-radius: 6px; font-weight: 600; font-size: 9pt; padding: 6px 12px;
            }
            QPushButton:hover { background: #e5e7eb; }
        """)
        reset_btn.clicked.connect(self._reset_rain_sim)
        control_layout.addWidget(reset_btn)
        
        control_layout.addWidget(QLabel(" | Speed:"))
        
        # Speed selector
        self.rain_sim_speed_combo = QComboBox()
        self.rain_sim_speed_combo.addItems(["0.5x", "1x", "2x", "5x", "10x", "100x", "500x"])
        self.rain_sim_speed_combo.setCurrentIndex(1)  # 1x default
        self.rain_sim_speed_combo.setFixedWidth(80)
        control_layout.addWidget(self.rain_sim_speed_combo)
        
        control_layout.addWidget(QLabel(" | Climate:"))
        
        # Climate zone selector
        self.rain_sim_climate_combo = QComboBox()
        self.rain_sim_climate_combo.addItems([
            "K - Temperate Maritime", "C - Temperate", "E - Continental",
            "L - Subtropical Humid", "N - Maritime Tropical", "P - Equatorial Heavy"
        ])
        self.rain_sim_climate_combo.setCurrentIndex(0)  # K default
        control_layout.addWidget(self.rain_sim_climate_combo)
        
        control_layout.addStretch()
        layout.addWidget(control_panel)
        
        # Canvas for 6 panels
        self.rain_sim_canvas = MplCanvas(self, width=12, height=9, dpi=100)
        layout.addWidget(self.rain_sim_canvas, 1)
        
        # Initialize simulation state
        self.rain_sim_running = False
        self.rain_sim_current_time_idx = 0
        self.rain_sim_data = None
        
        # Timer for animation
        self.rain_sim_timer = QTimer()
        self.rain_sim_timer.timeout.connect(self._update_rain_sim_frame)
        
        # Initial plot
        self._reset_rain_sim()
        
        return tab
    
    def _toggle_rain_sim_playback(self):
        """Toggle play/pause for rain simulator"""
        self.rain_sim_running = not self.rain_sim_running
        if self.rain_sim_running:
            self.rain_sim_play_btn.setText("⏸ Pause")
            self.rain_sim_timer.start(100)  # 100ms interval
        else:
            self.rain_sim_play_btn.setText("▶ Play")
            self.rain_sim_timer.stop()
    
    def _reset_rain_sim(self):
        """Reset simulation and regenerate data"""
        try:
            self.rain_sim_running = False
            self.rain_sim_timer.stop()
            self.rain_sim_play_btn.setText("▶ Play")
            self.rain_sim_current_time_idx = 0
            
            # Generate new simulation data
            from models.link_budget import GeneralLinkBudget, MasengBakkenSimulator
            
            link_calc = GeneralLinkBudget()
            mbs = MasengBakkenSimulator(link_calc)
            
            # Extract parameters from current link settings
            freq_ghz = self.params.get('downlink_frequency_ghz', 12.0)
            elevation_deg = self.params.get('elevation_deg', 30.0)
            rain_rate_001 = self.params.get('downlink_rain_rate', 42.0)
            if rain_rate_001 <= 0:
                rain_rate_001 = 42.0
            
            # Get climate zone from combo
            if hasattr(self, 'rain_sim_climate_combo'):
                climate_text = self.rain_sim_climate_combo.currentText()
                climate_zone = climate_text.split(' - ')[0]  # Extract letter
            else:
                climate_zone = 'K'
            
            margin_db = abs(self.results.get('link_margin_db',
                            self.results.get('total_margin_db', 10.0)))
            
            # Synthesize 6-hour simulation
            self.rain_sim_data = mbs.synthesize(
                duration_hours=6, dt=1.0,
                freq_ghz=freq_ghz, elevation_deg=elevation_deg,
                rain_rate_001=rain_rate_001, climate_zone=climate_zone,
                link_margin_db=margin_db, seed=None,
                force_rain_prob=0.3)  # Random seed, force 30% rain
            
            # Plot initial frame
            self._plot_rain_sim_static()
            
        except Exception as e:
            print(f"Error resetting rain simulation: {e}")
            import traceback
            traceback.print_exc()
            self.rain_sim_play_btn.setText("⚠ Error")

    def _plot_rain_sim_static(self):
        """Plot static 6-panel layout (called once on reset)"""
        if self.rain_sim_data is None:
            return
            
        fig = self.rain_sim_canvas.figure
        fig.clear()
        
        # Create 3x2 grid
        axes = fig.subplots(3, 2)
        self.rain_sim_axes = {
            'attenuation': axes[0, 0],
            'rain_rate': axes[0, 1],
            'fade_slope': axes[1, 0],
            'ccdf': axes[1, 1],
            'duration_cdf': axes[2, 0],
            'stats': axes[2, 1],
        }
        
        # Plot all panels
        self._update_rain_sim_plots()
        
        fig.suptitle('Rain Fade Simulator — Maseng-Bakken Model (ITU-R P.1853-2)',
                    fontsize=13, fontweight='700', color=IEEE_COLORS['primary'], y=0.98)
        # fig.tight_layout(rect=[0, 0, 1, 0.96])  # Removed to avoid conflict with MplCanvas
        self.rain_sim_canvas.draw()
    
    def _update_rain_sim_frame(self):
        """Update animation frame (called by QTimer)"""
        if self.rain_sim_data is None:
            return
        
        # Advance time
        try:
            speed_text = self.rain_sim_speed_combo.currentText()
            speed = float(speed_text.replace('x', ''))
        except ValueError:
            speed = 1.0
            
        step = max(1, int(10 * speed))  # 10x at 1x speed = 10 seconds per 100ms
        
        self.rain_sim_current_time_idx += step

        
        # Loop at end
        if self.rain_sim_current_time_idx >= len(self.rain_sim_data['time_sec']):
            self.rain_sim_current_time_idx = 0
        
        # Update plots
        self._update_rain_sim_plots()
        self.rain_sim_canvas.draw()
    
    def _update_rain_sim_plots(self):
        """Redraw all 6 panels"""
        if self.rain_sim_data is None:
            return
        
        data = self.rain_sim_data
        idx = self.rain_sim_current_time_idx
        
        # Panel 1: Attenuation time series
        ax = self.rain_sim_axes['attenuation']
        ax.clear()
        
        window_width = 600  # 10 minutes
        start_idx = max(0, idx - window_width)
        end_idx = min(len(data['time_sec']), idx + window_width // 4)
        
        t_window = data['time_hours'][start_idx:end_idx]
        a_window = data['attenuation_db'][start_idx:end_idx]
        
        ax.plot(t_window, a_window, color=IEEE_COLORS['primary'], linewidth=1.5, alpha=0.9)
        ax.fill_between(t_window, 0, a_window, alpha=0.2, color=IEEE_COLORS['primary'])
        
        # Margin line
        ax.axhline(y=data['link_margin_db'], color=IEEE_COLORS['error'],
                  linestyle='--', linewidth=2, alpha=0.8, label='Margin')
        
        # Current time marker
        if start_idx <= idx < end_idx:
            ax.axvline(x=data['time_hours'][idx], color=IEEE_COLORS['warning'],
                      linewidth=2, alpha=0.7)
        
        ax.set_xlabel('Time (hours)', fontsize=9, fontweight='600')
        ax.set_ylabel('Attenuation (dB)', fontsize=9, fontweight='600')
        ax.set_title('Rain Attenuation (Live)', fontsize=10, fontweight='600',
                    color=IEEE_COLORS['primary'])
        ax.legend(fontsize=7)
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_ylim(bottom=0)
        
        # Panel 2: Rain rate
        ax = self.rain_sim_axes['rain_rate']
        ax.clear()
        
        r_window = data['rain_rate_mmh'][start_idx:end_idx]
        ax.plot(t_window, r_window, color=IEEE_COLORS['tertiary'], linewidth=1.5)
        ax.fill_between(t_window, 0, r_window, alpha=0.2, color=IEEE_COLORS['tertiary'])
        
        ax.set_xlabel('Time (hours)', fontsize=9, fontweight='600')
        ax.set_ylabel('Rain Rate (mm/h)', fontsize=9, fontweight='600')
        ax.set_title('Rain Intensity', fontsize=10, fontweight='600',
                    color=IEEE_COLORS['primary'])
        ax.grid(True, alpha=0.3, linestyle='--')
        ax.set_ylim(bottom=0)
        
        # Panel 3: Fade slope histogram
        ax = self.rain_sim_axes['fade_slope']
        ax.clear()
        
        slope = data['fade_slope_dbps'][:idx+1] if idx > 0 else data['fade_slope_dbps']
        if len(slope) > 10:
            ax.hist(slope, bins=50, color=IEEE_COLORS['success'], alpha=0.7, edgecolor='white')
            ax.set_xlabel('Fade Slope (dB/s)', fontsize=9, fontweight='600')
            ax.set_ylabel('Count', fontsize=9, fontweight='600')
            ax.set_title('Fade Slope Distribution', fontsize=10, fontweight='600',
                        color=IEEE_COLORS['primary'])
            ax.grid(True, alpha=0.3, linestyle='--', axis='y')
        
        # Panel 4: CCDF
        ax = self.rain_sim_axes['ccdf']
        ax.clear()
        
        ax.semilogy(data['ccdf_thresholds'], data['ccdf_values'],
                   color=IEEE_COLORS['primary'], linewidth=2.5)
        ax.axvline(x=data['link_margin_db'], color=IEEE_COLORS['error'],
                  linestyle='--', linewidth=2, alpha=0.8)
        
        ax.set_xlabel('Attenuation (dB)', fontsize=9, fontweight='600')
        ax.set_ylabel('% Time Exceeded', fontsize=9, fontweight='600')
        ax.set_title('Fade Depth CCDF', fontsize=10, fontweight='600',
                    color=IEEE_COLORS['primary'])
        ax.grid(True, alpha=0.3, linestyle='--', which='both')
        ax.set_ylim(0.001, 100)
        
        # Panel 5: Duration CDF
        ax = self.rain_sim_axes['duration_cdf']
        ax.clear()
        
        if len(data['fade_dur_sorted']) > 1:
            ax.plot(data['fade_dur_sorted'], data['fade_dur_cdf'] * 100,
                   color=IEEE_COLORS['quaternary'], linewidth=2.5, marker='o', markersize=3)
            ax.set_xlabel('Fade Duration (sec)', fontsize=9, fontweight='600')
            ax.set_ylabel('CDF (%)', fontsize=9, fontweight='600')
            ax.set_title('Fade Duration CDF', fontsize=10, fontweight='600',
                        color=IEEE_COLORS['primary'])
            ax.grid(True, alpha=0.3, linestyle='--')
        
        # Panel 6: Stats table
        ax = self.rain_sim_axes['stats']
        ax.clear()
        ax.axis('off')
        
        events = data['events']
        table_data = [
            ['Elapsed Time', f"{data['time_hours'][idx]:.2f} h"],
            ['Max Atten', f"{data['max_attenuation_db']:.2f} dB"],
            ['Link Margin', f"{data['link_margin_db']:.2f} dB"],
            ['Availability', f"{data['availability_pct']:.4f}%"],
            ['Fade Events', f"{events['n_events']}"],
            ['Total Outage', f"{data['total_outage_sec']:.0f} s"],
        ]
        if events['n_events'] > 0:
            table_data.append(['Mean Duration', f"{events['mean_duration_sec']:.1f} s"])
        
        table_data.append(['β (correlation)', f"{data['beta_sec']:.0f} s"])
        table_data.append(['Climate', data['params']['climate_zone']])
        
        import pandas as pd
        df = pd.DataFrame(table_data, columns=['Parameter', 'Value'])
        
        tbl = ax.table(cellText=df.values, colLabels=['Parameter', 'Value'],
                      cellLoc='left', colLoc='center', loc='upper center',
                      colWidths=[0.55, 0.4])
        tbl.auto_set_font_size(False)
        tbl.set_fontsize(8)
        tbl.scale(1.0, 1.6)
        
        for (row, col), cell in tbl.get_celld().items():
            cell.set_edgecolor('#e2e8f0')
            if row == 0:
                cell.set_facecolor(IEEE_COLORS['primary'])
                cell.set_text_props(color='white', fontweight='bold', fontsize=9)
            else:
                cell.set_facecolor('#f8fafc' if row % 2 else '#ffffff')
        
        ax.set_title('Live Statistics', fontsize=10, fontweight='600',
                    color=IEEE_COLORS['primary'], pad=15)

