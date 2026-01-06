
#!/usr/bin/env python3

import argparse
import logging
import os
import sys

APP_NAME = "Open Razer macOS Control"
LOG_FILE_BASENAME = "open_razer_macos_control_app.log"

if getattr(sys, 'frozen', False):
    frameworks_dir = os.path.join(os.path.dirname(sys.executable), '..', 'Frameworks')
    os.environ['DYLD_LIBRARY_PATH'] = frameworks_dir

def setup_logging(debug_mode: bool):
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
    log_level = logging.DEBUG if debug_mode else logging.INFO

    handlers = [logging.FileHandler(log_file, mode=log_mode)]
    if debug_mode:
        handlers.append(logging.StreamHandler(sys.stdout))

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=handlers
    )

    logging.info("="*20 + f" {APP_NAME} Started " + "="*20)
    logging.info(f"Python: {sys.version}")
    logging.info(f"Platform: {sys.platform}")
    logging.info(f"Executable path: {sys.executable}")
    logging.info(f"Arguments: {sys.argv}")
    logging.info(f"Log path: {log_file}")
    if debug_mode:
        logging.info("Debug mode enabled.")

def main():
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument('--debug', '-d', action='store_true', help='Enable debug mode (verbose logging to console and file)')
    parser.add_argument('--prod', action='store_true', help='Enable production mode (file logging only, default)')
    args = parser.parse_args()

    debug_mode = args.debug
    # --prod is default, so if --prod is set we don't change anything unless debug was also set, but let's assume debug takes precedence or they are mutually exclusive.
    # Current implementation: debug=True wins. If both false, debug=False.

    setup_logging(debug_mode)

    # In debug mode, scan and log devices immediately.
    # This ensures that even if the GUI crashes (e.g. PyQt plugin issues),
    # the user still gets the PID information they need.
    if debug_mode:
        logging.info("Debug mode: performing early device scan...")
        try:
            from razer_common import scan_razer_devices
            scan_razer_devices(debug_mode=True)
        except Exception as e:
            logging.error(f"Early scan failed: {e}")

    try:
        logging.info("Importing UI modules...")
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QLibraryInfo, QCoreApplication
        import PyQt5
        from razer_ui import MainWindow
        logging.info("Imports completed successfully.")

        # Attempt to fix missing plugin issue on macOS
        if sys.platform == 'darwin':
            logging.info("Checking Qt plugins configuration for macOS...")

            # Method 1: Ask QLibraryInfo
            plugin_path = QLibraryInfo.location(QLibraryInfo.PluginsPath)
            if plugin_path:
                logging.info(f"QLibraryInfo.PluginsPath: {plugin_path}")

            # Method 2: Check relative to PyQt5 package
            pkg_path = os.path.dirname(PyQt5.__file__)
            logging.info(f"PyQt5 package path: {pkg_path}")

            potential_paths = []
            if plugin_path:
                potential_paths.append(plugin_path)

            potential_paths.extend([
                os.path.join(pkg_path, 'Qt5', 'plugins'),
                os.path.join(pkg_path, 'Qt', 'plugins'),
                os.path.join(pkg_path, 'plugins'),
            ])

            found_plugin_dir = None
            for p in potential_paths:
                cocoa_path = os.path.join(p, 'platforms', 'libqcocoa.dylib')
                if os.path.exists(cocoa_path):
                    logging.info(f"Found 'libqcocoa.dylib' at: {cocoa_path}")
                    found_plugin_dir = p
                    break

            if found_plugin_dir:
                # Explicitly tell Qt where to find plugins
                logging.info(f"Adding library path: {found_plugin_dir}")
                QCoreApplication.addLibraryPath(found_plugin_dir)

                # Also set env var for good measure (though SIP might strip it)
                if 'QT_PLUGIN_PATH' not in os.environ:
                    os.environ['QT_PLUGIN_PATH'] = found_plugin_dir

        logging.info("Creating QApplication...")
        app = QApplication(sys.argv)
        logging.info("QApplication created.")

        logging.info("Creating MainWindow from razer_ui...")
        window = MainWindow(debug_mode=debug_mode)
        logging.info("MainWindow created.")

        window.show()
        logging.info("Application window displayed.")

        logging.info("Starting QApplication event loop...")
        exit_code = app.exec_()
        logging.info(f"Application exited with code: {exit_code}")
        logging.info("="*20 + f" {APP_NAME} Terminated " + "="*20 + "\n")
        sys.exit(exit_code)

    except ImportError as import_err:
        logging.critical(f"Critical import error: {import_err}. Application cannot start.", exc_info=True)
        print(f"Import error: {import_err}", file=sys.stderr)
        sys.exit(1)
    except Exception as general_err:
        logging.critical(f"Unexpected critical error: {general_err}", exc_info=True)
        print(f"Critical error: {general_err}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
