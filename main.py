
#!/usr/bin/env python3

import logging
import os
import sys

APP_NAME = "Open Razer macOS Control"
LOG_FILE_BASENAME = "open_razer_macos_control_app.log"

if getattr(sys, 'frozen', False):
    frameworks_dir = os.path.join(os.path.dirname(sys.executable), '..', 'Frameworks')
    os.environ['DYLD_LIBRARY_PATH'] = frameworks_dir

try:
    log_dir = os.path.expanduser("~/Library/Logs")
    if not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, LOG_FILE_BASENAME)
    log_exists = os.path.exists(log_file)
except OSError:
    log_dir = os.path.expanduser("~")
    log_file = os.path.join(log_dir, LOG_FILE_BASENAME)
    log_exists = os.path.exists(log_file)

log_mode = 'a' if log_exists else 'w'
logging.basicConfig(
    filename=log_file,
    filemode=log_mode,
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logging.info("="*20 + f" {APP_NAME} Started " + "="*20)
logging.info(f"Python: {sys.version}")
logging.info(f"Platform: {sys.platform}")
logging.info(f"Executable path: {sys.executable}")
logging.info(f"Arguments: {sys.argv}")
logging.info(f"Log path: {log_file}")

try:
    logging.info("Importing UI modules...")
    from PyQt5.QtWidgets import QApplication
    from razer_ui import MainWindow
    logging.info("Imports completed successfully.")

    def main():
        logging.info("Creating QApplication...")
        app = QApplication(sys.argv)
        logging.info("QApplication created.")

        logging.info("Creating MainWindow from razer_ui...")
        window = MainWindow()
        logging.info("MainWindow created.")

        window.show()
        logging.info("Application window displayed.")

        logging.info("Starting QApplication event loop...")
        exit_code = app.exec_()
        logging.info(f"Application exited with code: {exit_code}")
        sys.exit(exit_code)

    if __name__ == "__main__":
        main()

except ImportError as import_err:
    logging.critical(f"Critical import error: {import_err}. Application cannot start.", exc_info=True)
    sys.exit(f"Import error: {import_err}")
except Exception as general_err:
    logging.critical(f"Unexpected critical error: {general_err}", exc_info=True)
    sys.exit(f"Critical error: {general_err}")
finally:
    logging.info("="*20 + f" {APP_NAME} Terminated " + "="*20 + "\n")
