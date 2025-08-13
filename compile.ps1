# PowerShell version of compile.bat
$ErrorActionPreference = 'Stop'
Write-Host "[DEBUG] Starting the script..."

# Check if Python is installed
if (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "[DEBUG] Python is installed."
    try {
        python --version
    } catch {
        Write-Host "[DEBUG] Python command failed. Ensure Python is correctly installed and in PATH."
        exit 1
    }
    Write-Host "[DEBUG] Proceeding to compilation..."
} else {
    Write-Host "[DEBUG] Python is not installed. Prompting user..."
    $choice = Read-Host "Would you like to install Python now? (y/n)"
    Write-Host "[DEBUG] User chose: $choice"
    if ($choice -eq 'y') {
        Write-Host "[DEBUG] Downloading Python installer..."
        $installerPath = "$env:USERPROFILE\Downloads\python-installer.exe"
        Invoke-WebRequest -Uri "https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe" -OutFile $installerPath
        if (-not (Test-Path $installerPath)) {
            Write-Host "[DEBUG] Failed to download the Python installer."
            Write-Host "Failed to download the Python installer. Please check your internet connection and try again."
            exit 1
        }
        Write-Host "Launching the installer..."
        Start-Process -FilePath $installerPath -Wait
        Write-Host "[DEBUG] Python installation complete."
    } else {
        Write-Host "[DEBUG] User chose not to install Python."
        Write-Host "Python installation skipped. Exiting."
        exit 1
    }
}

# Compile Python files
Write-Host "[DEBUG] Compiling Python files..."
try {
    python -m compileall -q src
} catch {
    Write-Host "[DEBUG] Compilation failed."
    Write-Host "Compilation failed. Please check for errors in your Python scripts."
    exit 1
}
Write-Host "[DEBUG] Compilation successful."
Write-Host "Compilation successful."
pause
