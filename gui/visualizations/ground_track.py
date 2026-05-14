"""Ground track / orbit tab with satellite footprint overlay."""

import os
import csv
import numpy as np
from datetime import datetime, timedelta

from gui.core.mpl_canvas import MplCanvas
from models.orbit import create_satellite_from_type

_map_cache = None


def _load_map():
    """Parse detailed_shapes.csv into a list of (lons, lats) polygons."""
    global _map_cache
    if _map_cache is not None:
        return _map_cache

    path = os.path.join(os.path.dirname(__file__), '..', '..', 'detailed_shapes.csv')
    path = os.path.normpath(path)
    if not os.path.exists(path):
        _map_cache = []
        return _map_cache

    W, H = 2000.0, 857.0
    raw = {}
    with open(path, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            sid = row['ShapeID']
            if row['PointIndex'] != '0':
                continue
            if sid not in raw:
                raw[sid] = {'pts': [], 'closed': row.get('IsClosed', 'True') == 'True'}
            x, y = float(row['SampleX']), float(row['SampleY'])
            raw[sid]['pts'].append(((x / W) * 360 - 180, 90 - (y / H) * 180))

    polys = []
    for sd in raw.values():
        pts = sd['pts']
        if len(pts) < 3:
            continue
        lons, lats = zip(*pts)
        lons, lats = list(lons), list(lats)
        if sd['closed'] and (lons[0] != lons[-1] or lats[0] != lats[-1]):
            lons.append(lons[0])
            lats.append(lats[0])
        polys.append((lons, lats))

    _map_cache = polys
    return _map_cache


def _draw_map(ax):
    polys = _load_map()
    if not polys:
        # fallback continents
        for c in [
            [(-130,50),(-125,60),(-100,62),(-80,60),(-55,48),(-65,45),
             (-80,25),(-105,20),(-120,35),(-130,50)],
            [(-80,10),(-60,12),(-35,-5),(-35,-20),(-50,-30),(-70,-55),
             (-75,-45),(-70,-20),(-80,10)],
            [(-10,36),(0,43),(5,48),(10,55),(25,60),(30,55),(28,45),
             (25,35),(15,38),(5,36),(-10,36)],
            [(-15,15),(-15,5),(5,-2),(10,-15),(30,-35),(40,-25),(50,12),
             (45,15),(35,30),(10,35),(-5,35),(-15,15)],
            [(30,35),(40,40),(50,45),(60,55),(80,55),(100,50),(120,55),
             (140,45),(130,35),(120,25),(105,15),(95,10),(80,15),(65,25),
             (45,30),(30,35)],
            [(115,-15),(130,-12),(150,-15),(153,-25),(148,-35),(135,-35),
             (120,-30),(115,-15)],
        ]:
            xs, ys = zip(*c)
            ax.fill(xs, ys, color='#e0e0e0', alpha=0.5, zorder=0)
            ax.plot(xs, ys, color='#9e9e9e', linewidth=0.7, alpha=0.6, zorder=1)
        return

    for lons, lats in polys:
        ax.fill(lons, lats, color='#d4e6c3', alpha=0.55, zorder=0, linewidth=0)
        ax.plot(lons, lats, color='#8a9a7b', linewidth=0.4, alpha=0.7, zorder=1)


def _sun_subsolar(dt):
    """Sub-solar point (lat, lon) in degrees for *dt*."""
    n = (dt - datetime(2000, 1, 1, 12)).total_seconds() / 86400.0
    L = (280.460 + 0.9856474 * n) % 360
    g = np.radians((357.528 + 0.9856003 * n) % 360)
    lam = np.radians(L + 1.915 * np.sin(g) + 0.020 * np.sin(2 * g))
    eps = np.radians(23.439 - 4e-7 * n)
    dec = np.arcsin(np.sin(eps) * np.sin(lam))
    utc_h = dt.hour + dt.minute / 60.0 + dt.second / 3600.0
    return np.degrees(dec), -(utc_h - 12) * 15.0


def _draw_sun(ax, dt, cache):
    lat, lon = _sun_subsolar(dt)
    (pt,) = ax.plot(lon, lat, 'o', color='#FFD700', markersize=8,
                    markeredgecolor='orange', markeredgewidth=2, zorder=3, label='Sun')
    cache['terminator'] = [pt]


def _footprint_circle(sat_lat, sat_lon, alt_km):
    """Visibility circle vertices for a satellite at *alt_km*."""
    Re = 6371.0
    half_angle = np.arccos(Re / (Re + alt_km))
    th = np.linspace(0, 2 * np.pi, 200)
    slat, slon = np.radians(sat_lat), np.radians(sat_lon)

    lat_r = np.arcsin(np.sin(slat) * np.cos(half_angle) +
                      np.cos(slat) * np.sin(half_angle) * np.cos(th))
    dlon = np.arctan2(np.sin(th) * np.sin(half_angle) * np.cos(slat),
                      np.cos(half_angle) - np.sin(slat) * np.sin(lat_r))
    lon_d = np.degrees(slon + dlon)
    lon_d = (lon_d + 180) % 360 - 180
    return np.degrees(lat_r), lon_d


def _split_antimeridian(lats, lons):
    """Split a track at ±180° jumps and return list of segments."""
    segs = []
    sl, sn = [lats[0]], [lons[0]]
    for i in range(1, len(lons)):
        if abs(lons[i] - lons[i - 1]) > 180:
            segs.append((sl, sn))
            sl, sn = [lats[i]], [lons[i]]
        else:
            sl.append(lats[i]); sn.append(lons[i])
    segs.append((sl, sn))
    return segs


def _draw_footprint(ax, sat_lat, sat_lon, alt_km, cache):
    if alt_km <= 0:
        return
    clat, clon = _footprint_circle(sat_lat, sat_lon, alt_km)
    arts = []
    for i, (sl, sn) in enumerate(_split_antimeridian(clat, clon)):
        lbl = 'Visibility' if i == 0 else None
        (ln,) = ax.plot(sn, sl, '--', color='#ffffff', linewidth=1,
                        alpha=0.8, zorder=2.5, label=lbl)
        arts.append(ln)
    cache['footprint'] = arts


def _hms(seconds):
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    return f"{h % 24:02d}:{m:02d}:{s:02d}"


# ── tab creation ──────────────────────────────────────────────────────────

def create_orbit_tab(mw):
    """Canvas + playback slider toolbar."""
    from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                                 QPushButton, QLabel, QSlider, QComboBox)
    from PyQt5.QtCore import Qt

    tab = QWidget()
    lay = QVBoxLayout(tab)

    mw.orbit_canvas = MplCanvas(mw, width=10, height=6, dpi=100)
    lay.addWidget(mw.orbit_canvas)

    bar = QWidget()
    bar.setFixedHeight(50)
    bar.setStyleSheet("background-color:#f5f5f5; border-top:1px solid #dcdcdc;")
    bl = QHBoxLayout(bar)
    bl.setContentsMargins(10, 5, 10, 5)

    mw.btn_orbit_play = QPushButton("\u25b6")
    mw.btn_orbit_play.setFixedWidth(50)
    mw.btn_orbit_play.setStyleSheet(
        "QPushButton{padding:5px; font-size:14pt; font-weight:bold; border-radius:8px;}")
    mw.btn_orbit_play.setToolTip("Play/Pause")
    mw.btn_orbit_play.clicked.connect(lambda: _toggle_play(mw))
    bl.addWidget(mw.btn_orbit_play)

    mw.orbit_time_slider = QSlider(Qt.Horizontal)
    mw.orbit_time_slider.setRange(0, 24 * 3600)
    mw.orbit_time_slider.sliderPressed.connect(lambda: setattr(mw, '_slider_dragging', True))
    mw.orbit_time_slider.sliderReleased.connect(lambda: _slider_released(mw))
    mw.orbit_time_slider.valueChanged.connect(lambda v: _slider_moved(mw, v))
    bl.addWidget(mw.orbit_time_slider)

    mw.lbl_orbit_time = QLabel("T = 00:00:00")
    mw.lbl_orbit_time.setFixedWidth(80)
    mw.lbl_orbit_time.setStyleSheet("font-family:monospace; font-weight:bold;")
    bl.addWidget(mw.lbl_orbit_time)

    lay.addWidget(bar)
    mw.orbit_artists = {}
    return tab


