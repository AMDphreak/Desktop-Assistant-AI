@echo off
setlocal enabledelayedexpansion
@echo off
setlocal enabledelayedexpansion

:: Check if Python is installed
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo Python is not installed. Please run 'compile.bat' in this directory to set up Python and compile the scripts.
    exit /b 1
)

:: Check if the compiled file exists
if not exist "src\__pycache__\main.cpython-313.pyc" (
    echo Compiled file not found. Please run 'compile.bat' in this directory first.
    exit /b 1
)

:: Run the compiled Python file
set PYTHONPYCACHEPREFIX=src\__pycache__
echo Running the compiled Python script...
python src\__pycache__\main.cpython-313.pyc
if %errorlevel% neq 0 (
    echo Failed to run the Python script. Please check for errors in your code.
    exit /b 1
)

echo Script executed successfully.
pause
