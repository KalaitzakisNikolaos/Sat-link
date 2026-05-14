"""3D Earth and satellite visualization using PyVista."""

import numpy as np
import os
os.environ['QT_API'] = 'pyqt5'

import pyvista as pv
from pyvista import examples as pv_examples
from pyvistaqt import QtInteractor
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from models.constants import (EARTH_RADIUS, EARTH_SEMI_MAJOR, EARTH_SEMI_MINOR,
                               EARTH_FLATTENING, EARTH_ECCENTRICITY_SQ)

_OBLATE = EARTH_SEMI_MINOR / EARTH_SEMI_MAJOR   # b/a ratio for z-squish


def _geodetic_to_cartesian_wgs84(lat_deg, lon_deg, alt_km=0):
    lat = np.radians(lat_deg)
    lon = np.radians(lon_deg)
    N = EARTH_SEMI_MAJOR / np.sqrt(1 - EARTH_ECCENTRICITY_SQ * np.sin(lat)**2)
    x = (N + alt_km) * np.cos(lat) * np.cos(lon)
    y = (N + alt_km) * np.cos(lat) * np.sin(lon)
    z = (N * (1 - EARTH_ECCENTRICITY_SQ) + alt_km) * np.sin(lat)
    return np.array([x, y, z])


def _sweep_ring(axis, half_angle, npts, R):
    """generate `npts` points on a spherical cap boundary using rodrigues rotation."""
    # any perpendicular to the axis will do
    ref = [0,0,1] if abs(axis[2]) < 0.9 else [1,0,0]
    perp = np.cross(axis, ref)
    perp /= np.linalg.norm(perp)

    # tilt axis away by half_angle
    c, s = np.cos(half_angle), np.sin(half_angle)
    tilted = axis*c + np.cross(perp, axis)*s + perp * np.dot(perp, axis)*(1-c)

    # now rotate tilted vector around axis for full 360
    out = np.empty((npts, 3))
    for i, phi in enumerate(np.linspace(0, 2*np.pi, npts)):
        cp, sp = np.cos(phi), np.sin(phi)
        v = tilted*cp + np.cross(axis, tilted)*sp + axis*np.dot(axis, tilted)*(1-cp)
        out[i] = R * v / np.linalg.norm(v)
    return out


