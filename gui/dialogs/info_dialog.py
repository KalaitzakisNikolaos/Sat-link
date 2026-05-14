"""
Info dialog module — shows application information with university logo,
authors, version, description, and license.
"""
import os
import sys
import platform
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                              QPushButton, QFrame, QScrollArea, QWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPixmap


def show_info_dialog(mw):
    """Display a polished, information-rich About dialog."""
    dlg = QDialog(mw)
    dlg.setWindowTitle("About — Satellite Link Simulator")
    dlg.setFixedSize(600, 750)
    dlg.setStyleSheet("""
        QDialog {
            background-color: #ffffff;
            border-radius: 12px;
        }
        QScrollArea {
            border: none;
            background: transparent;
        }
        QScrollBar:vertical {
            background: #f1f5f9;
            width: 8px;
            margin: 0px;
            border-radius: 4px;
        }
        QScrollBar::handle:vertical {
            background: #cbd5e1;
            min-height: 20px;
            border-radius: 4px;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
    """)

    main_layout = QVBoxLayout(dlg)
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)

    # ── HEADER HEADER ───────────────────────────────────────────────
    # A soft purple gradient header
    header = QFrame()
    header.setFixedHeight(140)
    header.setStyleSheet("""
        QFrame {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #4f46e5, stop:1 #7c3aed);
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
            border-bottom-left-radius: 0px;
            border-bottom-right-radius: 0px;
        }
    """)
    header_layout = QHBoxLayout(header)
    header_layout.setContentsMargins(24, 0, 24, 0)
    header_layout.setSpacing(20)

    # Logo
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    logo_path = os.path.join(base_dir, "hmu.png")
    logo_pix = QPixmap(logo_path)
    
    if not logo_pix.isNull():
        logo_label = QLabel()
        # White circle container for logo
        logo_label.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.95);
            border-radius: 40px;
            padding: 5px;
        """)
        logo_label.setFixedSize(80, 80)
        scaled = logo_pix.scaled(70, 70,
                                  Qt.AspectRatioMode.KeepAspectRatio,
                                  Qt.TransformationMode.SmoothTransformation)
        logo_label.setPixmap(scaled)
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(logo_label)

    # Types + Version
    titles_layout = QVBoxLayout()
    titles_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)
    titles_layout.setSpacing(4)
    
    app_title = QLabel("Satellite Link Simulator")
    app_title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
    app_title.setStyleSheet("color: #ffffff; background: transparent;")
    
    app_ver = QLabel("Professional Edition v3.0")
    app_ver.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
    app_ver.setStyleSheet("""
        color: #e0e7ff; 
        background-color: rgba(255,255,255,0.2); 
        padding: 4px 12px;
        border-radius: 12px;
    """)
    app_ver.adjustSize()
    
    titles_layout.addWidget(app_title)
    titles_layout.addWidget(app_ver, 0, Qt.AlignmentFlag.AlignLeft)
    header_layout.addLayout(titles_layout)
    header_layout.addStretch()

    main_layout.addWidget(header)

    # ── SCROLLABLE CONTENT ──────────────────────────────────────────
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    
    content_widget = QWidget()
    content_widget.setStyleSheet("background-color: #ffffff;")
    content_layout = QVBoxLayout(content_widget)
    content_layout.setContentsMargins(32, 24, 32, 24)
    content_layout.setSpacing(20)

    # -- Description --
    desc_label = QLabel(
        "A comprehensive tool for end-to-end satellite link budget analysis, "
        "designed for academic and professional use. Compliant with ITU-R standards."
    )
    desc_label.setWordWrap(True)
    desc_label.setStyleSheet("color: #334155; font-size: 11pt; line-height: 1.4;")
    desc_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
    content_layout.addWidget(desc_label)

    # -- Helper to create "Cards" --
    def create_section(title, content_list=None, text_content=None, icon=None):
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background-color: #f8fafc;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
            }
        """)
        cl = QVBoxLayout(card)
        cl.setContentsMargins(20, 16, 20, 16)
        cl.setSpacing(10)
        
        # Title
        header_row = QHBoxLayout()
        if icon:
            ic_lbl = QLabel(icon)
            ic_lbl.setStyleSheet("border: none; font-size: 14pt;")
            header_row.addWidget(ic_lbl)
            
        t_lbl = QLabel(title)
        t_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        t_lbl.setStyleSheet("color: #4f46e5; border: none;")
        header_row.addWidget(t_lbl)
        header_row.addStretch()
        cl.addLayout(header_row)
        
        # Content
        if content_list:
            for item in content_list:
                row = QHBoxLayout()
                row.setSpacing(10)
                bullet = QLabel("•")
                bullet.setStyleSheet("color: #818cf8; font-size: 14pt; border: none;")
                txt = QLabel(item)
                txt.setStyleSheet("color: #475569; font-size: 10pt; border: none;")
                txt.setWordWrap(True)
                row.addWidget(bullet, 0, Qt.AlignmentFlag.AlignTop)
                row.addWidget(txt, 1)
                cl.addLayout(row)
        elif text_content:
            txt = QLabel(text_content)
            txt.setStyleSheet("color: #475569; font-size: 10pt; border: none;")
            txt.setWordWrap(True)
            cl.addWidget(txt)
            
        return card

    # -- Key Features --
    features = [
        "ITU-R P.618-13 Rain Attenuation Models",
        "Full Uplink & Downlink Budget Calculation",
        "Visual Link Waterfalls & Carrier-over-Noise Charts",
        "Support for GEO, MEO, LEO & HEO Orbits",
        "Adaptive Modulation & Coding (ACM) Analysis"
    ]
    content_layout.addWidget(create_section("Key Capabilities", features, icon="✨"))

    # -- Tech Stack (Grid) --
    tech_card = QFrame()
    tech_card.setStyleSheet("""
        QFrame {
            background-color: #fefeff;
            border: 1px solid #e0e7ff;
            border-radius: 12px;
        }
    """)
    tc_layout = QVBoxLayout(tech_card)
    tc_layout.setContentsMargins(20, 16, 20, 16)
    
    tc_title = QLabel("🛠️  Technical Stack")
    tc_title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
    tc_title.setStyleSheet("color: #4f46e5; border: none;")
    tc_layout.addWidget(tc_title)
    tc_layout.addSpacing(10)
    
    libraries = [
        ("Python", platform.python_version()),
        ("Qt Framework", "PyQt5"),
        ("Mathematics", "NumPy & SciPy"),
        ("Data Analysis", "Pandas"),
        ("Visualization", "Matplotlib & PyQtGraph")
    ]
    
    grid = QVBoxLayout()
    grid.setSpacing(6)
    for lib, ver in libraries:
        row = QHBoxLayout()
        l_lbl = QLabel(lib)
        l_lbl.setStyleSheet("color: #334155; font-weight: 600; border: none;")
        v_lbl = QLabel(ver)
        v_lbl.setStyleSheet("color: #64748b; border: none;")
        row.addWidget(l_lbl)
        row.addStretch()
        row.addWidget(v_lbl)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #f1f5f9; border: none; max-height: 1px;")
        
        grid.addLayout(row)
        grid.addWidget(line)
        
    tc_layout.addLayout(grid)
    content_layout.addWidget(tech_card)

    # -- Credits --
    credits_content = (
        "<p style='margin-bottom: 5px'>Developed by:</p>"
        "<h3 style='margin: 0; color: #334155'>Kalaitzakis Nikolaos</h3>"
        "<h3 style='margin: 0; color: #334155'>Papoudakis Ioannis</h3>"
        "<h3 style='margin: 0; color: #334155'>Kontos Alexandros</h3>"
        "<br>"
        "Department of Electronic and Computer Engineering<br>"
        "<b>Hellenic Mediterranean University (HMU)</b>"
    )
    credits_card = create_section("Credits", text_content=None, icon="🎓")
    # Custom label for HTML support
    c_lbl = QLabel(credits_content)
    c_lbl.setStyleSheet("color: #475569; font-size: 10pt; border: none;")
    c_lbl.setWordWrap(True)
    credits_card.layout().addWidget(c_lbl)
    
    content_layout.addWidget(credits_card)

    content_layout.addStretch()
    scroll.setWidget(content_widget)
    main_layout.addWidget(scroll)

    # ── FOOTER ──────────────────────────────────────────────────────
    footer = QFrame()
    footer.setStyleSheet("background-color: #f8fafc; border-top: 1px solid #e2e8f0;")
    footer_layout = QHBoxLayout(footer)
    footer_layout.setContentsMargins(24, 16, 24, 16)

    # License text tiny
    lic_lbl = QLabel("© 2026 HMU • MIT License")
    lic_lbl.setStyleSheet("color: #94a3b8; font-size: 9pt;")
    footer_layout.addWidget(lic_lbl)
    
    footer_layout.addStretch()

    close_btn = QPushButton("Close")
    close_btn.setFixedWidth(100)
    close_btn.setStyleSheet("""
        QPushButton {
            background-color: #4f46e5;
            color: white;
            border-radius: 8px;
            padding: 8px 16px;
            font-weight: 600;
        }
        QPushButton:hover {
            background-color: #4338ca;
        }
    """)
    close_btn.clicked.connect(dlg.accept)
    footer_layout.addWidget(close_btn)

    main_layout.addWidget(footer)

    dlg.exec()
