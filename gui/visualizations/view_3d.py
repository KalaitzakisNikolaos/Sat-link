"""3D Earth view with satellite orbits, ground stations and TLE import."""

import numpy as np
import urllib.request
import json
try:
    import sip
except ImportError:
    sip = None

try:
    import pyvista as pv
    from gui.earth_3d import Earth3DVisualization, _geodetic_to_cartesian_wgs84
    from models.constants import EARTH_RADIUS
    HAS_3D = True
except ImportError:
    HAS_3D = False

_SAT_COLORS = ['red', '#FF4081', '#E040FB', '#7C4DFF', '#536DFE', '#448AFF']
_GS_COLORS = ['green', '#00E676', '#76FF03', '#64FFDA', '#18FFFF', '#40C4FF']
_TLE_COLORS = ['#22d3ee', '#a78bfa', '#f472b6', '#facc15', '#34d399', '#fb923c']


def _widget_alive(widget):
    """Check if a Qt widget's C++ side still exists."""
    if widget is None:
        return False
    if sip is not None:
        try:
            return not sip.isdeleted(widget)
        except Exception:
            pass
    try:
        widget.isVisible()
        return True
    except RuntimeError:
        return False


def _place_sat(plotter, pos, radius_frac, color, name, label=None, label_name=None):
    """Add a satellite sphere (and optional label) to the plotter."""
    sphere = pv.Sphere(radius=EARTH_RADIUS * radius_frac, center=pos)
    plotter.add_mesh(sphere, color=color, opacity=1.0, name=name)
    if label and label_name:
        plotter.add_point_labels(
            [pos], [label], font_size=20, text_color='yellow', name=label_name)


# tab creation ─────────────────────────────────────────────────────────────

