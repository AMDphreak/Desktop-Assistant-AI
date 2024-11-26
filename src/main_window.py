import logging
logging.basicConfig(filename='debug.log', level=logging.ERROR)
import usersettings
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env
import os
import webbrowser
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPainter, QColor, QBrush, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QSystemTrayIcon,
    QMenu, QAction, QDialog, QLabel, QLineEdit, QHBoxLayout
)
from PyQt5.QtMultimedia import QAudioProbe, QAudioBuffer
from PIL import ImageGrab
import pyttsx3
from datetime import datetime
from openai import OpenAI
import whisper
import pyaudio
import wave

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Initialize text-to-speech
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Speed of speech

# Screenshot function
def capture_screenshot():
    screenshot = ImageGrab.grab()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = f"screenshot_{timestamp}.png"
    screenshot.save(screenshot_path, "PNG")
    return screenshot_path

# Function to interact with ChatGPT
def query_chatgpt(prompt, screenshot_path=None):
    # Base prompt
    messages = [{"role": "system", "content": "You are an assistant that helps troubleshoot projects based on screenshots and questions."}]
    messages.append({"role": "user", "content": prompt})

    # Include screenshot if provided
    files = None
    if screenshot_path:
        with open(screenshot_path, "rb") as file:
            files = {"file": file}

    # Call the OpenAI API
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error querying ChatGPT: {e}"

# Function to convert text to speech
def speak(text):
    engine.say(text)
    engine.runAndWait()

class MainWindow(QMainWindow):
    """
    Main application window.
    """
    def __init__(self, model):
        super().__init__()
        self.setWindowTitle("AI Assistant with Whisper")
        self.setFixedSize(600, 600)

        # Set up the central widget with the Whisper model
        self.central_widget = CentralWidget(model)
        self.setCentralWidget(self.central_widget)
        
        # Initialize UI components
        self.central_widget = CentralWidget()
        self.setCentralWidget(self.central_widget)

        # Create menu bar and settings
        self.settings_action = QAction("Settings", self)
        self.settings_action.triggered.connect(self.open_settings)
        self.menu_bar = self.menuBar()
        self.menu_bar.addAction(self.settings_action)

        # System tray integration
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("resources/Desktop User AI logo.png"))
        self.tray_icon_menu = QMenu(self)
        restore_action = QAction("Restore", self)
        restore_action.triggered.connect(self.show)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(QApplication.instance().quit)
        self.tray_icon_menu.addAction(restore_action)
        self.tray_icon_menu.addAction(exit_action)
        self.tray_icon.setContextMenu(self.tray_icon_menu)
        self.tray_icon.activated.connect(self.show)
        self.tray_icon.show()

        # Close to tray behavior
        self.setWindowFlags(self.windowFlags() | Qt.WindowMinimizeButtonHint)
        self.setAttribute(Qt.WA_DeleteOnClose)

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray_icon.showMessage("AI Assistant", "Minimized to system tray.")

    def open_settings(self):
        settings_dialog = SettingsDialog(self)
        settings_dialog.exec_()

