from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel
from main_window import MainWindow
from loading_screen import LoadingScreen, ModelLoaderThread

class AppManager:
    """
    Manages the loading screen and the main application window.
    """
    def __init__(self):
        self.app = QApplication([])
        self.loading_screen = LoadingScreen()
        self.main_window = None

        # Model loading thread
        self.model_loader_thread = ModelLoaderThread()
        self.model_loader_thread.progress_update.connect(self.loading_screen.update_progress)
        self.model_loader_thread.finished_loading.connect(self.on_model_loaded)

    def start(self):
        """
        Starts the application.
        """
        self.loading_screen.show()
        self.model_loader_thread.start()
        self.app.exec_()

    def on_model_loaded(self, model):
        """
        Handles the completion of model loading.
        """
        self.loading_screen.close()
        if model is not None:
            self.main_window = MainWindow(model)
            self.main_window.show()
        else:
            error_message = QLabel("Failed to load the Whisper model. Please try again later.")
            error_message.setAlignment(Qt.AlignCenter)
            error_window = QMainWindow()
            error_window.setCentralWidget(error_message)
            error_window.setWindowTitle("Error")
            error_window.setFixedSize(400, 200)
            error_window.show()
        self.app.exec_()


# Run Application
if __name__ == "__main__":
    manager = AppManager()
    manager.start()