def _toggle_play(mw):
    if hasattr(mw, 'animation_running'):
        mw.animation_running = not mw.animation_running
        mw.btn_orbit_play.setText("\u23f8" if mw.animation_running else "\u25b6")


def _slider_released(mw):
    mw._slider_dragging = False
    mw.current_time = float(mw.orbit_time_slider.value())
    if hasattr(mw, 'update_realtime'):
        mw.update_realtime()


def _slider_moved(mw, val):
    if getattr(mw, '_slider_dragging', False):
        mw.lbl_orbit_time.setText(_hms(val))


# ── lightweight animation update ─────────────────────────────────────────

def update_orbit_anim_only(mw):
    """Redraw sun, satellite icon and footprint without touching the base map."""
    if not hasattr(mw, 'orbit_canvas'):
        return
    ax = mw.orbit_canvas.axes
    cache = getattr(mw, 'orbit_artists', {})

    # remove old dynamic artists
    for key in ('sun', 'terminator', 'sat_icon', 'footprint'):
        for a in (cache.get(key) or []):
            try: a.remove()
            except: pass
        cache[key] = []
    mw.orbit_artists = cache

    sim_t = datetime.utcnow() + timedelta(seconds=mw.current_time)
    try:
        _draw_sun(ax, sim_t, cache)
    except Exception:
        pass

    try:
        sat = mw.satellite
        if sat:
            eci = sat.get_satellite_position_eci(mw.current_time)
            ecef = sat._eci_to_ecef(eci, mw.current_time)
            r = np.linalg.norm(ecef)
            lat = np.degrees(np.arcsin(ecef[2] / r))
            lon = np.degrees(np.arctan2(ecef[1], ecef[0]))
            alt = r - 6371.0

            _draw_footprint(ax, lat, lon, alt, cache)
            (ic,) = ax.plot(lon, lat, '*', color='#FFD700', markersize=15,
                            markeredgecolor='#E65100', markeredgewidth=1.5, zorder=6)
            cache['sat_icon'] = [ic]
    except:
        pass

    # sync slider / label
    if hasattr(mw, 'orbit_time_slider') and not getattr(mw, '_slider_dragging', False):
        mw.orbit_time_slider.blockSignals(True)
        mw.orbit_time_slider.setValue(int(mw.current_time) % (24 * 3600))
        mw.orbit_time_slider.blockSignals(False)
        mw.lbl_orbit_time.setText(_hms(mw.current_time))

    if hasattr(mw, 'btn_orbit_play'):
        mw.btn_orbit_play.setText(
            "\u23f8" if getattr(mw, 'animation_running', False) else "\u25b6")

    mw.orbit_canvas.draw_idle()


