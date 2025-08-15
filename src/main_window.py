import logging
import threading
import base64
import tempfile
import os
logging.basicConfig(filename='debug.log', level=logging.ERROR)
from usersettings import user_settings
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env
import webbrowser
from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QPainter, QColor, QBrush, QIcon
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QSystemTrayIcon,
    QMenu, QAction, QDialog, QLabel, QLineEdit, QHBoxLayout, QComboBox, QTextEdit, QProgressBar
)
from PyQt5.QtMultimedia import QAudioProbe, QAudioBuffer
from PIL import ImageGrab
from datetime import datetime
from openai import OpenAI
import whisper
import pyaudio
import wave
import torch
import numpy as np
import silero_vad
from PyQt5.QtCore import QObject, pyqtSignal
import soundfile as sf
import sounddevice as sd
import contextlib

class RedirectStdout(QObject):
    text_written = pyqtSignal(str)

    def write(self, text):
        self.text_written.emit(text)

    def flush(self):
        pass

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Initialize Coqui TTS
class TTSManager(QObject):
    tts_initialized = pyqtSignal(bool)
    tts_initialization_started = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.tts = None
        self.interrupt_speech = threading.Event()
        self.tts_lock = threading.Lock()
        self.initialized = False
        self.stdout_redirector = RedirectStdout()
        self.initialization_thread = threading.Thread(target=self._initialize_tts_thread, daemon=True)
        self.initialization_thread.start()

    def _initialize_tts_thread(self):
        """Initialize Coqui TTS in a background thread"""
        self.tts_initialization_started.emit()
        try:
            from TTS.api import TTS
            with contextlib.redirect_stdout(self.stdout_redirector):
                self.tts = TTS(model_name="tts_models/en/ljspeech/tacotron2-DDC", progress_bar=True)
            self.initialized = True
            logging.info("Coqui TTS initialized successfully")
            self.tts_initialized.emit(True)
        except Exception as e:
            logging.error(f"Failed to initialize Coqui TTS: {e}")
            self.tts = None
            self.initialized = False
            self.tts_initialized.emit(False)

    def speak(self, text):
        if not self.initialized or self.tts is None:
            logging.error("Coqui TTS not initialized, skipping speech.")
            return

        with self.tts_lock:
            self.interrupt_speech.clear()
            try:
                self._speak_coqui(text)
            except Exception as e:
                logging.error(f"Error during TTS playback: {e}")

    def _speak_coqui(self, text):
        """Use Coqui TTS for speech synthesis and handle interruptions."""
        try:
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_file:
                tmp_path = tmp_file.name
            
            self.tts.tts_to_file(text=text, file_path=tmp_path)
            
            data, samplerate = sf.read(tmp_path)
            
            device_index = user_settings.get("audio_output_device_index", None)

            # Play audio in chunks to allow for interruption
            chunk_size = 1024
            start_pos = 0
            while start_pos < len(data) and not self.interrupt_speech.is_set():
                end_pos = start_pos + chunk_size
                chunk = data[start_pos:end_pos]
                if device_index is not None:
                    sd.play(chunk, samplerate, device=device_index)
                else:
                    sd.play(chunk, samplerate)
                sd.wait()
                start_pos = end_pos

            if self.interrupt_speech.is_set():
                logging.info("TTS playback interrupted.")
                sd.stop()

            os.unlink(tmp_path)

        except Exception as e:
            logging.error(f"Coqui TTS playback error: {e}")

    def stop_speaking(self):
        """Stop current TTS playback"""
        self.interrupt_speech.set()

# Initialize TTS manager
tts_manager = TTSManager()

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
        return response.choices[0].message.content
    except Exception as e:
        logging.error(f"Error querying ChatGPT: {e}", exc_info=True)
        return f"Error querying ChatGPT: {e}"

# Global reference to the central widget for AI voice activity
_central_widget = None

def set_central_widget(widget):
    global _central_widget
    _central_widget = widget

# Function to convert text to speech
def speak(text):
    global tts_manager, _central_widget
    
    # Start AI voice activity
    if _central_widget and hasattr(_central_widget, 'start_ai_speaking'):
        _central_widget.start_ai_speaking()
    
    try:
        tts_manager.speak(text)
    finally:
        # Stop AI voice activity
        if _central_widget and hasattr(_central_widget, 'stop_ai_speaking'):
            _central_widget.stop_ai_speaking()

def stop_speaking():
    """Safely stops the TTS playback"""
    global tts_manager
    tts_manager.stop_speaking()

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
        event.accept()

    def open_settings(self):
        settings_dialog = SettingsDialog(self)
        settings_dialog.exec_()