class Earth3DVisualization(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self._nn = 0
        self.satellite_actors = []
        self.orbit_actors = []
        self.link_actors = []
        self.coverage_actors = []
        self.spot_beam_actors = []
        self.gs_actors = []
        self.atmo_actor = None
        # kept for backwards compat with single-sat code paths
        self.satellite_actor = None
        self.orbit_actor = None
        self.link_actor = None
        self.coverage_actor = None

        layout = QVBoxLayout(self)
        self.plotter = QtInteractor(self)
        layout.addWidget(self.plotter.interactor)
        self._init_earth()
        self.plotter.view_isometric()
        self.plotter.reset_camera()

    def _nxt(self, tag):
        self._nn += 1
        return f'{tag}_{self._nn}'

    def _init_earth(self):
        # try pyvista's textured earth first
        try:
            mesh = pv_examples.planets.load_earth(
                radius=EARTH_SEMI_MAJOR, lat_resolution=80, lon_resolution=120)
            tex = pv_examples.load_globe_texture()
            # flip x,y so prime meridian lines up with +X
            mesh.points[:, 0] *= -1
            mesh.points[:, 1] *= -1
            mesh.points[:, 2] *= _OBLATE
            self.plotter.add_mesh(mesh, texture=tex, smooth_shading=True, name='earth')
        except Exception:
            # parametric ellipsoid fallback (no texture)
            try:
                la = np.linspace(-np.pi/2, np.pi/2, 80)
                lo = np.linspace(0, 2*np.pi, 120)
                lo, la = np.meshgrid(lo, la)
                g = pv.StructuredGrid(
                    EARTH_SEMI_MAJOR*np.cos(la)*np.cos(lo),
                    EARTH_SEMI_MAJOR*np.cos(la)*np.sin(lo),
                    EARTH_SEMI_MINOR*np.sin(la))
                self.plotter.add_mesh(g, color='lightblue', opacity=0.9,
                                       smooth_shading=True, name='earth')
            except Exception:
                sph = pv.Sphere(radius=EARTH_RADIUS, theta_resolution=60, phi_resolution=60)
                self.plotter.add_mesh(sph, color='lightblue', opacity=0.9,
                                       smooth_shading=True, name='earth')

        # semi-transparent atmosphere shell
        try:
            atmo = pv.Sphere(radius=EARTH_SEMI_MAJOR*1.015,
                             theta_resolution=60, phi_resolution=60)
            atmo.points[:, 2] *= _OBLATE
            self.atmo_actor = self.plotter.add_mesh(
                atmo, color='#4da6ff', opacity=0.08, smooth_shading=True, name='atmosphere')
        except Exception:
            pass  # cosmetic, dont care if it fails

        try:
            self.plotter.set_background(
                pv_examples.planets.download_stars_sky_background(load=False))
        except Exception:
            self.plotter.set_background('black')

    def add_satellite(self, position, label='Satellite', color='red'):
        n1 = self._nxt('sat')
        n2 = self._nxt('sat_lbl')
        sph = pv.Sphere(radius=EARTH_RADIUS*0.02, center=position)
        a = self.plotter.add_mesh(sph, color=color, name=n1)
        la = self.plotter.add_point_labels(
            [position], [label], font_size=20, text_color='yellow', name=n2)
        self.satellite_actors.append((a, la))
        self.satellite_actor = a

    def add_orbit_trace(self, positions, color='yellow', label=''):
        pts = np.array(positions)
        line = pv.Spline(pts, n_points=len(pts))
        a = self.plotter.add_mesh(line, color=color, line_width=2, opacity=0.7,
                                   name=self._nxt('orb'))
        self.orbit_actors.append(a)
        self.orbit_actor = a

    def add_ground_station(self, lat_deg, lon_deg, alt_km=0,
                            label='Ground Station', color='green'):
        pos = _geodetic_to_cartesian_wgs84(lat_deg, lon_deg, alt_km)
        # normal to WGS-84 surface != position direction
        a2 = EARTH_SEMI_MAJOR**2
        b2 = EARTH_SEMI_MINOR**2
        nrm = np.array([pos[0]/a2, pos[1]/a2, pos[2]/b2])
        nrm /= np.linalg.norm(nrm)

        cone = pv.Cone(center=pos, direction=nrm.tolist(),
                        height=EARTH_RADIUS*0.1, radius=EARTH_RADIUS*0.03)
        n1 = self._nxt('gs')
        n2 = self._nxt('gs_lbl')
        a = self.plotter.add_mesh(cone, color=color, name=n1)
        la = self.plotter.add_point_labels(
            [pos.tolist()], [label], font_size=18, text_color='lime', name=n2)
        self.gs_actors.append((a, la))

    def add_link_line(self, sat_pos, gs_lat, gs_lon, gs_alt=0,
                       color='cyan', direction='both', line_width=3):
        gs = _geodetic_to_cartesian_wgs84(gs_lat, gs_lon, gs_alt)
        line = pv.Line(gs.tolist(), list(sat_pos))
        a = self.plotter.add_mesh(line, color=color, line_width=line_width,
                                   opacity=0.6, name=self._nxt('link'))
        self.link_actors.append(a)
        self.link_actor = a

    def add_uplink(self, sat_pos, gs_lat, gs_lon, gs_alt=0):
        """blue UL line, offset slightly so it doesnt overlap the DL"""
        self._directional_link(sat_pos, gs_lat, gs_lon, gs_alt, '#2196F3', +1)

    def add_downlink(self, sat_pos, gs_lat, gs_lon, gs_alt=0):
        self._directional_link(sat_pos, gs_lat, gs_lon, gs_alt, '#FF9800', -1)

    def _directional_link(self, sat_pos, gs_lat, gs_lon, gs_alt, color, sign):
        gs = _geodetic_to_cartesian_wgs84(gs_lat, gs_lon, gs_alt)
        sa = np.asarray(sat_pos, dtype=float)
        ga = np.asarray(gs, dtype=float)
        d = sa - ga
        d /= np.linalg.norm(d) + 1e-12
        # cross with z (or x if nearly vertical) to get lateral offset direction
        ref = [0,0,1] if abs(d[2]) < 0.9 else [1,0,0]
        perp = np.cross(d, ref)
        perp /= np.linalg.norm(perp) + 1e-12
        off = perp * EARTH_RADIUS * 0.004 * sign
        line = pv.Line((ga + off).tolist(), (sa + off).tolist())
        a = self.plotter.add_mesh(line, color=color, line_width=3, opacity=0.7,
                                   name=self._nxt('link'))
        self.link_actors.append(a)
        self.link_actor = a

    def add_coverage_circle(self, sat_pos, elevation_angle=5, color='orange'):
        """coverage footprint on the earth surface for given min elevation"""
        sat_pos = np.asarray(sat_pos, dtype=float)
        h = np.linalg.norm(sat_pos) - EARTH_RADIUS
        if h <= 0:
            return
        el = np.radians(elevation_angle)
        # earth central angle, from Roddy eq 3.2
        gamma = np.arccos(EARTH_RADIUS/(EARTH_RADIUS+h) * np.cos(el)) - el

        su = sat_pos / np.linalg.norm(sat_pos)
        ring = _sweep_ring(su, gamma, 120, EARTH_RADIUS)
        ring = np.vstack([ring, ring[0:1]])
        a = self.plotter.add_mesh(pv.Spline(ring, n_points=121), color=color,
                                   line_width=3, opacity=0.7, name=self._nxt('cov'))
        self.coverage_actors.append(a)
        self.coverage_actor = a

    def add_spot_beam(self, center_lat, center_lon, beamwidth_deg,
                       color='#2196F3', opacity=0.35, label=None):
        """filled disc + outline on the globe surface for a spot beam"""
        cxyz = _geodetic_to_cartesian_wgs84(center_lat, center_lon, 0)
        cu = cxyz / np.linalg.norm(cxyz)

        gamma = max(np.radians(beamwidth_deg * 0.75), 0.001)
        ring = _sweep_ring(cu, gamma, 80, EARTH_SEMI_MAJOR)
        ring[:, 2] *= _OBLATE

        # center point, also squished, raised slightly to avoid z-fighting
        cp = cxyz.copy()
        cp[2] *= _OBLATE
        cp *= 1.002
        ring *= 1.002

        # fan triangles from center to ring
        n = len(ring)
        verts = np.vstack([cp.reshape(1,3), ring])
        faces = []
        for i in range(n):
            faces.extend([3, 0, i+1, (i+1) % n + 1])
        disc = pv.PolyData(verts, faces=faces)
        self.spot_beam_actors.append(
            self.plotter.add_mesh(disc, color=color, opacity=opacity,
                                   smooth_shading=True, name=self._nxt('beam')))
        # ring outline
        closed = np.vstack([ring, ring[0:1]])
        self.spot_beam_actors.append(
            self.plotter.add_mesh(pv.Spline(closed, n_points=n+1), color=color,
                                   line_width=3, opacity=min(opacity+0.3, 1.0),
                                   name=self._nxt('beam_ol')))
        if label:
            self.spot_beam_actors.append(
                self.plotter.add_point_labels(
                    [cp.tolist()], [label], font_size=16, text_color='white',
                    name=self._nxt('beam_lbl')))

    def clear_spot_beams(self):
        for a in self.spot_beam_actors:
            try: self.plotter.remove_actor(a)
            except Exception: pass
        self.spot_beam_actors.clear()

    def update_camera_view(self, view_type='isometric'):
        fn = {'isometric': self.plotter.view_isometric,
              'top': self.plotter.view_xy,
              'side': self.plotter.view_xz}.get(view_type)
        if fn: fn()
        else: self.plotter.view_isometric()
        self.plotter.reset_camera()

    def clear_dynamic_actors(self):
        """strips everything except the earth globe and atmosphere"""
        try: cam = self.plotter.camera_position
        except Exception: cam = None

        self.clear_spot_beams()

        # satellite and gs have (mesh, label) tuples
        for bucket in (self.satellite_actors, self.gs_actors):
            for pair in bucket:
                for a in pair:
                    try: self.plotter.remove_actor(a)
                    except Exception: pass
            bucket.clear()

        for bucket in (self.link_actors, self.orbit_actors, self.coverage_actors):
            for a in bucket:
                try: self.plotter.remove_actor(a)
                except Exception: pass
            bucket.clear()

        self._nn = 0
        self.satellite_actor = self.orbit_actor = self.link_actor = self.coverage_actor = None

        if cam:
            try: self.plotter.camera_position = cam
            except Exception: pass

    def clear_scene(self):
        self.clear_dynamic_actors()
        self.plotter.clear_actors()
        self._init_earth()


def create_advanced_earth_plot(plotter):
    """sets up textured WGS-84 globe on an external plotter instance"""
    earth = pv_examples.planets.load_earth(radius=EARTH_SEMI_MAJOR)
    tex = pv_examples.load_globe_texture()
    earth.points[:, 0] *= -1
    earth.points[:, 1] *= -1
    earth.points[:, 2] *= _OBLATE
    plotter.add_mesh(earth, texture=tex, smooth_shading=True)

    atmo = pv.Sphere(radius=EARTH_SEMI_MAJOR*1.015,
                      theta_resolution=60, phi_resolution=60)
    atmo.points[:, 2] *= _OBLATE
    plotter.add_mesh(atmo, color='#4da6ff', opacity=0.08, smooth_shading=True)

    try:
        plotter.set_background(
            pv_examples.planets.download_stars_sky_background(load=False))
    except Exception:
        plotter.set_background('black')