def create_3d_tab(mw):
    """3D globe with overlay playback controls and visibility toggles."""
    from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                                 QPushButton, QLabel, QComboBox, QCheckBox,
                                 QFrame)
    from PyQt5.QtCore import Qt

    if not HAS_3D:
        fallback = QWidget()
        QVBoxLayout(fallback).addWidget(QLabel("3D visualization not available (install pyvista)"))
        return fallback

    from models.orbit import create_satellite_from_type

    container = QWidget()
    lay = QVBoxLayout(container)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(0)

    mw.earth_3d = Earth3DVisualization()
    lay.addWidget(mw.earth_3d)

    # visibility toggle panel (top-right overlay)
    mw._3d_vis_panel = QFrame(container)
    mw._3d_vis_panel.setFrameShape(QFrame.Shape.NoFrame)
    mw._3d_vis_panel.setStyleSheet("""
        QFrame#visPanel {
            background: rgba(20, 20, 30, 0.92);
            border-radius: 10px;
        }
        QCheckBox {
            color: rgba(255,255,255,0.9);
            font-size: 8pt; font-weight: 600; spacing: 5px;
            background: transparent;
        }
        QCheckBox::indicator {
            width: 14px; height: 14px;
            border: 2px solid rgba(255,255,255,0.4);
            border-radius: 4px;
            background: rgba(255,255,255,0.1);
        }
        QCheckBox::indicator:checked {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                stop:0 #6366f1, stop:1 #8b5cf6);
            border-color: #6366f1;
        }
        QCheckBox::indicator:hover { border-color: #818cf8; }
        QLabel { color: rgba(255,255,255,0.7); font-size: 7pt; font-weight: 700;
                 background: transparent; letter-spacing: 1px; }
    """)
    mw._3d_vis_panel.setObjectName("visPanel")
    vl = QVBoxLayout(mw._3d_vis_panel)
    vl.setContentsMargins(10, 8, 10, 8)
    vl.setSpacing(3)

    vis_title = QLabel("\U0001f441 VISIBILITY")
    vis_title.setStyleSheet("color: rgba(255,255,255,0.9); font-size: 8pt; font-weight: 700; background: transparent;")
    vl.addWidget(vis_title)

    mw._3d_vis_cb_container = QWidget()
    mw._3d_vis_cb_container.setStyleSheet("background: transparent;")
    mw._3d_vis_cb_layout = QVBoxLayout(mw._3d_vis_cb_container)
    mw._3d_vis_cb_layout.setContentsMargins(0, 0, 0, 0)
    mw._3d_vis_cb_layout.setSpacing(2)
    vl.addWidget(mw._3d_vis_cb_container)

    mw._3d_vis_panel.raise_()
    mw._3d_bs_visible = {}
    mw._3d_sat_visible = {}

    # playback overlay
    overlay = QFrame(container)
    overlay.setFixedHeight(80)
    overlay.setFrameShape(QFrame.Shape.NoFrame)
    overlay.setObjectName("playbackOverlay")
    overlay.setStyleSheet("QFrame#playbackOverlay { background: rgba(20, 20, 30, 0.92); border-radius: 10px; }")
    ol = QVBoxLayout(overlay)
    ol.setContentsMargins(12, 6, 12, 8)
    ol.setSpacing(4)

    btn_css = """
        QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 rgba(255,255,255,0.85), stop:0.5 rgba(230,230,245,0.75),
                stop:1 rgba(200,200,220,0.65));
            color: #1e293b; border: 1px solid rgba(255,255,255,0.6);
            border-bottom: 2px solid rgba(0,0,0,0.15); border-radius: 8px;
            font-size: 13pt; font-weight: 700;
            min-width: 38px; min-height: 34px; max-width: 38px; max-height: 34px;
            padding: 0px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 rgba(255,255,255,0.95), stop:1 rgba(220,220,240,0.85));
            border: 1px solid rgba(99,102,241,0.5);
        }
        QPushButton:pressed {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 rgba(180,180,200,0.7), stop:1 rgba(210,210,230,0.8));
            border-bottom: 1px solid rgba(0,0,0,0.1); padding-top: 1px;
        }
    """

    btn_row = QHBoxLayout()
    btn_row.setSpacing(6)

    for icon, tip, cb in [
        ("\u23EA", "Rewind", lambda: _playback_rewind(mw)),
        ("\u25B6", "Play / Pause", lambda: _playback_play_pause(mw)),
        ("\u23E9", "Fast-forward", lambda: _playback_fast_forward(mw)),
        ("\u23EE", "Reset to t = 0", lambda: _playback_reset(mw)),
    ]:
        b = QPushButton(icon)
        b.setToolTip(tip)
        b.setStyleSheet(btn_css)
        b.clicked.connect(cb)
        btn_row.addWidget(b)
        if icon == "\u25B6":
            mw.btn_play_pause = b

    btn_row.addSpacing(12)

    speed_lbl = QLabel("Speed")
    speed_lbl.setStyleSheet("color: rgba(255,255,255,0.9); font-weight: 700; font-size: 8pt; background: transparent;")
    btn_row.addWidget(speed_lbl)
    mw.speed_combo = QComboBox()
    mw.speed_combo.addItems(["0.1x", "0.5x", "1x", "2x", "5x", "10x", "50x"])
    mw.speed_combo.setCurrentText("1x")
    mw.speed_combo.setFixedWidth(70)
    mw.speed_combo.setStyleSheet("""
        QComboBox {
            background: rgba(255,255,255,0.8); border: 1px solid rgba(255,255,255,0.5);
            border-radius: 6px; padding: 4px 6px; font-size: 8pt; font-weight: 600; color: #1e293b;
        }
        QComboBox::drop-down { border: none; width: 18px; }
        QComboBox QAbstractItemView {
            background: white; border: 1px solid #e2e8f0; border-radius: 6px;
            selection-background-color: #eef2ff;
        }
    """)
    mw.speed_combo.currentTextChanged.connect(lambda t: _on_speed_changed(mw, t))
    btn_row.addWidget(mw.speed_combo)

    btn_row.addSpacing(12)

    tle_css = """
        QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #06b6d4, stop:1 #0891b2);
            color: white; border: none; border-radius: 8px;
            font-size: 8pt; font-weight: 700; padding: 6px 14px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #22d3ee, stop:1 #06b6d4);
        }
        QPushButton:pressed { background: #0e7490; }
    """
    mw.btn_import_tle = QPushButton("\U0001f6f0 Import TLE")
    mw.btn_import_tle.setToolTip("Import satellite from Two-Line Element (CelesTrak / NORAD)")
    mw.btn_import_tle.setStyleSheet(tle_css)
    mw.btn_import_tle.clicked.connect(lambda: _show_tle_dialog(mw))
    btn_row.addWidget(mw.btn_import_tle)

    btn_row.addStretch()
    ol.addLayout(btn_row)

    mw.time_display_label = QLabel("T = 0 s  (0.0 min)")
    mw.time_display_label.setStyleSheet(
        "font-family: 'Consolas', 'JetBrains Mono', monospace; font-size: 8pt;"
        " font-weight: 600; color: rgba(255,255,255,0.9); background: transparent;")
    ol.addWidget(mw.time_display_label)

    overlay.raise_()
    mw._3d_overlay = overlay
    mw._3d_container = container

    if not hasattr(mw, '_tle_satellites'):
        mw._tle_satellites = []
        mw._tle_visible = {}

    mw._3d_needs_full_rebuild = True
    _rebuild_3d_visibility_panel(mw)

    container.resizeEvent = lambda e: _reposition_3d_overlay(mw, e)
    return container