# ── full redraw ───────────────────────────────────────────────────────────

def update_orbit_plot(mw):
    """Full redraw: map, ground track, stations, dynamic overlay."""
    if mw.satellite is None:
        mw.satellite = create_satellite_from_type(mw.sat_type_combo.currentText())

    ax = mw.orbit_canvas.axes
    ax.clear()
    ax.set_facecolor('#c8ddf0')
    _draw_map(ax)

    # ground track
    lats, lons = mw.satellite.calculate_ground_track(num_points=500, duration_hours=24)
    for i, (sl, sn) in enumerate(_split_antimeridian(lats, lons)):
        ax.plot(sn, sl, color='#d32f2f', linewidth=2.0, alpha=0.8, zorder=4,
                label='Ground Track' if i == 0 else None)

    # dynamic overlay
    update_orbit_anim_only(mw)

    # base stations
    if hasattr(mw, 'base_stations'):
        for i, bs in enumerate(mw.base_stations):
            ax.plot(bs.longitude, bs.latitude, '^', color='#1976D2', markersize=10,
                    markeredgecolor='white', markeredgewidth=1.5, zorder=5,
                    label='Ground Station' if i == 0 else None)
            ax.text(bs.longitude + 2, bs.latitude + 2, bs.name,
                    color='#0D47A1', fontsize=9, fontweight='bold', zorder=5)
    else:
        ax.plot(mw.gs_lon_spin.value(), mw.gs_lat_spin.value(), '^', markersize=10,
                color='#1976D2', markeredgecolor='white', zorder=5, label='Ground Station')

    ax.set_xlabel('Longitude (\u00b0)')
    ax.set_ylabel('Latitude (\u00b0)')
    name = getattr(mw.satellite, 'name', mw.sat_type_combo.currentText())
    ax.set_title(f'{name} - Ground Track & Visibility', fontweight='bold')
    ax.grid(True, alpha=0.3, linestyle='--')

    # deduplicate legend entries
    h, l = ax.get_legend_handles_labels()
    by_label = dict(zip(l, h))
    ax.legend(by_label.values(), by_label.keys(), loc='lower left', fontsize=8)

    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)

    mw.orbit_canvas.figure.tight_layout()
    mw.orbit_canvas.draw()
