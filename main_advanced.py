import sys
import os
import warnings
import numpy as np

# Suppress Qt font enumeration warnings
os.environ['QT_LOGGING_RULES'] = '*.debug=false;qt.qpa.fonts=false'

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'pdfs'))

from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QTabWidget, QLabel, QComboBox, 
                             QDoubleSpinBox, QSpinBox, QPushButton, QGroupBox,
                             QGridLayout, QSplitter, QStatusBar, QTextEdit,
                             QSlider, QCheckBox, QMessageBox, QScrollArea,
                             QFrame, QDialog, QTextBrowser, QGraphicsOpacityEffect, QSplashScreen,
                             QToolBar, QAction, QFileDialog, QProgressBar, QToolButton,
                             QMenu, QToolTip, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QSize, pyqtSignal, QPointF
from PyQt5.QtGui import (QFont, QIcon, QPixmap, QPainter, QLinearGradient, QColor,
                         QKeySequence, QCursor, QPolygonF)
import json
import csv
import pandas as pd
import seaborn as sns
from datetime import datetime
import pyqtgraph as pg
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, FancyBboxPatch
from matplotlib.lines import Line2D

# Suppress matplotlib tight_layout warnings
warnings.filterwarnings('ignore', category=UserWarning, message='.*tight_layout.*')

from models.link_budget import (LinkBudget, MonteCarloSimulator, 
                                FadeDynamicsAnalyzer, RegulatoryComplianceChecker)
from models.orbit import SatelliteOrbit, create_satellite_from_type
from models.modulation import ModulationPerformance, ChannelCoding
# BeamPattern removed — multispot beam functionality has been removed
from models.transponder import SatelliteTransponder, TransponderStage
from models.link_diagram import (draw_waterfall_detailed as _draw_waterfall,
                                 draw_combined_summary as _draw_summary,
                                 draw_waterfall_figure, draw_link_diagram)
from models.constants import (FREQUENCY_BANDS, SATELLITE_TYPES, 
                              MODULATION_SCHEMES, CODING_SCHEMES, RAIN_ZONES,
                              MONTE_CARLO_PARAMS, FADE_DYNAMICS_PARAMS, 
                              ITU_PFD_LIMITS, EIRP_DENSITY_MASKS,
                              SATELLITE_BAND_ALLOCATIONS)
from models.base_station import BaseStation
from models.satellite import Satellite as SatelliteConfig

# ── GUI Module Imports ─────────────────────────────────────────────────
from gui.core.splash_screen import create_splash_screen

from gui.panels.header import (create_header as _mod_create_header,
                                toggle_metrics_visibility as _mod_toggle_metrics)
from gui.panels.dashboard import (create_dashboard_cards as _mod_create_dashboard,
                                   create_tracking_cards as _mod_create_tracking,
                                   update_dashboard_cards as _mod_update_dashboard,
                                   update_tracking_cards as _mod_update_tracking)

from gui.visualizations.waterfall import (create_waterfall_tab as _mod_waterfall_tab,
                                           update_waterfall_diagram as _mod_waterfall_update)
from gui.visualizations.complete_link import (create_complete_link_tab as _mod_cl_tab,
                                               update_complete_results_text as _mod_cl_update)
from gui.visualizations.ber_curves import (create_ber_tab as _mod_ber_tab,
                                            update_ber_plot as _mod_ber_update)
from gui.visualizations.constellation import (create_constellation_tab as _mod_const_tab,
                                               update_constellation as _mod_const_update)
from gui.visualizations.ground_track import (create_orbit_tab as _mod_orbit_tab,
                                              update_orbit_plot as _mod_orbit_update,
                                              update_orbit_anim_only)
from gui.visualizations.link_diagram_view import (create_link_diagram_tab as _mod_ld_tab,
                                                   update_link_diagram_complete as _mod_ld_update)
from gui.visualizations.transponder_view import (
    create_transponder_tab as _mod_tp_tab,
    update_transponder_block_diagram as _mod_tp_block,
    update_transponder_transfer_curve as _mod_tp_transfer,
    update_transponder_noise_cascade as _mod_tp_noise)

from gui.visualizations.view_3d import (create_3d_tab as _mod_3d_tab,
                                         update_3d_view as _mod_3d_update)

from gui.hub.hub_tab import create_hub_tab as _mod_hub_tab
from gui.hub.dialogs import (add_base_station_dialog as _mod_add_bs,
                              edit_base_station as _mod_edit_bs,
                              delete_base_station as _mod_del_bs,
                              add_satellite_dialog as _mod_add_sat,
                              edit_satellite as _mod_edit_sat,
                              delete_satellite as _mod_del_sat)

from gui.dialogs.info_dialog import show_info_dialog as _mod_info
from gui.dialogs.math_details import show_math_details_dialog as _mod_math
from gui.dialogs.history_dialog import (show_history_dialog as _mod_history,
                                         _export_history_csv as _mod_export_hist)

from gui.utils.export import (export_pdf as _mod_export_pdf,
                               export_csv as _mod_export_csv,
                               copy_results_to_clipboard as _mod_copy_clip)
from gui.utils.save_load import (save_parameters as _mod_save,
                                  load_parameters as _mod_load)
from gui.utils.presets import load_preset as _mod_preset
from gui.utils.app_paths import get_user_data_dir, get_resource_path

from gui.advanced_analysis.dialog import AdvancedAnalysisDialog


# Try to import 3D visualization (optional)
try:
    os.environ['QT_API'] = 'pyqt5'
    from gui.earth_3d import Earth3DVisualization
    HAS_3D = True
    print("3D visualization enabled!")
except Exception as e:
    HAS_3D = False
    print(f"3D visualization disabled (optional): {type(e).__name__}")


