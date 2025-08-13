# PowerShell version of compile_test.bat
$ErrorActionPreference = 'Stop'
Write-Host "[DEBUG] Starting the script..."

# Check if running in PowerShell
Write-Host "[DEBUG] PowerShell detected."
Write-Host "[DEBUG] Running in PowerShell."

# Check for Python
if (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "[DEBUG] Python is installed. Proceeding to check Python version..."
    try {
        python --version
    } catch {
        Write-Host "[DEBUG] Unable to execute the Python command. Ensure Python is in the PATH."
        exit 1
    }
    Write-Host "[DEBUG] Python command works. Proceeding to compilation..."
} else {
    Write-Host "[DEBUG] Python is not installed or not in PATH. Exiting."
    exit 1
}

# Compile Python files in the current directory
Write-Host "[DEBUG] Compiling Python files in the current directory..."
try {
    python -m compileall . | Out-Null
} catch {
    Write-Host "[DEBUG] Compilation failed."
    Write-Host "Compilation failed. Please check for errors in your Python scripts."
    exit 1
}
Write-Host "[DEBUG] Compilation successful."
Write-Host "Compilation successful."
pause
