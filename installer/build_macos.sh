#!/usr/bin/env bash
# Build Sat-Link.app and a drag-to-Applications .dmg (macOS counterpart of build_installer.ps1).
# Must run on a Mac; the result matches that Mac's CPU (arm64 = Apple Silicon, x86_64 = Intel).
#
# Usage: bash installer/build_macos.sh [version] [python]
#   e.g. python3 -m venv .venv && bash installer/build_macos.sh 3.0.0 .venv/bin/python
set -euo pipefail

VERSION="${1:-3.0.0}"
PYTHON="${2:-python3}"

if [ "$(uname -s)" != "Darwin" ]; then
    echo "This script must run on macOS (PyInstaller cannot build a Mac app on other systems)." >&2
    exit 1
fi

# This script lives in installer/; all build paths are relative to the repo root.
cd "$(dirname "$0")/.."

ARCH="$(uname -m)"
APP="dist/Sat-Link.app"
DMG="release/SatLink-${VERSION}-macOS-${ARCH}.dmg"

echo
echo "==> Installing dependencies for build"
"$PYTHON" -m pip install --upgrade pip
"$PYTHON" -m pip install -r requirements.txt
# Pillow lets PyInstaller turn the PNG icon into the .icns format macOS needs.
"$PYTHON" -m pip install --upgrade pyinstaller pyinstaller-hooks-contrib pillow

echo
echo "==> Building Sat-Link.app with PyInstaller"
rm -rf build dist
"$PYTHON" -m PyInstaller \
    --noconfirm \
    --clean \
    --windowed \
    --name "Sat-Link" \
    --icon "assets/satellite_icon.png" \
    --osx-bundle-identifier "org.satlink.Sat-Link" \
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

if [ ! -d "$APP" ]; then
    echo "PyInstaller did not produce $APP" >&2
    exit 1
fi

# Version shown in Finder's "Get Info", and sharp text on Retina screens.
PLIST="$APP/Contents/Info.plist"
plutil -replace CFBundleShortVersionString -string "$VERSION" "$PLIST"
plutil -replace CFBundleVersion -string "$VERSION" "$PLIST"
plutil -replace NSHighResolutionCapable -bool true "$PLIST"

# Editing Info.plist breaks PyInstaller's ad-hoc signature; Apple Silicon refuses to run
# apps with a broken signature, so re-sign ad hoc (no Apple Developer ID needed).
codesign --force --deep --sign - "$APP"
codesign --verify --deep --strict "$APP"
echo "App bundle complete: $APP"

echo
echo "==> Creating .dmg"
STAGING="build/dmg"
rm -rf "$STAGING"
mkdir -p "$STAGING" release
ditto "$APP" "$STAGING/Sat-Link.app"
# The Applications shortcut is what makes the classic "drag the app here" window.
ln -s /Applications "$STAGING/Applications"
# hdiutil sometimes fails with "Resource busy" while macOS is still scanning the freshly
# written files (Spotlight, XProtect), so wait and retry a few times before giving up.
for attempt in 1 2 3 4 5; do
    rm -f "$DMG"
    if hdiutil create -volname "Sat-Link" -srcfolder "$STAGING" -ov -format UDZO "$DMG"; then
        break
    fi
    if [ "$attempt" -eq 5 ]; then
        echo "hdiutil failed $attempt times; giving up." >&2
        exit 1
    fi
    echo "hdiutil failed (attempt $attempt of 5); retrying in 10 s..." >&2
    sleep 10
done

echo
echo "Installer build complete: $DMG"
