"""Tests for razer_common.py battery protocol functions."""

import pytest
from unittest.mock import patch, MagicMock
from helpers import make_razer_response, MockHIDDevice

from razer_common import (
    construct_razer_report,
    calculate_crc,
    get_battery_level,
    get_charging_status,
    send_and_receive_report,
    validate_response,
    REPORT_LEN,
    RAZER_STATUS_SUCCESS,
    RAZER_STATUS_BUSY,
    RAZER_STATUS_FAILURE,
    RAZER_STATUS_TIMEOUT,
    RAZER_STATUS_NOT_SUPPORTED,
)


# --- 6.2: Protocol unit tests ---

class TestConstructReport:
    def test_construct_battery_report(self):
        """Verify construct_razer_report for battery level command produces 90-byte report with valid CRC."""
        report = construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00])
        assert len(report) == REPORT_LEN
        assert report[0] == 0x00  # status
        assert report[1] == 0x1F  # transaction_id
        assert report[5] == 0x02  # data_size
        assert report[6] == 0x07  # command_class
        assert report[7] == 0x80  # command_id
        assert report[8] == 0x00  # arguments[0]
        assert report[9] == 0x00  # arguments[1]
        # CRC check
        assert report[88] == calculate_crc(report)

    def test_construct_charging_report(self):
        """Verify construct_razer_report for charging status command."""
        report = construct_razer_report(0x1F, 0x07, 0x84, 0x02, [0x00, 0x00])
        assert len(report) == REPORT_LEN
        assert report[6] == 0x07  # command_class
        assert report[7] == 0x84  # command_id
        assert report[88] == calculate_crc(report)

    def test_crc_validation(self):
        """Construct a report and verify XOR of bytes 2-87 equals byte 88."""
        report = construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00])
        crc = 0
        for i in range(2, 88):
            crc ^= report[i]
        assert crc == report[88]


class TestBatteryLevelParsing:
    @patch("razer_common.send_and_receive_report")
    def test_battery_level_parsing(self, mock_send, mock_device):
        """Mock response with response[10]=0xE2 (226) -> battery 89%."""
        mock_send.return_value = make_razer_response(battery_byte=0xE2)
        result = get_battery_level(mock_device)
        assert result == 89  # round(226/255*100)

    @patch("razer_common.send_and_receive_report")
    def test_battery_level_zero(self, mock_send, mock_device):
        """response[10]=0x00 -> 0%."""
        mock_send.return_value = make_razer_response(battery_byte=0x00)
        result = get_battery_level(mock_device)
        assert result == 0

    @patch("razer_common.send_and_receive_report")
    def test_battery_level_full(self, mock_send, mock_device):
        """response[10]=0xFF (255) -> 100%."""
        mock_send.return_value = make_razer_response(battery_byte=0xFF)
        result = get_battery_level(mock_device)
        assert result == 100

    @patch("razer_common.send_and_receive_report")
    def test_battery_level_failure(self, mock_send, mock_device):
        """Mock returns None -> -1."""
        mock_send.return_value = None
        result = get_battery_level(mock_device)
        assert result == -1


class TestChargingStatus:
    @patch("razer_common.send_and_receive_report")
    def test_charging_status_true(self, mock_send, mock_device):
        """response[10]=0x01 -> True."""
        mock_send.return_value = make_razer_response(battery_byte=0x01)
        result = get_charging_status(mock_device)
        assert result is True

    @patch("razer_common.send_and_receive_report")
    def test_charging_status_false(self, mock_send, mock_device):
        """response[10]=0x00 -> False."""
        mock_send.return_value = make_razer_response(battery_byte=0x00)
        result = get_charging_status(mock_device)
        assert result is False

    @patch("razer_common.send_and_receive_report")
    def test_charging_status_failure(self, mock_send, mock_device):
        """Mock returns None -> False."""
        mock_send.return_value = None
        result = get_charging_status(mock_device)
        assert result is False