# overlay repositioning

def _reposition_3d_overlay(mw, event):
    """Pin playback overlay bottom-left, visibility panel top-right."""
    if hasattr(mw, '_3d_overlay') and hasattr(mw, '_3d_container'):
        if not _widget_alive(mw._3d_container):
            return
        w = mw._3d_container.width()
        h = mw._3d_container.height()
        ov = mw._3d_overlay
        if not _widget_alive(ov):
            return
        ov.setFixedWidth(min(420, w - 16))
        ov.move(8, h - ov.height() - 8)
    if hasattr(mw, '_3d_vis_panel') and hasattr(mw, '_3d_container'):
        if not _widget_alive(mw._3d_container) or not _widget_alive(mw._3d_vis_panel):
            return
        w = mw._3d_container.width()
        vp = mw._3d_vis_panel
        vp.adjustSize()
        vp_w = max(vp.sizeHint().width(), 160)
        vp.setFixedWidth(vp_w)
        vp.move(w - vp_w - 10, 10)


# visibility panel

def _rebuild_3d_visibility_panel(mw):
    """Rebuild visibility checkboxes to match current BS/Sat lists."""
    from PyQt5.QtWidgets import QCheckBox, QLabel
    from PyQt5.QtCore import Qt

    if not hasattr(mw, '_3d_vis_cb_layout'):
        return
    if not _widget_alive(mw._3d_vis_cb_container):
        return
    try:
        while mw._3d_vis_cb_layout.count():
            item = mw._3d_vis_cb_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
    except RuntimeError:
        return

    old_bs = dict(mw._3d_bs_visible) if hasattr(mw, '_3d_bs_visible') else {}
    old_sat = dict(mw._3d_sat_visible) if hasattr(mw, '_3d_sat_visible') else {}
    mw._3d_bs_visible = {}
    mw._3d_sat_visible = {}
    mw._3d_vis_checkboxes_bs = {}
    mw._3d_vis_checkboxes_sat = {}

    def _section(label, color):
        h = QLabel(label)
        h.setStyleSheet(f"color: {color}; font-size: 7pt; font-weight: 700; background: transparent; letter-spacing: 1px; margin-top: 2px;")
        mw._3d_vis_cb_layout.addWidget(h)

    _section("BASE STATIONS", "#10b981")
    for i, bs in enumerate(mw.base_stations):
        cb = QCheckBox(f"\U0001f4cd {bs.name}")
        vis = old_bs.get(i, True)
        cb.setChecked(vis)
        mw._3d_bs_visible[i] = vis
        cb.stateChanged.connect(lambda state, idx=i: _on_vis_changed(mw, 'bs', idx, state))
        mw._3d_vis_cb_layout.addWidget(cb)
        mw._3d_vis_checkboxes_bs[i] = cb

    _section("SATELLITES", "#f59e0b")
    for j, sc in enumerate(mw.satellite_configs):
        cb = QCheckBox(f"\U0001f6f0 {sc.name}")
        vis = old_sat.get(j, True)
        cb.setChecked(vis)
        mw._3d_sat_visible[j] = vis
        cb.stateChanged.connect(lambda state, idx=j: _on_vis_changed(mw, 'sat', idx, state))
        mw._3d_vis_cb_layout.addWidget(cb)
        mw._3d_vis_checkboxes_sat[j] = cb

    tle_sats = getattr(mw, '_tle_satellites', [])
    if tle_sats:
        _section("TLE IMPORTS", "#22d3ee")
        old_tle = dict(getattr(mw, '_tle_visible', {}))
        mw._tle_visible = {}
        mw._3d_vis_checkboxes_tle = {}
        for k, td in enumerate(tle_sats):
            cb = QCheckBox(f"\U0001f6f0 {td['name']}")
            vis = old_tle.get(k, True)
            cb.setChecked(vis)
            mw._tle_visible[k] = vis
            cb.stateChanged.connect(lambda state, idx=k: _on_vis_changed(mw, 'tle', idx, state))
            mw._3d_vis_cb_layout.addWidget(cb)
            mw._3d_vis_checkboxes_tle[k] = cb

    mw._3d_vis_panel.adjustSize()
    if hasattr(mw, '_3d_container') and _widget_alive(mw._3d_container):
        _reposition_3d_overlay(mw, None)


