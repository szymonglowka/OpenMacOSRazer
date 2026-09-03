#!/usr/bin/env python3
"""Razer Battery Tray — lightweight macOS menu bar battery monitor for Razer mice."""

import sys
import os
import time
import logging
import subprocess
import threading
import traceback
from logging.handlers import RotatingFileHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import rumps
from razer_common import scan_razer_devices, get_battery_level, get_charging_status
from settings import Settings

# --- Constants ---
DISCONNECTED_POLL = 30       # seconds — faster polling when device lost
WAKE_DELAY = 2.0             # seconds to wait after wake for USB re-enumeration
STALENESS_THRESHOLD = 600    # seconds (10 min) — force refresh if older than this
MAX_CONSECUTIVE_FAILURES = 3 # show warning icon after this many failures
MAX_FAILURE_BACKOFF = 300     # seconds — cap exponential backoff at 5 minutes
ACCESS_HINT_COOLDOWN = 900    # seconds — avoid spamming repeated remediation hints
INPUT_MONITORING_SETTINGS_URL = "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent"

POLL_CHOICES = {
    60: "1 minute",
    300: "5 minutes",
    600: "10 minutes",
    900: "15 minutes",
}

THRESHOLD_CHOICES = {
    0: "Off",
    10: "10%",
    15: "15%",
    20: "20%",
}

DISPLAY_CHOICES = {
    "icon_percent": "Icon + percentage",
    "percent_only": "Percentage only",
    "icon_only": "Icon only",
}

LAUNCH_AGENT_LABEL = "com.forest.razer-battery-tray"
LAUNCH_AGENT_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{LAUNCH_AGENT_LABEL}.plist")

# Battery icon filenames (without extension) keyed by state
ICON_NAMES = {
    "critical": "battery_critical",
    "low": "battery_low",
    "medium": "battery_medium",
    "full": "battery_full",
    "charging_low": "battery_charging_low",
    "charging": "battery_charging",
    "disconnected": "battery_disconnected",
}


def _resolve_icon_dir():
    """Locate the battery_icons directory (works in dev and py2app bundle)."""
    # py2app sets RESOURCEPATH inside the .app bundle
    resource_path = os.environ.get("RESOURCEPATH")
    if resource_path:
        d = os.path.join(resource_path, "battery_icons")
        if os.path.isdir(d):
            return d
    # Development: relative to this file
    here = os.path.dirname(os.path.abspath(__file__))
    d = os.path.join(here, "resources", "battery_icons")
    if os.path.isdir(d):
        return d
    return None

# --- Logging setup ---
LOG_PATH = os.path.expanduser("~/Library/Logs/razer-battery-tray.log")
os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)

logger = logging.getLogger("razer_battery_tray")
logger.setLevel(logging.DEBUG)

_handler_exists = any(
    isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == LOG_PATH
    for h in logger.handlers
)
if not _handler_exists:
    _handler = RotatingFileHandler(LOG_PATH, maxBytes=5 * 1024 * 1024, backupCount=3)
    _handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(_handler)
else:
    _handler = next(
        h for h in logger.handlers
        if isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == LOG_PATH
    )

# Route razer_common logs to the same file so HID errors are visible
logging.getLogger("razer_common").setLevel(logging.DEBUG)
if _handler not in logging.getLogger("razer_common").handlers:
    logging.getLogger("razer_common").addHandler(_handler)


def _setup_wake_observer(callback):
    """Register for NSWorkspaceDidWakeNotification. Returns observer to prevent GC."""
    try:
        import objc
        from Foundation import NSObject
        from AppKit import NSWorkspace

        class WakeObserver(NSObject):
            def initWithCallback_(self, cb):
                self = objc.super(WakeObserver, self).init()
                if self is None:
                    return None
                self._callback = cb
                return self

            def handleWake_(self, notification):
                try:
                    self._callback()
                except Exception:
                    logger.error("Wake callback error: %s", traceback.format_exc())

        observer = WakeObserver.alloc().initWithCallback_(callback)
        center = NSWorkspace.sharedWorkspace().notificationCenter()
        center.addObserver_selector_name_object_(
            observer,
            "handleWake:",
            "NSWorkspaceDidWakeNotification",
            None,
        )
        logger.info("Wake observer registered")
        return observer
    except Exception:
        logger.warning("Could not register wake observer: %s", traceback.format_exc())
        return None


