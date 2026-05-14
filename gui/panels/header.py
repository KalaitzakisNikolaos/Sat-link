"""Header panel with gradient toolbar and action buttons.

Every function takes `mw` (the main window instance) as its first parameter
so it can access and set attributes on the QMainWindow.
"""
import os
from PyQt5.QtWidgets import (QWidget, QHBoxLayout, QLabel, QPushButton,
                              QMenu, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QKeySequence, QPixmap


def create_header(mw):
    """Create gradient header with toolbar and action buttons."""
    header = QWidget()
    header.setFixedHeight(64)
    header.setStyleSheet("""
        QWidget {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #4f46e5, stop:0.4 #7c3aed, stop:0.8 #6366f1, stop:1 #4f46e5);
            border-radius: 16px;
        }
    """)
    layout = QHBoxLayout(header)
    layout.setContentsMargins(20, 8, 20, 8)

    title = QLabel("Sat-Link")
    title.setFont(QFont("Segoe UI", 17, QFont.Weight.Bold))
    title.setStyleSheet("color: white; background: transparent; letter-spacing: 1px;")
    layout.addWidget(title)

    subtitle = QLabel("ITU-R Compliant Link Budget Analysis")
    subtitle.setFont(QFont("Segoe UI", 9))
    subtitle.setStyleSheet("color: rgba(255,255,255,0.7); background: transparent; font-weight: 400;")
    layout.addWidget(subtitle)

    layout.addStretch()

    # Toolbar button style
    btn_style = """
        QPushButton {
            font-size: 9pt;
            padding: 7px 14px;
            background-color: rgba(255, 255, 255, 0.15);
            color: white;
            border: 1px solid rgba(255, 255, 255, 0.25);
            border-radius: 10px;
            font-weight: 600;
            min-height: 16px;
        }
        QPushButton:hover {
            background-color: rgba(255, 255, 255, 0.25);
            border: 1px solid rgba(255, 255, 255, 0.4);
        }
        QPushButton:pressed {
            background-color: rgba(255, 255, 255, 0.1);
        }
        QPushButton::menu-indicator {
            subcontrol-position: right center;
            subcontrol-origin: padding;
            right: 6px;
        }
    """

    # Presets dropdown
    mw.presets_btn = QPushButton("\U0001F4CB Presets")
    mw.presets_btn.setStyleSheet(btn_style)
    mw.presets_btn.setToolTip("Manage scenario presets")
    
    # Initialize menu
    rebuild_presets_menu(mw)
    
    layout.addWidget(mw.presets_btn)

    # Export button
    export_btn = QPushButton("\U0001F4E4 Export")
    export_btn.setStyleSheet(btn_style)
    export_btn.setToolTip("Export report (Ctrl+E)")
    export_menu = QMenu(mw)
    export_menu.addAction("Export PDF Report", mw.export_report)
    export_menu.addAction("Export CSV Data", mw.export_csv)
    export_menu.addAction("Copy Results to Clipboard", mw.copy_results_to_clipboard)
    export_btn.setMenu(export_menu)
    layout.addWidget(export_btn)

    # Pin/Compare button
    mw.pin_btn = QPushButton("\U0001F4CC Pin")
    mw.pin_btn.setStyleSheet(btn_style)
    mw.pin_btn.setToolTip("Pin current result for comparison (Ctrl+P)")
    mw.pin_btn.clicked.connect(mw.pin_current_result)
    layout.addWidget(mw.pin_btn)

    # History button
    history_btn = QPushButton("\U0001F4DC History")
    history_btn.setStyleSheet(btn_style)
    history_btn.setToolTip("View calculation history (Ctrl+H)")
    history_btn.clicked.connect(mw.show_history_dialog)
    layout.addWidget(history_btn)

    # Toggle left panel button
    mw.toggle_panel_btn = QPushButton("\u25C0 Hide Panel")
    mw.toggle_panel_btn.setStyleSheet(btn_style)
    mw.toggle_panel_btn.setToolTip("Show / Hide parameters panel")
    mw.toggle_panel_btn.clicked.connect(mw.toggle_left_panel)
    layout.addWidget(mw.toggle_panel_btn)

    # Separator - subtle vertical line
    sep = QFrame()
    sep.setFrameShape(QFrame.Shape.VLine)
    sep.setFixedWidth(1)
    sep.setStyleSheet("background-color: rgba(255,255,255,0.2); border: none;")
    layout.addWidget(sep)

    # Accent style buttons
    accent_style = """
        QPushButton {
            font-size: 9pt;
            padding: 7px 14px;
            background-color: rgba(16, 185, 129, 0.3);
            color: #d1fae5;
            border: 1px solid rgba(16, 185, 129, 0.4);
            border-radius: 10px;
            font-weight: 600;
            min-height: 16px;
        }
        QPushButton:hover {
            background-color: rgba(16, 185, 129, 0.45);
            border: 1px solid rgba(52, 211, 153, 0.6);
            color: white;
        }
    """

    # Info button
    info_btn = QPushButton("\u2139\uFE0F Info")
    info_btn.setStyleSheet(accent_style)
    info_btn.clicked.connect(mw.show_info_dialog)
    layout.addWidget(info_btn)

    # Math Details button
    math_btn = QPushButton("\U0001F4CA Math")
    math_btn.setStyleSheet(btn_style)
    math_btn.clicked.connect(mw.show_math_details_dialog)
    layout.addWidget(math_btn)

    # Advanced analysis button
    advanced_style = """
        QPushButton {
            font-size: 9pt;
            padding: 7px 14px;
            background-color: rgba(249, 115, 22, 0.3);
            color: #fed7aa;
            border: 1px solid rgba(249, 115, 22, 0.4);
            border-radius: 10px;
            font-weight: 600;
            min-height: 16px;
        }
        QPushButton:hover {
            background-color: rgba(249, 115, 22, 0.45);
            border: 1px solid rgba(251, 146, 60, 0.6);
            color: white;
        }
    """
    advanced_btn = QPushButton("\U0001F52C Advanced")
    advanced_btn.setStyleSheet(advanced_style)
    advanced_btn.clicked.connect(mw.show_advanced_analysis_dialog)
    layout.addWidget(advanced_btn)

    # Hide/Show metrics toggle
    mw.metrics_btn = QPushButton("\U0001F4C9 Hide Metrics")
    mw.metrics_btn.setStyleSheet(btn_style)
    mw.metrics_btn.setToolTip("Show/hide the dashboard & tracking cards (Ctrl+M)")
    mw.metrics_btn.setShortcut(QKeySequence("Ctrl+M"))
    mw.metrics_btn.clicked.connect(lambda: toggle_metrics_visibility(mw))
    layout.addWidget(mw.metrics_btn)

    # University logo - top right
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logo_path = os.path.join(base_dir, "hmu.png")
    logo_pix = QPixmap(logo_path)
    if not logo_pix.isNull():
        logo_label = QLabel()
        scaled_logo = logo_pix.scaled(40, 40,
                                       Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(scaled_logo)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("background: transparent; border: none; margin-left: 8px;")
        logo_label.setFixedSize(48, 48)
        layout.addWidget(logo_label)
        layout.addSpacing(4)

    return header


def toggle_metrics_visibility(mw):
    """Toggle visibility of the dashboard and tracking card rows."""
    visible = mw.dashboard_widget.isVisible()
    mw.dashboard_widget.setVisible(not visible)
    mw.tracking_widget.setVisible(not visible)
    if visible:
        mw.metrics_btn.setText("\U0001F4C8 Show Metrics")
    else:
        mw.metrics_btn.setText("\U0001F4C9 Hide Metrics")


def rebuild_presets_menu(mw):
    """Dynamically rebuild the presets menu (Built-in + User)."""
    from gui.utils.presets import (load_user_presets, load_preset, 
                                   save_current_as_preset, delete_user_preset,
                                   BUILTIN_DISPLAY_NAMES)

    menu = QMenu(mw)
    
    # 1. Built-in Presets
    menu.addSection("System Presets")
    for key, name in BUILTIN_DISPLAY_NAMES.items():
        menu.addAction(name, lambda checked=False, k=key: load_preset(mw, k, is_user_preset=False))
        
    # 2. User Presets
    user_presets = load_user_presets()
    if user_presets:
        menu.addSeparator()
        menu.addSection("My Presets")
        for name in user_presets.keys():
            menu.addAction(f"\U0001f4be {name}", lambda checked=False, n=name: load_preset(mw, n, is_user_preset=True))
            
    menu.addSeparator()
    
    # 3. Actions
    menu.addAction("\u2795 Save Current as Preset...", lambda checked=False: save_current_as_preset(mw))
    
    # Delete submenu
    if user_presets:
        del_menu = menu.addMenu("\U0001f5d1 Delete Preset")
        for name in user_presets.keys():
            del_menu.addAction(name, lambda checked=False, n=name: delete_user_preset(mw, n))
            
    menu.addSeparator()
    menu.addAction("\U0001f4c2 Load from File...", mw.load_parameters)
    
    mw.presets_btn.setMenu(menu)