def _on_vis_changed(mw, kind, index, state):
    from PyQt5.QtCore import Qt
    checked = (state == Qt.CheckState.Checked.value if hasattr(Qt.CheckState.Checked, 'value')
               else state == 2)
    if kind == 'bs':
        mw._3d_bs_visible[index] = checked
    elif kind == 'tle':
        mw._tle_visible[index] = checked
    else:
        mw._3d_sat_visible[index] = checked
    mw._3d_needs_full_rebuild = True
    update_3d_view(mw)


# playback controls

def _playback_play_pause(mw):
    mw.animation_running = not mw.animation_running
    if mw.animation_running:
        mw.animation_direction = 1
    _update_play_btn(mw)


def _playback_rewind(mw):
    mw.animation_direction = -1
    mw.animation_running = True
    _update_play_btn(mw)


def _playback_fast_forward(mw):
    mw.animation_direction = 1
    mw.animation_running = True
    _update_play_btn(mw)


def _playback_reset(mw):
    mw.current_time = 0
    mw.animation_running = False
    _update_play_btn(mw)
    _update_time_label(mw)
    mw._3d_needs_full_rebuild = True
    if HAS_3D:
        update_3d_view(mw)


def _on_speed_changed(mw, text):
    try:
        mw.animation_speed = 10 * float(text.replace('x', ''))
    except ValueError:
        mw.animation_speed = 10


def _update_play_btn(mw):
    if mw.animation_running:
        mw.btn_play_pause.setText("\u23F8")
        mw.btn_play_pause.setToolTip("Pause")
    else:
        mw.btn_play_pause.setText("\u25B6")
        mw.btn_play_pause.setToolTip("Play")


def _update_time_label(mw):
    t = mw.current_time
    if abs(t) < 3600:
        mw.time_display_label.setText(f"T = {t:.0f} s  ({t/60:.1f} min)")
    else:
        mw.time_display_label.setText(f"T = {t:.0f} s  ({t/3600:.2f} h)")


# main 3D update

