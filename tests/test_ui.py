"""Safety net tests for razer_ui.py — mocked PyQt5, no real GUI required."""

import sys
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

# Mock PyQt5 before importing razer_ui
mock_qt_widgets = MagicMock()

# Create mock classes that behave like Qt widgets
class MockQComboBox:
    def __init__(self, *a, **kw):
        self._items = []
        self._current_index = -1

    def clear(self):
        self._items = []
        self._current_index = -1

    def addItem(self, text, data=None):
        self._items.append((text, data))
        if self._current_index < 0:
            self._current_index = 0

    def setCurrentIndex(self, idx):
        self._current_index = idx

    def currentIndex(self):
        return self._current_index

    def itemData(self, idx):
        if 0 <= idx < len(self._items):
            return self._items[idx][1]
        return None

mock_qt_widgets.QComboBox = MockQComboBox
mock_qt_widgets.QMainWindow = type("MockQMainWindow", (), {
    "__init__": lambda self, *a, **kw: None,
    "setWindowTitle": lambda self, t: None,
    "setMinimumSize": lambda self, w, h: None,
    "setCentralWidget": lambda self, w: None,
})
mock_qt_widgets.QWidget = lambda *a, **kw: MagicMock()
mock_qt_widgets.QVBoxLayout = lambda *a, **kw: MagicMock()
mock_qt_widgets.QHBoxLayout = lambda *a, **kw: MagicMock()
mock_qt_widgets.QFormLayout = lambda *a, **kw: MagicMock()
mock_qt_widgets.QTabWidget = lambda *a, **kw: MagicMock()
mock_qt_widgets.QLabel = lambda *a, **kw: MagicMock()
mock_qt_widgets.QSpinBox = lambda *a, **kw: MagicMock(value=MagicMock(return_value=128))
mock_qt_widgets.QPushButton = lambda *a, **kw: MagicMock()
mock_qt_widgets.QRadioButton = lambda *a, **kw: MagicMock(isChecked=MagicMock(return_value=True))
mock_qt_widgets.QMessageBox = MagicMock()

sys.modules["PyQt5"] = MagicMock()
sys.modules["PyQt5.QtWidgets"] = mock_qt_widgets

from razer_ui import MainWindow


class TestRefreshDevices:
    def test_refresh_empty_shows_warning(self):
        """refresh_devices with no devices shows QMessageBox warning."""
        mock_qt_widgets.QMessageBox.reset_mock()
        with patch("razer_ui.scan_razer_devices", return_value=[]):
            win = MainWindow()
        mock_qt_widgets.QMessageBox.warning.assert_called()

    def test_refresh_populates_combo(self):
        """refresh_devices with a device populates the combo box."""
        device = {
            "name": "Razer Viper", "pid": 0x0078, "type": "mouse",
            "transaction_id": 0x3F, "interfaces": [{"path": b"/dev/hid0", "interface_number": 0}],
        }
        with patch("razer_ui.scan_razer_devices", return_value=[device]):
            win = MainWindow()
        assert win.device_combo.currentIndex() == 0
        assert win.device_combo.itemData(0) is device


class TestGetSelectedDevice:
    def test_no_index_returns_none(self):
        """get_selected_device with no items returns None."""
        with patch("razer_ui.scan_razer_devices", return_value=[]):
            win = MainWindow()
        result = win.get_selected_device()
        assert result is None


class TestSendEffects:
    def _make_window_with_device(self, device_type="mouse"):
        if device_type == "mouse":
            device = {
                "name": "Razer Viper", "pid": 0x0078, "type": "mouse",
                "transaction_id": 0x3F, "interfaces": [{"path": b"/dev/hid0", "interface_number": 0}],
            }
        else:
            device = {
                "name": "Unknown", "pid": 0xFFFF, "type": "unknown",
                "transaction_id": 0x00, "interfaces": [],
            }
        with patch("razer_ui.scan_razer_devices", return_value=[device]):
            win = MainWindow()
        # Mock the QSpinBox values
        win.static_spin_r = MagicMock(value=MagicMock(return_value=255))
        win.static_spin_g = MagicMock(value=MagicMock(return_value=0))
        win.static_spin_b = MagicMock(value=MagicMock(return_value=0))
        return win

    def test_send_unsupported_device_shows_warning(self):
        """Sending to unsupported device type shows warning."""
        mock_qt_widgets.QMessageBox.reset_mock()
        win = self._make_window_with_device(device_type="unknown")
        win.send_static()
        mock_qt_widgets.QMessageBox.warning.assert_called()

    def test_send_mouse_success(self):
        """Sending static effect to mouse device shows success."""
        mock_qt_widgets.QMessageBox.reset_mock()
        win = self._make_window_with_device(device_type="mouse")
        with patch("razer_ui.send_report_to_device", return_value=True):
            win.send_static()
        mock_qt_widgets.QMessageBox.information.assert_called()

    def test_send_mouse_failure(self):
        """Failed send to mouse device shows error."""
        mock_qt_widgets.QMessageBox.reset_mock()
        win = self._make_window_with_device(device_type="mouse")
        with patch("razer_ui.send_report_to_device", return_value=False):
            win.send_static()
        mock_qt_widgets.QMessageBox.warning.assert_called()
