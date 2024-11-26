@echo off
setlocal enabledelayedexpansion

:: Debug Breakpoint: Start script
echo [DEBUG] Starting the script...

:: Check if Python is installed
where python >nul 2>nul
if %errorlevel%==0 (
    echo [DEBUG] Python is installed.
    python --version
    if %errorlevel% neq 0 (
        echo [DEBUG] Python command failed. Ensure Python is correctly installed and in PATH.
        exit /b 1
    )
    echo [DEBUG] Proceeding to compilation...
    goto :compile
)

:: Handle Python not installed
echo [DEBUG] Python is not installed. Prompting user...
echo Would you like to install Python now? (y/n)
set /p user_choice=
echo [DEBUG] User chose: !user_choice!
if /i "!user_choice!"=="y" (
    echo [DEBUG] Downloading Python installer...
    bitsadmin /transfer "PythonDownload" https://www.python.org/ftp/python/3.11.5/python-3.11.5-amd64.exe "%USERPROFILE%\Downloads\python-installer.exe"
    if %errorlevel% neq 0 (
        echo [DEBUG] Failed to download the Python installer.
        echo Failed to download the Python installer. Please check your internet connection and try again.
        exit /b 1
    )
    echo Launching the installer...
    start /wait "%USERPROFILE%\Downloads\python-installer.exe"
    if %errorlevel% neq 0 (
        echo [DEBUG] Python installation failed.
        echo Python installation failed. Please check the installer for errors.
        exit /b 1
    )
    echo [DEBUG] Python installation complete.
    goto :compile
) else (
    echo [DEBUG] User chose not to install Python.
    echo Python installation skipped. Exiting.
    exit /b 1
)

:compile
:: Debug Breakpoint: Compile Python files
echo [DEBUG] Compiling Python files...
python -m compileall .\src >nul 2>nul
if %errorlevel% neq 0 (
    echo [DEBUG] Compilation failed.
    echo Compilation failed. Please check for errors in your Python scripts.
    exit /b 1
)

echo [DEBUG] Compilation successful.
echo Compilation successful.
pause
/