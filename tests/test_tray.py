"""Tests for razer_battery_tray.py — menu bar app logic.

These tests mock rumps and HID to run without macOS UI or hardware.
"""

import os
import time
import pytest
from unittest.mock import patch, MagicMock

from helpers import make_app, mock_rumps

import settings as settings_mod
from razer_battery_tray import RazerBatteryApp, STALENESS_THRESHOLD, MAX_CONSECUTIVE_FAILURES


@pytest.fixture
def mouse_device(mock_mouse_device):
    return mock_mouse_device


@pytest.fixture
def keyboard_device(mock_keyboard_device):
    return mock_keyboard_device


# --- 6.3: Tray app unit tests ---

class TestTitleStates:
    def test_title_normal_battery(self, mouse_device):
        """battery=75, charging=False -> title shows 75% with full icon."""
        app = make_app(device=mouse_device, battery=75, charging=False)
        assert "75%" in app.title
        assert "battery_full" in app.icon

    def test_title_low_battery(self, mouse_device):
        """battery=15, charging=False -> title shows 15% with low icon."""
        app = make_app(device=mouse_device, battery=15, charging=False)
        assert "15%" in app.title
        assert "battery_low" in app.icon

    def test_title_charging(self, mouse_device):
        """battery=50, charging=True -> icon shows charging state."""
        app = make_app(device=mouse_device, battery=50, charging=True)
        assert "50%" in app.title
        assert "battery_charging" in app.icon

    def test_title_disconnected(self):
        """No device -> title shows '--'."""
        app = make_app(device=None, battery=-1, charging=False)
        assert "--" in app.title

    def test_title_persistent_failure(self, mouse_device):
        """3 consecutive failures -> title shows warning icon."""
        app = make_app(device=mouse_device, battery=75)

        # Simulate 3 consecutive failures
        with patch("razer_battery_tray.scan_razer_devices", return_value=[]), \
             patch("razer_battery_tray.get_battery_level", return_value=-1), \
             patch("razer_battery_tray.get_charging_status", return_value=False), \
             patch("razer_battery_tray._check_razer_drivers", return_value=[]):
            app.device = None
            for _ in range(3):
                app.update_battery()

        assert "\u26a0" in app.title  # warning icon


class TestDeviceDiscovery:
    def test_find_device_filters_mice_only(self, mouse_device, keyboard_device):
        """scan returns keyboard + mouse, only mouse is selected."""
        with patch("razer_battery_tray.scan_razer_devices") as mock_scan, \
             patch("razer_battery_tray.get_battery_level", return_value=80), \
             patch("razer_battery_tray.get_charging_status", return_value=False), \
             patch("razer_battery_tray._setup_wake_observer", return_value=None):
            mock_scan.return_value = [keyboard_device, mouse_device]

            app = RazerBatteryApp()
            assert app.device is not None
            assert app.device["type"] == "mouse"
            assert app.device["pid"] == 0x00B7

    def test_find_device_no_devices(self):
        """Empty scan -> device is None."""
        app = make_app(device=None)
        assert app.device is None
        assert app.device_name_item.title == "No device found"


class TestReconnection:
    def test_device_reconnection_clears_flag(self, mouse_device):
        """Simulate disconnect then reconnect, verify was_disconnected resets."""
        app = make_app(device=mouse_device, battery=80)

        # Disconnect
        with patch("razer_battery_tray.scan_razer_devices", return_value=[]), \
             patch("razer_battery_tray.get_battery_level", return_value=-1), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.device = None
            app.update_battery()
        assert app.was_disconnected is True

        # Reconnect
        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]), \
             patch("razer_battery_tray.get_battery_level", return_value=90), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.update_battery()
        assert app.was_disconnected is False
        assert "90%" in app.title


# Staleness guard test lives in test_deep.py::TestStalenessDeep (more thorough version)

# --- Phase 8: Settings tests ---

