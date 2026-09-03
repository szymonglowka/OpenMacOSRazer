"""Shared test helpers for Razer battery tests.

This module contains:
1. Mock response/device helpers for HID protocol tests
2. Centralized rumps mock (installed once, shared across all test files)
3. make_app factory for tray app tests
"""

import sys
import os
from unittest.mock import patch, MagicMock


# =====================================================================
# HID protocol test helpers
# =====================================================================

def make_razer_response(status=0x02, battery_byte=0x00, report_id=0x00):
    """Build a 91-byte mock response (report ID + 90-byte Razer report).

    Args:
        status: Status byte at report position 0 (response index 1).
        battery_byte: Value at arguments[1] = report position 9 (response index 10).
        report_id: HID report ID prefix byte.
    """
    response = [0] * 91
    response[0] = report_id
    response[1] = status        # report byte 0: status
    response[2] = 0x1F          # report byte 1: transaction_id
    # bytes 2-4: reserved (0x00)
    response[5] = 0x00          # report byte 4: reserved
    response[6] = 0x02          # report byte 5: data_size
    response[7] = 0x07          # report byte 6: command_class
    response[8] = 0x80          # report byte 7: command_id
    response[9] = 0x00          # report byte 8: arguments[0]
    response[10] = battery_byte  # report byte 9: arguments[1] = battery value
    # Compute CRC: XOR of report bytes 2-87 = response indices 3-88
    crc = 0
    for i in range(3, 89):
        crc ^= response[i]
    response[89] = crc          # report byte 88: CRC
    response[90] = 0x00         # report byte 89: reserved
    return response


class MockHIDDevice:
    """Mock hid.device() that returns configurable responses."""

    def __init__(self, response=None, raise_on_open=None, raise_on_send=None):
        self.response = response
        self.raise_on_open = raise_on_open
        self.raise_on_send = raise_on_send
        self.opened = False
        self.closed = False
        self.sent_reports = []
        self.get_feature_report_calls = []

    def open_path(self, path):
        if self.raise_on_open:
            raise self.raise_on_open
        self.opened = True

    def send_feature_report(self, data):
        if self.raise_on_send:
            raise self.raise_on_send
        self.sent_reports.append(data)
        return len(data)

    def get_feature_report(self, report_id, length):
        self.get_feature_report_calls.append((report_id, length))
        return self.response

    def close(self):
        self.closed = True


# =====================================================================
# Centralized rumps mock — installed once, shared by all test files
# =====================================================================

# Guard: only create mock once per process
if "rumps" not in sys.modules or not hasattr(sys.modules["rumps"], "_is_test_mock"):
    mock_rumps = MagicMock()
    mock_rumps._is_test_mock = True
    mock_rumps.App = type("MockApp", (), {
        "__init__": lambda self, *a, **kw: None,
        "run": lambda self: None,
    })
    mock_rumps.timer = lambda interval: lambda func: func
    mock_rumps.quit_application = MagicMock()
    mock_rumps.notification = MagicMock()

    class _MockMenuItem:
        """Mock rumps.MenuItem with dict-like menu support."""
        def __init__(self, title="", callback=None, **kwargs):
            self.title = title
            self.callback = callback
            self.state = 0
            self._items = {}

        def clear(self):
            self._items = {}

        def add(self, item):
            if isinstance(item, _MockMenuItem):
                self._items[item.title] = item

        def __setitem__(self, key, value):
            self._items[key] = value

        def __getitem__(self, key):
            return self._items[key]

        def keys(self):
            return self._items.keys()

    mock_rumps.MenuItem = _MockMenuItem

    class _MockTimer:
        def __init__(self, callback, interval):
            self.callback = callback
            self.interval = interval
            self.running = False
        def start(self):
            self.running = True
        def stop(self):
            self.running = False

    mock_rumps.Timer = _MockTimer
    sys.modules["rumps"] = mock_rumps
else:
    mock_rumps = sys.modules["rumps"]

# Redirect settings so tests don't read real user config
import settings as settings_mod
settings_mod.CONFIG_FILE = "/tmp/razer-battery-test-settings.json"
if os.path.exists(settings_mod.CONFIG_FILE):
    os.remove(settings_mod.CONFIG_FILE)

# Import tray app AFTER rumps mock is installed
from razer_battery_tray import RazerBatteryApp


def make_app(device=None, battery=75, charging=False):
    """Create a RazerBatteryApp with mocked dependencies."""
    if os.path.exists(settings_mod.CONFIG_FILE):
        os.remove(settings_mod.CONFIG_FILE)
    with patch("razer_battery_tray.scan_razer_devices") as mock_scan, \
         patch("razer_battery_tray.get_battery_level") as mock_bat, \
         patch("razer_battery_tray.get_charging_status") as mock_chrg, \
         patch("razer_battery_tray._setup_wake_observer") as mock_wake:
        mock_scan.return_value = [device] if device else []
        mock_bat.return_value = battery
        mock_chrg.return_value = charging
        mock_wake.return_value = None
        app = RazerBatteryApp()
    return app
