# PowerShell script to run the application.
$ErrorActionPreference = 'Stop'

# --- Prerequisite Checks ---
# 1. Check if Python is available
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python is not installed or not in PATH. Please run 'setup.ps1' to configure the environment." -ForegroundColor Red
    exit 1
}

# 2. Check if running inside a virtual environment
$venvCheck = python -c "import sys; print(hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))"
if ($venvCheck -ne 'True') {
    Write-Host "ERROR: You must activate the Python virtual environment before running this app." -ForegroundColor Red
    Write-Host "Please run '.\.venv\Scripts\Activate.ps1' first, then re-run this script." -ForegroundColor Yellow
    Write-Host "If the virtual environment does not exist, run 'setup.ps1'." -ForegroundColor Yellow
    exit 1
}

# 3. Quick check for a key dependency to infer if installation was run
try {
    python -c "import PyQt5" | Out-Null
} catch {
    Write-Host "A required package (PyQt5) is missing." -ForegroundColor Red
    Write-Host "Please run 'setup.ps1' to install all required dependencies." -ForegroundColor Yellow
    exit 1
}

# --- Run the Application ---
# --- Run the Application ---
Write-Host "Running the application..." -ForegroundColor Cyan
$env:PYTHONPATH = "$PWD\src"
python src\main.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to run the Python script. Please check for errors in your code." -ForegroundColor Red
    exit 1
}

Write-Host "Script executed successfully." -ForegroundColor Green
