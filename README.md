
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

This project uses a PowerShell script to automate the setup process. It will check for the required Python version (3.11), create a virtual environment, and install all the necessary dependencies.

1. **Download or clone this repository.**

2. **Run the setup script:**

    Open a PowerShell terminal and run the following command:

    ```powershell
    .\setup.ps1
    ```

    The script will guide you through the setup process. If you don't have Python 3.11 installed, it will offer to install it for you from the Microsoft Store.

3. **Run the application:**

    Once the setup is complete, you can launch the application with:

    ```powershell
    .\run.ps1
    ```

**See also:** [gotchas.md](gotchas.md) for troubleshooting common installation issues.

## Usage

After installation, launch the assistant using `run.ps1`. The app will show a loading screen while the Whisper and Coqui TTS models load, then present the main window for interaction.

## Developer Setup

To set up a development environment, simply follow the installation instructions above. The `setup.ps1` script will create a self-contained virtual environment in the `.venv` directory, which you can use for development.

## Project Structure

- `src/` — Main source code
- `resources/` — Images and logos
- `run.bat`, `compile.bat` — Windows scripts for running and compiling
- `download_dependencies.sh` — Dependency installer for Linux

## Security Notes

See `The nature of the security vulnerability.md` for details on a Powershell script parser vulnerability related to speculative execution in batch scripts. This project is designed with security in mind, but always review scripts before running.

## License

MIT License (see LICENSE file if present)

## Built With

- [PyQt5](https://riverbankcomputing.com/software/pyqt/intro) - The GUI framework used
- [OpenAI](https://openai.com) - For ChatGPT and Whisper integration
- [Coqui TTS](https://coqui.ai/) - For text-to-speech
- [PyAudio](https://people.csail.mit.edu/hubert/pyaudio/) - For audio I/O
- [Silero VAD](https://github.com/snakers4/silero-vad) - For voice activity detection

## Screenshots

v0.2 - PyQt5 GUI with CoquiTTS.

![screenshot](<v0.2_Screenshot_2025-08-14_235842.png>)

v0.1 - Command line with pyttsx3

![screenshot1](<v0.1_screenshot_20241120_123944.png>)
