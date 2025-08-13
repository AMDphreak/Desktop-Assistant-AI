import logging
import threading
import base64
logging.basicConfig(filename='debug.log', level=logging.ERROR)
from usersettings import user_settings
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env
import os
import webbrowser
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QBrush, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QSystemTrayIcon,
    QMenu, QAction, QDialog, QLabel, QLineEdit, QHBoxLayout, QComboBox, QTextEdit
)
from PyQt5.QtMultimedia import QAudioProbe, QAudioBuffer
from PIL import ImageGrab
import pyttsx3
from datetime import datetime
from openai import OpenAI
import whisper
import pyaudio
import wave
import torch
import numpy as np
import silero_vad

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Initialize text-to-speech
engine = pyttsx3.init()
engine.setProperty('rate', 150)  # Speed of speech
interrupt_speech = threading.Event()
engine_lock = threading.Lock()

# Screenshot function
def capture_screenshot():
    screenshot = ImageGrab.grab()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_path = f"screenshot_{timestamp}.png"
    screenshot.save(screenshot_path, "PNG")
    return screenshot_path

# Function to interact with ChatGPT
def query_chatgpt(prompt, screenshot_path=None):
    """
    Queries ChatGPT with a prompt and an optional screenshot.
    """
    user_content = [{"type": "text", "text": prompt}]

    if screenshot_path:
        try:
            with open(screenshot_path, "rb") as image_file:
                base64_image = base64.b64encode(image_file.read()).decode('utf-8')
            
            user_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{base64_image}"
                }
            })
        except Exception as e:
            logging.error(f"Error processing screenshot: {e}", exc_info=True)
            return f"Error processing screenshot: {e}"

    messages = [
        {"role": "system", "content": "You are an assistant that helps troubleshoot projects based on screenshots and questions."},
        {"role": "user", "content": user_content}
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=500
        )
        return response.choices.message.content
    except Exception as e:
        logging.error(f"Error querying ChatGPT: {e}", exc_info=True)
        return f"Error querying ChatGPT: {e}"