class SatelliteSimulatorGUIAdvanced(QMainWindow):
    """Advanced main application window with 3D visualization"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sat-Link")
        self.setGeometry(50, 50, 1900, 1000)
        
        self.calculation_history = []  # Store past calculations for comparison
        self.comparison_mode = False
        self.pinned_result = None  # For side-by-side comparison
        
        # Generate arrow icons for stylesheet
        self._generate_arrow_icons()
        
        # Apply modern stylesheet
        self.apply_stylesheet()
        
        # Initialize models
        self.link_budget = LinkBudget()
        self.transponder = SatelliteTransponder(preset='Ku-band_standard')
        self.satellite = None
        self.current_time = 0
        self.animation_running = False
        self.animation_speed = 10       # seconds of sim-time per tick (default 1x)
        self.animation_direction = 1    # +1 forward, -1 rewind

        
        # Hub: Base station and satellite configurations
        self.base_stations = [
            BaseStation(name="Athens GS", latitude=37.9755648, longitude=23.7348324),
        ]
        self.satellite_configs = [
            SatelliteConfig(name="Hotbird 13E", sat_type="GEO", longitude=13.0,
                           band="Ku-band", uplink_freq_ghz=14.25, downlink_freq_ghz=11.725, bandwidth_mhz=36.0),
        ]
        
        # 3D view dirty flag — set True when config changes to trigger full rebuild
        self._3d_needs_full_rebuild = True
        
        # Setup UI
        self.setup_ui()
        
        # Setup keyboard shortcuts
        self.setup_shortcuts()
        
        # Initialize plot theme colors
        self.plot_bg = '#ffffff'
        self.plot_text = '#212121'
        self.plot_grid = '#bdbdbd'
        
        # Setup timer for real-time updates
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_realtime)
        self.timer.start(100)  # Update every 100ms
        
        # Initial calculation
        self.calculate_complete_link()
        
        # Center window
        self.center_window()

    def center_window(self):
        """Center the window on the primary screen"""
        qr = self.frameGeometry()
        cp = QApplication.primaryScreen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())
    
    def _generate_arrow_icons(self):
        """Generate small arrow icon PNGs for use in stylesheets (Qt can't do CSS border-triangles)"""
        # Use a per-user writable location so installs under Program Files still work.
        icons_dir = os.path.join(get_user_data_dir(), 'assets')
        os.makedirs(icons_dir, exist_ok=True)
        self._icons_dir = icons_dir.replace('\\', '/')
        
        # Dropdown arrow (dark gray chevron)
        pix = QPixmap(12, 12)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#64748b'))
        p.drawPolygon(QPolygonF([QPointF(1,3), QPointF(11,3), QPointF(6,10)]))
        p.end()
        pix.save(os.path.join(icons_dir, 'arrow_down.png'))
        
        # Up arrow (green)
        pix = QPixmap(10, 10)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#10b981'))
        p.drawPolygon(QPolygonF([QPointF(5,1), QPointF(9,8), QPointF(1,8)]))
        p.end()
        pix.save(os.path.join(icons_dir, 'arrow_up_green.png'))
        
        # Down arrow (red)
        pix = QPixmap(10, 10)
        pix.fill(Qt.GlobalColor.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor('#ef4444'))
        p.drawPolygon(QPolygonF([QPointF(1,2), QPointF(9,2), QPointF(5,9)]))
        p.end()
        pix.save(os.path.join(icons_dir, 'arrow_down_red.png'))
    
    def apply_stylesheet(self):
        """Apply modern web-inspired light theme with glassmorphism and soft shadows"""
        icons = self._icons_dir
        stylesheet = """
        /* ══════════════ GLOBAL FOUNDATIONS ══════════════ */
        QMainWindow {
            background-color: #f0f4f8;
        }
        QWidget {
            background-color: #f0f4f8;
            color: #1e293b;
            font-family: 'Segoe UI', 'Inter', 'SF Pro Display', -apple-system, sans-serif;
            font-size: 10pt;
        }

        /* ══════════════ GLASSMORPHISM CARDS (GroupBox) ══════════════ */
        QGroupBox {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            margin-top: 18px;
            padding: 18px 14px 14px 14px;
            font-weight: 700;
            font-size: 9.5pt;
        }
        QGroupBox::title {
            color: #0f172a;
            subcontrol-origin: margin;
            left: 16px;
            padding: 2px 12px;
            font-weight: 700;
            font-size: 10pt;
            background-color: #ffffff;
            border-radius: 8px;
        }

        /* ══════════════ BUTTONS - PILL STYLE ══════════════ */
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #6366f1, stop:1 #4f46e5);
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 10px;
            font-weight: 600;
            font-size: 9.5pt;
            min-height: 18px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #818cf8, stop:1 #6366f1);
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4338ca, stop:1 #3730a3);
        }
        QPushButton[variant="success"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #10b981, stop:1 #059669);
        }
        QPushButton[variant="success"]:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #34d399, stop:1 #10b981);
        }
        QPushButton[variant="success"]:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #047857, stop:1 #065f46);
        }
        QPushButton[variant="warning"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #f97316, stop:1 #ea580c);
        }
        QPushButton[variant="warning"]:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #fb923c, stop:1 #f97316);
        }
        QPushButton[variant="warning"]:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #c2410c, stop:1 #9a3412);
        }
        QPushButton[variant="secondary"] {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #a78bfa, stop:1 #7c3aed);
        }
        QPushButton[variant="secondary"]:hover {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #c4b5fd, stop:1 #a78bfa);
        }
        QPushButton[variant="secondary"]:pressed {
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #6d28d9, stop:1 #5b21b6);
        }
        QPushButton[variant="outline"] {
            background-color: #ffffff;
            color: #4f46e5;
            border: 1.5px solid #c7d2fe;
        }
        QPushButton[variant="outline"]:hover {
            background-color: #eef2ff;
            border: 1.5px solid #6366f1;
            color: #4338ca;
        }
        QPushButton[variant="outline"]:pressed {
            background-color: #e0e7ff;
        }

        /* ══════════════ INPUTS - MODERN FLOATING STYLE ══════════════ */
        QComboBox, QDoubleSpinBox, QSpinBox {
            background-color: #ffffff;
            border: 1.5px solid #e2e8f0;
            border-radius: 10px;
            padding: 7px 10px;
            color: #1e293b;
            font-size: 9.5pt;
            selection-background-color: #c7d2fe;
        }
        QComboBox:hover, QDoubleSpinBox:hover, QSpinBox:hover {
            border: 1.5px solid #a5b4fc;
            background-color: #ffffff;
        }
        QComboBox:focus, QDoubleSpinBox:focus, QSpinBox:focus {
            border: 2px solid #6366f1;
            background-color: #ffffff;
        }
        QComboBox::drop-down {
            border: none;
            border-left: 1px solid #e2e8f0;
            width: 24px;
            border-top-right-radius: 10px;
            border-bottom-right-radius: 10px;
        }
        QComboBox::down-arrow {
            image: url(__ICONS_DIR__/arrow_down.png);
            width: 12px;
            height: 12px;
        }
        QComboBox QAbstractItemView {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 10px;
            padding: 4px;
            selection-background-color: #eef2ff;
            selection-color: #4338ca;
            outline: none;
        }

        /* ══════════════ SPIN BOX BUTTONS - GREEN + / RED − ══════════════ */
        QDoubleSpinBox::up-button, QSpinBox::up-button {
            subcontrol-origin: border;
            subcontrol-position: top right;
            width: 22px;
            border: none;
            border-left: 1px solid #e2e8f0;
            border-bottom: 1px solid #e2e8f0;
            border-top-right-radius: 9px;
            background-color: #ecfdf5;
        }
        QDoubleSpinBox::up-button:hover, QSpinBox::up-button:hover {
            background-color: #d1fae5;
        }
        QDoubleSpinBox::up-button:pressed, QSpinBox::up-button:pressed {
            background-color: #a7f3d0;
        }
        QDoubleSpinBox::up-arrow, QSpinBox::up-arrow {
            image: url(__ICONS_DIR__/arrow_up_green.png);
            width: 10px;
            height: 10px;
        }
        QDoubleSpinBox::down-button, QSpinBox::down-button {
            subcontrol-origin: border;
            subcontrol-position: bottom right;
            width: 22px;
            border: none;
            border-left: 1px solid #e2e8f0;
            border-top: 1px solid #e2e8f0;
            border-bottom-right-radius: 9px;
            background-color: #fef2f2;
        }
        QDoubleSpinBox::down-button:hover, QSpinBox::down-button:hover {
            background-color: #fee2e2;
        }
        QDoubleSpinBox::down-button:pressed, QSpinBox::down-button:pressed {
            background-color: #fecaca;
        }
        QDoubleSpinBox::down-arrow, QSpinBox::down-arrow {
            image: url(__ICONS_DIR__/arrow_down_red.png);
            width: 10px;
            height: 10px;
        }

        /* ══════════════ LABELS ══════════════ */
        QLabel {
            color: #475569;
            font-weight: 500;
            background: transparent;
        }

        /* ══════════════ TABS - PILL / SEGMENT STYLE ══════════════ */
        QTabWidget::pane {
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            background-color: #ffffff;
            padding: 8px;
            top: -1px;
        }
        QTabBar {
            background: #f0f4f8;
        }
        QTabBar::tab {
            background-color: #f1f5f9;
            color: #64748b;
            padding: 10px 22px;
            border-radius: 10px;
            border: none;
            margin: 2px 2px 4px 2px;
            font-weight: 600;
            font-size: 9pt;
        }
        QTabBar::tab:selected {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #6366f1, stop:1 #8b5cf6);
            color: white;
        }
        QTabBar::tab:hover:!selected {
            background-color: rgba(224, 231, 255, 0.8);
            color: #4338ca;
        }

        /* ══════════════ TEXT EDITOR - CODE BLOCK STYLE ══════════════ */
        QTextEdit {
            background-color: #f8fafc;
            color: #1e293b;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            font-family: 'JetBrains Mono', 'Cascadia Code', 'Fira Code', 'Consolas', monospace;
            font-size: 9pt;
            padding: 12px;
            selection-background-color: #c7d2fe;
        }

        /* ══════════════ STATUS BAR ══════════════ */
        QStatusBar {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #f8fafc, stop:1 #f1f5f9);
            color: #4f46e5;
            border-top: 1px solid #e2e8f0;
            padding: 6px 12px;
            font-weight: 600;
            font-size: 9pt;
        }

        /* ══════════════ SCROLL AREA ══════════════ */
        QScrollArea {
            border: none;
            background-color: transparent;
        }

        /* ══════════════ TOOLTIPS ══════════════ */
        QToolTip {
            background-color: #1e293b;
            color: #f1f5f9;
            border: none;
            padding: 10px 14px;
            border-radius: 10px;
            font-size: 9pt;
            font-weight: 500;
        }

        /* ══════════════ SCROLLBARS ══════════════ */
        QScrollBar:vertical {
            background-color: transparent;
            width: 8px;
            margin: 4px 2px;
        }
        QScrollBar::handle:vertical {
            background-color: rgba(148, 163, 184, 0.5);
            border-radius: 4px;
            min-height: 40px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: rgba(100, 116, 139, 0.7);
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0;
        }
        QScrollBar:horizontal {
            background-color: transparent;
            height: 8px;
            margin: 2px 4px;
        }
        QScrollBar::handle:horizontal {
            background-color: rgba(148, 163, 184, 0.5);
            border-radius: 4px;
            min-width: 40px;
        }
        QScrollBar::handle:horizontal:hover {
            background-color: rgba(100, 116, 139, 0.7);
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0;
        }

        /* ══════════════ PROGRESS BAR ══════════════ */
        QProgressBar {
            border: none;
            border-radius: 6px;
            background-color: #e2e8f0;
            text-align: center;
            color: #1e293b;
            font-weight: 600;
            min-height: 10px;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #6366f1, stop:1 #8b5cf6);
            border-radius: 6px;
        }

        /* ══════════════ CHECKBOXES - TOGGLE STYLE ══════════════ */
        QCheckBox {
            spacing: 8px;
            font-weight: 500;
            color: #475569;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 2px solid #cbd5e1;
            border-radius: 6px;
            background-color: #ffffff;
        }
        QCheckBox::indicator:hover {
            border-color: #6366f1;
        }
        QCheckBox::indicator:checked {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #6366f1, stop:1 #8b5cf6);
            border-color: #6366f1;
        }

        /* ══════════════ MENUS - FLOATING CARD ══════════════ */
        QMenu {
            background-color: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 6px;
        }
        QMenu::item {
            padding: 10px 24px;
            border-radius: 8px;
            font-weight: 500;
        }
        QMenu::item:selected {
            background-color: #eef2ff;
            color: #4338ca;
        }
        QMenu::separator {
            height: 1px;
            background: #e2e8f0;
            margin: 6px 12px;
        }

        /* ══════════════ SPLITTER ══════════════ */
        QSplitter::handle {
            background-color: #e2e8f0;
            width: 2px;
            height: 2px;
            border-radius: 1px;
        }
        QSplitter::handle:hover {
            background-color: #6366f1;
        }

        /* ══════════════ FRAMES ══════════════ */
        QFrame {
            background-color: #f0f4f8;
        }
        """
        stylesheet = stylesheet.replace('__ICONS_DIR__', icons)
        self.setStyleSheet(stylesheet)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts for power users"""
        from PyQt5.QtWidgets import QShortcut
        # Ctrl+Enter: Calculate
        QShortcut(QKeySequence("Ctrl+Return"), self, self.calculate_complete_link)

        # Ctrl+R: Reset parameters
        QShortcut(QKeySequence("Ctrl+R"), self, self.reset_parameters)
        # Ctrl+E: Export report
        QShortcut(QKeySequence("Ctrl+E"), self, self.export_report)
        # Ctrl+S: Save parameters
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_parameters)
        # Ctrl+O: Load parameters
        QShortcut(QKeySequence("Ctrl+O"), self, self.load_parameters)
        # Ctrl+P: Pin current result for comparison
        QShortcut(QKeySequence("Ctrl+P"), self, self.pin_current_result)
        # Ctrl+H: Show calculation history
        QShortcut(QKeySequence("Ctrl+H"), self, self.show_history_dialog)
    
    def setup_ui(self):
        """Setup the user interface"""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout with more breathing room
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 8, 10, 8)
        main_layout.setSpacing(8)
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Live dashboard cards row
        self.dashboard_widget = self.create_dashboard_cards()
        main_layout.addWidget(self.dashboard_widget)
        
        # Real-time satellite tracking cards row
        self.tracking_widget = self.create_tracking_cards()
        main_layout.addWidget(self.tracking_widget)
        
        # Create splitter for resizable panels
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Link Budget Configuration with component selectors
        self.left_panel = self.create_link_budget_panel()
        self.main_splitter.addWidget(self.left_panel)
        
        # Right panel: Visualizations (Tabs)
        right_panel = self.create_visualization_panel()
        self.main_splitter.addWidget(right_panel)
        
        self.main_splitter.setSizes([450, 1450])
        self._left_panel_last_width = 450
        main_layout.addWidget(self.main_splitter)
        
        # Status bar
        self.statusBar().showMessage("System Ready - All models loaded")
    
    def create_header(self):
        """Create header — delegated to gui.panels.header"""
        return _mod_create_header(self)

    def toggle_metrics_visibility(self):
        """Toggle dashboard/tracking visibility — delegated"""
        _mod_toggle_metrics(self)

    def create_dashboard_cards(self):
        """Create dashboard cards — delegated to gui.panels.dashboard"""
        return _mod_create_dashboard(self)

    def create_tracking_cards(self):
        """Create tracking cards — delegated to gui.panels.dashboard"""
        return _mod_create_tracking(self)

    def create_unified_control_panel(self):
        """Create unified control panel with BOTH uplink and downlink parameters"""
        # Create scroll area for the controls
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # ===== COMMON PARAMETERS =====
        common_group = self.create_common_params_group()
        layout.addWidget(common_group)
        
        # ===== UPLINK PARAMETERS =====
        self.uplink_group = self.create_uplink_params_group()
        layout.addWidget(self.uplink_group)
        
        # ===== DOWNLINK PARAMETERS =====
        self.downlink_group = self.create_downlink_params_group()
        layout.addWidget(self.downlink_group)
        
        # ===== MODULATION & CODING =====
        modcod_group = self.create_modcod_group()
        layout.addWidget(modcod_group)
        
        # ===== TRANSPONDER (BLACK BOX) =====
        transponder_group = self.create_transponder_params_group()
        layout.addWidget(transponder_group)
        
        # ===== LOSSES & ADVANCED =====
        losses_group = self.create_losses_group()
        layout.addWidget(losses_group)
        
        # ===== ATMOSPHERIC PARAMETERS =====
        atm_group = self.create_atmospheric_params_group()
        layout.addWidget(atm_group)
        
        # Control buttons with modern gradient styling
        button_layout = QHBoxLayout()
        
        calc_button = QPushButton("Calculate Complete Link")
        calc_button.clicked.connect(self.calculate_complete_link)
        calc_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #059669);
                font-size: 11pt;
                padding: 12px 20px;
                border-radius: 12px;
                font-weight: 700;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #34d399, stop:1 #10b981);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #047857, stop:1 #065f46);
            }
        """)
        button_layout.addWidget(calc_button)
        
        reset_button = QPushButton("↺ Reset")
        reset_button.clicked.connect(self.reset_parameters)
        reset_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f59e0b, stop:1 #d97706);
                padding: 12px 20px;
                border-radius: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #fbbf24, stop:1 #f59e0b);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #b45309, stop:1 #92400e);
            }
        """)
        button_layout.addWidget(reset_button)
        
        layout.addLayout(button_layout)

        layout.addStretch()
        
        scroll.setWidget(panel)
        return scroll
    
    def create_common_params_group(self):
        """Create common parameters group (satellite, path, ground station location)"""
        group = QGroupBox("Common Parameters")
        layout = QGridLayout()
        
        # Link Mode Selection
        layout.addWidget(QLabel("Link Mode:"), 0, 0)
        self.link_mode_combo = QComboBox()
        self.link_mode_combo.addItems(['Full Link', 'Uplink Only', 'Downlink Only'])
        self.link_mode_combo.setCurrentText('Full Link')
        self.link_mode_combo.setToolTip("Select link analysis mode:\n- Full Link: Complete end-to-end analysis\n- Uplink Only: Ground Station → Satellite\n- Downlink Only: Satellite → Ground Station")
        self.link_mode_combo.setStyleSheet("""
            QComboBox {
                font-weight: bold;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #eef2ff, stop:1 #e0e7ff);
                border: 2px solid #6366f1;
                color: #4338ca;
            }
        """)
        self.link_mode_combo.currentTextChanged.connect(self.on_link_mode_changed)
        layout.addWidget(self.link_mode_combo, 0, 1)
        
        # Satellite Type
        layout.addWidget(QLabel("Satellite Type:"), 1, 0)
        self.sat_type_combo = QComboBox()
        self.sat_type_combo.addItems(list(SATELLITE_TYPES.keys()))
        self.sat_type_combo.setCurrentText('GEO')
        self.sat_type_combo.currentTextChanged.connect(self.on_satellite_type_changed)
        layout.addWidget(self.sat_type_combo, 1, 1)
        
        # Altitude
        layout.addWidget(QLabel("Altitude (h):"), 2, 0)
        self.altitude_spin = QDoubleSpinBox()
        self.altitude_spin.setRange(160, 50000)
        self.altitude_spin.setValue(35786)
        self.altitude_spin.setSuffix(" km")
        self.altitude_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.altitude_spin, 2, 1)
        
        # Ground Station Location
        layout.addWidget(QLabel("GS Latitude (φ_gs):"), 3, 0)
        self.gs_lat_spin = QDoubleSpinBox()
        self.gs_lat_spin.setRange(-90, 90)
        self.gs_lat_spin.setDecimals(7)
        self.gs_lat_spin.setValue(37.9755648)
        self.gs_lat_spin.setSuffix("°")
        self.gs_lat_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.gs_lat_spin, 3, 1)
        
        layout.addWidget(QLabel("GS Longitude (λ_gs):"), 4, 0)
        self.gs_lon_spin = QDoubleSpinBox()
        self.gs_lon_spin.setRange(-180, 180)
        self.gs_lon_spin.setDecimals(7)
        self.gs_lon_spin.setValue(23.7348324)
        self.gs_lon_spin.setSuffix("°")
        self.gs_lon_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.gs_lon_spin, 4, 1)
        
        # Place Base Station button
        self.place_bs_btn = QPushButton("📍 Place BS")
        self.place_bs_btn.setToolTip("Place Base Station at custom coordinates")
        self.place_bs_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #059669);
                color: white; font-weight: bold; font-size: 10pt;
                border: none; border-radius: 8px; padding: 6px 12px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #34d399, stop:1 #10b981);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #047857, stop:1 #065f46);
            }
        """)
        self.place_bs_btn.clicked.connect(self._place_base_station)
        layout.addWidget(self.place_bs_btn, 4, 2)
        
        # Satellite Longitude (for GEO)
        layout.addWidget(QLabel("Sat Longitude (λ_sat):"), 5, 0)
        self.sat_lon_spin = QDoubleSpinBox()
        self.sat_lon_spin.setRange(-180, 180)
        self.sat_lon_spin.setValue(13.0)  # Default: Hotbird position
        self.sat_lon_spin.setSuffix("°")
        self.sat_lon_spin.setToolTip("Satellite orbital position (longitude)")
        self.sat_lon_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.sat_lon_spin, 5, 1)
        
        # Satellite Latitude (for LEO/MEO - always 0 for GEO)
        layout.addWidget(QLabel("Sat Latitude (φ_sat):"), 6, 0)
        self.sat_lat_spin = QDoubleSpinBox()
        self.sat_lat_spin.setRange(-90, 90)
        self.sat_lat_spin.setValue(0.0)  # Default: 0° for GEO (equatorial)
        self.sat_lat_spin.setSuffix("°")
        self.sat_lat_spin.setToolTip("Satellite latitude (0° for GEO, varies for LEO/MEO/HEO)")
        self.sat_lat_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.sat_lat_spin, 6, 1)
        
        # Bandwidth
        layout.addWidget(QLabel("Bandwidth (B):"), 7, 0)
        self.bandwidth_spin = QDoubleSpinBox()
        self.bandwidth_spin.setRange(0.1, 500)
        self.bandwidth_spin.setValue(36.0)
        self.bandwidth_spin.setSuffix(" MHz")
        self.bandwidth_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.bandwidth_spin, 7, 1)
        
        group.setLayout(layout)
        return group
    
    def create_uplink_params_group(self):
        """Create uplink parameters group (Ground Station TX → Satellite RX)"""
        group = QGroupBox("UPLINK (Ground → Satellite)")
        group.setStyleSheet("""
            QGroupBox {
                border: 1px solid rgba(99, 102, 241, 0.3);
                border-left: 4px solid #6366f1;
                border-radius: 14px;
            }
            QGroupBox::title { color: #4f46e5; }
        """)
        layout = QGridLayout()
        
        # Ground Station Transmitter
        layout.addWidget(QLabel("GS Power (P_tx):"), 0, 0)
        self.uplink_tx_power_spin = QDoubleSpinBox()
        self.uplink_tx_power_spin.setRange(-10, 30)
        self.uplink_tx_power_spin.setValue(10.0)
        self.uplink_tx_power_spin.setSuffix(" dBW")
        self.uplink_tx_power_spin.setToolTip("Ground station transmit power\nTypical: 1-20 dBW for VSAT, 10-30 dBW for broadcast uplinks")
        self.uplink_tx_power_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.uplink_tx_power_spin, 0, 1)
        
        layout.addWidget(QLabel("GS Antenna (D_tx):"), 1, 0)
        self.uplink_antenna_spin = QDoubleSpinBox()
        self.uplink_antenna_spin.setRange(0.5, 15)
        self.uplink_antenna_spin.setValue(2.4)
        self.uplink_antenna_spin.setSuffix(" m")
        self.uplink_antenna_spin.setToolTip("Ground station transmit antenna diameter\nTypical: 1.2-2.4m VSAT, 3.7-9.0m broadcast")
        self.uplink_antenna_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.uplink_antenna_spin, 1, 1)
        
        layout.addWidget(QLabel("Uplink Freq (f_up):"), 2, 0)
        self.uplink_freq_spin = QDoubleSpinBox()
        self.uplink_freq_spin.setRange(1, 50)
        self.uplink_freq_spin.setValue(14.0)
        self.uplink_freq_spin.setSuffix(" GHz")
        self.uplink_freq_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.uplink_freq_spin, 2, 1)
        
        layout.addWidget(QLabel("Rain Rate (R_up):"), 3, 0)
        self.uplink_rain_spin = QDoubleSpinBox()
        self.uplink_rain_spin.setRange(0, 150)
        self.uplink_rain_spin.setValue(0)
        self.uplink_rain_spin.setSuffix(" mm/h")
        self.uplink_rain_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.uplink_rain_spin, 3, 1)
        
        # Satellite Receiver
        layout.addWidget(QLabel("Sat Gain (G_rx):"), 4, 0)
        self.sat_rx_gain_spin = QDoubleSpinBox()
        self.sat_rx_gain_spin.setRange(0, 50)
        self.sat_rx_gain_spin.setValue(30.0)
        self.sat_rx_gain_spin.setSuffix(" dBi")
        self.sat_rx_gain_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.sat_rx_gain_spin, 4, 1)
        
        layout.addWidget(QLabel("Sat Noise Fig (NF):"), 5, 0)
        self.sat_nf_spin = QDoubleSpinBox()
        self.sat_nf_spin.setRange(0.5, 5)
        self.sat_nf_spin.setValue(2.0)
        self.sat_nf_spin.setSuffix(" dB")
        self.sat_nf_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.sat_nf_spin, 5, 1)
        
        group.setLayout(layout)
        return group
    
    def create_downlink_params_group(self):
        """Create downlink parameters group (Satellite TX → Ground Station RX)"""
        group = QGroupBox("DOWNLINK (Satellite → Ground)")
        group.setStyleSheet("""
            QGroupBox {
                border: 1px solid rgba(249, 115, 22, 0.3);
                border-left: 4px solid #f97316;
                border-radius: 14px;
            }
            QGroupBox::title { color: #ea580c; }
        """)
        layout = QGridLayout()
        
        # Satellite Transmitter
        layout.addWidget(QLabel("Sat Power (P_sat):"), 0, 0)
        self.tx_power_spin = QDoubleSpinBox()
        self.tx_power_spin.setRange(-10, 50)
        self.tx_power_spin.setValue(10.0)
        self.tx_power_spin.setSuffix(" dBW")
        self.tx_power_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.tx_power_spin, 0, 1)
        
        layout.addWidget(QLabel("Sat Gain (G_tx):"), 1, 0)
        self.tx_gain_spin = QDoubleSpinBox()
        self.tx_gain_spin.setRange(0, 60)
        self.tx_gain_spin.setValue(32.0)
        self.tx_gain_spin.setSuffix(" dBi")
        self.tx_gain_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.tx_gain_spin, 1, 1)
        
        layout.addWidget(QLabel("Downlink Freq (f_dn):"), 2, 0)
        self.frequency_spin = QDoubleSpinBox()
        self.frequency_spin.setRange(1, 75)
        self.frequency_spin.setValue(12.0)
        self.frequency_spin.setDecimals(3)
        self.frequency_spin.setSuffix(" GHz")
        self.frequency_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.frequency_spin, 2, 1)
        
        layout.addWidget(QLabel("Rain Rate (R_dn):"), 3, 0)
        self.rain_spin = QDoubleSpinBox()
        self.rain_spin.setRange(0, 150)
        self.rain_spin.setValue(0)
        self.rain_spin.setSuffix(" mm/h")
        self.rain_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.rain_spin, 3, 1)
        
        # Ground Station Receiver
        layout.addWidget(QLabel("GS Antenna (D_rx):"), 4, 0)
        self.gs_diameter_spin = QDoubleSpinBox()
        self.gs_diameter_spin.setRange(0.3, 30)
        self.gs_diameter_spin.setValue(1.2)
        self.gs_diameter_spin.setDecimals(2)
        self.gs_diameter_spin.setSuffix(" m")
        self.gs_diameter_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.gs_diameter_spin, 4, 1)
        
        layout.addWidget(QLabel("LNA Temp (T_lna):"), 5, 0)
        self.lna_temp_spin = QDoubleSpinBox()
        self.lna_temp_spin.setRange(10, 500)
        self.lna_temp_spin.setValue(50)
        self.lna_temp_spin.setSuffix(" K")
        self.lna_temp_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.lna_temp_spin, 5, 1)
        
        group.setLayout(layout)
        return group
    
    def create_modcod_group(self):
        """Create modulation & coding group"""
        group = QGroupBox("Modulation & Coding")
        group.setStyleSheet("""
            QGroupBox {
                background-color: #fef3c7;
                border: 2px solid #f59e0b;
                border-left: 5px solid #d97706;
                border-radius: 12px;
                padding: 10px 8px 8px 8px;
                margin-top: 14px;
                font-weight: 700;
                font-size: 10pt;
            }
            QGroupBox::title {
                color: #ffffff;
                font-weight: 800;
                font-size: 10pt;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #f59e0b, stop:1 #d97706);
                border-radius: 6px;
                padding: 3px 12px;
                subcontrol-origin: margin;
                left: 12px;
            }
            QLabel {
                color: #1e293b; font-weight: 600; font-size: 9pt;
                background: transparent; border: none;
            }
        """)
        layout = QGridLayout()
        
        layout.addWidget(QLabel("Modulation:"), 0, 0)
        self.modulation_combo = QComboBox()
        self.modulation_combo.addItems(list(MODULATION_SCHEMES.keys()))
        self.modulation_combo.setCurrentText('QPSK')
        self.modulation_combo.currentTextChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.modulation_combo, 0, 1)
        
        layout.addWidget(QLabel("Coding:"), 1, 0)
        self.coding_combo = QComboBox()
        self.coding_combo.addItems(list(CODING_SCHEMES.keys()))
        self.coding_combo.setCurrentText('LDPC (R=3/4)')
        self.coding_combo.currentTextChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.coding_combo, 1, 1)
        
        group.setLayout(layout)
        return group
    
    def create_transponder_params_group(self):
        """Create transponder (black box) parameters group"""
        group = QGroupBox("TRANSPONDER (Black Box)")
        group.setStyleSheet("""
            QGroupBox {
                border: 1px solid rgba(239, 68, 68, 0.3);
                border-left: 4px solid #ef4444;
                border-radius: 14px;
            }
            QGroupBox::title { color: #dc2626; }
        """)
        layout = QGridLayout()
        
        # Preset selection
        layout.addWidget(QLabel("Preset:"), 0, 0)
        self.transponder_preset_combo = QComboBox()
        self.transponder_preset_combo.addItems(['Custom'] + list(SatelliteTransponder.PRESETS.keys()))
        self.transponder_preset_combo.setCurrentText('Ku-band_standard')
        self.transponder_preset_combo.currentTextChanged.connect(self.on_transponder_preset_changed)
        layout.addWidget(self.transponder_preset_combo, 0, 1)
        
        # LNA parameters
        layout.addWidget(QLabel("LNA Gain (G_lna):"), 1, 0)
        self.lna_gain_spin = QDoubleSpinBox()
        self.lna_gain_spin.setRange(10, 50)
        self.lna_gain_spin.setValue(30.0)
        self.lna_gain_spin.setSuffix(" dB")
        self.lna_gain_spin.setToolTip("Low Noise Amplifier gain - first stage")
        self.lna_gain_spin.valueChanged.connect(self.on_transponder_param_changed)
        layout.addWidget(self.lna_gain_spin, 1, 1)
        
        layout.addWidget(QLabel("LNA NF:"), 2, 0)
        self.lna_nf_spin = QDoubleSpinBox()
        self.lna_nf_spin.setRange(0.3, 5.0)
        self.lna_nf_spin.setValue(1.2)
        self.lna_nf_spin.setDecimals(1)
        self.lna_nf_spin.setSuffix(" dB")
        self.lna_nf_spin.setToolTip("LNA Noise Figure")
        self.lna_nf_spin.valueChanged.connect(self.on_transponder_param_changed)
        layout.addWidget(self.lna_nf_spin, 2, 1)
        
        # Mixer parameters
        layout.addWidget(QLabel("Mixer Gain:"), 3, 0)
        self.mixer_gain_spin = QDoubleSpinBox()
        self.mixer_gain_spin.setRange(-15, 5)
        self.mixer_gain_spin.setValue(-6.0)
        self.mixer_gain_spin.setSuffix(" dB")
        self.mixer_gain_spin.setToolTip("Mixer gain (typically negative = loss)")
        self.mixer_gain_spin.valueChanged.connect(self.on_transponder_param_changed)
        layout.addWidget(self.mixer_gain_spin, 3, 1)
        
        layout.addWidget(QLabel("Mixer NF:"), 4, 0)
        self.mixer_nf_spin = QDoubleSpinBox()
        self.mixer_nf_spin.setRange(3, 15)
        self.mixer_nf_spin.setValue(8.0)
        self.mixer_nf_spin.setDecimals(1)
        self.mixer_nf_spin.setSuffix(" dB")
        self.mixer_nf_spin.setToolTip("Mixer Noise Figure")
        self.mixer_nf_spin.valueChanged.connect(self.on_transponder_param_changed)
        layout.addWidget(self.mixer_nf_spin, 4, 1)
        
        # IF Amplifier
        layout.addWidget(QLabel("IF Amp Gain:"), 5, 0)
        self.if_gain_spin = QDoubleSpinBox()
        self.if_gain_spin.setRange(10, 50)
        self.if_gain_spin.setValue(30.0)
        self.if_gain_spin.setSuffix(" dB")
        self.if_gain_spin.setToolTip("Intermediate Frequency Amplifier gain")
        self.if_gain_spin.valueChanged.connect(self.on_transponder_param_changed)
        layout.addWidget(self.if_gain_spin, 5, 1)
        
        # PA (Power Amplifier)
        layout.addWidget(QLabel("PA Gain (G_pa):"), 6, 0)
        self.pa_gain_spin = QDoubleSpinBox()
        self.pa_gain_spin.setRange(5, 40)
        self.pa_gain_spin.setValue(20.0)
        self.pa_gain_spin.setSuffix(" dB")
        self.pa_gain_spin.setToolTip("Power Amplifier gain")
        self.pa_gain_spin.valueChanged.connect(self.on_transponder_param_changed)
        layout.addWidget(self.pa_gain_spin, 6, 1)
        
        layout.addWidget(QLabel("P_sat:"), 7, 0)
        self.pa_psat_spin = QDoubleSpinBox()
        self.pa_psat_spin.setRange(-5, 25)
        self.pa_psat_spin.setValue(10.0)
        self.pa_psat_spin.setSuffix(" dBW")
        self.pa_psat_spin.setToolTip("PA Saturated output power")
        self.pa_psat_spin.valueChanged.connect(self.on_transponder_param_changed)
        layout.addWidget(self.pa_psat_spin, 7, 1)
        
        # Summary labels
        self.transponder_gain_label = QLabel("Total Gain: -- dB")
        self.transponder_gain_label.setStyleSheet("color: #ef4444; font-weight: bold;")
        layout.addWidget(self.transponder_gain_label, 8, 0, 1, 2)
        
        self.transponder_nf_label = QLabel("Cascade NF: -- dB")
        self.transponder_nf_label.setStyleSheet("color: #ef4444; font-weight: bold;")
        layout.addWidget(self.transponder_nf_label, 9, 0, 1, 2)
        
        self.transponder_eirp_label = QLabel("Sat EIRP: -- dBW")
        self.transponder_eirp_label.setStyleSheet("color: #ef4444; font-weight: bold;")
        layout.addWidget(self.transponder_eirp_label, 10, 0, 1, 2)
        
        group.setLayout(layout)
        return group
    
    def on_transponder_preset_changed(self, preset_name):
        """Handle transponder preset change"""
        if preset_name == 'Custom':
            return
        if preset_name in SatelliteTransponder.PRESETS:
            self.transponder = SatelliteTransponder(preset=preset_name)
            p = SatelliteTransponder.PRESETS[preset_name]
            # Update spinboxes to match preset
            self.lna_gain_spin.blockSignals(True)
            self.lna_nf_spin.blockSignals(True)
            self.mixer_gain_spin.blockSignals(True)
            self.mixer_nf_spin.blockSignals(True)
            self.if_gain_spin.blockSignals(True)
            self.pa_gain_spin.blockSignals(True)
            self.pa_psat_spin.blockSignals(True)
            
            self.lna_gain_spin.setValue(p['lna_gain_db'])
            self.lna_nf_spin.setValue(p['lna_nf_db'])
            self.mixer_gain_spin.setValue(p['mixer_gain_db'])
            self.mixer_nf_spin.setValue(p['mixer_nf_db'])
            self.if_gain_spin.setValue(p['if_gain_db'])
            self.pa_gain_spin.setValue(p['pa_gain_db'])
            self.pa_psat_spin.setValue(p['saturated_power_dbw'])
            
            self.lna_gain_spin.blockSignals(False)
            self.lna_nf_spin.blockSignals(False)
            self.mixer_gain_spin.blockSignals(False)
            self.mixer_nf_spin.blockSignals(False)
            self.if_gain_spin.blockSignals(False)
            self.pa_gain_spin.blockSignals(False)
            self.pa_psat_spin.blockSignals(False)
            
            self.update_transponder_labels()
            self.calculate_complete_link()
    
    def on_transponder_param_changed(self):
        """Handle individual transponder parameter change"""
        # Update transponder model from spinboxes
        self.transponder.set_stage_params('LNA', 
            gain_db=self.lna_gain_spin.value(), 
            noise_figure_db=self.lna_nf_spin.value())
        self.transponder.set_stage_params('Mixer', 
            gain_db=self.mixer_gain_spin.value(),
            noise_figure_db=self.mixer_nf_spin.value())
        self.transponder.set_stage_params('IF_Amp', 
            gain_db=self.if_gain_spin.value())
        self.transponder.set_stage_params('PA', 
            gain_db=self.pa_gain_spin.value())
        self.transponder.saturated_power_dbw = self.pa_psat_spin.value()
        
        # Set preset combo to 'Custom' since user changed params
        self.transponder_preset_combo.blockSignals(True)
        self.transponder_preset_combo.setCurrentText('Custom')
        self.transponder_preset_combo.blockSignals(False)
        
        self.update_transponder_labels()
        self.calculate_complete_link()
    
    def update_transponder_labels(self):
        """Update transponder summary labels"""
        total_gain = self.transponder.calculate_total_gain()
        cascade_nf = self.transponder.calculate_cascade_noise_figure()
        sat_eirp = self.transponder.calculate_satellite_eirp()
        
        self.transponder_gain_label.setText(f"Total Gain: {total_gain:.1f} dB")
        self.transponder_nf_label.setText(f"Cascade NF: {cascade_nf:.2f} dB")
        self.transponder_eirp_label.setText(f"Sat EIRP: {sat_eirp:.1f} dBW")
    
    def create_losses_group(self):
        """Create losses and advanced parameters group"""
        group = QGroupBox("Losses & Advanced")
        group.setStyleSheet("""
            QGroupBox {
                border: 1px solid rgba(139, 92, 246, 0.3);
                border-left: 4px solid #8b5cf6;
                border-radius: 14px;
            }
            QGroupBox::title { color: #7c3aed; }
        """)
        layout = QGridLayout()
        
        # Feed Loss (TX/RX)
        layout.addWidget(QLabel("Feed Loss (L_f):"), 0, 0)
        self.feed_loss_spin = QDoubleSpinBox()
        self.feed_loss_spin.setRange(0, 5)
        self.feed_loss_spin.setValue(0.5)
        self.feed_loss_spin.setSingleStep(0.1)
        self.feed_loss_spin.setSuffix(" dB")
        self.feed_loss_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.feed_loss_spin, 0, 1)
        
        # TX Pointing Loss (Θ_T) — uplink: affects GS EIRP
        layout.addWidget(QLabel("TX Pointing Loss (Θ_T):"), 1, 0)
        self.pointing_loss_tx_spin = QDoubleSpinBox()
        self.pointing_loss_tx_spin.setRange(0, 3)
        self.pointing_loss_tx_spin.setValue(0.3)
        self.pointing_loss_tx_spin.setSingleStep(0.1)
        self.pointing_loss_tx_spin.setSuffix(" dB")
        self.pointing_loss_tx_spin.setToolTip("Transmit antenna pointing error loss (Θ_T)\nApplied to uplink GS EIRP\nSource: ITU-R S.465-6")
        self.pointing_loss_tx_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.pointing_loss_tx_spin, 1, 1)
        
        # RX Pointing Loss (Θ_R) — downlink: affects GS G/T
        layout.addWidget(QLabel("RX Pointing Loss (Θ_R):"), 2, 0)
        self.pointing_loss_rx_spin = QDoubleSpinBox()
        self.pointing_loss_rx_spin.setRange(0, 3)
        self.pointing_loss_rx_spin.setValue(0.2)
        self.pointing_loss_rx_spin.setSingleStep(0.1)
        self.pointing_loss_rx_spin.setSuffix(" dB")
        self.pointing_loss_rx_spin.setToolTip("Receive antenna pointing error loss (Θ_R)\nApplied to downlink GS G/T\nSource: ITU-R S.465-6")
        self.pointing_loss_rx_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.pointing_loss_rx_spin, 2, 1)
        
        # Polarization Loss
        layout.addWidget(QLabel("Pol. Loss (L_pol):"), 3, 0)
        self.pol_loss_spin = QDoubleSpinBox()
        self.pol_loss_spin.setRange(0, 3)
        self.pol_loss_spin.setValue(0.2)
        self.pol_loss_spin.setSingleStep(0.1)
        self.pol_loss_spin.setSuffix(" dB")
        self.pol_loss_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.pol_loss_spin, 3, 1)
        
        # HPA Type Selector
        layout.addWidget(QLabel("HPA Type:"), 4, 0)
        self.hpa_type_combo = QComboBox()
        self.hpa_type_combo.addItems(['TWTA', 'SSPA', 'Linearized'])
        self.hpa_type_combo.setCurrentText('TWTA')
        self.hpa_type_combo.setToolTip(
            "TWTA: Traveling Wave Tube Amplifier (Saleh model)\n"
            "SSPA: Solid State Power Amplifier (Rapp model)\n"
            "Linearized: Pre-distorted TWTA (near-linear)")
        self.hpa_type_combo.currentTextChanged.connect(self._on_ibo_or_hpa_changed)
        layout.addWidget(self.hpa_type_combo, 4, 1)
        
        # Input Backoff (IBO)
        layout.addWidget(QLabel("Input Backoff (IBO):"), 5, 0)
        self.ibo_spin = QDoubleSpinBox()
        self.ibo_spin.setRange(0, 15)
        self.ibo_spin.setValue(1.0)
        self.ibo_spin.setSingleStep(0.5)
        self.ibo_spin.setSuffix(" dB")
        self.ibo_spin.setToolTip("Input Back-Off — sets transponder operating point")
        self.ibo_spin.valueChanged.connect(self._on_ibo_or_hpa_changed)
        layout.addWidget(self.ibo_spin, 5, 1)
        
        # Output Backoff (OBO) — auto-calculated from IBO via HPA model
        layout.addWidget(QLabel("Output Backoff (OBO):"), 6, 0)
        self.obo_spin = QDoubleSpinBox()
        self.obo_spin.setRange(0, 20)
        self.obo_spin.setValue(2.5)
        self.obo_spin.setSingleStep(0.5)
        self.obo_spin.setSuffix(" dB")
        self.obo_spin.setToolTip("Output Back-Off — auto-calculated from IBO via HPA model\n"
                                 "(Saleh model for TWTA, Rapp model for SSPA)")
        self.obo_spin.setReadOnly(True)
        self.obo_spin.setStyleSheet("QDoubleSpinBox { background-color: rgba(100,100,100,0.1); }")
        layout.addWidget(self.obo_spin, 6, 1)
        
        # AM/PM Phase distortion (read-only indicator)
        layout.addWidget(QLabel("AM/PM Phase:"), 7, 0)
        self.ampm_label = QLabel("0.0°")
        self.ampm_label.setToolTip("Phase distortion from HPA nonlinearity (Saleh AM/PM model)")
        self.ampm_label.setStyleSheet("QLabel { color: #7c3aed; font-weight: bold; }")
        layout.addWidget(self.ampm_label, 7, 1)
        
        # Antenna Efficiency
        layout.addWidget(QLabel("Antenna Eff. (η):"), 8, 0)
        self.antenna_eff_spin = QDoubleSpinBox()
        self.antenna_eff_spin.setRange(0.3, 0.9)
        self.antenna_eff_spin.setValue(0.6)
        self.antenna_eff_spin.setSingleStep(0.05)
        self.antenna_eff_spin.setDecimals(2)
        self.antenna_eff_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.antenna_eff_spin, 8, 1)
        
        # C/IM (Intermodulation) — auto-calculated from IBO
        layout.addWidget(QLabel("C/IM (auto):"), 9, 0)
        self.cim_spin = QDoubleSpinBox()
        self.cim_spin.setRange(5, 60)
        self.cim_spin.setValue(30)
        self.cim_spin.setSuffix(" dB")
        self.cim_spin.setToolTip("Carrier-to-Intermodulation ratio\n"
                                 "Auto-calculated from IBO and HPA type\n"
                                 "C/IM ≈ 2·IBO + K (K depends on HPA type)")
        self.cim_spin.setReadOnly(True)
        self.cim_spin.setStyleSheet("QDoubleSpinBox { background-color: rgba(100,100,100,0.1); }")
        layout.addWidget(self.cim_spin, 8, 1)
        
        group.setLayout(layout)
        return group
    
    def _on_ibo_or_hpa_changed(self):
        """When IBO or HPA type changes, auto-calculate OBO and C/IM via HPA model."""
        ibo = self.ibo_spin.value()
        hpa_type = self.hpa_type_combo.currentText()
        
        # Update transponder model
        self.transponder.hpa_type = hpa_type
        self.transponder.input_backoff_db = ibo
        
        # Calculate OBO from IBO via HPA nonlinear model
        obo = self.transponder.calculate_obo_from_ibo(ibo)
        self.obo_spin.blockSignals(True)
        self.obo_spin.setValue(round(obo, 2))
        self.obo_spin.blockSignals(False)
        self.transponder.output_backoff_db = obo
        
        # Calculate C/IM from IBO
        num_carriers = 1  # Default single carrier
        cim = self.transponder.calculate_cim_from_ibo(ibo, num_carriers)
        self.cim_spin.blockSignals(True)
        self.cim_spin.setValue(round(cim, 1))
        self.cim_spin.blockSignals(False)
        
        # Calculate AM/PM phase distortion
        am_pm = self.transponder.calculate_am_pm(ibo)
        self.ampm_label.setText(f"{am_pm:.1f}°")
        
        # Trigger full link recalculation
        self.calculate_complete_link()
    
    def create_atmospheric_params_group(self):
        """Create atmospheric parameters group for ITU-R calculations"""
        group = QGroupBox("Atmospheric Parameters (ITU-R)")
        group.setStyleSheet("""
            QGroupBox {
                border: 1px solid rgba(6, 182, 212, 0.3);
                border-left: 4px solid #06b6d4;
                border-radius: 14px;
            }
            QGroupBox::title { color: #0891b2; }
        """)
        layout = QGridLayout()
        
        # Ground Station Height (km) - affects rain path length
        layout.addWidget(QLabel("GS Height (h_s):"), 0, 0)
        self.gs_height_spin = QDoubleSpinBox()
        self.gs_height_spin.setRange(0, 5)
        self.gs_height_spin.setValue(0.0)
        self.gs_height_spin.setDecimals(2)
        self.gs_height_spin.setSingleStep(0.1)
        self.gs_height_spin.setSuffix(" km")
        self.gs_height_spin.setToolTip("Ground station height above sea level (ITU-R P.618)")
        self.gs_height_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.gs_height_spin, 0, 1)
        
        # Water Vapor Density (g/m³) - affects gaseous attenuation
        layout.addWidget(QLabel("Water Vapor (ρ):"), 1, 0)
        self.water_vapor_spin = QDoubleSpinBox()
        self.water_vapor_spin.setRange(0, 30)
        self.water_vapor_spin.setValue(7.5)
        self.water_vapor_spin.setDecimals(1)
        self.water_vapor_spin.setSingleStep(0.5)
        self.water_vapor_spin.setSuffix(" g/m³")
        self.water_vapor_spin.setToolTip("Surface water vapor density (ITU-R P.676)\n0-5: Dry/Desert, 5-10: Temperate, 10-20: Tropical")
        self.water_vapor_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.water_vapor_spin, 1, 1)
        
        # Cloud Liquid Water Content (kg/m²) - affects cloud attenuation
        layout.addWidget(QLabel("Cloud LWC (L):"), 2, 0)
        self.cloud_lwc_spin = QDoubleSpinBox()
        self.cloud_lwc_spin.setRange(0, 3)
        self.cloud_lwc_spin.setValue(0.5)
        self.cloud_lwc_spin.setDecimals(2)
        self.cloud_lwc_spin.setSingleStep(0.1)
        self.cloud_lwc_spin.setSuffix(" kg/m²")
        self.cloud_lwc_spin.setToolTip("Columnar liquid water content (ITU-R P.840)\n0: Clear, 0.1-0.5: Light clouds, 0.5-2: Heavy clouds")
        self.cloud_lwc_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.cloud_lwc_spin, 2, 1)
        
        # Rain Height (km) - typically 3-5 km, varies with latitude
        layout.addWidget(QLabel("Rain Height (h_R):"), 3, 0)
        self.rain_height_spin = QDoubleSpinBox()
        self.rain_height_spin.setRange(1, 7)
        self.rain_height_spin.setValue(3.0)
        self.rain_height_spin.setDecimals(1)
        self.rain_height_spin.setSingleStep(0.5)
        self.rain_height_spin.setSuffix(" km")
        self.rain_height_spin.setToolTip("Rain height above sea level (ITU-R P.839)\nTropical: 5km, Temperate: 3km, Polar: 2km")
        self.rain_height_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.rain_height_spin, 3, 1)
        
        # Polarization Tilt Angle (degrees) - for rain attenuation
        layout.addWidget(QLabel("Pol. Tilt (τ):"), 4, 0)
        self.pol_tilt_spin = QDoubleSpinBox()
        self.pol_tilt_spin.setRange(0, 90)
        self.pol_tilt_spin.setValue(45)
        self.pol_tilt_spin.setDecimals(0)
        self.pol_tilt_spin.setSingleStep(5)
        self.pol_tilt_spin.setSuffix("°")
        self.pol_tilt_spin.setToolTip("Polarization tilt angle (ITU-R P.838)\n0°: Horizontal, 45°: Circular, 90°: Vertical")
        self.pol_tilt_spin.valueChanged.connect(self.calculate_complete_link)
        layout.addWidget(self.pol_tilt_spin, 4, 1)
        
        group.setLayout(layout)
        return group
    
    # ==================== NEW: LINK BUDGET PANEL & HUB ====================
    
    def create_link_budget_panel(self):
        """Create the new link budget panel with component selectors and general parameters"""
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # First, create all hidden param widgets for backward compatibility
        self._create_hidden_param_widgets()
        
        # ===== COMPONENT SELECTORS =====
        selector_group = QGroupBox("Link Configuration")
        selector_group.setStyleSheet("""
            QGroupBox {
                background-color: #eef2ff;
                border: 2px solid #6366f1;
                border-left: 5px solid #4f46e5;
                border-radius: 12px;
                padding: 10px 8px 8px 8px;
                margin-top: 14px;
                font-weight: 700;
                font-size: 10pt;
            }
            QGroupBox::title {
                color: #ffffff;
                font-weight: 800;
                font-size: 10pt;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #6366f1, stop:1 #4f46e5);
                border-radius: 6px;
                padding: 3px 12px;
                subcontrol-origin: margin;
                left: 12px;
            }
            QLabel {
                color: #1e293b;
                font-weight: 600;
                font-size: 9pt;
                background: transparent;
                border: none;
            }
            QComboBox {
                background-color: #ffffff;
                border: 1.5px solid #c7d2fe;
                border-radius: 6px;
                padding: 4px 8px;
                font-size: 9pt;
                min-height: 26px;
                color: #1e293b;
            }
            QComboBox:focus {
                border: 2px solid #6366f1;
            }
        """)
        selector_layout = QGridLayout()
        selector_layout.setSpacing(6)
        selector_layout.setContentsMargins(8, 8, 8, 8)
        
        # Link Mode
        lm_label = QLabel("Link Mode:")
        lm_label.setStyleSheet("color: #1e293b; font-weight: 700; font-size: 9pt; background: transparent; border: none;")
        selector_layout.addWidget(lm_label, 0, 0)
        self.link_mode_combo = QComboBox()
        self.link_mode_combo.addItems(['Full Link', 'Uplink Only', 'Downlink Only'])
        self.link_mode_combo.setCurrentText('Full Link')
        self.link_mode_combo.setStyleSheet("""
            QComboBox {
                font-weight: bold;
                font-size: 9.5pt;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #eef2ff, stop:1 #e0e7ff);
                border: 2px solid #6366f1;
                border-radius: 6px;
                padding: 4px 8px;
                min-height: 28px;
                color: #4338ca;
            }
        """)
        self.link_mode_combo.currentTextChanged.connect(self.on_link_mode_changed)
        selector_layout.addWidget(self.link_mode_combo, 0, 1, 1, 2)
        
        # --- Add button style (compact) ---
        add_btn_style = """
            QPushButton {
                background: transparent;
                color: #10b981; font-weight: bold; font-size: 11pt;
                border: 1px solid #10b981; border-radius: 4px;
                min-width: 22px; min-height: 22px;
                max-width: 22px; max-height: 22px;
                padding: 0px;
            }
            QPushButton:hover {
                background: #10b981; color: white;
            }
        """
        
        # 1st Base Station (Uplink GS)
        bs1_label = QLabel("BS1 (Uplink):")
        bs1_label.setStyleSheet("color: #4338ca; font-weight: 700; font-size: 9pt; background: transparent; border: none;")
        selector_layout.addWidget(bs1_label, 1, 0)
        self.bs1_combo = QComboBox()
        self.bs1_combo.setEditable(True)
        self.bs1_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.bs1_combo.setToolTip("Select uplink ground station (type to search)")
        self.bs1_combo.currentIndexChanged.connect(self._on_bs1_changed)
        selector_layout.addWidget(self.bs1_combo, 1, 1)
        bs1_add_btn = QPushButton("+")
        bs1_add_btn.setStyleSheet(add_btn_style)
        bs1_add_btn.setToolTip("Add new Base Station")
        bs1_add_btn.clicked.connect(self._add_base_station_dialog)
        selector_layout.addWidget(bs1_add_btn, 1, 2)
        
        # Satellite
        sat_label = QLabel("Satellite:")
        sat_label.setStyleSheet("color: #c2410c; font-weight: 700; font-size: 9pt; background: transparent; border: none;")
        selector_layout.addWidget(sat_label, 2, 0)
        self.sat_combo = QComboBox()
        self.sat_combo.setEditable(True)
        self.sat_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.sat_combo.setToolTip("Select satellite (type to search)")
        self.sat_combo.currentIndexChanged.connect(self._on_sat_changed)
        selector_layout.addWidget(self.sat_combo, 2, 1)
        sat_add_btn = QPushButton("+")
        sat_add_btn.setStyleSheet(add_btn_style)
        sat_add_btn.setToolTip("Add new Satellite")
        sat_add_btn.clicked.connect(self._add_satellite_dialog)
        selector_layout.addWidget(sat_add_btn, 2, 2)
        
        # 2nd Base Station (Downlink GS)
        bs2_label = QLabel("BS2 (Downlink):")
        bs2_label.setStyleSheet("color: #6d28d9; font-weight: 700; font-size: 9pt; background: transparent; border: none;")
        selector_layout.addWidget(bs2_label, 3, 0)
        self.bs2_combo = QComboBox()
        self.bs2_combo.setEditable(True)
        self.bs2_combo.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.bs2_combo.setToolTip("Select downlink ground station (type to search)")
        self.bs2_combo.currentIndexChanged.connect(self._on_bs2_changed)
        selector_layout.addWidget(self.bs2_combo, 3, 1)
        bs2_add_btn = QPushButton("+")
        bs2_add_btn.setStyleSheet(add_btn_style)
        bs2_add_btn.setToolTip("Add new Base Station")
        bs2_add_btn.clicked.connect(self._add_base_station_dialog)
        selector_layout.addWidget(bs2_add_btn, 3, 2)
        
        selector_group.setLayout(selector_layout)
        layout.addWidget(selector_group)
        
        # ===== GENERAL LINK PARAMETERS =====
        general_group = QGroupBox("General Link Parameters")
        general_group.setStyleSheet("""
            QGroupBox {
                background-color: #ecfdf5;
                border: 2px solid #10b981;
                border-left: 5px solid #059669;
                border-radius: 12px;
                padding: 10px 8px 8px 8px;
                margin-top: 14px;
                font-weight: 700;
                font-size: 10pt;
            }
            QGroupBox::title {
                color: #ffffff;
                font-weight: 800;
                font-size: 10pt;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #10b981, stop:1 #059669);
                border-radius: 6px;
                padding: 3px 12px;
                subcontrol-origin: margin;
                left: 12px;
            }
            QLabel {
                color: #1e293b; font-weight: 600; font-size: 9pt;
                background: transparent; border: none;
            }
        """)
        gen_layout = QGridLayout()
        
        # Uplink Frequency
        gen_layout.addWidget(QLabel("Uplink Freq (f_up):"), 0, 0)
        self.uplink_freq_spin = QDoubleSpinBox()
        self.uplink_freq_spin.setRange(1, 50)
        self.uplink_freq_spin.setValue(14.0)
        self.uplink_freq_spin.setSuffix(" GHz")
        self.uplink_freq_spin.valueChanged.connect(self.calculate_complete_link)
        gen_layout.addWidget(self.uplink_freq_spin, 0, 1)
        
        # Downlink Frequency
        gen_layout.addWidget(QLabel("Downlink Freq (f_dn):"), 1, 0)
        self.frequency_spin = QDoubleSpinBox()
        self.frequency_spin.setRange(1, 75)
        self.frequency_spin.setValue(12.0)
        self.frequency_spin.setDecimals(3)
        self.frequency_spin.setSuffix(" GHz")
        self.frequency_spin.valueChanged.connect(self.calculate_complete_link)
        gen_layout.addWidget(self.frequency_spin, 1, 1)
        
        # Bandwidth
        gen_layout.addWidget(QLabel("Bandwidth (B):"), 2, 0)
        self.bandwidth_spin = QDoubleSpinBox()
        self.bandwidth_spin.setRange(0.1, 500)
        self.bandwidth_spin.setValue(36.0)
        self.bandwidth_spin.setSuffix(" MHz")
        self.bandwidth_spin.valueChanged.connect(self.calculate_complete_link)
        gen_layout.addWidget(self.bandwidth_spin, 2, 1)
        
        # Uplink Rain Rate
        gen_layout.addWidget(QLabel("UL Rain Rate (R_up):"), 3, 0)
        self.uplink_rain_spin = QDoubleSpinBox()
        self.uplink_rain_spin.setRange(0, 150)
        self.uplink_rain_spin.setValue(0)
        self.uplink_rain_spin.setSuffix(" mm/h")
        self.uplink_rain_spin.valueChanged.connect(self.calculate_complete_link)
        gen_layout.addWidget(self.uplink_rain_spin, 3, 1)
        
        # Downlink Rain Rate
        gen_layout.addWidget(QLabel("DL Rain Rate (R_dn):"), 4, 0)
        self.rain_spin = QDoubleSpinBox()
        self.rain_spin.setRange(0, 150)
        self.rain_spin.setValue(0)
        self.rain_spin.setSuffix(" mm/h")
        self.rain_spin.valueChanged.connect(self.calculate_complete_link)
        gen_layout.addWidget(self.rain_spin, 4, 1)
        
        general_group.setLayout(gen_layout)
        layout.addWidget(general_group)
        
        # ===== MODULATION & CODING =====
        modcod_group = self.create_modcod_group()
        layout.addWidget(modcod_group)
        
        # ===== POLARIZATION & MISC LOSSES =====
        pol_group = QGroupBox("Polarization")
        pol_group.setStyleSheet("""
            QGroupBox {
                background-color: #f5f3ff;
                border: 2px solid #8b5cf6;
                border-left: 5px solid #7c3aed;
                border-radius: 12px;
                padding: 10px 8px 8px 8px;
                margin-top: 14px;
                font-weight: 700;
                font-size: 10pt;
            }
            QGroupBox::title {
                color: #ffffff;
                font-weight: 800;
                font-size: 10pt;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #8b5cf6, stop:1 #7c3aed);
                border-radius: 6px;
                padding: 3px 12px;
                subcontrol-origin: margin;
                left: 12px;
            }
            QLabel {
                color: #1e293b; font-weight: 600; font-size: 9pt;
                background: transparent; border: none;
            }
        """)
        pol_layout = QGridLayout()
        
        pol_layout.addWidget(QLabel("Pol. Loss (L_pol):"), 0, 0)
        self.pol_loss_spin = QDoubleSpinBox()
        self.pol_loss_spin.setRange(0, 3)
        self.pol_loss_spin.setValue(0.2)
        self.pol_loss_spin.setSingleStep(0.1)
        self.pol_loss_spin.setSuffix(" dB")
        self.pol_loss_spin.valueChanged.connect(self.calculate_complete_link)
        pol_layout.addWidget(self.pol_loss_spin, 0, 1)
        
        pol_group.setLayout(pol_layout)
        layout.addWidget(pol_group)
        
        # ===== ATMOSPHERIC PARAMETERS (ITU-R) =====
        atm_group = QGroupBox("Atmospheric Parameters (ITU-R)")
        atm_group.setStyleSheet("""
            QGroupBox {
                background-color: #ecfeff;
                border: 2px solid #06b6d4;
                border-left: 5px solid #0891b2;
                border-radius: 12px;
                padding: 10px 8px 8px 8px;
                margin-top: 14px;
                font-weight: 700;
                font-size: 10pt;
            }
            QGroupBox::title {
                color: #ffffff;
                font-weight: 800;
                font-size: 10pt;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #06b6d4, stop:1 #0891b2);
                border-radius: 6px;
                padding: 3px 12px;
                subcontrol-origin: margin;
                left: 12px;
            }
            QLabel {
                color: #1e293b; font-weight: 600; font-size: 9pt;
                background: transparent; border: none;
            }
        """)
        atm_layout = QGridLayout()
        
        atm_layout.addWidget(QLabel("Water Vapor (ρ):"), 0, 0)
        self.water_vapor_spin = QDoubleSpinBox()
        self.water_vapor_spin.setRange(0, 30)
        self.water_vapor_spin.setValue(7.5)
        self.water_vapor_spin.setDecimals(1)
        self.water_vapor_spin.setSingleStep(0.5)
        self.water_vapor_spin.setSuffix(" g/m³")
        self.water_vapor_spin.setToolTip("Surface water vapor density (ITU-R P.676)")
        self.water_vapor_spin.valueChanged.connect(self.calculate_complete_link)
        atm_layout.addWidget(self.water_vapor_spin, 0, 1)
        
        atm_layout.addWidget(QLabel("Cloud LWC (L):"), 1, 0)
        self.cloud_lwc_spin = QDoubleSpinBox()
        self.cloud_lwc_spin.setRange(0, 3)
        self.cloud_lwc_spin.setValue(0.5)
        self.cloud_lwc_spin.setDecimals(2)
        self.cloud_lwc_spin.setSingleStep(0.1)
        self.cloud_lwc_spin.setSuffix(" kg/m²")
        self.cloud_lwc_spin.setToolTip("Columnar liquid water content (ITU-R P.840)")
        self.cloud_lwc_spin.valueChanged.connect(self.calculate_complete_link)
        atm_layout.addWidget(self.cloud_lwc_spin, 1, 1)
        
        atm_layout.addWidget(QLabel("Rain Height (h_R):"), 2, 0)
        self.rain_height_spin = QDoubleSpinBox()
        self.rain_height_spin.setRange(1, 7)
        self.rain_height_spin.setValue(3.0)
        self.rain_height_spin.setDecimals(1)
        self.rain_height_spin.setSingleStep(0.5)
        self.rain_height_spin.setSuffix(" km")
        self.rain_height_spin.setToolTip("Rain height above sea level (ITU-R P.839)")
        self.rain_height_spin.valueChanged.connect(self.calculate_complete_link)
        atm_layout.addWidget(self.rain_height_spin, 2, 1)
        
        atm_layout.addWidget(QLabel("Pol. Tilt (τ):"), 3, 0)
        self.pol_tilt_spin = QDoubleSpinBox()
        self.pol_tilt_spin.setRange(0, 90)
        self.pol_tilt_spin.setValue(45)
        self.pol_tilt_spin.setDecimals(0)
        self.pol_tilt_spin.setSingleStep(5)
        self.pol_tilt_spin.setSuffix("°")
        self.pol_tilt_spin.setToolTip("Polarization tilt angle (ITU-R P.838)")
        self.pol_tilt_spin.valueChanged.connect(self.calculate_complete_link)
        atm_layout.addWidget(self.pol_tilt_spin, 3, 1)
        
        atm_group.setLayout(atm_layout)
        layout.addWidget(atm_group)
        
        # ===== CALCULATE BUTTONS =====
        button_layout = QHBoxLayout()
        
        calc_button = QPushButton("▶ Calculate")
        calc_button.clicked.connect(self.calculate_complete_link)
        calc_button.setStyleSheet("""
            QPushButton {
                background: #10b981;
                font-size: 9pt;
                padding: 6px 14px;
                border-radius: 6px;
                font-weight: 600;
                color: white;
                border: none;
            }
            QPushButton:hover { background: #059669; }
            QPushButton:pressed { background: #047857; }
        """)
        button_layout.addWidget(calc_button)
        
        reset_button = QPushButton("↺ Reset")
        reset_button.clicked.connect(self.reset_parameters)
        reset_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                padding: 6px 14px;
                border-radius: 6px;
                font-weight: 600;
                font-size: 9pt;
                color: #d97706;
                border: 1px solid #d97706;
            }
            QPushButton:hover { background: #fef3c7; }
            QPushButton:pressed { background: #fde68a; }
        """)
        button_layout.addWidget(reset_button)
        
        layout.addLayout(button_layout)
        
        layout.addStretch()
        
        scroll.setWidget(panel)
        
        # Populate combos from stored lists
        self._refresh_combos()
        
        return scroll
    
    def _create_hidden_param_widgets(self):
        """Create internal parameter widgets for backward compatibility.
        
        These widgets are NOT added to any layout — they exist as internal
        attributes so that calculate_complete_link and other methods can
        read values from them transparently. When the user selects a BS or
        Satellite from the combos, these hidden widgets get synced.
        """
        # --- Satellite type (internal) ---
        self.sat_type_combo = QComboBox()
        self.sat_type_combo.addItems(list(SATELLITE_TYPES.keys()))
        self.sat_type_combo.setCurrentText('GEO')
        
        # --- Altitude ---
        self.altitude_spin = QDoubleSpinBox()
        self.altitude_spin.setRange(160, 50000)
        self.altitude_spin.setValue(35786)
        
        # --- GS Location (from BS1) ---
        self.gs_lat_spin = QDoubleSpinBox()
        self.gs_lat_spin.setRange(-90, 90)
        self.gs_lat_spin.setDecimals(7)
        self.gs_lat_spin.setValue(37.9755648)
        
        self.gs_lon_spin = QDoubleSpinBox()
        self.gs_lon_spin.setRange(-180, 180)
        self.gs_lon_spin.setDecimals(7)
        self.gs_lon_spin.setValue(23.7348324)
        
        # --- Satellite position ---
        self.sat_lon_spin = QDoubleSpinBox()
        self.sat_lon_spin.setRange(-180, 180)
        self.sat_lon_spin.setValue(13.0)
        
        self.sat_lat_spin = QDoubleSpinBox()
        self.sat_lat_spin.setRange(-90, 90)
        self.sat_lat_spin.setValue(0.0)
        
        # --- Uplink TX (from BS1) ---
        self.uplink_tx_power_spin = QDoubleSpinBox()
        self.uplink_tx_power_spin.setRange(-10, 30)
        self.uplink_tx_power_spin.setValue(10.0)
        
        self.uplink_antenna_spin = QDoubleSpinBox()
        self.uplink_antenna_spin.setRange(0.5, 15)
        self.uplink_antenna_spin.setValue(2.4)
        
        # --- Satellite RX ---
        self.sat_rx_gain_spin = QDoubleSpinBox()
        self.sat_rx_gain_spin.setRange(0, 50)
        self.sat_rx_gain_spin.setValue(30.0)
        
        self.sat_nf_spin = QDoubleSpinBox()
        self.sat_nf_spin.setRange(0.5, 10)
        self.sat_nf_spin.setValue(2.0)
        
        # --- Satellite TX ---
        self.tx_power_spin = QDoubleSpinBox()
        self.tx_power_spin.setRange(-10, 50)
        self.tx_power_spin.setValue(10.0)
        
        self.tx_gain_spin = QDoubleSpinBox()
        self.tx_gain_spin.setRange(0, 60)
        self.tx_gain_spin.setValue(32.0)
        
        # --- GS RX (from BS2) ---
        self.gs_diameter_spin = QDoubleSpinBox()
        self.gs_diameter_spin.setRange(0.3, 30)
        self.gs_diameter_spin.setValue(1.2)
        
        self.lna_temp_spin = QDoubleSpinBox()
        self.lna_temp_spin.setRange(10, 500)
        self.lna_temp_spin.setValue(50)
        
        # --- Losses (from BS) ---
        self.feed_loss_spin = QDoubleSpinBox()
        self.feed_loss_spin.setRange(0, 5)
        self.feed_loss_spin.setValue(0.5)
        
        self.pointing_loss_tx_spin = QDoubleSpinBox()
        self.pointing_loss_tx_spin.setRange(0, 3)
        self.pointing_loss_tx_spin.setValue(0.3)
        
        self.pointing_loss_rx_spin = QDoubleSpinBox()
        self.pointing_loss_rx_spin.setRange(0, 3)
        self.pointing_loss_rx_spin.setValue(0.2)
        
        self.antenna_eff_spin = QDoubleSpinBox()
        self.antenna_eff_spin.setRange(0.3, 0.9)
        self.antenna_eff_spin.setValue(0.6)
        self.antenna_eff_spin.setDecimals(2)
        
        # --- HPA / Transponder (from Satellite) ---
        self.hpa_type_combo = QComboBox()
        self.hpa_type_combo.addItems(['TWTA', 'SSPA', 'Linearized'])
        self.hpa_type_combo.setCurrentText('TWTA')
        
        self.ibo_spin = QDoubleSpinBox()
        self.ibo_spin.setRange(0, 15)
        self.ibo_spin.setValue(1.0)
        
        self.obo_spin = QDoubleSpinBox()
        self.obo_spin.setRange(0, 20)
        self.obo_spin.setValue(2.5)
        
        self.cim_spin = QDoubleSpinBox()
        self.cim_spin.setRange(5, 60)
        self.cim_spin.setValue(30)
        
        self.ampm_label = QLabel("0.0°")
        
        # --- GS Height (from BS1) ---
        self.gs_height_spin = QDoubleSpinBox()
        self.gs_height_spin.setRange(0, 5)
        self.gs_height_spin.setValue(0.0)
        self.gs_height_spin.setDecimals(2)
        
        # --- Transponder preset (from Satellite) ---
        self.transponder_preset_combo = QComboBox()
        self.transponder_preset_combo.addItems(['Custom'] + list(SatelliteTransponder.PRESETS.keys()))
        self.transponder_preset_combo.setCurrentText('Ku-band_standard')
        
        self.lna_gain_spin = QDoubleSpinBox()
        self.lna_gain_spin.setRange(10, 50)
        self.lna_gain_spin.setValue(30.0)
        
        self.lna_nf_spin = QDoubleSpinBox()
        self.lna_nf_spin.setRange(0.3, 5.0)
        self.lna_nf_spin.setValue(1.2)
        self.lna_nf_spin.setDecimals(1)
        
        self.mixer_gain_spin = QDoubleSpinBox()
        self.mixer_gain_spin.setRange(-15, 5)
        self.mixer_gain_spin.setValue(-6.0)
        
        self.mixer_nf_spin = QDoubleSpinBox()
        self.mixer_nf_spin.setRange(3, 15)
        self.mixer_nf_spin.setValue(8.0)
        self.mixer_nf_spin.setDecimals(1)
        
        self.if_gain_spin = QDoubleSpinBox()
        self.if_gain_spin.setRange(10, 50)
        self.if_gain_spin.setValue(30.0)
        
        self.pa_gain_spin = QDoubleSpinBox()
        self.pa_gain_spin.setRange(5, 40)
        self.pa_gain_spin.setValue(20.0)
        
        self.pa_psat_spin = QDoubleSpinBox()
        self.pa_psat_spin.setRange(-5, 25)
        self.pa_psat_spin.setValue(10.0)
        
        # --- Labels for transponder summary ---
        self.transponder_gain_label = QLabel("Total Gain: -- dB")
        self.transponder_nf_label = QLabel("Cascade NF: -- dB")
        self.transponder_eirp_label = QLabel("Sat EIRP: -- dBW")
        
        # --- Dummy groups for on_link_mode_changed backward compat ---
        self.uplink_group = QGroupBox("UPLINK")
        self.downlink_group = QGroupBox("DOWNLINK")
        
        # --- Place BS button (backward compat) ---
        self.place_bs_btn = QPushButton("📍 Place BS")
    
    def _refresh_combos(self):
        """Refresh the BS1, Satellite, BS2 combo boxes from stored lists"""
        # Block signals to avoid triggering recalculation during refresh
        self.bs1_combo.blockSignals(True)
        self.sat_combo.blockSignals(True)
        self.bs2_combo.blockSignals(True)
        
        # Save current selections
        bs1_text = self.bs1_combo.currentText()
        sat_text = self.sat_combo.currentText()
        bs2_text = self.bs2_combo.currentText()
        
        # Clear and repopulate
        self.bs1_combo.clear()
        self.bs2_combo.clear()
        for bs in self.base_stations:
            self.bs1_combo.addItem(bs.name)
            self.bs2_combo.addItem(bs.name)
        
        self.sat_combo.clear()
        for sat in self.satellite_configs:
            self.sat_combo.addItem(sat.name)
        
        # Restore selections
        idx = self.bs1_combo.findText(bs1_text)
        if idx >= 0:
            self.bs1_combo.setCurrentIndex(idx)
        elif self.bs1_combo.count() > 0:
            self.bs1_combo.setCurrentIndex(0)
        
        idx = self.sat_combo.findText(sat_text)
        if idx >= 0:
            self.sat_combo.setCurrentIndex(idx)
        elif self.sat_combo.count() > 0:
            self.sat_combo.setCurrentIndex(0)
        
        idx = self.bs2_combo.findText(bs2_text)
        if idx >= 0:
            self.bs2_combo.setCurrentIndex(idx)
        elif self.bs2_combo.count() > 0:
            self.bs2_combo.setCurrentIndex(0)
        
        self.bs1_combo.blockSignals(False)
        self.sat_combo.blockSignals(False)
        self.bs2_combo.blockSignals(False)
        
        # Sync hidden widgets from current selection
        self._sync_from_selection()
    
    def _get_selected_bs(self, combo):
        """Get the BaseStation object selected in the given combo"""
        idx = combo.currentIndex()
        if 0 <= idx < len(self.base_stations):
            return self.base_stations[idx]
        return None
    
    def _get_selected_satellite_config(self):
        """Get the SatelliteConfig object selected in the sat combo"""
        idx = self.sat_combo.currentIndex()
        if 0 <= idx < len(self.satellite_configs):
            return self.satellite_configs[idx]
        return None
    
    def _sync_from_selection(self):
        """Sync hidden param widgets from selected BS/Sat objects"""
        bs1 = self._get_selected_bs(self.bs1_combo)
        sat = self._get_selected_satellite_config()
        bs2 = self._get_selected_bs(self.bs2_combo)
        
        if bs1:
            self.gs_lat_spin.setValue(bs1.latitude)
            self.gs_lon_spin.setValue(bs1.longitude)
            self.gs_height_spin.setValue(bs1.height_km)
            self.uplink_tx_power_spin.setValue(bs1.tx_power_dbw)
            self.uplink_antenna_spin.setValue(bs1.tx_antenna_diameter_m)
            self.antenna_eff_spin.setValue(bs1.antenna_efficiency)
            self.feed_loss_spin.setValue(bs1.feed_loss_db)
            self.pointing_loss_tx_spin.setValue(bs1.pointing_loss_tx_db)
        
        if bs2:
            self.gs_diameter_spin.setValue(bs2.rx_antenna_diameter_m)
            self.lna_temp_spin.setValue(bs2.lna_temp_k)
            self.pointing_loss_rx_spin.setValue(bs2.pointing_loss_rx_db)
        
        if sat:
            self.sat_type_combo.setCurrentText(sat.sat_type)
            self.altitude_spin.setValue(sat.altitude_km)
            self.sat_lat_spin.setValue(sat.latitude)
            self.sat_lon_spin.setValue(sat.longitude)
            self.sat_rx_gain_spin.setValue(sat.rx_gain_dbi)
            self.sat_nf_spin.setValue(sat.noise_figure_db)
            self.tx_power_spin.setValue(sat.tx_power_dbw)
            self.tx_gain_spin.setValue(sat.tx_gain_dbi)
            self.hpa_type_combo.setCurrentText(sat.hpa_type)
            self.ibo_spin.setValue(sat.input_backoff_db)
            
            # Sync band / frequency / bandwidth from satellite
            ul_freq = getattr(sat, 'uplink_freq_ghz', None)
            dl_freq = getattr(sat, 'downlink_freq_ghz', None)
            bw_mhz = getattr(sat, 'bandwidth_mhz', None)
            if ul_freq is not None:
                self.uplink_freq_spin.setValue(ul_freq)
            if dl_freq is not None:
                self.frequency_spin.setValue(dl_freq)
            if bw_mhz is not None:
                self.bandwidth_spin.setValue(bw_mhz)
            
            # Sync transponder model
            self._sync_transponder_from_satellite(sat)
            
            # Create SatelliteOrbit object for tracking
            if sat.sat_type in SATELLITE_TYPES:
                self.satellite = create_satellite_from_type(sat.sat_type)
    
    def _sync_transponder_from_satellite(self, sat):
        """Update the transponder model from a SatelliteConfig object"""
        # Update transponder preset if valid
        if sat.transponder_preset in SatelliteTransponder.PRESETS:
            self.transponder = SatelliteTransponder(preset=sat.transponder_preset)
        
        # Override with satellite-specific values
        self.transponder.set_stage_params('LNA',
            gain_db=sat.lna_gain_db,
            noise_figure_db=sat.lna_nf_db)
        self.transponder.set_stage_params('Mixer',
            gain_db=sat.mixer_gain_db,
            noise_figure_db=sat.mixer_nf_db)
        self.transponder.set_stage_params('IF_Amp',
            gain_db=sat.if_gain_db)
        self.transponder.set_stage_params('PA',
            gain_db=sat.pa_gain_db)
        self.transponder.saturated_power_dbw = sat.pa_psat_dbw
        self.transponder.hpa_type = sat.hpa_type
        self.transponder.input_backoff_db = sat.input_backoff_db
        
        # Calculate derived values
        obo = self.transponder.calculate_obo_from_ibo(sat.input_backoff_db)
        self.transponder.output_backoff_db = obo
        self.obo_spin.setValue(round(obo, 2))
        
        cim = self.transponder.calculate_cim_from_ibo(sat.input_backoff_db, 1)
        self.cim_spin.setValue(round(cim, 1))
        
        am_pm = self.transponder.calculate_am_pm(sat.input_backoff_db)
        self.ampm_label.setText(f"{am_pm:.1f}°")
        
        # Update hidden transponder spinboxes
        self.lna_gain_spin.setValue(sat.lna_gain_db)
        self.lna_nf_spin.setValue(sat.lna_nf_db)
        self.mixer_gain_spin.setValue(sat.mixer_gain_db)
        self.mixer_nf_spin.setValue(sat.mixer_nf_db)
        self.if_gain_spin.setValue(sat.if_gain_db)
        self.pa_gain_spin.setValue(sat.pa_gain_db)
        self.pa_psat_spin.setValue(sat.pa_psat_dbw)
        
        self.transponder.rx_antenna_gain_dbi = sat.rx_gain_dbi
        self.transponder.tx_antenna_gain_dbi = sat.tx_gain_dbi
    
    def _on_bs1_changed(self, index):
        """Handle BS1 combo selection change"""
        self._sync_from_selection()
        self.calculate_complete_link()
        self._3d_needs_full_rebuild = True
        if HAS_3D and hasattr(self, 'update_3d_view'):
            self.update_3d_view()
    
    def _on_sat_changed(self, index):
        """Handle Satellite combo selection change"""
        self._sync_from_selection()
        self.calculate_complete_link()
        self._3d_needs_full_rebuild = True
        if HAS_3D and hasattr(self, 'update_3d_view'):
            self.update_3d_view()
    
    def _on_bs2_changed(self, index):
        """Handle BS2 combo selection change"""
        self._sync_from_selection()
        self.calculate_complete_link()
        self._3d_needs_full_rebuild = True
        if HAS_3D and hasattr(self, 'update_3d_view'):
            self.update_3d_view()
    
    # ==================== HUB TAB ====================
    
    def create_hub_tab(self):
        """Create Hub tab — delegated to gui.hub.hub_tab"""
        return _mod_hub_tab(self)

    def _refresh_hub_lists(self):
        """Refresh hub lists — delegated"""
        self._3d_needs_full_rebuild = True
        from gui.hub.hub_tab import _refresh_hub_lists as _rhl
        _rhl(self)

    def _refresh_hub_bs_list(self):
        """Refresh BS list — delegated"""
        from gui.hub.hub_tab import _refresh_hub_bs_list as _rbl
        _rbl(self)

    def _refresh_hub_sat_list(self):
        """Refresh satellite list — delegated"""
        from gui.hub.hub_tab import _refresh_hub_sat_list as _rsl
        _rsl(self)

    def _create_bs_card(self, bs, index):
        """Create BS card — delegated"""
        from gui.hub.hub_tab import _create_bs_card as _cbc
        return _cbc(self, bs, index)

    def _create_sat_card(self, sat, index):
        """Create satellite card — delegated"""
        from gui.hub.hub_tab import _create_sat_card as _csc
        return _csc(self, sat, index)

    # ==================== ADD / EDIT / DELETE DIALOGS ====================
    
    def _add_base_station_dialog(self):
        """Add base station — delegated to gui.hub.dialogs"""
        _mod_add_bs(self)

    def _edit_base_station(self, index):
        """Edit base station — delegated"""
        _mod_edit_bs(self, index)

    def _delete_base_station(self, index):
        """Delete base station — delegated"""
        _mod_del_bs(self, index)

    def _add_satellite_dialog(self):
        """Add satellite — delegated to gui.hub.dialogs"""
        _mod_add_sat(self)

    def _edit_satellite(self, index):
        """Edit satellite — delegated"""
        _mod_edit_sat(self, index)

    def _delete_satellite(self, index):
        """Delete satellite — delegated"""
        _mod_del_sat(self, index)

    def _create_bs_dialog(self, bs=None):
        """Create BS dialog — delegated"""
        from gui.hub.dialogs import _create_bs_dialog as _cbd
        return _cbd(self, bs)

    def _create_sat_dialog(self, sat=None):
        """Create satellite dialog — delegated"""
        from gui.hub.dialogs import _create_sat_dialog as _csd
        return _csd(self, sat)

    # ==================== END NEW HUB/LINK BUDGET METHODS ====================

    def create_visualization_panel(self):
        """Create enhanced visualization panel with LAZY tab loading.
        
        Tabs are only built when first viewed. After a calculation, only
        the currently visible tab is updated; others are marked dirty and
        refreshed when the user switches to them.
        """
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Tab widget — stored on self for later access
        self.viz_tabs = QTabWidget()
        self.viz_tabs.setStyleSheet("QTabBar::tab { min-width: 120px; }")
        
        # ── Tab metadata: (label, create_method, is_3d_guard) ──
        self._tab_defs = [
            ("Hub",           self.create_hub_tab,            False),
            ("Complete Link", self.create_complete_link_tab,  False),
            ("Waterfall",     self.create_waterfall_tab,      False),
            ("BER Curves",    self.create_ber_tab,            False),
            ("Constellation", self.create_constellation_tab,  False),
            ("Ground Track",  self.create_orbit_tab,          False),
            ("Link Diagram",  self.create_link_diagram_tab,   False),
            ("Transponder",   self.create_transponder_tab,    False),
        ]
        if HAS_3D:
            self._tab_defs.append(("3D View", self.create_3d_tab, True))
        
        # Track which tabs have been built and which need a data refresh
        self._tab_built = {}       # index -> bool
        self._tab_dirty = {}       # index -> bool
        
        # Insert lightweight placeholder widgets for every tab
        for idx, (label, _creator, _is3d) in enumerate(self._tab_defs):
            placeholder = QWidget()
            placeholder.setLayout(QVBoxLayout())
            self.viz_tabs.addTab(placeholder, label)
            self._tab_built[idx] = False
            self._tab_dirty[idx] = False
        
        # Build tab 0 (Hub) eagerly — it's the default visible tab
        self._ensure_tab_built(0)
        
        # Connect tab-change signal for lazy init + dirty refresh
        self.viz_tabs.currentChanged.connect(self._on_viz_tab_changed)
        
        layout.addWidget(self.viz_tabs)
        return panel
    
    # ── Lazy-loading helpers ──────────────────────────────────────────
    
    def _ensure_tab_built(self, index):
        """Build the real content for a tab if it hasn't been created yet."""
        if self._tab_built.get(index):
            return
        _label, creator, _is3d = self._tab_defs[index]
        real_widget = creator()                       # call create_xxx_tab()
        # Swap placeholder → real widget without triggering currentChanged
        self.viz_tabs.blockSignals(True)
        current = self.viz_tabs.currentIndex()
        old = self.viz_tabs.widget(index)
        self.viz_tabs.removeTab(index)
        self.viz_tabs.insertTab(index, real_widget, _label)
        if old is not None:
            old.deleteLater()
        self._tab_built[index] = True
        self.viz_tabs.setCurrentIndex(current)
        self.viz_tabs.blockSignals(False)
    
    def _teardown_tab(self, index):
        """Destroy a tab's real content and replace with a lightweight placeholder."""
        if not self._tab_built.get(index):
            return
        _label = self._tab_defs[index][0]
        self.viz_tabs.blockSignals(True)
        current = self.viz_tabs.currentIndex()
        old = self.viz_tabs.widget(index)
        self.viz_tabs.removeTab(index)
        placeholder = QWidget()
        placeholder.setLayout(QVBoxLayout())
        self.viz_tabs.insertTab(index, placeholder, _label)
        if old is not None:
            old.deleteLater()
        self._tab_built[index] = False
        self._tab_dirty[index] = False
        self.viz_tabs.setCurrentIndex(current)
        self.viz_tabs.blockSignals(False)
    
    def _on_viz_tab_changed(self, index):
        """Called when the user switches tabs.
        
        1. Tear down the previously active tab (free its widgets/canvases).
        2. Build the newly selected tab fresh.
        3. Push latest data into it.
        """
        # Tear down all other built tabs so only one is alive at a time
        for idx in list(self._tab_built.keys()):
            if idx != index and self._tab_built.get(idx):
                self._teardown_tab(idx)
        
        # Build (or rebuild) the target tab
        self._ensure_tab_built(index)
        
        # Push latest data into it
        if self._tab_dirty.get(index) or True:  # always refresh on switch
            self._refresh_tab(index)
            self._tab_dirty[index] = False
    
    def _mark_all_tabs_dirty(self):
        """Flag every tab (except the active one) as needing a data refresh."""
        current = self.viz_tabs.currentIndex() if hasattr(self, 'viz_tabs') else -1
        for idx in self._tab_dirty:
            if idx != current:
                self._tab_dirty[idx] = True
    
    def _refresh_tab(self, index):
        """Push the latest data into tab *index* (must already be built)."""
        if not hasattr(self, 'last_results') or self.last_results is None:
            return
        results = self.last_results
        params  = self.last_params
        
        label = self._tab_defs[index][0]
        
        if label == "Complete Link":
            self.update_complete_results_text(results, params)
        elif label == "Waterfall":
            self.update_waterfall_diagram(results, params)
        elif label == "BER Curves":
            self.update_ber_plot()
        elif label == "Constellation":
            self.update_constellation()
        elif label == "Ground Track":
            self.update_orbit_plot()
        elif label == "Link Diagram":
            self.update_link_diagram_complete(results, params)
        elif label == "Transponder":
            self.update_transponder_block_diagram()
            self.update_transponder_transfer_curve()
            self.update_transponder_noise_cascade()
            self.update_transponder_labels()
        elif label == "3D View":
            self.update_3d_view()
        elif label == "Hub":
            self._refresh_hub_lists()
    
    def create_complete_link_tab(self):
        """Create Complete Link tab — delegated"""
        return _mod_cl_tab(self)

    def create_waterfall_tab(self):
        """Create Waterfall tab — delegated"""
        return _mod_waterfall_tab(self)

    def create_ber_tab(self):
        """Create BER tab — delegated"""
        return _mod_ber_tab(self)

    def create_constellation_tab(self):
        """Create Constellation tab — delegated"""
        return _mod_const_tab(self)

    def create_orbit_tab(self):
        """Create Orbit/Ground Track tab — delegated"""
        return _mod_orbit_tab(self)

    def create_link_diagram_tab(self):
        """Create Link Diagram tab — delegated"""
        return _mod_ld_tab(self)

    def create_transponder_tab(self):
        """Create Transponder tab — delegated"""
        return _mod_tp_tab(self)

    def update_transponder_block_diagram(self):
        """Update transponder block diagram — delegated"""
        if not hasattr(self, 'transponder_block_canvas'):
            return
        _mod_tp_block(self)

    def update_transponder_transfer_curve(self):
        """Update transponder transfer curve — delegated"""
        if not hasattr(self, 'transponder_transfer_canvas'):
            return
        _mod_tp_transfer(self)

    def update_transponder_noise_cascade(self):
        """Update transponder noise cascade — delegated"""
        if not hasattr(self, 'transponder_noise_canvas'):
            return
        _mod_tp_noise(self)

    def create_3d_tab(self):
        """Create 3D View tab — delegated"""
        return _mod_3d_tab(self)

    def _reposition_3d_overlay(self, event):
        """Reposition 3D overlay — delegated"""
        from gui.visualizations.view_3d import _reposition_3d_overlay
        _reposition_3d_overlay(self, event)

    def _rebuild_3d_visibility_panel(self):
        """Rebuild 3D visibility panel — delegated"""
        from gui.visualizations.view_3d import _rebuild_3d_visibility_panel
        _rebuild_3d_visibility_panel(self)

    def _on_3d_visibility_changed(self, kind, index, state):
        """Handle 3D visibility toggle — delegated"""
        from gui.visualizations.view_3d import _on_vis_changed
        _on_vis_changed(self, kind, index, state)

    # ==================== MAIN CALCULATION ====================
    
    def calculate_complete_link(self):
        """
        Perform complete link budget calculation (uplink + downlink + total)
        
        ═══════════════════════════════════════════════════════════════════════════════════
        EXECUTION ORDER OF METHODS IN link_budget.py:
        ═══════════════════════════════════════════════════════════════════════════════════
        
        UPLINK CALCULATION (full_uplink_budget):
        ─────────────────────────────────────────
        #1  calculate_gs_eirp()            → Ground Station EIRP (uses calculate_antenna_gain)
        #2  calculate_fspl()               → Free Space Path Loss
        #3  calculate_atmospheric_attenuation() → Atmospheric + Rain Attenuation
        #4  calculate_satellite_noise_temp()    → Satellite Noise Temperature
        #5  calculate_satellite_gt()       → Satellite G/T (uses calculate_gt_figure)
        #6  calculate_cn0()                → Uplink C/N₀
        #7  calculate_cn()                 → Uplink C/N
        #8  calculate_ebn0()               → Uplink Eb/N₀
        #9  calculate_link_margin()        → Uplink Margin
        
        DOWNLINK CALCULATION (full_downlink_budget):
        ─────────────────────────────────────────────
        #10 calculate_satellite_eirp()     → Satellite EIRP (uses calculate_eirp)
        #11 calculate_fspl()               → Free Space Path Loss
        #12 calculate_atmospheric_attenuation() → Atmospheric + Rain Attenuation
        #13 calculate_gs_gt()              → Ground Station G/T (uses calculate_antenna_gain,
                                              calculate_system_noise_temp, calculate_gt_figure)
        #14 calculate_cn0()                → Downlink C/N₀
        #15 calculate_cn()                 → Downlink C/N
        #16 calculate_ebn0()               → Downlink Eb/N₀
        #17 calculate_link_margin()        → Downlink Margin
        
        TOTAL LINK CALCULATION (calculate_total_link_margin):
        ─────────────────────────────────────────────────────
        #18 calculate_total_cn0()          → Combined C/N₀: 1/(C/N₀)_total = 1/(C/N₀)_up + 1/(C/N₀)_down
        #19 calculate_cn()                 → Total C/N
        #20 calculate_ebn0()               → Total Eb/N₀
        #21 calculate_link_margin()        → Total Margin
        
        ═══════════════════════════════════════════════════════════════════════════════════
        """
        # Ensure the Complete Link tab (index 1) is built so the canvas exists,
        # even if the user hasn't navigated to it yet (lazy loading).
        if not hasattr(self, 'complete_results_canvas'):
            if not hasattr(self, 'viz_tabs'):
                return  # UI not fully initialized yet (spinbox signals during setup)
            self._ensure_tab_built(1)
        
        # Get user inputs
        sat_lat = self.sat_lat_spin.value()
        sat_lon = self.sat_lon_spin.value()
        gs_lat = self.gs_lat_spin.value()
        gs_lon = self.gs_lon_spin.value()
        altitude = self.altitude_spin.value()
        
        # Calculate geometry from lat/lon (ITU-R S.1257 / P.618-13)
        Re = 6371  # Earth radius km
        Rs = Re + altitude
        
        # Central Angle γ
        lat_gs_rad = np.radians(gs_lat)
        lat_sat_rad = np.radians(sat_lat)
        delta_lon_rad = np.radians(gs_lon - sat_lon)
        cos_gamma = (np.cos(lat_gs_rad) * np.cos(lat_sat_rad) * np.cos(delta_lon_rad) + 
                     np.sin(lat_gs_rad) * np.sin(lat_sat_rad))
        cos_gamma = np.clip(cos_gamma, -1.0, 1.0)
        gamma = np.arccos(cos_gamma)  # Central angle in radians
        central_angle_deg = np.degrees(gamma)
        
        # Elevation Angle E
        if np.sin(gamma) < 1e-10:
            elevation = 90.0
        else:
            elevation = np.degrees(np.arctan((np.cos(gamma) - Re/Rs) / np.sin(gamma)))
        elevation = max(5.0, min(90.0, elevation))  # Clamp to valid range
        
        # Slant Range d
        calculated_slant_range = np.sqrt(Re**2 + Rs**2 - 2 * Re * Rs * np.cos(gamma))
        
        # Build complete parameters for end-to-end link
        # Now using USER INPUTS for all parameters (no more hardcoded values)
        params = {
            # Uplink parameters (Ground Station TX → Satellite RX)
            'gs_tx_power_dbw': self.uplink_tx_power_spin.value(),
            'gs_antenna_diameter_m': self.uplink_antenna_spin.value(),
            'gs_antenna_efficiency': self.antenna_eff_spin.value(),
            'gs_feed_loss_db': self.feed_loss_spin.value(),
            'gs_pointing_loss_tx_db': self.pointing_loss_tx_spin.value(),
            'gs_pointing_loss_rx_db': self.pointing_loss_rx_spin.value(),
            'uplink_frequency_ghz': self.uplink_freq_spin.value(),
            'uplink_rain_rate': self.uplink_rain_spin.value(),
            'sat_rx_gain_dbi': self.sat_rx_gain_spin.value(),
            'sat_noise_figure_db': self.sat_nf_spin.value(),
            'sat_antenna_temp_k': 290,
            'input_backoff_db': self.ibo_spin.value(),
            'output_backoff_db': self.obo_spin.value(),
            'polarization_loss_db': self.pol_loss_spin.value(),
            
            # Downlink parameters (Satellite TX → Ground Station RX)
            'sat_power_dbw': self.tx_power_spin.value(),
            'sat_antenna_gain_dbi': self.tx_gain_spin.value(),
            'downlink_frequency_ghz': self.frequency_spin.value(),
            'downlink_rain_rate': self.rain_spin.value(),
            'gs_lna_temp_k': self.lna_temp_spin.value(),
            'gs_antenna_temp_k': 30,
            'gs_line_loss_db': self.feed_loss_spin.value(),
            
            # Geometry parameters (for Math Details and calculations)
            'lat_gs': gs_lat,
            'lon_gs': gs_lon,
            'lat_sat': sat_lat,  # Satellite latitude (0 for GEO, varies for LEO/MEO/HEO)
            'lon_sat': sat_lon,  # Satellite longitude
            'altitude_km': altitude,
            
            # Link mode
            'link_mode': self.link_mode_combo.currentText(),
            
            # Common parameters - elevation calculated from geometry, slant range calculated
            'distance_km': calculated_slant_range,
            'elevation_deg': elevation,  # Calculated from geometry
            'central_angle_deg': central_angle_deg,  # Central angle
            'bandwidth_hz': self.bandwidth_spin.value() * 1e6,
            'data_rate_bps': self.bandwidth_spin.value() * 1e6 * 0.9,
            'coding_rate': CODING_SCHEMES[self.coding_combo.currentText()]['rate'],
            'ebn0_required_db': 8.0,
            'num_carriers': 1,
            
            # C/IM for total link calculation
            'c_im_db': self.cim_spin.value(),
            
            # Atmospheric parameters (ITU-R)
            'gs_height_km': self.gs_height_spin.value(),           # Station height above sea level (km)
            'water_vapor_density': self.water_vapor_spin.value(),  # g/m³
            'cloud_liquid_water': self.cloud_lwc_spin.value(),     # kg/m²
            'rain_height_km': self.rain_height_spin.value(),       # km
            'polarization_tilt_deg': self.pol_tilt_spin.value(),   # degrees
        }
        
        # ===== APPLY MODULATION & CODING EFFECTS =====
        modulation = self.modulation_combo.currentText()
        coding = self.coding_combo.currentText()
        
        # Get modulation parameters
        mod_params = MODULATION_SCHEMES.get(modulation, MODULATION_SCHEMES['QPSK'])
        spectral_efficiency = mod_params['efficiency']  # bits/symbol
        required_ebn0_uncoded = mod_params['required_ebn0_db']  # For BER=10^-6
        
        # Get coding parameters
        coding_params = CODING_SCHEMES.get(coding, CODING_SCHEMES['LDPC (R=3/4)'])
        coding_rate = coding_params['rate']
        coding_gain = coding_params['gain']
        
        # Calculate effective data rate based on modulation and coding
        # Data Rate = Symbol Rate * Spectral Efficiency * Coding Rate
        # Symbol Rate = Bandwidth / (1 + roll-off), assuming roll-off = 0.2
        roll_off = 0.2
        symbol_rate = params['bandwidth_hz'] / (1 + roll_off)
        effective_data_rate = symbol_rate * spectral_efficiency * coding_rate
        
        # Calculate required Eb/N0 with coding gain applied
        required_ebn0_coded = required_ebn0_uncoded - coding_gain
        
        # Update params with modulation-aware values
        params['modulation'] = modulation
        params['coding'] = coding
        params['spectral_efficiency'] = spectral_efficiency
        params['coding_rate'] = coding_rate
        params['coding_gain_db'] = coding_gain
        params['data_rate_bps'] = effective_data_rate
        params['ebn0_required_db'] = required_ebn0_coded
        params['symbol_rate_sps'] = symbol_rate
        
        # For downlink, use the GS RX antenna diameter
        params['gs_antenna_diameter_m_rx'] = self.gs_diameter_spin.value()
        
        # ===== UPDATE TRANSPONDER MODEL =====
        # Sync transponder frequency plan with uplink/downlink frequencies
        self.transponder.set_frequency_plan(
            params['uplink_frequency_ghz'], 
            params['downlink_frequency_ghz'])
        self.transponder.bandwidth_mhz = params['bandwidth_hz'] / 1e6
        self.transponder.hpa_type = self.hpa_type_combo.currentText()
        self.transponder.input_backoff_db = params.get('input_backoff_db', 1.0)
        # OBO auto-calculated from IBO via HPA model
        auto_obo = self.transponder.calculate_obo_from_ibo(params.get('input_backoff_db', 1.0))
        self.transponder.output_backoff_db = auto_obo
        params['output_backoff_db'] = auto_obo  # Feed auto-OBO into link budget
        # C/IM auto-calculated from IBO
        auto_cim = self.transponder.calculate_cim_from_ibo(
            params.get('input_backoff_db', 1.0), params.get('num_carriers', 1))
        params['c_im_db'] = auto_cim  # Feed auto-C/IM into link budget
        # HPA characteristics for results display
        params['hpa_type'] = self.transponder.hpa_type
        params['am_pm_deg'] = self.transponder.calculate_am_pm(params.get('input_backoff_db', 1.0))
        self.transponder.rx_antenna_gain_dbi = self.sat_rx_gain_spin.value()
        self.transponder.tx_antenna_gain_dbi = self.tx_gain_spin.value()
        
        # Feed transponder cascade noise figure into satellite NF
        cascade_nf = self.transponder.calculate_cascade_noise_figure()
        params['sat_noise_figure_db'] = cascade_nf
        
        # Feed transponder EIRP into satellite EIRP calculation
        sat_eirp_from_transponder = self.transponder.calculate_satellite_eirp()
        params['sat_power_dbw'] = sat_eirp_from_transponder - self.tx_gain_spin.value()
        
        # Add transponder summary to params for display
        params['transponder_summary'] = self.transponder.get_chain_summary()
        
        # Show loading animation
        self.statusBar().showMessage(" Calculating complete link budget...")
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #e8f4f8;
                color: #003f5c;
                font-weight: 600;
                padding: 6px;
            }
        """)
        QApplication.processEvents()  # Update UI immediately
        
        # ═══════════════════════════════════════════════════════════════════════════════
        # MAIN CALL: complete_link_budget() calls:
        #   → full_uplink_budget()        [Methods #1 - #9]
        #   → full_downlink_budget()      [Methods #10 - #17]
        #   → calculate_total_link_margin() [Methods #18 - #21]
        # ═══════════════════════════════════════════════════════════════════════════════
        results = self.link_budget.complete_link_budget(params)
        
        # ===== DOPPLER EFFECT CALCULATIONS =====
        # Compute Doppler shift, radial velocity, and satellite velocity
        # using the orbital mechanics model — these affect received frequencies
        try:
            if self.satellite is None:
                sat_type = self.sat_type_combo.currentText()
                self.satellite = create_satellite_from_type(sat_type)

            t = self.current_time
            ul_freq_hz = params['uplink_frequency_ghz'] * 1e9
            dl_freq_hz = params['downlink_frequency_ghz'] * 1e9

            # Doppler shift (Hz) — positive = approaching
            doppler_ul_hz = self.satellite.calculate_doppler_shift(
                ul_freq_hz, gs_lat, gs_lon, t)
            doppler_dl_hz = self.satellite.calculate_doppler_shift(
                dl_freq_hz, gs_lat, gs_lon, t)

            # Satellite velocity magnitude (km/s)
            vel_vec = self.satellite.get_satellite_velocity_eci(t)
            sat_velocity_kms = float(np.linalg.norm(vel_vec))

            # Radial velocity via finite-difference range rate
            look1 = self.satellite.calculate_look_angles(gs_lat, gs_lon, 0, t)
            look2 = self.satellite.calculate_look_angles(gs_lat, gs_lon, 0, t + 1.0)
            radial_velocity_kms = (look2['range'] - look1['range']) / 1.0  # km/s

            # Doppler-shifted received frequencies
            ul_freq_shifted_ghz = (ul_freq_hz + doppler_ul_hz) / 1e9
            dl_freq_shifted_ghz = (dl_freq_hz + doppler_dl_hz) / 1e9

            # Store in results for display
            results['doppler'] = {
                'uplink_doppler_hz': doppler_ul_hz,
                'downlink_doppler_hz': doppler_dl_hz,
                'uplink_doppler_khz': doppler_ul_hz / 1e3,
                'downlink_doppler_khz': doppler_dl_hz / 1e3,
                'uplink_freq_shifted_ghz': ul_freq_shifted_ghz,
                'downlink_freq_shifted_ghz': dl_freq_shifted_ghz,
                'radial_velocity_kms': radial_velocity_kms,
                'satellite_velocity_kms': sat_velocity_kms,
                'max_doppler_ul_khz': sat_velocity_kms * 1000 / 3e8 * ul_freq_hz / 1e3,
                'max_doppler_dl_khz': sat_velocity_kms * 1000 / 3e8 * dl_freq_hz / 1e3,
            }
        except Exception:
            results['doppler'] = {
                'uplink_doppler_hz': 0, 'downlink_doppler_hz': 0,
                'uplink_doppler_khz': 0, 'downlink_doppler_khz': 0,
                'uplink_freq_shifted_ghz': params['uplink_frequency_ghz'],
                'downlink_freq_shifted_ghz': params['downlink_frequency_ghz'],
                'radial_velocity_kms': 0, 'satellite_velocity_kms': 0,
                'max_doppler_ul_khz': 0, 'max_doppler_dl_khz': 0,
            }

        # Store for other visualizations
        self.last_results = results
        self.last_params = params
        
        # Add to calculation history
        self._add_to_history(results, params)
        
        # ── Lazy update: only refresh the ACTIVE tab, mark others dirty ──
        self._mark_all_tabs_dirty()
        active_idx = self.viz_tabs.currentIndex() if hasattr(self, 'viz_tabs') else -1
        if active_idx >= 0 and self._tab_built.get(active_idx):
            self._refresh_tab(active_idx)
            self._tab_dirty[active_idx] = False
        
        # Dashboard cards are always visible — always update
        self.update_dashboard_cards(results, params)
        
        # Clear any opacity effects to ensure canvas is fully visible
        if hasattr(self, 'complete_results_canvas'):
            try:
                self.complete_results_canvas.setGraphicsEffect(None)
            except RuntimeError:
                pass  # Widget may have been deleted by lazy tab teardown
        
        # Hide loading animation
        self.statusBar().showMessage("Calculation complete")
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #fafafa;
                color: #003f5c;
                border-top: 1px solid #e0e0e0;
                padding: 4px;
                font-weight: 500;
            }
        """)
        QTimer.singleShot(2000, lambda: self.statusBar().showMessage("System Ready - All models loaded"))
        
        # Update status bar based on link mode
        link_mode = params.get('link_mode', 'Full Link')
        if link_mode == 'Uplink Only':
            margin = results['uplink']['uplink_margin_db']
            status = "UPLINK OK" if margin > 0 else "UPLINK FAIL"
            self.statusBar().showMessage(f"Uplink Margin: {margin:.2f} dB | {status}")
        elif link_mode == 'Downlink Only':
            margin = results['downlink']['downlink_margin_db']
            status = "DOWNLINK OK" if margin > 0 else "DOWNLINK FAIL"
            self.statusBar().showMessage(f"Downlink Margin: {margin:.2f} dB | {status}")
        else:  # Full Link
            total_margin = results['total_margin_db']
            status = "LINK AVAILABLE" if total_margin > 0 else "LINK UNAVAILABLE"
            self.statusBar().showMessage(f"Total Link Margin: {total_margin:.2f} dB | {status}")
    
    def update_complete_results_text(self, results, params):
        """Update link budget tables — delegated"""
        if not hasattr(self, 'complete_results_canvas'):
            return
        _mod_cl_update(self, results, params)

    def update_waterfall_diagram(self, results, params):
        """Update waterfall diagram — delegated"""
        if not hasattr(self, 'waterfall_canvas'):
            return
        _mod_waterfall_update(self, results, params)

    def draw_waterfall_detailed(self, ax, title, eirp, fspl, gaseous_loss, rain_loss, 
                                   cloud_loss, scint_loss, pointing_loss, pol_loss, 
                                   backoff, rx_gain, gt, cn0, is_uplink, color_theme):
        """Draw a detailed waterfall diagram with ALL individual losses"""
        _draw_waterfall(ax, title, eirp, fspl, gaseous_loss, rain_loss,
                        cloud_loss, scint_loss, pointing_loss, pol_loss,
                        backoff, rx_gain, gt, cn0, is_uplink, color_theme)
    
    def draw_combined_summary(self, ax, results, params):
        """Draw combined link summary with margin indicators"""
        _draw_summary(ax, results, params)
    
    def update_link_diagram_complete(self, results, params):
        """Update link diagram — delegated"""
        if not hasattr(self, 'link_diagram_canvas'):
            return
        _mod_ld_update(self, results, params)

    def update_ber_plot(self):
        """Update BER plot — delegated"""
        if not hasattr(self, 'ber_canvas'):
            return
        _mod_ber_update(self)

    def update_constellation(self):
        """Update constellation diagram — delegated"""
        if not hasattr(self, 'constellation_canvas'):
            return
        _mod_const_update(self)

    def update_orbit_plot(self):
        """Update ground track plot — delegated"""
        if not hasattr(self, 'orbit_canvas'):
            return
        _mod_orbit_update(self)

    def _draw_simple_map(self, ax):
        """Draw simplified continent outlines for map context."""
        # Simplified continent polygons (lon, lat pairs)
        continents = [
            # North America
            [(-130,50),(-125,60),(-100,62),(-80,60),(-55,48),(-65,45),
             (-80,25),(-105,20),(-120,35),(-130,50)],
            # South America
            [(-80,10),(-60,12),(-35,-5),(-35,-20),(-50,-30),(-70,-55),
             (-75,-45),(-70,-20),(-80,10)],
            # Europe
            [(-10,36),(0,43),(5,48),(10,55),(25,60),(30,55),(28,45),
             (25,35),(15,38),(5,36),(-10,36)],
            # Africa
            [(-15,15),(-15,5),(5,-2),(10,-15),(30,-35),(40,-25),(50,12),
             (45,15),(35,30),(10,35),(-5,35),(-15,15)],
            # Asia (simplified)
            [(30,35),(40,40),(50,45),(60,55),(80,55),(100,50),(120,55),
             (140,45),(130,35),(120,25),(105,15),(95,10),(80,15),(65,25),
             (45,30),(30,35)],
            # Australia
            [(115,-15),(130,-12),(150,-15),(153,-25),(148,-35),(135,-35),
             (120,-30),(115,-15)],
        ]
        for c in continents:
            xs, ys = zip(*c)
            ax.fill(xs, ys, color='#e0e0e0', alpha=0.5, zorder=0)
            ax.plot(xs, ys, color='#9e9e9e', linewidth=0.7, alpha=0.6, zorder=1)
    
    def update_3d_view(self):
        """Update 3D view — delegated"""
        _mod_3d_update(self)

    def on_link_mode_changed(self, mode):
        """Handle link mode change — recalculate with new mode"""
        # Recalculate with new mode
        self.calculate_complete_link()
    
    def on_satellite_type_changed(self, sat_type):
        """Update all relevant parameters when switching orbit type (GEO/LEO/MEO/HEO).

        Reads typical values from SATELLITE_TYPES in constants.py and applies
        physically-correct defaults for altitude, frequency band, TX power,
        antenna gains, bandwidth, HPA type, transponder preset, and ground
        station receive parameters.

        Orbit-specific defaults:
          GEO  — Ku-band, 35 786 km, TWTA, 36 MHz BW, large GS antenna
          LEO  — Ku-band, 550 km, SSPA, 240 MHz BW, small flat-panel antenna
          MEO  — L-band, 20 200 km, SSPA, 20 MHz BW, small GS antenna
          HEO  — Ku-band, ~20 000 km avg, TWTA, 36 MHz BW, medium GS antenna
        """
        if sat_type not in SATELLITE_TYPES:
            return

        sat_info = SATELLITE_TYPES[sat_type]

        # ── Orbit-type-specific default parameters ──────────────────────────
        # Each dict mirrors the spinner/combo widgets that should be updated.
        orbit_defaults = {
            'GEO': {
                'altitude_km':        35786,
                'sat_lat':            0.0,        # equatorial
                # Frequencies — Ku-band (ITU-R Table 5)
                'uplink_freq_ghz':    14.0,
                'downlink_freq_ghz':  12.0,
                'bandwidth_mhz':      36.0,
                # Satellite parameters
                'sat_rx_gain_dbi':    30.0,
                'sat_nf_db':          2.0,
                'sat_tx_power_dbw':   10.0,
                'sat_tx_gain_dbi':    32.0,
                # Ground station parameters
                'gs_tx_power_dbw':    10.0,
                'gs_tx_antenna_m':    2.4,
                'gs_rx_antenna_m':    1.2,
                'lna_temp_k':         50.0,
                # HPA & transponder
                'hpa_type':           'TWTA',
                'ibo_db':             1.0,
                'transponder_preset': 'Ku-band_standard',
                # Modulation
                'modulation':         'QPSK',
                'coding':             'LDPC (R=3/4)',
            },
            'LEO': {
                'altitude_km':        sat_info['typical_altitude'],  # 550 km
                'sat_lat':            0.0,
                # Frequencies — Ku-band (Starlink-type broadband)
                'uplink_freq_ghz':    14.0,
                'downlink_freq_ghz':  12.0,
                'bandwidth_mhz':      240.0,      # wideband LEO
                # Satellite parameters — lower power, smaller aperture
                'sat_rx_gain_dbi':    32.0,
                'sat_nf_db':          2.0,
                'sat_tx_power_dbw':   5.0,
                'sat_tx_gain_dbi':    32.0,
                # Ground station parameters — small flat-panel terminal
                'gs_tx_power_dbw':    10.0,
                'gs_tx_antenna_m':    0.5,
                'gs_rx_antenna_m':    0.5,
                'lna_temp_k':         75.0,
                # HPA & transponder — SSPA is standard for LEO
                'hpa_type':           'SSPA',
                'ibo_db':             2.0,
                'transponder_preset': 'Ku-band_standard',
                # Modulation
                'modulation':         '8PSK',
                'coding':             'LDPC (R=3/4)',
            },
            'MEO': {
                'altitude_km':        sat_info['typical_altitude'],  # 20 200 km
                'sat_lat':            0.0,
                # Frequencies — L-band (GPS / navigation, IS-GPS-200)
                'uplink_freq_ghz':    1.6,         # MSS UL allocation
                'downlink_freq_ghz':  1.575,       # GPS L1 = 1575.42 MHz
                'bandwidth_mhz':      20.0,        # GPS L1 C/A ≈ 20.46 MHz
                # Satellite parameters (GPS Block IIA/IIF)
                'sat_rx_gain_dbi':    13.0,        # L-band Earth-coverage
                'sat_nf_db':          3.0,
                'sat_tx_power_dbw':   8.0,         # SATELLITE_TYPES typical
                'sat_tx_gain_dbi':    13.0,        # helix array at L-band
                # Ground station parameters
                'gs_tx_power_dbw':    10.0,
                'gs_tx_antenna_m':    1.0,
                'gs_rx_antenna_m':    0.3,
                'lna_temp_k':         50.0,
                # HPA & transponder — SSPA, use C-band preset (closest to L-band)
                'hpa_type':           'SSPA',
                'ibo_db':             2.0,
                'transponder_preset': 'C-band_standard',
                # Modulation
                'modulation':         'BPSK',
                'coding':             'Turbo (R=1/2)',
            },
            'HEO': {
                'altitude_km':        sat_info['typical_altitude'],  # ~20 000 km avg
                'sat_lat':            63.4,       # critical inclination latitude at apogee
                # Frequencies — Ku-band (Sirius XM / Molniya-style)
                'uplink_freq_ghz':    14.0,
                'downlink_freq_ghz':  12.0,
                'bandwidth_mhz':      36.0,
                # Satellite parameters
                'sat_rx_gain_dbi':    30.0,
                'sat_nf_db':          2.5,
                'sat_tx_power_dbw':   10.0,
                'sat_tx_gain_dbi':    30.0,
                # Ground station parameters
                'gs_tx_power_dbw':    10.0,
                'gs_tx_antenna_m':    2.4,
                'gs_rx_antenna_m':    1.2,
                'lna_temp_k':         55.0,
                # HPA & transponder — TWTA
                'hpa_type':           'TWTA',
                'ibo_db':             1.0,
                'transponder_preset': 'Ku-band_standard',
                # Modulation
                'modulation':         'QPSK',
                'coding':             'LDPC (R=3/4)',
            },
        }

        defaults = orbit_defaults.get(sat_type, orbit_defaults['GEO'])

        # ── Block signals to prevent intermediate recalculations ────────────
        self._block_all_signals(True)

        # Orbit / geometry
        self.altitude_spin.setValue(defaults['altitude_km'])
        self.sat_lat_spin.setValue(defaults['sat_lat'])

        # Uplink
        self.uplink_freq_spin.setValue(defaults['uplink_freq_ghz'])
        self.uplink_tx_power_spin.setValue(defaults['gs_tx_power_dbw'])
        self.uplink_antenna_spin.setValue(defaults['gs_tx_antenna_m'])
        self.sat_rx_gain_spin.setValue(defaults['sat_rx_gain_dbi'])
        self.sat_nf_spin.setValue(defaults['sat_nf_db'])

        # Downlink
        self.frequency_spin.setValue(defaults['downlink_freq_ghz'])
        self.tx_power_spin.setValue(defaults['sat_tx_power_dbw'])
        self.tx_gain_spin.setValue(defaults['sat_tx_gain_dbi'])
        self.gs_diameter_spin.setValue(defaults['gs_rx_antenna_m'])
        self.lna_temp_spin.setValue(defaults['lna_temp_k'])

        # Bandwidth
        self.bandwidth_spin.setValue(defaults['bandwidth_mhz'])

        # HPA / Transponder
        self.hpa_type_combo.setCurrentText(defaults['hpa_type'])
        self.ibo_spin.setValue(defaults['ibo_db'])
        if defaults['transponder_preset'] in SatelliteTransponder.PRESETS:
            self.transponder_preset_combo.setCurrentText(defaults['transponder_preset'])
            self.on_transponder_preset_changed(defaults['transponder_preset'])

        # Modulation & Coding
        self.modulation_combo.setCurrentText(defaults['modulation'])
        self.coding_combo.setCurrentText(defaults['coding'])

        # ── Unblock signals ─────────────────────────────────────────────────
        self._block_all_signals(False)

        # ── Update orbit model and recalculate ──────────────────────────────
        self.satellite = create_satellite_from_type(sat_type)
        self.calculate_complete_link()
        self._3d_needs_full_rebuild = True
        if HAS_3D:
            self.update_3d_view()
    
    def reset_parameters(self):
        """Reset all parameters to defaults"""
        # Reset stored configs
        self.base_stations = [
            BaseStation(name="Athens GS", latitude=37.9755648, longitude=23.7348324),
        ]
        self.satellite_configs = [
            SatelliteConfig(name="Hotbird 13E", sat_type="GEO", longitude=13.0,
                           band="Ku-band", uplink_freq_ghz=14.25, downlink_freq_ghz=11.725, bandwidth_mhz=36.0),
        ]
        self._3d_needs_full_rebuild = True
        
        # Reset visible combos
        self.link_mode_combo.setCurrentText('Full Link')
        self.uplink_freq_spin.setValue(14.0)
        self.frequency_spin.setValue(12.0)
        self.bandwidth_spin.setValue(36.0)
        self.uplink_rain_spin.setValue(0)
        self.rain_spin.setValue(0)
        self.modulation_combo.setCurrentText('QPSK')
        self.coding_combo.setCurrentText('LDPC (R=3/4)')
        self.pol_loss_spin.setValue(0.2)
        self.water_vapor_spin.setValue(7.5)
        self.cloud_lwc_spin.setValue(0.5)
        self.rain_height_spin.setValue(3.0)
        self.pol_tilt_spin.setValue(45)
        
        # Refresh combos and sync hidden widgets
        self._refresh_combos()
        self._refresh_hub_lists()
        self.calculate_complete_link()
    
    def toggle_animation(self, state):
        """Toggle satellite animation (kept for backward compat)"""
        self.animation_running = bool(state)
        self._update_play_button_icon()

    def _playback_play_pause(self):
        """Toggle play / pause"""
        self.animation_running = not self.animation_running
        if self.animation_running:
            self.animation_direction = 1  # default forward on play
        self._update_play_button_icon()

    def _playback_rewind(self):
        """Play backwards (rewind)"""
        self.animation_direction = -1
        self.animation_running = True
        self._update_play_button_icon()

    def _playback_fast_forward(self):
        """Play forward at current speed"""
        self.animation_direction = 1
        self.animation_running = True
        self._update_play_button_icon()

    def _playback_reset(self):
        """Reset simulation time to zero"""
        self.current_time = 0
        self.animation_running = False
        self._update_play_button_icon()
        self._update_time_display()
        self._3d_needs_full_rebuild = True
        if HAS_3D:
            self.update_3d_view()

    def _on_speed_changed(self, text):
        """Update animation speed multiplier"""
        try:
            multiplier = float(text.replace('x', ''))
            self.animation_speed = 10 * multiplier  # base step = 10 sec sim-time per tick
        except ValueError:
            self.animation_speed = 10

    def _update_play_button_icon(self):
        """Update the play/pause button icon"""
        if not hasattr(self, 'btn_play_pause'):
            return
        if self.animation_running:
            self.btn_play_pause.setText("\u23F8")  # ⏸
            self.btn_play_pause.setToolTip("Pause")
        else:
            self.btn_play_pause.setText("\u25B6")  # ▶
            self.btn_play_pause.setToolTip("Play")

    def _update_time_display(self):
        """Update the elapsed time label"""
        if not hasattr(self, 'time_display_label'):
            return
        try:
            t = self.current_time
            minutes = t / 60.0
            hours = t / 3600.0
            if abs(t) < 3600:
                self.time_display_label.setText(f"T = {t:.0f} s  ({minutes:.1f} min)")
            else:
                self.time_display_label.setText(f"T = {t:.0f} s  ({hours:.2f} h)")
        except RuntimeError:
            pass  # Widget deleted by lazy tab teardown

    def _place_base_station(self):
        """Redirect to the Base Station edit dialog for the currently selected BS1"""
        bs1 = self._get_selected_bs(self.bs1_combo)
        if bs1:
            idx = self.bs1_combo.currentIndex()
            self._edit_base_station(idx)
        else:
            self._add_base_station_dialog()
    
    def show_info_dialog(self):
        """Show info dialog — delegated"""
        _mod_info(self)

    def show_math_details_dialog(self):
        """Show math details — delegated"""
        _mod_math(self)

    def show_advanced_analysis_dialog(self):
        """Display advanced analysis dialog with 8 comprehensive analysis types"""
        if not hasattr(self, 'last_results') or self.last_results is None:
            QMessageBox.warning(self, "No Data", "Please run a calculation first to perform advanced analysis.")
            return
        
        dialog = AdvancedAnalysisDialog(self, self.last_params, self.last_results, self.link_budget)
        dialog.exec()

    def update_realtime(self):
        """Real-time update — tracking cards always refresh, 3D view when animating"""
        if self.animation_running:
            self.current_time += self.animation_speed * self.animation_direction
            # Prevent negative time wrapping below zero (optional: clamp)
            if self.current_time < 0:
                self.current_time = 0
                self.animation_running = False
                self._update_play_button_icon()
            self._update_time_display()
            
            # Check for active tab to update animation
            if hasattr(self, 'viz_tabs'):
                idx = self.viz_tabs.currentIndex()
                label = self.viz_tabs.tabText(idx)
                
                # 3D View Update
                if HAS_3D and label == "3D View":
                    self.update_3d_view()
                
                # Ground Track Update
                elif label == "Ground Track":
                    # Only update if built
                    if self._tab_built.get(idx, False):
                        update_orbit_anim_only(self)
        
        # Always update real-time tracking cards (distance, az, el, Doppler)
        self._update_tracking_cards()

    def _update_play_button_icon(self):
        """Update the play/pause button icon in 3D view AND Ground Track."""
        txt = "\u23F8" if self.animation_running else "\u25B6"  # ⏸ / ▶
        tip = "Pause" if self.animation_running else "Play"
        
        # 3D View Button
        if hasattr(self, 'btn_play_pause'):
            self.btn_play_pause.setText(txt)
            self.btn_play_pause.setToolTip(tip)
            
        # Ground Track Button
        if hasattr(self, 'btn_orbit_play'):
            self.btn_orbit_play.setText(txt)
            self.btn_orbit_play.setToolTip(tip)
    
    def _update_tracking_cards(self):
        """Update tracking cards — delegated"""
        _mod_update_tracking(self)

    # ==================== DASHBOARD & INTERACTIVE FEATURES ====================
    
    def update_dashboard_cards(self, results, params):
        """Update dashboard cards — delegated"""
        _mod_update_dashboard(self, results, params)

    def _add_to_history(self, results, params):
        """Add calculation to history"""
        entry = {
            'timestamp': datetime.now().strftime('%H:%M:%S'),
            'link_mode': params.get('link_mode', 'Full Link'),
            'sat_type': self.sat_type_combo.currentText(),
            'frequency_up': params.get('uplink_frequency_ghz', 0),
            'frequency_dn': params.get('downlink_frequency_ghz', 0),
            'total_margin_db': results.get('total_margin_db', 0),
            'total_cn0_db': results.get('total_cn0_db', 0),
            'total_ebn0_db': results.get('total_ebn0_db', 0),
            'modulation': params.get('modulation', 'QPSK'),
            'coding': params.get('coding', ''),
            'elevation_deg': params.get('elevation_deg', 0),
            'params_snapshot': {k: v for k, v in params.items() if k != 'transponder_summary'},
        }
        self.calculation_history.append(entry)
        # Keep last 50 entries
        if len(self.calculation_history) > 50:
            self.calculation_history = self.calculation_history[-50:]
    
    def pin_current_result(self):
        """Pin the current result for comparison"""
        if not hasattr(self, 'last_results') or self.last_results is None:
            self.statusBar().showMessage(" No result to pin - run a calculation first")
            return
        
        self.pinned_result = {
            'results': self.last_results.copy(),
            'params': {k: v for k, v in self.last_params.items() if k != 'transponder_summary'},
            'timestamp': datetime.now().strftime('%H:%M:%S'),
        }
        self.pin_btn.setText("📌 Pinned!")
        self.pin_btn.setStyleSheet("background-color: #4CAF50; color: white; font-size: 9pt; padding: 6px 12px;")
        self.statusBar().showMessage(f"Result pinned at {self.pinned_result['timestamp']} — change parameters and compare")
        QTimer.singleShot(3000, lambda: (
            self.pin_btn.setText("📌 Pin"),
            self.pin_btn.setProperty('variant', 'outline'),
            self.pin_btn.setStyleSheet("font-size: 9pt; padding: 6px 12px;")
        ))
    
    def show_history_dialog(self):
        """Show history dialog — delegated"""
        _mod_history(self)

    def _export_history_csv(self, parent_dialog=None):
        """Export history to CSV — delegated"""
        _mod_export_hist(self, parent_dialog)

    # ==================== EXPORT & SAVE/LOAD ====================
    
    def export_report(self):
        """Export PDF report — delegated"""
        _mod_export_pdf(self)

    def export_csv(self):
        """Export CSV — delegated"""
        _mod_export_csv(self)

    def copy_results_to_clipboard(self):
        """Copy to clipboard — delegated"""
        _mod_copy_clip(self)

    def save_parameters(self):
        """Save parameters — delegated"""
        _mod_save(self)

    def load_parameters(self):
        """Load parameters — delegated"""
        _mod_load(self)

    def _block_all_signals(self, block):
        """Block/unblock signals from all parameter widgets to prevent multiple recalculations"""
        widgets = [
            self.link_mode_combo, self.sat_type_combo, self.altitude_spin,
            self.gs_lat_spin, self.gs_lon_spin, self.sat_lon_spin, self.sat_lat_spin,
            self.bandwidth_spin, self.uplink_tx_power_spin, self.uplink_antenna_spin,
            self.uplink_freq_spin, self.uplink_rain_spin, self.sat_rx_gain_spin,
            self.sat_nf_spin, self.tx_power_spin, self.tx_gain_spin, self.frequency_spin,
            self.rain_spin, self.gs_diameter_spin, self.lna_temp_spin,
            self.modulation_combo, self.coding_combo, self.feed_loss_spin,
            self.pointing_loss_tx_spin, self.pointing_loss_rx_spin, self.pol_loss_spin, self.ibo_spin, self.obo_spin,
            self.hpa_type_combo, self.antenna_eff_spin, self.cim_spin,
            self.bs1_combo, self.sat_combo, self.bs2_combo,
        ]
        for w in widgets:
            w.blockSignals(block)
    
    def toggle_left_panel(self):
        """Toggle the left parameters panel visibility."""
        if self.left_panel.isVisible():
            # Save current width before hiding
            self._left_panel_last_width = self.main_splitter.sizes()[0]
            self.left_panel.setVisible(False)
            self.toggle_panel_btn.setText("\u25B6 Show Panel")
            self.toggle_panel_btn.setToolTip("Show parameters panel")
        else:
            self.left_panel.setVisible(True)
            # Restore saved width
            total = sum(self.main_splitter.sizes())
            left_w = self._left_panel_last_width or 450
            self.main_splitter.setSizes([left_w, total - left_w])
            self.toggle_panel_btn.setText("\u25C0 Hide Panel")
            self.toggle_panel_btn.setToolTip("Hide parameters panel")
    
    def load_preset(self, preset_name):
        """Load scenario preset — delegated"""
        _mod_preset(self, preset_name)

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Sat-Link")
    app.setApplicationDisplayName("Sat-Link")
    app.setStyle('Fusion')

    icon_path = get_resource_path("satellite_icon.ico")
    if os.path.isfile(icon_path):
        app_icon = QIcon(icon_path)
        app.setWindowIcon(app_icon)
    else:
        app_icon = None

    # Show splash screen
    splash_pix = create_splash_screen()
    splash = QSplashScreen(splash_pix)
    splash.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
    splash.show()

    # Process events to show splash immediately
    app.processEvents()

    # Simulate loading time
    QTimer.singleShot(2000, lambda: None)
    for i in range(20):
        QTimer.singleShot(i * 100, lambda: app.processEvents())

    # Create and show main window
    window = SatelliteSimulatorGUIAdvanced()
    if app_icon is not None:
        window.setWindowIcon(app_icon)

    # Close splash and show window
    QTimer.singleShot(2000, lambda: (splash.close(), window.show()))

    sys.exit(app.exec())


if __name__ == '__main__':
    main()
