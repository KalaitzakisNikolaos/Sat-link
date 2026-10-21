#!/usr/bin/env bash
# Build a single-file Sat-Link AppImage (Linux counterpart of build_installer.ps1).
# An AppImage runs on distributions with the same or newer glibc than the build machine,
# which is why the official builds are made on Ubuntu 22.04 (see .github/workflows/release.yml).
#
# Usage: bash installer/build_linux.sh [version] [python]
#   e.g. python3 -m venv .venv && bash installer/build_linux.sh 3.0.0 .venv/bin/python
set -euo pipefail

VERSION="${1:-3.0.0}"
PYTHON="${2:-python3}"

if [ "$(uname -s)" != "Linux" ]; then
    echo "This script must run on Linux." >&2
    exit 1
fi

# This script lives in installer/; all build paths are relative to the repo root.
cd "$(dirname "$0")/.."

ARCH="$(uname -m)"
APPDIR="build/AppDir"
APPIMAGE="release/SatLink-${VERSION}-linux-${ARCH}.AppImage"
APPIMAGETOOL=".build-cache/appimagetool-${ARCH}.AppImage"

echo
echo "==> Installing dependencies for build"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r requirements.txt
"$PYTHON" -m pip install --upgrade pyinstaller pyinstaller-hooks-contrib

# PyInstaller bundles the X11/xcb libraries Qt needs only if they exist on this machine;
# without them the AppImage would fail on PCs that lack them too, so stop early.
PYQT_DIR="$("$PYTHON" -c 'import os, PyQt5; print(os.path.dirname(PyQt5.__file__))')"
QXCB="$PYQT_DIR/Qt5/plugins/platforms/libqxcb.so"
QT_MISSING="$(LD_LIBRARY_PATH="$PYQT_DIR/Qt5/lib" ldd "$QXCB" | awk '/not found/ {print $1}' | sort -u)"
if [ -n "$QT_MISSING" ]; then
    echo "These system libraries must be installed before building (they get bundled into the AppImage):" >&2
    echo "$QT_MISSING" | sed 's/^/  /' >&2
    echo "  Debian/Ubuntu: sudo apt install libglib2.0-0 libdbus-1-3 libfontconfig1 libxkbcommon0 libxkbcommon-x11-0 \\" >&2
    echo "      libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render0 libxcb-render-util0 \\" >&2
    echo "      libxcb-shape0 libxcb-xinerama0 libxcb-xkb1" >&2
    exit 1
fi

echo
echo "==> Building Sat-Link with PyInstaller"
rm -rf build dist
"$PYTHON" -m PyInstaller \
    --noconfirm \
    --clean \
    --windowed \
    --name "Sat-Link" \
    --add-data "assets:assets" \
    --collect-all pyvista \
    --collect-all pyvistaqt \
    --collect-data pyqtgraph \
    --collect-data matplotlib \
    --collect-data seaborn \
    --exclude-module torch \
    --exclude-module torchvision \
    --exclude-module torchaudio \
    --exclude-module tensorflow \
    --exclude-module jax \
    --exclude-module triton \
    --exclude-module plotly \
    --exclude-module sympy \
    --exclude-module skimage \
    --exclude-module sklearn \
    --exclude-module numba \
    --exclude-module llvmlite \
    --exclude-module imageio \
    --exclude-module tkinter \
    --exclude-module _tkinter \
    --exclude-module PyQt5.QtBluetooth \
    --exclude-module PyQt5.QtDesigner \
    --exclude-module PyQt5.QtHelp \
    --exclude-module PyQt5.QtLocation \
    --exclude-module PyQt5.QtMultimedia \
    --exclude-module PyQt5.QtMultimediaWidgets \
    --exclude-module PyQt5.QtNfc \
    --exclude-module PyQt5.QtQml \
    --exclude-module PyQt5.QtQuick \
    --exclude-module PyQt5.QtQuick3D \
    --exclude-module PyQt5.QtQuickWidgets \
    --exclude-module PyQt5.QtRemoteObjects \
    --exclude-module PyQt5.QtSensors \
    --exclude-module PyQt5.QtSerialPort \
    --exclude-module PyQt5.QtSql \
    --exclude-module PyQt5.QtTextToSpeech \
    --exclude-module PyQt5.QtWebEngine \
    --exclude-module PyQt5.QtWebEngineCore \
    --exclude-module PyQt5.QtWebEngineWidgets \
    --exclude-module PyQt5.QtWebChannel \
    --exclude-module PyQt5.QtWebSockets \
    --exclude-module PyQt5.QtXml \
    --exclude-module PyQt5.QtXmlPatterns \
    --exclude-module pyqtgraph.examples \
    main_advanced.py

if [ ! -x "dist/Sat-Link/Sat-Link" ]; then
    echo "PyInstaller did not produce dist/Sat-Link/Sat-Link" >&2
    exit 1
fi
echo "Executable build complete: dist/Sat-Link/Sat-Link"

echo
echo "==> Assembling AppDir"
mkdir -p "$APPDIR/usr/bin"
cp -a dist/Sat-Link/. "$APPDIR/usr/bin/"
cp assets/satellite_icon.png "$APPDIR/sat-link.png"
cat > "$APPDIR/sat-link.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=Sat-Link
Comment=ITU-R-aligned satellite link-budget simulator
Exec=Sat-Link
Icon=sat-link
Categories=Science;Education;
Terminal=false
EOF
cat > "$APPDIR/AppRun" <<'EOF'
#!/bin/sh
HERE="$(dirname "$(readlink -f "$0")")"
exec "$HERE/usr/bin/Sat-Link" "$@"
EOF
chmod +x "$APPDIR/AppRun"

echo
echo "==> Packing AppImage"
if [ ! -x "$APPIMAGETOOL" ]; then
    mkdir -p "$(dirname "$APPIMAGETOOL")"
    curl -fL -o "$APPIMAGETOOL" \
        "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-${ARCH}.AppImage"
    chmod +x "$APPIMAGETOOL"
fi
mkdir -p release
rm -f "$APPIMAGE"
# Extract-and-run lets appimagetool work where FUSE is unavailable (containers, CI).
ARCH="$ARCH" APPIMAGE_EXTRACT_AND_RUN=1 "$APPIMAGETOOL" "$APPDIR" "$APPIMAGE"

echo
echo "Installer build complete: $APPIMAGE"
