
# Desktop-assistant-AI

Desktop-assistant-AI is an AI-powered desktop assistant designed to help users, especially coders, when they are unsure what to do next. It originally intended to take screenshots from PC or screen recording and provide it to the AI for analysis. It is not currently a useful product.

**Platform:** Windows only

## Features

- AI-powered help for coding and general desktop tasks
- Screenshot capture and context-aware assistance
- Integration with OpenAI (ChatGPT) and Whisper for speech recognition
- Text-to-speech responses
- Secure model loading with progress feedback
- Modern PyQt5 GUI

## Installation

Installation sets up and runs the app in the current folder as a stand-alone application. All files remain local to this directory, and no system-wide installation or file copying occurs.

1. Download or clone this repository.

2. Create and activate a Python virtual environment (recommended):

   ```sh
   python -m venv .venv
   .venv\Scripts\activate
   ```

3. Install dependencies:

   ```sh
   pip install -r requirements.txt
   ```

4. Compile and run the app using PowerShell scripts:

   ```powershell
   .\compile.ps1
   .\run.ps1
   ```

   This will check for Python and run the compiled application.

**See also:** [gotchas.md](gotchas.md) for troubleshooting common installation issues.

## Usage

After installation, launch the assistant using `run.bat`. The app will show a loading screen while the Whisper model loads, then present the main window for interaction.

## Developer Setup

To set up a development environment:

1. Ensure Python 3.11+ is installed.

2. Install dependencies:

   ```sh
   pip install pillow pyttsx3 openai logging PyQt5 python-dotenv openai-whisper torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
   ```

3. (Optional) Use `download_dependencies.sh` for Linux environments.

4. Compile the Python files (Windows):

   ```sh
   compile.bat
   ```

## Project Structure

- `src/` — Main source code
- `resources/` — Images and logos
- `run.bat`, `compile.bat` — Windows scripts for running and compiling
- `download_dependencies.sh` — Dependency installer for Linux

## Security Notes

See `The nature of the security vulnerability.md` for details on a Powershell script parser vulnerability related to speculative execution in batch scripts. This project is designed with security in mind, but always review scripts before running.

## License

MIT License (see LICENSE file if present)

## Credits

- AMDphreak (Author)
- OpenAI, Whisper, PyQt5, Pillow, pyttsx3, python-dotenv

## Screenshots

v0.1 - Early days screenshot

![screenshot1](<v0.1_screenshot_20241120_123944.png>)