class TestSettings:
    def test_display_mode_icon_percent(self, mouse_device):
        """Default display mode shows icon + percentage."""
        app = make_app(device=mouse_device, battery=80)
        assert "80%" in app.title
        assert "battery_full" in app.icon

    def test_display_mode_percent_only(self, mouse_device):
        """Percent-only mode shows just the number, no icon."""
        app = make_app(device=mouse_device, battery=80)
        app.settings.set("display_mode", "percent_only")
        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]), \
             patch("razer_battery_tray.get_battery_level", return_value=80), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.update_battery()
        assert app.title == "80%"

    def test_display_mode_icon_only(self, mouse_device):
        """Icon-only mode shows just the icon, no text."""
        app = make_app(device=mouse_device, battery=80)
        app.settings.set("display_mode", "icon_only")
        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]), \
             patch("razer_battery_tray.get_battery_level", return_value=80), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.update_battery()
        assert app.title == ""
        assert "battery_full" in app.icon

    def test_low_battery_notification(self, mouse_device):
        """Low battery notification fires when below threshold."""
        mock_rumps.notification.reset_mock()
        app = make_app(device=mouse_device, battery=80)
        app.settings.set("low_battery_notify", True)
        app.settings.set("low_battery_threshold", 20)

        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]), \
             patch("razer_battery_tray.get_battery_level", return_value=15), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.update_battery()

        assert app.low_battery_notified is True
        mock_rumps.notification.assert_called_once()

    def test_low_battery_notification_only_fires_once(self, mouse_device):
        """Notification only fires once per threshold crossing."""
        mock_rumps.notification.reset_mock()
        app = make_app(device=mouse_device, battery=80)
        app.settings.set("low_battery_notify", True)
        app.settings.set("low_battery_threshold", 20)

        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]), \
             patch("razer_battery_tray.get_battery_level", return_value=15), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.update_battery()
            app.update_battery()  # second time — should NOT fire again

        assert mock_rumps.notification.call_count == 1

    def test_low_battery_notification_resets_above_threshold(self, mouse_device):
        """Notification flag resets when battery goes above threshold."""
        mock_rumps.notification.reset_mock()
        app = make_app(device=mouse_device, battery=80)
        app.settings.set("low_battery_notify", True)
        app.settings.set("low_battery_threshold", 20)
        app.low_battery_notified = True

        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]), \
             patch("razer_battery_tray.get_battery_level", return_value=50), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.update_battery()

        assert app.low_battery_notified is False

    def test_custom_poll_interval(self, mouse_device):
        """Changing poll interval persists in settings."""
        app = make_app(device=mouse_device, battery=80)
        app.settings.set("poll_interval", 60)
        assert app.settings.get("poll_interval") == 60

    def test_open_input_monitoring_settings_menu_action(self, mouse_device):
        """Settings helper opens the Input Monitoring pane."""
        app = make_app(device=mouse_device, battery=80)
        with patch("razer_battery_tray.subprocess.run") as mock_run:
            app._open_input_monitoring_settings()
            assert mock_run.called
            args = mock_run.call_args[0][0]
            assert args[0] == "open"
            assert "Privacy_ListenEvent" in args[1]

    def test_repeated_open_failures_emit_remediation_hint(self, mouse_device):
        """At warning threshold, repeated open failures trigger remediation logging path."""
        app = make_app(device=mouse_device, battery=80)
        app.consecutive_failures = MAX_CONSECUTIVE_FAILURES - 1
        app.device["_diag_last_ok"] = False
        app.device["_diag_last_attempted_interfaces"] = [2, 1, 0]
        app.device["_diag_last_open_failed_count"] = 6
        app.device["_diag_last_io_errors"] = ["open failed"]

        with patch("razer_battery_tray.get_battery_level", return_value=-1), \
             patch("razer_battery_tray.get_charging_status", return_value=False), \
             patch.object(app, "_emit_access_remediation_once") as mock_emit:
            app.update_battery()
            mock_emit.assert_called_once()


# --- 6.4: Integration tests ---

class TestIntegration:
    def test_full_poll_cycle(self, mouse_device):
        """Mock HID, trigger poll(), verify title updated."""
        app = make_app(device=mouse_device, battery=65, charging=False)
        assert "65%" in app.title

        # Force poll to actually call update_battery
        app.last_successful_read = 0
        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]), \
             patch("razer_battery_tray.get_battery_level", return_value=60), \
             patch("razer_battery_tray.get_charging_status", return_value=True):
            app.poll(None)
        assert "60%" in app.title
        assert "battery_charging" in app.icon  # now charging

    def test_refresh_menu_action(self, mouse_device):
        """Call refresh(), verify both find_device and update_battery execute."""
        app = make_app(device=mouse_device, battery=70)

        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]) as mock_scan, \
             patch("razer_battery_tray.get_battery_level", return_value=55) as mock_bat, \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.refresh()
            assert mock_scan.called
            assert mock_bat.called
        assert "55%" in app.title

    def test_error_recovery_after_crash(self, mouse_device):
        """Mock get_battery_level to raise, verify app doesn't crash."""
        app = make_app(device=mouse_device, battery=80)

        with patch("razer_battery_tray.get_battery_level", side_effect=RuntimeError("HID crash")), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.update_battery()

        assert "--" in app.title or "\u26a0" in app.title