# Function to convert text to speech
def speak(text):
    global interrupt_speech, engine_lock
    with engine_lock:
        interrupt_speech.clear()
        engine.say(text)
        try:
            engine.runAndWait()
        except Exception:
            engine.stop()

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
    audio_level_updated = pyqtSignal(float)
    transcription_updated = pyqtSignal(str)

    def __init__(self, model):
        super().__init__()
        self.model = model
        self.is_active = False
        self.is_listening = False  # AI listening state
        self.has_greeted = False  # Tracks whether the greeting has been said
        self.whisper_model = model  # Use the loaded model passed from MainWindow
        self.speaking = False
        self.vad_model, self.vad_utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', trust_repo=True)

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

        # Audio Device Input
        self.audio_device_combo = QComboBox()
        self.populate_audio_devices()
        self.audio_device_combo.currentIndexChanged.connect(self.save_audio_device)
        self.layout.addWidget(self.audio_device_combo)

        # Transcription display
        self.transcription_display = QTextEdit()
        self.transcription_display.setReadOnly(True)
        self.layout.addWidget(self.transcription_display)
        self.transcription_updated.connect(self.transcription_display.setText)

        # Timer to update visualizer
        self.audio_level_updated.connect(self.visualizer.set_audio_level)

        # Reminder timer (30 minutes)
        self.reminder_timer = QTimer(self)
        self.reminder_timer.timeout.connect(self.remind_user)
        self.reminder_timer.start(30 * 60 * 1000)  # 30 minutes in milliseconds

    def toggle_state(self):
        """
        Toggles the AI listening session.
        """
        import threading
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
            # Start listening in a background thread
            self.listening_thread = threading.Thread(target=self.start_listening_session, daemon=True)
            self.listening_thread.start()

    def start_listening_session(self):
        global interrupt_speech
        try:
            while self.is_listening:
                # Interrupt speech if new input is detected
                interrupt_speech.set()
                # Record audio
                audio_path = self.record_audio()

                if not audio_path:
                    logging.error(f"[{datetime.now()}] No audio recorded.")
                    continue  # No audio recorded; refresh the listening loop

                # Transcribe audio with Whisper
                try:
                    result = self.whisper_model.transcribe(audio_path)
                except Exception as e:
                    logging.error(f"[{datetime.now()}] Error during transcription: {e}", exc_info=True)
                    speak(f"Error during transcription: {e}")
                    continue

                query = result.get("text", "").strip()
                if query:
                    logging.info(f"[{datetime.now()}] User said: {query}")
                    self.transcription_updated.emit(query)
                    # Respond in a separate thread so listening can continue
                    response_thread = threading.Thread(target=self.respond_to_query, args=(query,), daemon=True)
                    response_thread.start()
                else:
                    logging.warning(f"[{datetime.now()}] No valid transcription.")
                    continue

        except Exception as e:
            logging.error(f"[{datetime.now()}] Exception in interaction loop: {e}", exc_info=True)
            speak(f"An error occurred: {e}")

    def respond_to_query(self, query):
        import logging
        from datetime import datetime
        self.speaking = True
        try:
            response = query_chatgpt(query)
            logging.info(f"[{datetime.now()}] ChatGPT response: {response}")
            speak(response)
            self.transcription_updated.emit("")
        except Exception as e:
            logging.error(f"[{datetime.now()}] Error querying ChatGPT: {e}", exc_info=True)
            speak(f"Error querying ChatGPT: {e}")
        self.speaking = False

    def record_audio(self, silence_timeout=2.0):
        """
        Records audio from the microphone using VAD to detect speech.
        Recording starts when speech is detected and stops after a period of silence.
        """
        try:
            chunk = 1024
            sample_format = pyaudio.paInt16
            channels = 1
            rate = 16000
            temp_audio_file = "temp_audio.wav"

            audio = pyaudio.PyAudio()
            device_index = user_settings.get("audio_device_index", None)

            # Validate the device index
            if device_index is not None:
                try:
                    device_info = audio.get_device_info_by_index(device_index)
                    if device_info['maxInputChannels'] == 0:
                        logging.warning(f"Device at index {device_index} is not an input device. Falling back to default.")
                        device_index = None
                except OSError:
                    logging.warning(f"Invalid device index {device_index}. Falling back to default.")
                    device_index = None

            stream = audio.open(format=sample_format, channels=channels,
                                  rate=rate, input=True, frames_per_buffer=chunk,
                                  input_device_index=device_index)

            logging.info("Listening for speech...")
            frames = []
            is_speaking = False
            silence_chunks = 0
            max_silence_chunks = int(silence_timeout * rate / chunk)

            while self.is_listening:
                data = stream.read(chunk)
                
                audio_chunk_tensor = torch.from_numpy(np.frombuffer(data, dtype=np.int16).copy()).float() / 32768.0
                speech_prob = self.vad_model(audio_chunk_tensor, rate).item()
                self.audio_level_updated.emit(speech_prob)

                if speech_prob > 0.5:
                    if not is_speaking:
                        logging.info("Speech detected, recording...")
                        is_speaking = True
                        frames = [] # Start with a clean slate
                    frames.append(data)
                    silence_chunks = 0
                elif is_speaking:
                    silence_chunks += 1
                    if silence_chunks > max_silence_chunks:
                        logging.info("Silence detected, stopping recording.")
                        break
            
            stream.stop_stream()
            stream.close()
            audio.terminate()

            if not frames:
                return None

            with wave.open(temp_audio_file, 'wb') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(audio.get_sample_size(sample_format))
                wf.setframerate(rate)
                wf.writeframes(b''.join(frames))

            return temp_audio_file
        except Exception as e:
            logging.error(f"Error recording audio: {e}", exc_info=True)
            speak(f"Error recording audio: {e}")
            return None

    def remind_user(self):
        if self.is_listening:
            speak("I am still here and listening if you need help.")

    def populate_audio_devices(self):
        audio = pyaudio.PyAudio()
        for i in range(audio.get_device_count()):
            dev = audio.get_device_info_by_index(i)
            if dev['maxInputChannels'] > 0:
                self.audio_device_combo.addItem(dev['name'], i)
        
        current_device_index = user_settings.get("audio_device_index", None)
        if current_device_index is not None:
            index_to_set = self.audio_device_combo.findData(current_device_index)
            if index_to_set != -1:
                self.audio_device_combo.setCurrentIndex(index_to_set)
            else:
                logging.warning(f"Saved audio device with index {current_device_index} not found.")
                if self.audio_device_combo.count() > 0:
                    self.audio_device_combo.setCurrentIndex(0)
                    self.save_audio_device()

    def save_audio_device(self):
        device_index = self.audio_device_combo.currentData()
        user_settings.set("audio_device_index", device_index)

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
        self.audio_level = 0

    def set_audio_level(self, level):
        self.audio_level = level
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center = self.rect().center()
        max_radius = min(self.width(), self.height()) / 2
        
        # Pulsing effect based on audio level
        pulse_radius = max_radius * self.audio_level
        
        # Draw a solid circle for the base
        painter.setBrush(QBrush(QColor(0, 100, 255, 100)))
        painter.drawEllipse(center, int(max_radius), int(max_radius))

        # Draw the pulsing circle
        painter.setBrush(QBrush(QColor(0, 200, 255, 200)))
        painter.drawEllipse(center, int(pulse_radius), int(pulse_radius))




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
        self.api_key_input.setText(user_settings.get("OPENAI_API_KEY", ""))

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
        user_settings.set("OPENAI_API_KEY", new_key)
        os.environ["OPENAI_API_KEY"] = new_key
        self.close()