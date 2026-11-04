"""Scripted UI check used by the CI smoke tests: ``Sat-Link --self-test <out_dir>``.

Opens every tab, switches in and out of the 3D view (the path that crashed on macOS), runs the
3D animation, fetches a TLE from CelesTrak without system CA certificates, and saves
screenshots plus a log to <out_dir>. Quits with exit code 0 if nothing failed; a native crash
ends the process early, which the CI step reports as a failure.
"""

import os
import platform
import ssl
import subprocess
import sys
import traceback
import urllib.error

from PyQt5.QtCore import QTimer, QT_VERSION_STR
from PyQt5.QtWidgets import QApplication


def start_self_test(app, window, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    log = open(os.path.join(out_dir, 'selftest.log'), 'w', encoding='utf-8')
    failures = []
    state = {'has_gl': True}

    def say(msg):
        log.write(msg + '\n')
        log.flush()
        if sys.stdout is not None:
            print(msg, flush=True)

    previous_hook = sys.excepthook

    def hook(exc_type, exc, tb):
        failures.append(f'uncaught {exc_type.__name__}: {exc}')
        say('UNCAUGHT ' + ''.join(traceback.format_exception(exc_type, exc, tb)))
        previous_hook(exc_type, exc, tb)

    sys.excepthook = hook

    def tab_index(label):
        for i in range(window.viz_tabs.count()):
            if window.viz_tabs.tabText(i) == label:
                return i
        raise RuntimeError(f'no tab named {label!r}')

    def show_tab(label):
        window.viz_tabs.setCurrentIndex(tab_index(label))

    def screenshot(name):
        screen = QApplication.primaryScreen()
        if screen is not None and screen.grabWindow(0).save(os.path.join(out_dir, f'{name}.png')):
            say(f'    saved {name}.png')
        if sys.platform == 'darwin':
            # Qt's grab can miss the native OpenGL view on macOS; screencapture sees what the user sees
            subprocess.run(['screencapture', '-x', os.path.join(out_dir, f'{name}-screen.png')],
                           timeout=30, check=False)
            say(f'    saved {name}-screen.png')

    def environment():
        import numpy
        from numpy._core import _multiarray_umath
        say(f'    {platform.platform()} | {platform.machine()} | Python {platform.python_version()}'
            f' | frozen={getattr(sys, "frozen", False)}')
        say(f'    numpy {numpy.__version__} baseline {_multiarray_umath.__cpu_baseline__} | Qt {QT_VERSION_STR}')
        say(f'    default CA paths: {ssl.get_default_verify_paths()}')
        try:
            import vtk
            rw = vtk.vtkRenderWindow()
            rw.SetOffScreenRendering(1)
            state['has_gl'] = bool(rw.SupportsOpenGL())
            say(f'    vtk {vtk.vtkVersion.GetVTKVersion()} | OpenGL 3.2+ available: {state["has_gl"]}')
        except Exception as e:
            state['has_gl'] = False
            say(f'    vtk unavailable: {e}')

    def tle():
        from gui.visualizations.view_3d import fetch_tle_text
        # Point OpenSSL's default CA paths at nothing, like a Mac without the bundled OpenSSL's
        # certificate folder, to prove the download does not depend on them.
        saved = {k: os.environ.get(k) for k in ('SSL_CERT_FILE', 'SSL_CERT_DIR')}
        os.environ['SSL_CERT_FILE'] = os.path.join(out_dir, 'no-such-ca.pem')
        os.environ['SSL_CERT_DIR'] = os.path.join(out_dir, 'no-such-ca-dir')
        try:
            text = fetch_tle_text('25544')
            say(f'    TLE 25544: {text.splitlines()[0] if text else "(empty)"!r}')
        except (ssl.SSLError, urllib.error.URLError) as e:
            reason = getattr(e, 'reason', e)
            if isinstance(reason, ssl.SSLError) or isinstance(e, ssl.SSLError):
                raise  # certificate problems are what this step is checking
            say(f'    WARNING: CelesTrak unreachable from this machine, not counted as a failure: {e}')
        finally:
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def report_3d():
        e3d = getattr(window, 'earth_3d', None)
        if e3d is None:
            raise RuntimeError('3D view was not built')
        say(f'    earth texture error: {getattr(e3d, "earth_texture_error", None)}')
        rw = e3d.plotter.ren_win
        for line in (rw.ReportCapabilities() or '').splitlines()[:4]:
            say('    ' + line.strip())
        say(f'    render window size {rw.GetSize()} | actors {len(e3d.plotter.renderer.actors)}')
        img = e3d.plotter.screenshot(os.path.join(out_dir, '3d_vtk.png'), return_img=True)
        say(f'    saved 3d_vtk.png | pixel std {float(img.std()):.1f} (near 0 = blank)')
        if float(img.std()) < 2.0:
            raise RuntimeError('3D view rendered a blank image')

    def three_d(func):
        """Run a 3D step only where VTK can get an OpenGL 3.2 context (CI VMs may lack one)."""
        def run():
            if state['has_gl']:
                func()
            else:
                say('    SKIPPED: no OpenGL 3.2 on this machine')
        return run

    def set_animation(on):
        window.animation_running = on
        window.animation_direction = 1

    def finish():
        result = 'PASSED' if not failures else 'FAILED: ' + '; '.join(failures)
        say(f'SELFTEST {result}')
        log.close()
        app.exit(0 if not failures else 1)

    plan = [
        (0, 'environment', environment),
        (500, 'TLE download without system CA certificates', tle),
        (500, 'open Transponder', lambda: show_tab('Transponder')),
        (3000, 'screenshot Transponder', lambda: screenshot('transponder')),
        (500, 'open 3D View', three_d(lambda: show_tab('3D View'))),
        (15000, '3D render check', three_d(report_3d)),
        (500, 'screenshot 3D View', three_d(lambda: screenshot('3d_view'))),
    ]
    for i in range(3):
        plan += [
            (500, f'3D -> Transponder #{i + 1}', lambda: show_tab('Transponder')),
            (2500, f'Transponder -> 3D #{i + 1}', three_d(lambda: show_tab('3D View'))),
            (2500, f'3D still alive #{i + 1}', three_d(lambda: window.earth_3d.plotter.render())),
        ]
    plan += [
        (500, 'start 3D animation', three_d(lambda: set_animation(True))),
        (4000, 'leave 3D while animating', lambda: show_tab('Transponder')),
        (2500, 'back to 3D while animating', three_d(lambda: show_tab('3D View'))),
        (3000, 'stop animation', lambda: set_animation(False)),
    ]
    for i in range(window.viz_tabs.count()):
        label = window.viz_tabs.tabText(i)
        func = (lambda l=label: show_tab(l))
        plan.append((1500, f'open {label}', three_d(func) if label == '3D View' else func))
    plan.append((2000, 'finish', None))

    def run_step(i):
        # Each step schedules the next one, so a slow step cannot let later timers fire first
        _delay, name, func = plan[i]
        if func is None:
            finish()
            return
        say(f'--> {name}')
        try:
            func()
        except Exception:
            failures.append(name)
            say('FAILED ' + traceback.format_exc())
        QTimer.singleShot(plan[i + 1][0], lambda: run_step(i + 1))

    QTimer.singleShot(plan[0][0], lambda: run_step(0))
