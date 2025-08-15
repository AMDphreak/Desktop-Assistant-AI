# PowerShell script to set up the application environment.
$ErrorActionPreference = 'Stop'
Write-Host "Starting environment setup..."

# --- Prerequisite Checks ---
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    Write-Host "The Python version Launcher ('py.exe') is not installed or not in your PATH." -ForegroundColor Red
    $choice = Read-Host "Would you like to install the Python Launcher now? (y/n)"
    if ($choice -eq 'y') {
        Write-Host "Installing the Python Launcher via winget..."
        winget install Python.Launcher
        Write-Host "Python Launcher installation complete."
    } else {
        Write-Host "The Python Launcher is required to continue. Exiting." -ForegroundColor Red
        exit 1
    }
}

# Check for Python 3.11
try {
    Write-Host "Testing python availability: Getting python version..."
    $pythonVersion = & py -3.11 --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "$pythonVersion is already installed." -ForegroundColor Green
    } else {
        throw "Python 3.11 is not installed."
    }
} catch {
    Write-Host "Python 3.11 is not installed." -ForegroundColor Red
    $choice = Read-Host "Would you like to install Python 3.11 from the Microsoft Store now? (y/n)"
    if ($choice -eq 'y') {
        Write-Host "Installing Python 3.11 via winget..."
        winget install --id 9NRWMJP3717K
        Write-Host "Python 3.11 installation complete." -ForegroundColor Green
    } else {
        Write-Host "Python 3.11 installation skipped. Exiting." -ForegroundColor Red
        exit 1
    }
}

# --- Virtual Environment Setup ---
if (-not (Test-Path ".venv")) {
    Write-Host "Creating Python 3.11 virtual environment..."
    py -3.11 -m venv .venv
    Write-Host "Virtual environment created successfully." -ForegroundColor Green
    Write-Host "Next step: Please activate the virtual environment by running: .\.venv\Scripts\Activate.ps1" -ForegroundColor Yellow
    Write-Host "After activation, please re-run this setup script to install dependencies." -ForegroundColor Yellow
    
    $choice = Read-Host "Would you like to activate the environment and continue setup now? (y/n)"
    if ($choice -eq 'y') {
        & .\.venv\Scripts\Activate.ps1
        Write-Host "Virtual environment activated. Re-running setup to install dependencies..." -ForegroundColor Green
        .\setup.ps1
        exit 0
    } else {
        Write-Host "Setup paused. Please activate the environment and re-run the script manually." -ForegroundColor Yellow
        exit 0
    }
}

# --- Venv Activation Check ---
$venvCheck = python -c "import sys; print(hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))"
if ($venvCheck -ne 'True') {
    Write-Host "Virtual environment detected but not active." -ForegroundColor Yellow
    Write-Host "You can activate with '.\.venv\Scripts\Activate.ps1' then re-run this script to continue setup." -ForegroundColor Yellow
    Write-Host -NoNewline "Would you like us to activate the virtual environment for you? (y/n) " -ForegroundColor Cyan
    $choice = Read-Host
    if ($choice -eq 'y') {
        try {
            & .\.venv\Scripts\Activate.ps1
            Write-Host "Virtual environment activated for this shell session. Continuing setup..." -ForegroundColor Green
        } catch {
            Write-Host "Failed to activate the virtual environment. Please activate it manually by running '.\.venv\Scripts\Activate.ps1' and then re-run this script." -ForegroundColor Red
            exit 1
        }
    } else {
        Write-Host "Setup cannot continue without an active virtual environment. Please activate it manually and re-run the script." -ForegroundColor Yellow
        exit 1
    }
}
Write-Host "Virtual environment is active. Proceeding with setup." -ForegroundColor Green

# --- Install Dependencies ---
Write-Host "Installing required packages from requirements.txt..." -ForegroundColor Cyan
Write-Host "A new window will open to show the installation progress."
Write-Host "The installation log will be saved to pip_install.log"
$python_exe = "$PWD\.venv\Scripts\python.exe"
$command = "& '$python_exe' -m pip install -r requirements.txt | Tee-Object -FilePath pip_install.log; Read-Host 'Installation complete. Log file saved to pip_install.log. Press Enter to close this window.' "

if (Get-Command pwsh -ErrorAction SilentlyContinue) {
    Start-Process pwsh -ArgumentList "-NoExit", "-Command", "$command" -Wait
} else {
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "$command" -Wait
}

Write-Host "Setup successful. A detailed log is available in 'setup.log'." -ForegroundColor Green
Write-Host "To run the application, execute the run script: .\run.ps1" -ForegroundColor Yellow
Write-Host "To exit the virtual environment, enter 'deactivate' command." -ForegroundColor Yellow
pause