def update_3d_view(mw):
    """Full rebuild or lightweight animation tick."""
    if not HAS_3D or not hasattr(mw, 'earth_3d'):
        return
    if not _widget_alive(mw.earth_3d):
        return

    try:
        if not hasattr(mw, '_sat_orbits') or mw._sat_orbits is None:
            mw._3d_needs_full_rebuild = True
    except Exception:
        mw._3d_needs_full_rebuild = True

    from models.orbit import create_satellite_from_type

    bs1 = mw._get_selected_bs(mw.bs1_combo)
    sat_cfg = mw._get_selected_satellite_config()
    bs2 = mw._get_selected_bs(mw.bs2_combo)
    sat_idx = mw.sat_combo.currentIndex()

    if mw._3d_needs_full_rebuild:
        mw._3d_needs_full_rebuild = False

        if (not hasattr(mw, '_3d_bs_visible') or
                len(mw._3d_bs_visible) != len(mw.base_stations) or
                len(mw._3d_sat_visible) != len(mw.satellite_configs)):
            _rebuild_3d_visibility_panel(mw)

        try:
            saved_cam = mw.earth_3d.plotter.camera_position
        except Exception:
            saved_cam = None

        mw.earth_3d.clear_dynamic_actors()
        anim_names = ['_anim_uplink', '_anim_downlink']
        for j in range(len(mw.satellite_configs)):
            anim_names += [f'_anim_sat_{j}', f'_anim_sat_label_{j}']
        for n in anim_names:
            try:
                mw.earth_3d.plotter.remove_actor(n)
            except Exception:
                pass

        mw._sat_orbits = {}
        for j, sc in enumerate(mw.satellite_configs):
            try:
                mw._sat_orbits[j] = create_satellite_from_type(
                    sc.sat_type, getattr(sc, 'longitude', 0))
            except Exception:
                mw._sat_orbits[j] = None

        for i, bs in enumerate(mw.base_stations):
            if not mw._3d_bs_visible.get(i, True):
                continue
            mw.earth_3d.add_ground_station(
                bs.latitude, bs.longitude, getattr(bs, 'height_km', 0),
                label=bs.name, color=_GS_COLORS[i % len(_GS_COLORS)])

        mw._sat_positions = {}
        for j, sc in enumerate(mw.satellite_configs):
            if not mw._3d_sat_visible.get(j, True):
                continue
            orb = mw._sat_orbits.get(j)
            if orb is not None:
                sat_pos = orb.get_satellite_position_eci(mw.current_time)
                try:
                    times = np.linspace(0, orb.orbital_period * 60, 100)
                    positions = [orb.get_satellite_position_eci(t) for t in times]
                    mw.earth_3d.add_orbit_trace(positions, color='yellow')
                except Exception:
                    pass
            else:
                sat_pos = _geodetic_to_cartesian_wgs84(
                    sc.latitude, sc.longitude, sc.altitude_km).tolist()

            mw._sat_positions[j] = sat_pos
            color = _SAT_COLORS[j % len(_SAT_COLORS)]
            _place_sat(mw.earth_3d.plotter, sat_pos, 0.02, color,
                       f'_anim_sat_{j}', sc.name, f'_anim_sat_label_{j}')

        _draw_link_lines(mw, sat_cfg, sat_idx, bs1, bs2)
        _draw_tle_satellites(mw)

        if saved_cam is not None:
            try:
                mw.earth_3d.plotter.camera_position = saved_cam
            except Exception:
                pass
        return

    # lightweight animation tick
    if not hasattr(mw, '_sat_orbits'):
        return

    for j, sc in enumerate(mw.satellite_configs):
        orb = mw._sat_orbits.get(j)
        if orb is None:
            continue
        if not mw._3d_sat_visible.get(j, True):
            for n in [f'_anim_sat_{j}', f'_anim_sat_label_{j}']:
                try:
                    mw.earth_3d.plotter.remove_actor(n)
                except Exception:
                    pass
            continue

        sat_pos = orb.get_satellite_position_eci(mw.current_time)
        color = _SAT_COLORS[j % len(_SAT_COLORS)]
        _place_sat(mw.earth_3d.plotter, sat_pos, 0.02, color,
                   f'_anim_sat_{j}', sc.name, f'_anim_sat_label_{j}')

        if j == sat_idx:
            _draw_anim_link_lines(mw, sat_pos, bs1, bs2)

    _update_tle_anim(mw)


def _draw_link_lines(mw, sat_cfg, sat_idx, bs1, bs2):
    bi1 = mw.bs1_combo.currentIndex()
    bi2 = mw.bs2_combo.currentIndex()
    if sat_cfg is None or sat_idx not in mw._sat_positions:
        return
    if not mw._3d_sat_visible.get(sat_idx, True):
        return
    sat_pos = mw._sat_positions[sat_idx]
    if bs1 is not None and mw._3d_bs_visible.get(bi1, True):
        _add_link_mesh(mw, sat_pos, bs1, '#2196F3', '_anim_uplink', 1)
    if bs2 is not None and mw._3d_bs_visible.get(bi2, True):
        _add_link_mesh(mw, sat_pos, bs2, '#FF9800', '_anim_downlink', -1)


def _draw_anim_link_lines(mw, sat_pos, bs1, bs2):
    bi1 = mw.bs1_combo.currentIndex()
    bi2 = mw.bs2_combo.currentIndex()
    if bs1 is not None and mw._3d_bs_visible.get(bi1, True):
        _add_link_mesh(mw, sat_pos, bs1, '#2196F3', '_anim_uplink', 1)
    if bs2 is not None and mw._3d_bs_visible.get(bi2, True):
        _add_link_mesh(mw, sat_pos, bs2, '#FF9800', '_anim_downlink', -1)


def _add_link_mesh(mw, sat_pos, bs, color, name, offset_sign):
    gs_pos = _geodetic_to_cartesian_wgs84(
        bs.latitude, bs.longitude, getattr(bs, 'height_km', 0))
    sat_arr = np.array(sat_pos, dtype=float)
    gs_arr = np.array(gs_pos, dtype=float)
    ld = sat_arr - gs_arr
    ld_n = ld / (np.linalg.norm(ld) + 1e-12)
    perp = (np.cross(ld_n, [0, 0, 1]) if abs(ld_n[2]) < 0.9
            else np.cross(ld_n, [1, 0, 0]))
    perp = perp / (np.linalg.norm(perp) + 1e-12)
    off = perp * EARTH_RADIUS * 0.004 * offset_sign
    line = pv.Line((gs_arr + off).tolist(), (sat_arr + off).tolist())
    mw.earth_3d.plotter.add_mesh(line, color=color, line_width=3, opacity=0.7, name=name)


