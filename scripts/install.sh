#!/usr/bin/env bash
# Installation script for Linux and macOS
# Run from anywhere; the venv is created in the repo root.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Installing Satellite Downlink Simulator..."
echo

# Check Python (3.9+)
echo "Checking Python installation..."
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 \
        && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
        PYTHON="$candidate"
        break
    fi
done
if [ -z "$PYTHON" ]; then
    echo "Python 3.9 or later not found! Please install it first." >&2
    case "$(uname -s)" in
        Darwin) echo "  macOS: brew install python   (or https://www.python.org/downloads/)" >&2 ;;
        Linux)  echo "  Debian/Ubuntu: sudo apt install python3 python3-venv" >&2 ;;
    esac
    exit 1
fi
echo "Found: $("$PYTHON" --version 2>&1)"

# Create virtual environment
echo
echo "Creating virtual environment..."
if [ -x "venv/bin/python" ]; then
    echo "Virtual environment already exists, skipping..."
else
    if ! "$PYTHON" -m venv venv; then
        # A failed venv leaves a half-made folder behind; remove it so a rerun starts clean.
        rm -rf venv
        echo "Could not create the virtual environment." >&2
        echo "  Debian/Ubuntu: sudo apt install python3-venv" >&2
        exit 1
    fi
    echo "Virtual environment created"
fi

# Upgrade pip
echo
echo "Upgrading pip..."
venv/bin/python -m pip install --upgrade pip

# Install dependencies
echo
echo "Installing dependencies..."
venv/bin/python -m pip install -r requirements.txt

# Linux: the pip Qt wheels need X11/xcb system libraries that pip cannot install
QT_MISSING=""
if [ "$(uname -s)" = "Linux" ] && command -v ldd >/dev/null 2>&1; then
    QXCB="$(find venv -path '*/plugins/platforms/libqxcb.so' 2>/dev/null | head -n 1)"
    if [ -n "$QXCB" ]; then
        QT_LIB_DIR="$(dirname "$(dirname "$(dirname "$QXCB")")")/lib"
        QT_MISSING="$(LD_LIBRARY_PATH="$QT_LIB_DIR" ldd "$QXCB" | awk '/not found/ {print $1}' | sort -u)"
    fi
fi

echo
echo "======================================================="
echo "Installation completed successfully!"
echo "======================================================="
echo
echo "To run the simulator:"
echo "  bash scripts/run.sh"
echo

if [ -n "$QT_MISSING" ]; then
    echo "WARNING: Qt cannot open windows until these system libraries are installed:" >&2
    echo "$QT_MISSING" | sed 's/^/  /' >&2
    echo >&2
    echo "  Debian/Ubuntu:" >&2
    echo "  sudo apt install libglib2.0-0 libdbus-1-3 libfontconfig1 libxkbcommon0 libxkbcommon-x11-0 \\" >&2
    echo "      libxcb-icccm4 libxcb-image0 libxcb-keysyms1 libxcb-render0 libxcb-render-util0 \\" >&2
    echo "      libxcb-shape0 libxcb-xinerama0 libxcb-xkb1" >&2
    echo >&2
fi
