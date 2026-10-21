# Launch script for advanced version with 3D
# Run from anywhere; paths are resolved from the repo root.
Set-Location (Split-Path -Parent $PSScriptRoot)

Write-Host "Starting Advanced Satellite Downlink Simulator (with 3D)..." -ForegroundColor Green
Write-Host ""

# Activate virtual environment
if (Test-Path "venv\Scripts\Activate.ps1") {
    & ".\venv\Scripts\Activate.ps1"
} else {
    Write-Host " Virtual environment not found!" -ForegroundColor Red
    Write-Host "Please run scripts\install.ps1 first" -ForegroundColor Yellow
    exit 1
}

# Run advanced simulator
python main_advanced.py
