
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
            # Check if we have already restarted to apply environment variables
            if not os.environ.get('OPEN_RAZER_RESTARTED'):
                logging.info("Checking Qt plugins configuration for macOS (Pre-launch)...")

                # Method 1: Ask QLibraryInfo
                plugin_path = QLibraryInfo.location(QLibraryInfo.PluginsPath)
                logging.info(f"QLibraryInfo.PluginsPath: {plugin_path}")

                # Method 2: Check relative to PyQt5 package (often robust in venvs)
                pkg_path = os.path.dirname(PyQt5.__file__)
                logging.info(f"PyQt5 package path: {pkg_path}")

                potential_paths = []
                if plugin_path:
                    potential_paths.append(plugin_path)

                # Common layouts
                potential_paths.extend([
                    os.path.join(pkg_path, 'Qt5', 'plugins'),
                    os.path.join(pkg_path, 'Qt', 'plugins'),
                    os.path.join(pkg_path, 'plugins'),
                ])

                found_plugin_dir = None
                found_platforms_dir = None

                for p in potential_paths:
                    cocoa_path = os.path.join(p, 'platforms', 'libqcocoa.dylib')
                    if os.path.exists(cocoa_path):
                        logging.info(f"Found 'libqcocoa.dylib' at: {cocoa_path}")
                        found_plugin_dir = p
                        found_platforms_dir = os.path.join(p, 'platforms')
                        break
                    else:
                        logging.debug(f"Checked for cocoa plugin at {cocoa_path} (not found)")

                # Try to locate the 'lib' directory (Qt Frameworks)
                # It is usually parallel to 'plugins' or 'bin' in 'Qt5' folder.
                # e.g. .../PyQt5/Qt5/lib
                found_lib_dir = None
                if found_plugin_dir:
                    # found_plugin_dir is usually .../Qt5/plugins
                    # Try ../lib
                    potential_lib = os.path.join(os.path.dirname(found_plugin_dir), 'lib')
                    if os.path.exists(potential_lib):
                        found_lib_dir = potential_lib
                        logging.info(f"Found Qt lib directory at: {found_lib_dir}")

                env_updates = {}

                # Only set variables if they aren't already set, to respect user overrides
                if found_plugin_dir and 'QT_PLUGIN_PATH' not in os.environ:
                    logging.info(f"Setting QT_PLUGIN_PATH to: {found_plugin_dir}")
                    env_updates['QT_PLUGIN_PATH'] = found_plugin_dir

                if found_platforms_dir and 'QT_QPA_PLATFORM_PLUGIN_PATH' not in os.environ:
                    logging.info(f"Setting QT_QPA_PLATFORM_PLUGIN_PATH to: {found_platforms_dir}")
                    env_updates['QT_QPA_PLATFORM_PLUGIN_PATH'] = found_platforms_dir

                if debug_mode and 'QT_DEBUG_PLUGINS' not in os.environ:
                    logging.info("Enabling QT_DEBUG_PLUGINS for debug mode")
                    env_updates['QT_DEBUG_PLUGINS'] = '1'

                if found_lib_dir:
                    current_dyld = os.environ.get('DYLD_LIBRARY_PATH', '')
                    new_dyld = f"{found_lib_dir}:{current_dyld}" if current_dyld else found_lib_dir
                    logging.info(f"Updating DYLD_LIBRARY_PATH with: {found_lib_dir}")
                    env_updates['DYLD_LIBRARY_PATH'] = new_dyld

                    current_framework = os.environ.get('DYLD_FRAMEWORK_PATH', '')
                    new_framework = f"{found_lib_dir}:{current_framework}" if current_framework else found_lib_dir
                    logging.info(f"Updating DYLD_FRAMEWORK_PATH with: {found_lib_dir}")
                    env_updates['DYLD_FRAMEWORK_PATH'] = new_framework

                if env_updates:
                    logging.info("Restarting application to apply environment variables...")
                    env = os.environ.copy()
                    env.update(env_updates)
                    env['OPEN_RAZER_RESTARTED'] = '1'

                    # Flush stdout/stderr before restart
                    sys.stdout.flush()
                    sys.stderr.flush()

                    try:
                        os.execvpe(sys.executable, [sys.executable] + sys.argv, env)
                    except OSError as e:
                        logging.error(f"Failed to restart application: {e}")
                        # Fallback: try setting os.environ locally
                        os.environ.update(env_updates)
            else:
                logging.info("Environment variables applied via restart.")

            # Explicitly add library paths to Qt (works even if env vars are stripped by SIP)
            if 'QT_PLUGIN_PATH' in os.environ:
                logging.info(f"Adding library path from environment: {os.environ['QT_PLUGIN_PATH']}")
                QCoreApplication.addLibraryPath(os.environ['QT_PLUGIN_PATH'])
            elif 'found_plugin_dir' in locals() and found_plugin_dir:
                 # Should not happen in restart branch unless we re-detect, but safe to add
                 logging.info(f"Adding library path from detection: {found_plugin_dir}")
                 QCoreApplication.addLibraryPath(found_plugin_dir)

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