# TLE import dialog

def _show_tle_dialog(mw):
    from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout,
                                 QTextEdit, QPushButton, QLabel, QLineEdit,
                                 QMessageBox, QGroupBox, QGridLayout)
    from PyQt5.QtCore import Qt
    from PyQt5.QtGui import QFont

    dlg = QDialog(mw)
    dlg.setWindowTitle("Import TLE \u2014 Two-Line Element Data")
    dlg.setMinimumSize(600, 480)
    dlg.setStyleSheet("""
        QDialog { background: #f8fafc; }
        QGroupBox {
            font-weight: 700; font-size: 10pt; color: #1e293b;
            border: 1px solid #e2e8f0; border-radius: 10px;
            padding-top: 18px; margin-top: 6px; background: white;
        }
        QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; }
        QLabel { color: #475569; font-size: 9pt; }
        QLineEdit {
            border: 1px solid #cbd5e1; border-radius: 6px;
            padding: 6px 10px; font-size: 9pt; background: white;
        }
        QLineEdit:focus { border-color: #6366f1; }
        QTextEdit {
            border: 1px solid #cbd5e1; border-radius: 6px; padding: 6px;
            font-family: 'Consolas', 'JetBrains Mono', monospace;
            font-size: 9pt; background: white;
        }
        QTextEdit:focus { border-color: #6366f1; }
        QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #6366f1, stop:1 #8b5cf6);
            color: white; border: none; border-radius: 8px;
            font-weight: 700; font-size: 9pt; padding: 8px 20px;
        }
        QPushButton:hover { background: #4f46e5; }
        QPushButton:pressed { background: #4338ca; }
    """)

    lay = QVBoxLayout(dlg)
    lay.setSpacing(12)

    # paste TLE
    pg = QGroupBox("Paste TLE Data")
    pl = QVBoxLayout(pg)
    pl.addWidget(QLabel("Paste 2-line or 3-line TLE data (e.g. from CelesTrak, Space-Track):"))

    tle_edit = QTextEdit()
    tle_edit.setPlaceholderText(
        "ISS (ZARYA)\n"
        "1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9002\n"
        "2 25544  51.6400 208.9163 0006703  41.4475  83.1189 15.49560440434827"
    )
    tle_edit.setFixedHeight(100)
    pl.addWidget(tle_edit)
    lay.addWidget(pg)

    # fetch from CelesTrak
    fg = QGroupBox("Fetch from CelesTrak")
    fl = QGridLayout(fg)

    fl.addWidget(QLabel("NORAD Catalog ID:"), 0, 0)
    norad_input = QLineEdit()
    norad_input.setPlaceholderText("e.g. 25544 (ISS)")
    fl.addWidget(norad_input, 0, 1)

    fetch_btn = QPushButton("Fetch TLE")
    fetch_btn.setStyleSheet("""
        QPushButton {
            background: qlineargradient(x1:0,y1:0,x2:1,y2:0,
                stop:0 #06b6d4, stop:1 #0891b2);
            color: white; border: none; border-radius: 8px;
            font-weight: 700; font-size: 9pt; padding: 8px 20px;
        }
        QPushButton:hover { background: #0891b2; }
    """)

    def _fetch_tle():
        nid = norad_input.text().strip()
        if not nid:
            QMessageBox.warning(dlg, "Error", "Please enter a NORAD Catalog ID.")
            return
        try:
            url = f"https://celestrak.org/NORAD/elements/gp.php?CATNR={nid}&FORMAT=TLE"
            req = urllib.request.Request(url, headers={'User-Agent': 'SatLinkBudget/1.0'})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read().decode('utf-8').strip()
            if not data or 'No GP data found' in data:
                QMessageBox.warning(dlg, "Not Found", f"No TLE data found for NORAD ID {nid}")
                return
            tle_edit.setPlainText(data)
        except Exception as e:
            QMessageBox.warning(dlg, "Fetch Error", f"Could not fetch TLE:\n{e}")

    fetch_btn.clicked.connect(_fetch_tle)
    fl.addWidget(fetch_btn, 0, 2)

    fl.addWidget(QLabel("Quick:"), 1, 0)
    presets = QHBoxLayout()
    for pname, pid in [("ISS", "25544"), ("Hubble", "20580"),
                       ("Starlink-1007", "44713"), ("GPS BIIR-2", "24876")]:
        pb = QPushButton(pname)
        pb.setFixedWidth(90)
        pb.setStyleSheet("""
            QPushButton {
                background: #f1f5f9; color: #334155; border: 1px solid #e2e8f0;
                border-radius: 6px; font-size: 8pt; font-weight: 600; padding: 4px 8px;
            }
            QPushButton:hover { background: #e0e7ff; border-color: #6366f1; color: #4f46e5; }
        """)
        pb.clicked.connect(lambda checked, nid=pid: (norad_input.setText(nid), _fetch_tle()))
        presets.addWidget(pb)
    presets.addStretch()
    fl.addLayout(presets, 1, 1, 1, 2)
    lay.addWidget(fg)

    # import / cancel
    br = QHBoxLayout()
    br.addStretch()

    import_btn = QPushButton("Import Satellite")
    import_btn.setFixedWidth(180)

    def _do_import():
        txt = tle_edit.toPlainText().strip()
        if not txt:
            QMessageBox.warning(dlg, "Error", "Please paste or fetch TLE data first.")
            return
        try:
            from models.orbit import parse_tle
            result = parse_tle(txt)
            mw._tle_satellites.append(result)
            mw._tle_visible[len(mw._tle_satellites) - 1] = True
            mw._3d_needs_full_rebuild = True
            _rebuild_3d_visibility_panel(mw)
            update_3d_view(mw)
            QMessageBox.information(dlg, "Success",
                f"Imported: {result['name']}\n"
                f"Altitude: {result['altitude_km']:.1f} km\n"
                f"Inclination: {result['inclination_deg']:.1f}\u00b0\n"
                f"Period: {result['period_min']:.1f} min")
            dlg.accept()
        except Exception as e:
            QMessageBox.critical(dlg, "Parse Error", f"Failed to parse TLE:\n{e}")

    import_btn.clicked.connect(_do_import)
    br.addWidget(import_btn)

    cancel_btn = QPushButton("Cancel")
    cancel_btn.setFixedWidth(100)
    cancel_btn.setStyleSheet("""
        QPushButton {
            background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0;
            border-radius: 8px; font-weight: 600; font-size: 9pt; padding: 8px 20px;
        }
        QPushButton:hover { background: #e2e8f0; }
    """)
    cancel_btn.clicked.connect(dlg.reject)
    br.addWidget(cancel_btn)
    lay.addLayout(br)

    dlg.exec_()