class CentralWidget(QWidget):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.is_active = False
        self.is_listening = False  # AI listening state
        self.has_greeted = False  # Tracks whether the greeting has been said
        self.whisper_model = whisper.load_model("base")  # Load Whisper model

        # Layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # On/Off Button
        self.on_off_button = QPushButton(self)
        self.on_off_button.setFixedSize(200, 200)
        self.on_off_button.setStyleSheet(self.get_button_style("grey"))
        self.on_off_button.clicked.connect(self.toggle_state)

        # Visualizer
        self.visualizer = VoiceVisualizer(self)
        self.visualizer.setFixedSize(400, 400)

        self.layout.addWidget(self.visualizer, alignment=Qt.AlignCenter)
        self.layout.addWidget(self.on_off_button, alignment=Qt.AlignCenter)

        # Timer to update visualizer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.visualizer.update_visualizer)
        self.timer.start(50)

        # Reminder timer (30 minutes)
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self.remind_user)
        self.reminder_timer.start(30 * 60 * 1000)  # 30 minutes in milliseconds

    def toggle_state(self):
        """
        Toggles the AI listening session.
        """
        if self.is_listening:
            self.is_listening = False
            self.on_off_button.setStyleSheet(self.get_button_style("grey"))
            speak("Session ended.")
        else:
            self.is_listening = True
            self.on_off_button.setStyleSheet(self.get_button_style("green"))
            if not self.has_greeted:
                speak("Session started. I am listening. What can I help you with?")
                self.has_greeted = True
            else:
                speak("Session started. I am listening.")
            self.start_listening_session()

    def start_listening_session(self):
        """
        Handles the AI listening session using Whisper for transcription.
        """
        try:
            while self.is_listening:
                # Record audio
                audio_path = self.record_audio()

                if not audio_path:
                    continue  # No audio recorded; refresh the listening loop

                # Transcribe audio with Whisper
                result = self.whisper_model.transcribe(audio_path)

                query = result.get("text", "").strip()
                if query:
                    speak(f"Processing your request: {query}")
                    response = query_chatgpt(query)
                    speak(response)
                else:
                    # If no valid transcription, silently refresh
                    continue

        except Exception as e:
            speak(f"An error occurred: {e}")

    def record_audio(self, duration=10):
        """
        Records audio from the microphone and saves it to a temporary file.
        Returns the file path of the recorded audio.
        """
        try:
            chunk = 1024  # Buffer size
            sample_format = pyaudio.paInt16  # 16-bit audio
            channels = 1  # Mono audio
            rate = 16000  # 16 kHz sample rate
            temp_audio_file = "temp_audio.wav"

            audio = pyaudio.PyAudio()
            stream = audio.open(format=sample_format, channels=channels,
                                rate=rate, input=True, frames_per_buffer=chunk)

            frames = []

            for _ in range(0, int(rate / chunk * duration)):
                data = stream.read(chunk)
                frames.append(data)

            # Stop and close the stream
            stream.stop_stream()
            stream.close()
            audio.terminate()

            # Save the recorded audio to a file
            with wave.open(temp_audio_file, 'wb') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(audio.get_sample_size(sample_format))
                wf.setframerate(rate)
                wf.writeframes(b''.join(frames))

            return temp_audio_file
        except Exception as e:
            speak(f"Error recording audio: {e}")
            return None

    def remind_user(self):
        if self.is_listening:
            speak("I am still here and listening if you need help.")

    def get_button_style(self, color):
        return f"""
        QPushButton {{
            border-radius: 100px;
            background-color: {color};
        }}
        """


class VoiceVisualizer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.frequency_data = [0] * 50

    def update_visualizer(self):
        self.frequency_data = [min(100, value + 1) for value in self.frequency_data]  # Simulated data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = self.rect().center()
        max_radius = min(self.width(), self.height()) / 2

        for i, value in enumerate(self.frequency_data):
            angle = i * (360 / len(self.frequency_data))
            radius = max_radius * (value / 100)
            color = QColor(0, 255 - value * 2, 255)
            painter.setBrush(QBrush(color))
            x = center.x() + radius * 0.5 * (-1)**i
            y = center.y() + radius * 0.5 * (-1)**(i + 1)
            painter.drawEllipse(int(x), int(y), 10, 10)


# Voice Visualizer Class
class VoiceVisualizer(QWidget):
    """
    Visualizes audio frequencies in a circular pattern.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.frequency_data = [0] * 50  # Simulated frequency data for visualization

    def update_visualizer(self):
        """
        Update the frequency data (simulated for now).
        """
        self.frequency_data = [min(100, value + 1) for value in self.frequency_data]  # Simulate data
        self.update()

    def paintEvent(self, event):
        """
        Custom paint event for drawing the visualizer.
        """
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = self.rect().center()
        max_radius = min(self.width(), self.height()) / 2

        for i, value in enumerate(self.frequency_data):
            angle = i * (360 / len(self.frequency_data))
            radius = max_radius * (value / 100)
            color = QColor(0, 255 - value * 2, 255)
            painter.setBrush(QBrush(color))
            x = center.x() + radius * 0.5 * (-1)**i
            y = center.y() + radius * 0.5 * (-1)**(i + 1)
            painter.drawEllipse(int(x), int(y), 10, 10)


# Settings Dialog Class
class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setFixedSize(400, 200)

        # Layout
        layout = QVBoxLayout()
        self.setLayout(layout)

        # API Key Input
        api_key_label = QLabel("OpenAI API Key:")
        self.api_key_input = QLineEdit()
        self.api_key_input.setPlaceholderText("Enter your API key")
        self.api_key_input.setText(os.environ.get("OPENAI_API_KEY", ""))

        # Open API Key URL Button
        open_api_url_button = QPushButton("Generate API Key")
        open_api_url_button.clicked.connect(self.open_api_key_url)

        # Save Button
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_api_key)


        # Add widgets to layout
        layout.addWidget(api_key_label)
        layout.addWidget(self.api_key_input)
        layout.addWidget(open_api_url_button)
        layout.addWidget(save_button)

    def open_api_key_url(self):
        webbrowser.open("https://platform.openai.com/account/api-keys")

    def save_api_key(self):
        new_key = self.api_key_input.text().strip()
        with open(".env", "w") as f:
            f.write(f"OPENAI_API_KEY={new_key}\n")
        os.environ["OPENAI_API_KEY"] = new_key
        self.close()