class TestResponseValidation:
    def test_response_status_success(self):
        """Status 0x02 (success) passes validation."""
        response = make_razer_response(status=RAZER_STATUS_SUCCESS)
        assert validate_response(response, "test") is True

    def test_response_status_busy(self):
        """Status 0x01 (busy) fails validation."""
        response = make_razer_response(status=RAZER_STATUS_BUSY)
        assert validate_response(response, "test") is False

    def test_response_status_failure(self):
        """Status 0x03 (failure) fails validation."""
        response = make_razer_response(status=RAZER_STATUS_FAILURE)
        assert validate_response(response, "test") is False

    def test_response_status_timeout(self):
        """Status 0x04 (timeout) fails validation."""
        response = make_razer_response(status=RAZER_STATUS_TIMEOUT)
        assert validate_response(response, "test") is False

    def test_response_status_not_supported(self):
        """Status 0x05 (not supported) fails validation."""
        response = make_razer_response(status=RAZER_STATUS_NOT_SUPPORTED)
        assert validate_response(response, "test") is False

    def test_response_too_short(self):
        """Short response fails validation."""
        assert validate_response([0x00] * 5, "test") is False
        assert validate_response(None, "test") is False
        assert validate_response([], "test") is False


class TestSendAndReceive:
    @patch("razer_common.hid")
    def test_send_receive_success(self, mock_hid_module, mock_device):
        """Successful send and receive returns response."""
        response = make_razer_response(battery_byte=0xC8)
        mock_dev = MockHIDDevice(response=response)
        mock_hid_module.device.return_value = mock_dev

        result = send_and_receive_report(
            mock_device,
            construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00]),
            "test",
        )
        assert result == response
        assert mock_dev.opened
        assert mock_dev.closed

    @patch("razer_common.hid")
    def test_send_receive_oserror_retries(self, mock_hid_module, mock_device):
        """OSError on first attempt retries, then returns None if both fail."""
        mock_dev = MockHIDDevice(raise_on_open=OSError("device busy"))
        mock_hid_module.device.return_value = mock_dev

        # Device with single interface — should attempt twice then fail
        single_iface_device = {**mock_device, "interfaces": [mock_device["interfaces"][0]]}
        result = send_and_receive_report(
            single_iface_device,
            construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00]),
            "test",
        )
        assert result is None

    @patch("razer_common.hid")
    def test_send_receive_valueerror_no_retry(self, mock_hid_module, mock_device):
        """ValueError does not retry (breaks immediately to next interface)."""
        mock_dev = MockHIDDevice(raise_on_open=ValueError("bad report"))
        mock_hid_module.device.return_value = mock_dev

        single_iface_device = {**mock_device, "interfaces": [mock_device["interfaces"][0]]}
        result = send_and_receive_report(
            single_iface_device,
            construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00]),
            "test",
        )
        assert result is None

    @patch("razer_common.hid")
    def test_send_receive_prioritizes_interface_zero_and_caches_preferred(self, mock_hid_module, mock_device):
        """Interface 0 is preferred first and remembered on success."""
        response = make_razer_response(battery_byte=0xC8)
        opened_paths = []

        class PathAwareMockDevice(MockHIDDevice):
            def open_path(self, path):
                opened_paths.append(path)
                if path != b"/dev/mock-hid-0":
                    raise OSError("open failed")
                self.opened = True

        mock_dev = PathAwareMockDevice(response=response)
        mock_hid_module.device.return_value = mock_dev

        unordered = {
            **mock_device,
            "interfaces": [
                {"path": b"/dev/mock-hid-2", "interface_number": 2},
                {"path": b"/dev/mock-hid-1", "interface_number": 1},
                {"path": b"/dev/mock-hid-0", "interface_number": 0},
            ],
        }

        result = send_and_receive_report(
            unordered,
            construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00]),
            "test",
        )

        assert result == response
        assert opened_paths[0] == b"/dev/mock-hid-0"
        assert unordered["preferred_interface_path"] == b"/dev/mock-hid-0"

    @patch("razer_common.hid")
    def test_send_receive_records_open_failure_diagnostics(self, mock_hid_module, mock_device):
        """When all open_path calls fail, diagnostic counters are populated."""
        mock_dev = MockHIDDevice(raise_on_open=OSError("open failed"))
        mock_hid_module.device.return_value = mock_dev

        single_iface_device = {
            **mock_device,
            "interfaces": [{"path": b"/dev/mock-hid-0", "interface_number": 0}],
        }
        result = send_and_receive_report(
            single_iface_device,
            construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00]),
            "test-open-fail",
        )

        assert result is None
        assert single_iface_device["_diag_last_ok"] is False
        assert single_iface_device["_diag_last_command"] == "test-open-fail"
        assert single_iface_device["_diag_last_open_failed_count"] >= 1
        assert single_iface_device["_diag_last_attempted_interfaces"] == [0]
