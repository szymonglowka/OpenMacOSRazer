"""Shared test fixtures for Razer battery tests.

Mock setup (rumps, settings, make_app) lives in helpers.py to avoid
double-execution issues with pytest conftest loading.
"""

import sys
import os
import pytest

# Ensure the project root and tests dir are on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

# Trigger mock setup by importing helpers (runs once per process)
import helpers  # noqa: F401


@pytest.fixture
def mock_device():
    """A device dict matching the structure returned by scan_razer_devices()."""
    return {
        "name": "Razer DeathAdder V3 Pro (Wireless)",
        "pid": 0x00B7,
        "type": "mouse",
        "transaction_id": 0x1F,
        "interfaces": [
            {"path": b"/dev/mock-hid-0", "interface_number": 0},
            {"path": b"/dev/mock-hid-1", "interface_number": 1},
        ],
    }


@pytest.fixture
def mock_mouse_device():
    """A mouse device dict for tray/deep tests."""
    return {
        "name": "Razer DeathAdder V3 Pro (Wireless)",
        "pid": 0x00B7,
        "type": "mouse",
        "transaction_id": 0x1F,
        "interfaces": [{"path": b"/dev/mock-0", "interface_number": 0}],
    }


@pytest.fixture
def mock_mouse_device_2():
    """A second mouse device for multi-device tests."""
    return {
        "name": "Razer Viper V3 Pro (Wireless)",
        "pid": 0x00C1,
        "type": "mouse",
        "transaction_id": 0x1F,
        "interfaces": [{"path": b"/dev/mock-1", "interface_number": 0}],
    }


@pytest.fixture
def mock_keyboard_device():
    """A keyboard device dict."""
    return {
        "name": "Razer BlackWidow V4",
        "pid": 0x0287,
        "type": "keyboard",
        "transaction_id": 0x1F,
        "interfaces": [{"path": b"/dev/mock-kbd-0", "interface_number": 0}],
    }