def _check_razer_drivers():
    """Check if Razer DriverKit extensions are loaded."""
    try:
        result = subprocess.run(
            ["systemextensionsctl", "list"],
            capture_output=True, text=True, timeout=5,
        )
        output = result.stdout + result.stderr
        matches = [l for l in output.splitlines() if "razer" in l.lower()]
        if result.returncode != 0:
            logger.warning("systemextensionsctl returned code %d: %s",
                           result.returncode, result.stderr.strip())
        return matches
    except Exception as e:
        logger.warning("Failed to check Razer drivers: %s", e)
        return []


class RazerBatteryApp(rumps.App):
    def __init__(self):
        super().__init__("", quit_button=None)
        self.settings = Settings()
        self.device = None
        self.low_battery_notified = False

        # Battery icons
        self._icon_dir = _resolve_icon_dir()
        if self._icon_dir:
            logger.info("Battery icons found: %s", self._icon_dir)
        else:
            logger.warning("Battery icons not found, using emoji fallback")

        # Menu items
        self.device_name_item = rumps.MenuItem("No device", callback=None)
        self.refresh_item = rumps.MenuItem("Refresh Now", callback=self.refresh)
        self.open_permissions_item = rumps.MenuItem(
            "Open Input Monitoring Settings", callback=self._open_input_monitoring_settings
        )
        self.open_log_item = rumps.MenuItem("Open Log File", callback=self._open_log_file)
        self.quit_item = rumps.MenuItem("Quit", callback=rumps.quit_application)

        # Settings submenu
        self.settings_menu = rumps.MenuItem("Settings")
        self._build_settings_menu()

        self.menu = [
            self.device_name_item, None,
            self.refresh_item, None,
            self.open_permissions_item,
            self.open_log_item, None,
            self.settings_menu, None,
            self.quit_item,
        ]
        self._set_icon("disconnected")
        self.title = " --" if self._icon_dir else "\U0001f50b --"

        # State tracking
        self.last_successful_read = 0.0
        self.was_disconnected = False
        self.consecutive_failures = 0
        self._wake_observer = None
        self._disconnected_timer = None
        self._update_lock = threading.Lock()
        self._last_update_attempt = 0.0
        self._last_access_hint_at = 0.0

        logger.info("Starting Razer Battery Tray")
        self.find_device()
        self.update_battery()

        self._wake_observer = _setup_wake_observer(self._on_wake)

    # --- Battery icon helpers ---
    def _get_icon_state(self, battery, charging):
        """Return the icon state key for the given battery level and charging flag."""
        if charging:
            return "charging" if battery > 30 else "charging_low"
        if battery <= 10:
            return "critical"
        if battery <= 30:
            return "low"
        if battery <= 60:
            return "medium"
        return "full"

    def _set_icon(self, state):
        """Set the menu bar icon by state name. Returns True if icon was set."""
        if not self._icon_dir:
            return False
        name = ICON_NAMES.get(state)
        if not name:
            return False
        path = os.path.join(self._icon_dir, f"{name}.png")
        if os.path.exists(path):
            self.icon = path
            self.template = False
            return True
        return False

    # --- Settings menu ---
    def _build_settings_menu(self):
        """Build the Settings submenu with current values."""
        if getattr(self.settings_menu, '_menu', None) is not None:
            self.settings_menu.clear()

        # Poll interval
        poll_menu = rumps.MenuItem("Poll Interval")
        current_poll = self.settings.get("poll_interval")
        for seconds, label in POLL_CHOICES.items():
            item = rumps.MenuItem(label, callback=self._make_poll_callback(seconds))
            item.state = 1 if seconds == current_poll else 0
            poll_menu.add(item)
        self.settings_menu.add(poll_menu)

        # Low battery alert
        alert_menu = rumps.MenuItem("Low Battery Alert")
        current_threshold = self.settings.get("low_battery_threshold")
        notify_enabled = self.settings.get("low_battery_notify")
        for threshold, label in THRESHOLD_CHOICES.items():
            item = rumps.MenuItem(label, callback=self._make_threshold_callback(threshold))
            if threshold == 0:
                item.state = 1 if not notify_enabled else 0
            else:
                item.state = 1 if (notify_enabled and threshold == current_threshold) else 0
            alert_menu.add(item)
        self.settings_menu.add(alert_menu)

        # Display mode
        display_menu = rumps.MenuItem("Menu Bar Display")
        current_display = self.settings.get("display_mode")
        for mode, label in DISPLAY_CHOICES.items():
            item = rumps.MenuItem(label, callback=self._make_display_callback(mode))
            item.state = 1 if mode == current_display else 0
            display_menu.add(item)
        self.settings_menu.add(display_menu)

        # Launch at login
        launch_item = rumps.MenuItem("Launch at Login", callback=self._toggle_launch_at_login)
        launch_item.state = 1 if os.path.exists(LAUNCH_AGENT_PATH) else 0
        self.settings_menu.add(launch_item)

    def _make_poll_callback(self, seconds):
        def callback(_):
            self.settings.set("poll_interval", seconds)
            logger.info("Poll interval changed to %ds", seconds)
            self._build_settings_menu()
        return callback

    def _make_threshold_callback(self, threshold):
        def callback(_):
            if threshold == 0:
                self.settings.set("low_battery_notify", False)
                logger.info("Low battery alert disabled")
            else:
                self.settings.set("low_battery_notify", True)
                self.settings.set("low_battery_threshold", threshold)
                logger.info("Low battery alert set to %d%%", threshold)
            self.low_battery_notified = False
            self._build_settings_menu()
        return callback

    def _make_display_callback(self, mode):
        def callback(_):
            self.settings.set("display_mode", mode)
            logger.info("Display mode changed to %s", mode)
            self._build_settings_menu()
            self._schedule_update()
        return callback

    def _open_input_monitoring_settings(self, _=None):
        """Open the macOS Input Monitoring privacy pane."""
        try:
            subprocess.run(
                ["open", INPUT_MONITORING_SETTINGS_URL],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            logger.info("Opened Input Monitoring settings pane")
        except Exception:
            logger.error("Failed to open Input Monitoring settings: %s", traceback.format_exc())

    def _open_log_file(self, _=None):
        """Open the app log file in Finder."""
        try:
            subprocess.run(
                ["open", "-R", LOG_PATH],
                check=False,
                capture_output=True,
                text=True,
                timeout=5,
            )
            logger.info("Opened log file in Finder: %s", LOG_PATH)
        except Exception:
            logger.error("Failed to reveal log file: %s", traceback.format_exc())

    def _toggle_launch_at_login(self, sender):
        if sender.state:
            # Disable: remove LaunchAgent
            try:
                result = subprocess.run(["launchctl", "bootout", f"gui/{os.getuid()}", LAUNCH_AGENT_PATH],
                                        capture_output=True, text=True, timeout=5)
                if result.returncode != 0:
                    logger.error("launchctl bootout failed (code %d): %s",
                                 result.returncode, result.stderr.strip())
                if os.path.exists(LAUNCH_AGENT_PATH):
                    os.remove(LAUNCH_AGENT_PATH)
                if result.returncode == 0:
                    logger.info("Launch at login disabled")
            except Exception:
                logger.error("Error disabling launch at login: %s", traceback.format_exc())
        else:
            # Enable: create and load LaunchAgent
            try:
                script_path = os.path.abspath(__file__)
                python_path = sys.executable
                plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{LAUNCH_AGENT_LABEL}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>{script_path}</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <false/>
</dict>
</plist>"""
                os.makedirs(os.path.dirname(LAUNCH_AGENT_PATH), exist_ok=True)
                with open(LAUNCH_AGENT_PATH, "w") as f:
                    f.write(plist_content)
                result = subprocess.run(["launchctl", "bootstrap", f"gui/{os.getuid()}", LAUNCH_AGENT_PATH],
                                        capture_output=True, text=True, timeout=5)
                if result.returncode != 0:
                    logger.error("launchctl bootstrap failed (code %d): %s",
                                 result.returncode, result.stderr.strip())
                else:
                    logger.info("Launch at login enabled")
            except Exception:
                logger.error("Error enabling launch at login: %s", traceback.format_exc())
        self._build_settings_menu()

    # --- Background update scheduling ---
    def _failure_backoff(self):
        """Exponential backoff based on consecutive failures."""
        if self.consecutive_failures <= 1:
            return DISCONNECTED_POLL
        exponent = min(self.consecutive_failures - 1, 4)  # cap at 2^4 = 16x
        return min(DISCONNECTED_POLL * (2 ** exponent), MAX_FAILURE_BACKOFF)

    def _schedule_update(self, include_scan=False):
        """Dispatch battery update to a background thread (non-blocking).
        Keeps the main Cocoa run loop responsive.
        """
        if not self._update_lock.acquire(blocking=False):
            logger.debug("Update already in progress, skipping")
            return
        self._last_update_attempt = time.time()

        def worker():
            try:
                if include_scan or not self.device:
                    self.find_device()
                self.update_battery()
            except Exception:
                logger.error("Background update error: %s", traceback.format_exc())
            finally:
                self._update_lock.release()

        threading.Thread(target=worker, daemon=True).start()

    # --- Wake handler ---
    def _on_wake(self):
        logger.info("System wake detected, scheduling refresh in %.1fs", WAKE_DELAY)
        t = threading.Timer(WAKE_DELAY, self._wake_refresh)
        t.daemon = True
        t.start()

    def _wake_refresh(self):
        if not self._update_lock.acquire(blocking=False):
            logger.debug("Update in progress, skipping wake refresh")
            return
        try:
            self._last_update_attempt = time.time()
            self.find_device()
            self.update_battery()
        except Exception:
            logger.error("Wake refresh error: %s", traceback.format_exc())
        finally:
            self._update_lock.release()

    # --- Disconnected fast-poll ---
    def _start_disconnect_poll(self):
        if self._disconnected_timer is not None:
            return
        logger.info("Starting fast poll (every %ds) for reconnection", DISCONNECTED_POLL)
        self._disconnected_timer = rumps.Timer(self._check_reconnect, DISCONNECTED_POLL)
        self._disconnected_timer.start()

    def _stop_disconnect_poll(self):
        if self._disconnected_timer is not None:
            self._disconnected_timer.stop()
            self._disconnected_timer = None
            logger.info("Stopped fast reconnection poll")

    def _check_reconnect(self, _=None):
        # Respect backoff — don't hammer the device
        if self.consecutive_failures > 1:
            elapsed = time.time() - self._last_update_attempt
            if elapsed < self._failure_backoff():
                return
        self._schedule_update(include_scan=True)

    def _prioritize_device_interfaces(self, device):
        """Prefer the most likely working HID interface order for feature reports."""
        if not device:
            return
        interfaces = list(device.get("interfaces", []))
        preferred_path = device.get("preferred_interface_path")
        interfaces.sort(key=lambda iface: (
            0 if preferred_path is not None and iface.get("path") == preferred_path else 1,
            0 if iface.get("interface_number", -1) == 0 else 1,
            iface.get("interface_number", 999),
        ))
        device["interfaces"] = interfaces

    def _last_failure_is_full_open_failure(self, device=None):
        """True when all attempted HID interfaces failed at open_path()."""
        target = device if device is not None else self.device
        if not target:
            return False
        if target.get("_diag_last_ok", True):
            return False
        attempted = target.get("_diag_last_attempted_interfaces") or []
        open_failed_count = int(target.get("_diag_last_open_failed_count", 0))
        return bool(attempted) and open_failed_count >= len(attempted)

    def _emit_access_remediation_once(self, failure_device=None):
        """Log and notify actionable troubleshooting hints for repeated HID failures."""
        now = time.time()
        if (now - self._last_access_hint_at) < ACCESS_HINT_COOLDOWN:
            return
        self._last_access_hint_at = now
        target = failure_device if failure_device is not None else self.device

        drivers = _check_razer_drivers()
        if drivers:
            logger.error("Razer DriverKit extensions detected (can block HID access): %s", drivers)
            logger.error("Remediation: sudo systemextensionsctl uninstall R2H967U7J8 com.razer.appengine.driver")
            logger.error("Remediation: sudo systemextensionsctl uninstall R2H967U7J8 com.razer.appengine.virtual.driver")

        if self._last_failure_is_full_open_failure(target):
            recent_errors = target.get("_diag_last_io_errors", []) if target else []
            logger.error(
                "HID open failed on every interface. Likely macOS privacy permission denial for this app."
            )
            if recent_errors:
                logger.error("Recent HID I/O errors: %s", "; ".join(recent_errors))
            logger.error(
                "Grant access in System Settings -> Privacy & Security -> Input Monitoring "
                "for 'Razer Battery', then relaunch the app."
            )
            try:
                rumps.notification(
                    title="Razer Battery needs permission",
                    subtitle="Input Monitoring",
                    message="Enable 'Razer Battery' in Input Monitoring and relaunch.",
                )
            except Exception:
                logger.debug("Notification failed while sending access hint")
        elif not drivers:
            logger.error("Repeated battery read failures. Open logs for details: %s", LOG_PATH)

    # --- Core logic ---
    def find_device(self):
        """Scan for the first connected Razer wireless mouse."""
        try:
            devices = scan_razer_devices()
            mice = [d for d in devices if d['type'] == 'mouse']
            if mice:
                old_device = self.device
                self.device = mice[0]
                self._prioritize_device_interfaces(self.device)
                self.device_name_item.title = self.device['name']
                if old_device is None:
                    logger.info("Device found: %s (PID 0x%04X)", self.device['name'], self.device['pid'])
            else:
                if self.device is not None:
                    logger.info("Device lost: %s", self.device['name'])
                self.device = None
                self.device_name_item.title = "No device found"
        except Exception:
            logger.error("find_device error: %s", traceback.format_exc())
            self.device = None
            self.device_name_item.title = "No device found"

    def _format_title(self, battery, charging):
        """Format the menu bar title based on display mode setting."""
        mode = self.settings.get("display_mode")

        if self._icon_dir:
            # Icon is set via self.icon — title is text only
            if mode == "percent_only":
                self.icon = None
                return f"{battery}%"
            if mode == "icon_only":
                return ""
            return f" {battery}%"

        # Emoji fallback when icons are not available
        low_threshold = self.settings.get("low_battery_threshold") if self.settings.get("low_battery_notify") else 0

        if charging:
            icon = "\u26a1"
        elif low_threshold and battery <= low_threshold:
            icon = "\U0001faab"
        else:
            icon = "\U0001f50b"

        if mode == "percent_only":
            return f"{battery}%"
        elif mode == "icon_only":
            return icon
        else:  # icon_percent
            return f"{icon} {battery}%"

    def update_battery(self):
        """Read battery and update menu bar title."""
        try:
            # Staleness guard
            if (self.last_successful_read > 0 and
                    time.time() - self.last_successful_read > STALENESS_THRESHOLD):
                logger.warning("Battery reading stale (>%ds), forcing re-scan", STALENESS_THRESHOLD)
                self.find_device()

            if not self.device:
                self.find_device()
            if not self.device:
                self.was_disconnected = True
                self.consecutive_failures += 1
                self._start_disconnect_poll()
                self._set_icon("disconnected")
                if self.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    self._emit_access_remediation_once()
                    self.title = " \u26a0\ufe0f" if self._icon_dir else "\U0001f50b \u26a0\ufe0f"
                else:
                    self.title = " --" if self._icon_dir else "\U0001f50b --"
                return

            battery = get_battery_level(self.device)
            if battery < 0:
                logger.warning("Battery read failed, marking device disconnected")
                failed_device = self.device
                self.device = None
                self.was_disconnected = True
                self.consecutive_failures += 1
                self._start_disconnect_poll()
                self._set_icon("disconnected")
                if self.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                    self._emit_access_remediation_once(failed_device)
                    self.title = " \u26a0\ufe0f" if self._icon_dir else "\U0001f50b \u26a0\ufe0f"
                else:
                    self.title = " --" if self._icon_dir else "\U0001f50b --"
                return

            charging = get_charging_status(self.device)

            # Success
            self.last_successful_read = time.time()
            self.consecutive_failures = 0
            self._stop_disconnect_poll()

            if self.was_disconnected:
                logger.info("Device reconnected, battery: %d%%, charging: %s", battery, charging)
                self.was_disconnected = False

            self._set_icon(self._get_icon_state(battery, charging))
            self.title = self._format_title(battery, charging)

            # Low battery notification
            self._check_low_battery(battery)

            logger.info("Battery: %d%%, charging: %s", battery, charging)

        except Exception:
            logger.error("update_battery error: %s", traceback.format_exc())
            self.consecutive_failures += 1
            self._set_icon("disconnected")
            if self.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                self._emit_access_remediation_once()
                self.title = " \u26a0\ufe0f" if self._icon_dir else "\U0001f50b \u26a0\ufe0f"
            else:
                self.title = " --" if self._icon_dir else "\U0001f50b --"

    def _check_low_battery(self, battery):
        """Fire a low-battery notification if threshold crossed."""
        if not self.settings.get("low_battery_notify"):
            return
        threshold = self.settings.get("low_battery_threshold")
        if battery <= threshold and not self.low_battery_notified:
            self.low_battery_notified = True
            device_name = self.device['name'] if self.device else "Razer Mouse"
            rumps.notification(
                title="Razer Battery Low",
                subtitle=device_name,
                message=f"Battery at {battery}% \u2014 plug in soon",
            )
            logger.info("Low battery notification fired: %d%%", battery)
        elif battery > threshold:
            self.low_battery_notified = False

    def refresh(self, _=None):
        """Manual refresh triggered from menu."""
        logger.info("Manual refresh triggered")
        self._schedule_update(include_scan=True)

    @rumps.timer(60)
    def poll(self, _):
        """Periodic battery poll — checks against configured interval."""
        poll_interval = self.settings.get("poll_interval")
        if self.consecutive_failures > 0:
            backoff = self._failure_backoff()
            since_attempt = time.time() - self._last_update_attempt if self._last_update_attempt > 0 else backoff + 1
            if since_attempt < backoff:
                return
        else:
            elapsed = time.time() - self.last_successful_read if self.last_successful_read > 0 else poll_interval + 1
            if elapsed < poll_interval:
                return
        self._schedule_update()


if __name__ == "__main__":
    RazerBatteryApp().run()
