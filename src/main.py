import os
import sys
import tempfile
import psutil
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QMessageBox
from main_window import MainWindow
from loading_screen import LoadingScreen, ModelLoaderThread

class SingleInstanceChecker:
    """
    Ensures only one instance of the application can run using a file lock.
    """
    def __init__(self):
        self.lock_file = os.path.join(tempfile.gettempdir(), 'desktop_assistant_ai.lock')
        self.lock_file_handle = None
        
    def try_acquire_lock(self):
        """Try to acquire the lock and indicate if successful."""
        try:
            # Try to create the lock file exclusively
            self.lock_file_handle = os.open(self.lock_file, os.O_CREAT | os.O_EXCL | os.O_RDWR)
            # Write PID to the lock file
            pid = str(os.getpid())
            os.write(self.lock_file_handle, pid.encode())
            return True  # Lock acquired successfully
        except FileExistsError:
            # Lock file exists, check if the original process is still running
            try:
                with open(self.lock_file, 'r') as f:
                    pid_str = f.read().strip()
                if pid_str:
                    pid = int(pid_str)
                    if psutil.pid_exists(pid):
                        # The process that created the lock is still running
                        return False
                    else:
                        # The process is gone, the lock is orphaned. Delete it.
                        print("Previous crash detected. Deleting orphaned lock file.")
                        os.remove(self.lock_file)
                        # Now try to acquire the lock again recursively
                        return self.try_acquire_lock()
            except (ValueError, FileNotFoundError):
                # Handle cases where the file is empty or malformed
                if os.path.exists(self.lock_file):
                    os.remove(self.lock_file)
                return self.try_acquire_lock()
            except Exception as e:
                print(f"Error checking for orphaned lock: {e}", file=sys.stderr)
                return False
        except Exception as e:
            # Handle other potential errors during lock acquisition
            print(f"Error acquiring lock: {e}", file=sys.stderr)
            return False # Be conservative in case of other errors
        
    def release_lock(self):
        """Release the lock when application exits."""
        try:
            if self.lock_file_handle is not None:
                os.close(self.lock_file_handle)
                self.lock_file_handle = None
            if os.path.exists(self.lock_file):
                os.remove(self.lock_file)
        except Exception as e:
            print(f"Error releasing lock: {e}", file=sys.stderr)

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
        import logging
        logging.basicConfig(filename='debug.log', level=logging.DEBUG)
        self.loading_screen.close()
        if model is not None:
            logging.debug("Model loaded successfully, showing main window.")
            self.main_window = MainWindow(model)
            # Call set_central_widget to link the main_window's central_widget
            from main_window import set_central_widget
            set_central_widget(self.main_window.central_widget)
            self.main_window.show()
        else:
            logging.error("Model is None. Showing error window.")
            error_message = QLabel("Failed to load the Whisper model. Please try again later.")
            error_message.setAlignment(Qt.AlignCenter)
            error_window = QMainWindow()
            error_window.setCentralWidget(error_message)
            error_window.setWindowTitle("Error")
            error_window.setFixedSize(400, 200)
            error_window.show()


# Run Application
if __name__ == "__main__":
    # Check for single instance
    single_instance = SingleInstanceChecker()
    
    if not single_instance.try_acquire_lock():
        app = QApplication(sys.argv) # Initialize QApplication for QMessageBox
        QMessageBox.warning(None, "Application Already Running",
                            "Desktop Assistant AI is already running. Only one instance is allowed.")
        sys.exit(1)
    
    try:
        # Ensure lock is released when app exits
        manager = AppManager()
        app = manager.app # Use manager's QApplication instance
        app.aboutToQuit.connect(single_instance.release_lock) # Ensure lock released cleanly
        manager.start()
    except Exception as e:
        single_instance.release_lock() # Ensure lock is released even on startup exception
        raise