# TLE satellite rendering

def _draw_tle_satellites(mw):
    """Add TLE satellites during full rebuild."""
    if not HAS_3D:
        return
    for k, td in enumerate(getattr(mw, '_tle_satellites', [])):
        if not mw._tle_visible.get(k, True):
            continue
        orb = td['orbit']
        color = _TLE_COLORS[k % len(_TLE_COLORS)]

        try:
            times = np.linspace(0, orb.orbital_period * 60, 120)
            mw.earth_3d.add_orbit_trace(
                [orb.get_satellite_position_eci(t) for t in times], color=color)
        except Exception:
            pass

        pos = orb.get_satellite_position_eci(mw.current_time)
        _place_sat(mw.earth_3d.plotter, pos, 0.018, color,
                   f'_anim_tle_{k}', td['name'], f'_anim_tle_label_{k}')


def _update_tle_anim(mw):
    """Update TLE satellite positions during animation tick."""
    if not HAS_3D:
        return
    for k, td in enumerate(getattr(mw, '_tle_satellites', [])):
        if not mw._tle_visible.get(k, True):
            for n in [f'_anim_tle_{k}', f'_anim_tle_label_{k}']:
                try:
                    mw.earth_3d.plotter.remove_actor(n)
                except Exception:
                    pass
            continue

        color = _TLE_COLORS[k % len(_TLE_COLORS)]
        pos = td['orbit'].get_satellite_position_eci(mw.current_time)
        _place_sat(mw.earth_3d.plotter, pos, 0.018, color,
                   f'_anim_tle_{k}', td['name'], f'_anim_tle_label_{k}')
