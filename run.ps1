# PowerShell version of run.bat
$ErrorActionPreference = 'Stop'

# Check if Python is installed
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python is not installed. Run 'compile.ps1' in this directory to set up Python and compile the scripts." -ForegroundColor Red
    exit 1
}

# Check if running inside a virtual environment
$venvCheck = python -c "import sys; print(hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix))"
if ($venvCheck -ne 'True') {
    Write-Host "ERROR: You must activate your Python virtual environment before running this app." -ForegroundColor Red
    Write-Host "To exit the virtual environment, type: deactivate" -ForegroundColor Yellow
    Write-Host "To activate, run: .venv\Scripts\Activate.ps1. To exit the virtual environment, type: deactivate." -ForegroundColor Yellow
    $choice = Read-Host "Would you like to activate the virtual environment now? (y/n)"
    if ($choice -eq 'y') {
        & .venv\Scripts\Activate.ps1
        Write-Host "Virtual environment activated. To exit the virtual environment, type: deactivate. Please re-run this script." -ForegroundColor Green
    }
    exit 1
}

# Check Python version (require >= 3.10)
$pyVersion = python -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
$major, $minor = $pyVersion -split '\.'
if ([int]$major -lt 3 -or ([int]$major -eq 3 -and [int]$minor -lt 10)) {
    Write-Host "Python 3.10 or newer is required. Please install the correct version." -ForegroundColor Red
    exit 1
}

# Check required packages
$requirements = @('pillow','pyttsx3','openai','logging','PyQt5','python-dotenv','openai-whisper','torch','torchvision','torchaudio','usersettings','pyaudio','silero-vad')
$missing = @()
foreach ($pkg in $requirements) {
    try {
        python -c "import $pkg" | Out-Null
    } catch {
        $missing += $pkg
    }
}
if ($missing.Count -gt 0) {
    Write-Host "One or more required packages are missing: $($missing -join ', ')" -ForegroundColor Red
    Write-Host "Please run 'compile.ps1' to install dependencies." -ForegroundColor Yellow
    exit 1
}

# Check if the compiled file exists
if (-not (Test-Path "src\__pycache__\main.cpython-313.pyc")) {
    Write-Host "Compiled file not found. Please run 'compile.ps1' in this directory first." -ForegroundColor Red
    exit 1
}

# Run the compiled Python file
Write-Host "Running the compiled Python script..." -ForegroundColor Cyan
python src\__pycache__\main.cpython-313.pyc
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to run the Python script. Please check for errors in your code." -ForegroundColor Red
    exit 1
}

Write-Host "Script executed successfully." -ForegroundColor Green
pause
