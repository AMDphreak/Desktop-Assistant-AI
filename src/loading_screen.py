from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QProgressBar, QLabel
import whisper


import whisper

class ModelLoaderThread(QThread):
    """
    Thread for loading the Whisper model.
    """
    progress_update = pyqtSignal(int, str)  # Emits progress percentage and step description
    finished_loading = pyqtSignal(object)  # Emits the loaded model

    def run(self):
        """
        Load the Whisper model with progress updates.
        """
        try:
            steps = [
                (10, "Initializing Whisper model"),
                (40, "Downloading model weights"),
                (70, "Configuring model"),
                (100, "Finalizing setup"),
            ]

            for progress, step in steps:
                self.progress_update.emit(progress, step)
                self.sleep(1)  # Simulate time for each step

            # Load the actual Whisper model securely
            model = whisper.load_model("base")
            self.progress_update.emit(100, "Model loaded successfully!")
            self.finished_loading.emit(model)

        except Exception as e:
            import logging
            logging.basicConfig(filename='debug.log', level=logging.DEBUG)
            logging.error(f"Exception in Whisper model loading: {e}", exc_info=True)
            self.finished_loading.emit(None)
            self.progress_update.emit(100, f"Error loading model: {e}")



class LoadingScreen(QWidget):
    """
    Displays a loading screen with a progress bar and status label.
    """
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Loading Whisper Model")
        self.setFixedSize(400, 200)

        # Layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Progress bar
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        # Status label
        self.status_label = QLabel("Initializing...", self)
        self.status_label.setAlignment(Qt.AlignCenter)

        self.layout.addWidget(self.progress_bar)
        self.layout.addWidget(self.status_label)

    def update_progress(self, value, status):
        """
        Update the progress bar and status label.
        """
        self.progress_bar.setValue(value)
        self.status_label.setText(status)
