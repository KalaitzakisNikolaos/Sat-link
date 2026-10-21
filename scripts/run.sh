#!/usr/bin/env bash
# Launch script for Linux and macOS (advanced version with 3D)
# Run from anywhere; paths are resolved from the repo root.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "Starting Advanced Satellite Downlink Simulator (with 3D)..."
echo

if [ ! -x "venv/bin/python" ]; then
    echo "Virtual environment not found!" >&2
    echo "Please run: bash scripts/install.sh" >&2
    exit 1
fi

exec venv/bin/python main_advanced.py "$@"