class CentralWidget(QWidget):
    voice_activity_updated = pyqtSignal(float)
    transcription_updated = pyqtSignal(str)

    def __init__(self, model):
        super().__init__()
        self.model = model
        self.is_active = False
        self.is_listening = False  # AI listening state
        self.has_greeted = False  # Tracks whether the greeting has been said
        self.whisper_model = model  # Use the loaded model passed from MainWindow
        self.speaking = False
        self.ai_speaking = False
        self.vad_model, self.vad_utils = torch.hub.load(repo_or_dir='snakers4/silero-vad', model='silero_vad', trust_repo=True)

        # Layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # On/Off Button
        button_row = QHBoxLayout()
        self.on_off_button = QPushButton("Start Listening", self)
        self.on_off_button.setFixedSize(160, 40)
        self.on_off_button.setEnabled(False)
        self.on_off_button.clicked.connect(self.toggle_state)
        button_row.addWidget(self.on_off_button)
        
        # On/Off Button Status Indicator
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(24, 24)
        self.status_indicator.setStyleSheet(self.get_indicator_style("grey"))
        button_row.addWidget(self.status_indicator)

        # Minimize to System Tray Button
        self.minimize_button = QPushButton("Hide to Tray", self)
        self.minimize_button.setFixedSize(120, 40)
        self.minimize_button.clicked.connect(self.minimizeToSystemTray)
        button_row.addWidget(self.minimize_button)
        
        button_row.addStretch()
        self.layout.addLayout(button_row)

        # Progress display for downloads
        self.progress_label = QLabel(self)
        self.progress_label.setText("")
        self.progress_label.setVisible(False)  # Initially hidden
        self.layout.addWidget(self.progress_label)

        # Voice Activity Visualizers
        activity_layout = QVBoxLayout()
        
        # User voice activity
        user_label = QLabel("Your Voice Activity:")
        user_label.setAlignment(Qt.AlignCenter)
        self.voice_activity_bar = QProgressBar(self)
        self.voice_activity_bar.setRange(0, 100)
        self.voice_activity_bar.setFixedSize(400, 30)
        self.voice_activity_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #4CAF50;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
            }
        """)
        
        # AI voice activity
        ai_label = QLabel("AI Voice Activity:")
        ai_label.setAlignment(Qt.AlignCenter)
        self.ai_voice_bar = QProgressBar(self)
        self.ai_voice_bar.setRange(0, 100)
        self.ai_voice_bar.setFixedSize(400, 30)
        self.ai_voice_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #2196F3;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #2196F3;
            }
        """)
        
        activity_layout.addWidget(user_label)
        activity_layout.addWidget(self.voice_activity_bar)
        activity_layout.addWidget(ai_label)
        activity_layout.addWidget(self.ai_voice_bar)
        
        self.layout.addLayout(activity_layout)

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

        # Timer to update voice activity bar
        self.voice_activity_updated.connect(self.set_voice_activity_level)

        # Connect TTS initialization signal
        tts_manager.tts_initialization_started.connect(self.on_tts_initialization_started)
        tts_manager.tts_initialized.connect(self.on_tts_initialized)

    def update_progress_text(self, text):
        # The progress bar text often ends with a carriage return '\r' to
        # rewrite the line. We'll strip whitespace to clean it up.
        self.progress_label.setText(text.strip())

    def on_tts_initialization_started(self):
        self.on_off_button.setText("Downloading TTS Model...")
        self.on_off_button.setEnabled(False)
        self.progress_label.setText("Initializing download...")
        self.progress_label.setVisible(True)

    def on_tts_initialized(self, initialized):
        if initialized:
            self.on_off_button.setEnabled(True)
            self.on_off_button.setText("Start Listening")
            self.progress_label.setText("TTS Model loaded successfully.")
        else:
            self.on_off_button.setEnabled(False)
            self.on_off_button.setText("TTS Failed to Load")
            self.progress_label.setText("Failed to load TTS Model.")
        
        # Hide the progress label after a few seconds
        QTimer.singleShot(5000, lambda: self.progress_label.setVisible(False))

    def minimizeToSystemTray(self):
        self.parent().hide()
        self.parent().tray_icon.showMessage("AI Assistant", "Minimized to system tray.")

    def set_voice_activity_level(self, level):
        # level expected in [0, 1], scale to [0, 100]
        self.voice_activity_bar.setValue(int(level * 100))

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
            self.on_off_button.setText("Start")
            self.status_indicator.setStyleSheet(self.get_indicator_style("grey"))
            stop_speaking()
            speak("Session ended.")
        else:
            self.is_listening = True
            self.on_off_button.setText("Stop")
            self.status_indicator.setStyleSheet(self.get_indicator_style("green"))
            if not self.has_greeted:
                speak("What can I help you with?")
                self.has_greeted = True
            # Start listening in a background thread
            self.listening_thread = threading.Thread(target=self.start_listening_session, daemon=True)
            self.listening_thread.start()

    def start_listening_session(self):
        try:
            while self.is_listening:
                # Interrupt speech if new input is detected
                stop_speaking()
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
            chunk = 512
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
                try:
                    data = stream.read(chunk)
                except IOError:
                    # An IOError will be raised when the stream is closed from another thread
                    # We can safely break the loop and clean up.
                    break
                
                audio_chunk_tensor = torch.from_numpy(np.frombuffer(data, dtype=np.int16).copy()).float() / 32768.0
                speech_prob = self.vad_model(audio_chunk_tensor, rate).item()
                self.voice_activity_updated.emit(speech_prob)

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

    def populate_audio_output_devices(self):
        audio = pyaudio.PyAudio()
        for i in range(audio.get_device_count()):
            dev = audio.get_device_info_by_index(i)
            if dev['maxOutputChannels'] > 0:
                self.audio_output_device_combo.addItem(dev['name'], i)
        
        current_device_index = user_settings.get("audio_output_device_index", None)
        if current_device_index is not None:
            index_to_set = self.audio_output_device_combo.findData(current_device_index)
            if index_to_set != -1:
                self.audio_output_device_combo.setCurrentIndex(index_to_set)
            else:
                logging.warning(f"Saved audio output device with index {current_device_index} not found.")
                if self.audio_output_device_combo.count() > 0:
                    self.audio_output_device_combo.setCurrentIndex(0)
                    self.save_audio_output_device()

    def save_audio_output_device(self):
        device_index = self.audio_output_device_combo.currentData()
        user_settings.set("audio_output_device_index", device_index)


    def get_indicator_style(self, color):
        return f"""
        QLabel {{
            background-color: {color};
            border-radius: 12px;
            border: 2px solid #888;
        }}
        """






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