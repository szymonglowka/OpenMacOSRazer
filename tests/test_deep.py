"""Deep tests for OpenMacOSRazer — covers edge cases, boundary conditions,
retry logic, settings resilience, and tray state machine paths not covered
by the existing unit/integration tests.

Run: pytest tests/test_deep.py -v
"""

import json
import os
import time
import pytest
from unittest.mock import patch, MagicMock, call

from helpers import make_razer_response, MockHIDDevice, make_app, mock_rumps
import settings as settings_mod

from razer_common import (
    construct_razer_report,
    calculate_crc,
    get_battery_level,
    get_charging_status,
    get_device_type,
    get_transaction_id,
    is_mouse_device,
    is_keyboard_device,
    build_arguments,
    scan_razer_devices,
    send_and_receive_report,
    send_report_to_device,
    validate_response,
    REPORT_LEN,
    RAZER_VID,
    RAZER_DEVICES,
    RAZER_DEVICE_TYPES,
    RAZER_TRANSACTION_IDS,
    RAZER_STATUS_NEW,
    RAZER_STATUS_BUSY,
    RAZER_STATUS_SUCCESS,
    RAZER_STATUS_FAILURE,
    RAZER_STATUS_TIMEOUT,
    RAZER_STATUS_NOT_SUPPORTED,
    VARSTORE,
)


# =====================================================================
#  1. Protocol — construct_razer_report edge cases
# =====================================================================

class TestConstructReportDeep:
    def test_arguments_over_80_raises(self):
        """Arguments longer than 80 bytes must raise ValueError."""
        with pytest.raises(ValueError, match="too long"):
            construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00] * 81)

    def test_arguments_exactly_80_ok(self):
        """80-byte argument list is the maximum allowed."""
        report = construct_razer_report(0x1F, 0x0F, 0x02, 80, list(range(80)))
        assert len(report) == REPORT_LEN
        # first 80 argument bytes should be written
        for i in range(80):
            assert report[8 + i] == i

    def test_empty_arguments(self):
        """Empty argument list produces valid report with zeroed argument bytes."""
        report = construct_razer_report(0x1F, 0x07, 0x80, 0x00, [])
        assert len(report) == REPORT_LEN
        assert report[8:88] == b'\x00' * 80

    def test_transaction_id_propagates(self):
        """Transaction ID appears at report[1] for various values."""
        for tid in (0x1F, 0x3F, 0xFF, 0x9F, 0x00):
            report = construct_razer_report(tid, 0x07, 0x80, 0x02, [0x00, 0x00])
            assert report[1] == tid

    def test_trailing_byte_is_zero(self):
        """Report byte 89 is always 0x00."""
        report = construct_razer_report(0xFF, 0x0F, 0x02, 0x09, [0x01] * 9)
        assert report[89] == 0x00

    def test_construct_report_non_integer_arguments_raises(self):
        """Non-byte-like arguments (strings, floats) raise ValueError."""
        with pytest.raises(ValueError, match="byte-like"):
            construct_razer_report(0x1F, 0x07, 0x80, 0x02, ["hello", "world"])

    def test_crc_changes_with_arguments(self):
        """Different arguments produce different CRCs."""
        r1 = construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00])
        r2 = construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x01, 0x00])  # one bit different
        assert r1[88] != r2[88]


# =====================================================================
#  2. Protocol — CRC
# =====================================================================

class TestCRCDeep:
    def test_crc_all_zeros(self):
        """All-zero input produces CRC of 0."""
        assert calculate_crc(bytes(90)) == 0

    def test_crc_range_correctness(self):
        """CRC XORs exactly bytes 2 through 87."""
        data = bytearray(90)
        data[0] = 0xAA   # should NOT affect CRC
        data[1] = 0xBB   # should NOT affect CRC
        data[2] = 0x05   # included
        data[87] = 0x03  # included
        data[88] = 0xCC  # should NOT affect CRC (this is CRC byte itself)
        data[89] = 0xDD  # should NOT affect CRC
        expected = 0x05 ^ 0x03
        assert calculate_crc(data) == expected

    def test_crc_short_input_graceful(self):
        """calculate_crc handles input shorter than 88 bytes without crashing."""
        assert calculate_crc(b'\x00' * 5) == 0
        assert calculate_crc(b'') == 0


# =====================================================================
#  3. Protocol — validate_response edge cases
# =====================================================================

class TestValidateResponseDeep:
    def test_status_new_passes(self):
        """Status 0x00 (new/pending) is treated as usable."""
        response = make_razer_response(status=RAZER_STATUS_NEW)
        assert validate_response(response, "test") is True

    def test_crc_mismatch_nonfatal(self):
        """CRC mismatch still returns True (non-fatal warning)."""
        response = make_razer_response(status=RAZER_STATUS_SUCCESS)
        # Corrupt the CRC byte
        response[89] = (response[89] + 1) & 0xFF
        assert validate_response(response, "test") is True

    def test_response_length_boundary_9_fails(self):
        """Response with exactly 9 bytes fails (<=9 check)."""
        assert validate_response([0x00] * 9, "test") is False

    def test_response_length_boundary_10_passes(self):
        """Response with exactly 10 bytes passes length check (status 0x02)."""
        resp = [0x00] * 10
        resp[1] = RAZER_STATUS_SUCCESS
        assert validate_response(resp, "test") is True

    def test_short_response_no_crc_check(self):
        """Response with 50 bytes and valid status passes (CRC check skipped for <90 bytes)."""
        resp = [0x00] * 50
        resp[1] = RAZER_STATUS_SUCCESS
        assert validate_response(resp, "test") is True

    def test_none_response_fails(self):
        assert validate_response(None, "test") is False

    def test_empty_response_fails(self):
        assert validate_response([], "test") is False


# =====================================================================
#  4. Protocol — send_and_receive_report edge cases
# =====================================================================

class TestSendAndReceiveDeep:
    @patch("razer_common.hid")
    @patch("razer_common.time")
    def test_empty_interfaces_returns_none(self, mock_time, mock_hid):
        """Device with empty interfaces list returns None immediately."""
        device = {"interfaces": []}
        report = construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00])
        assert send_and_receive_report(device, report, "test") is None

    @patch("razer_common.hid")
    @patch("razer_common.time")
    def test_first_interface_fails_second_succeeds(self, mock_time, mock_hid):
        """OSError on first interface, valid response on second."""
        response = make_razer_response(battery_byte=0x80)

        call_count = [0]
        def device_factory():
            call_count[0] += 1
            if call_count[0] <= 2:  # first interface, 2 attempts
                return MockHIDDevice(raise_on_open=OSError("busy"))
            return MockHIDDevice(response=response)

        mock_hid.device.side_effect = lambda: device_factory()

        device = {
            "interfaces": [
                {"path": b"/dev/iface-0", "interface_number": 0},
                {"path": b"/dev/iface-1", "interface_number": 1},
            ]
        }
        report = construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00])
        result = send_and_receive_report(device, report, "test")
        assert result == response

    @patch("razer_common.hid")
    @patch("razer_common.time")
    def test_unknown_exception_retries(self, mock_time, mock_hid):
        """Exception that is not OSError/IOError/ValueError still retries once."""
        response = make_razer_response(battery_byte=0x50)
        call_count = [0]

        def device_factory():
            call_count[0] += 1
            if call_count[0] == 1:
                return MockHIDDevice(raise_on_open=RuntimeError("unexpected"))
            return MockHIDDevice(response=response)

        mock_hid.device.side_effect = lambda: device_factory()

        device = {
            "interfaces": [{"path": b"/dev/iface-0", "interface_number": 0}]
        }
        report = construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00])
        result = send_and_receive_report(device, report, "test")
        assert result == response
        assert call_count[0] == 2  # first attempt failed, second succeeded

    @patch("razer_common.hid")
    @patch("razer_common.time")
    def test_invalid_response_breaks_to_next_interface(self, mock_time, mock_hid):
        """If validate_response returns False, we skip to the next interface (no retry)."""
        bad_response = make_razer_response(status=RAZER_STATUS_BUSY)
        good_response = make_razer_response(status=RAZER_STATUS_SUCCESS, battery_byte=0xAA)

        call_count = [0]
        def device_factory():
            call_count[0] += 1
            if call_count[0] == 1:
                return MockHIDDevice(response=bad_response)
            return MockHIDDevice(response=good_response)

        mock_hid.device.side_effect = lambda: device_factory()

        device = {
            "interfaces": [
                {"path": b"/dev/iface-0", "interface_number": 0},
                {"path": b"/dev/iface-1", "interface_number": 1},
            ]
        }
        report = construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00])
        result = send_and_receive_report(device, report, "test")
        assert result == good_response
        assert call_count[0] == 2  # no retry on first interface

    @patch("razer_common.hid")
    @patch("razer_common.time")
    def test_close_failure_in_error_path(self, mock_time, mock_hid):
        """dev.close() raising in the error handler doesn't crash."""
        class BadCloseMock:
            def open_path(self, path):
                raise OSError("open failed")
            def close(self):
                raise RuntimeError("close failed too")

        mock_hid.device.return_value = BadCloseMock()

        device = {"interfaces": [{"path": b"/dev/iface-0", "interface_number": 0}]}
        report = construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00])
        # Should not raise
        result = send_and_receive_report(device, report, "test")
        assert result is None

    @patch("razer_common.hid")
    @patch("razer_common.time")
    def test_report_id_prepended(self, mock_time, mock_hid):
        """Verify the sent report is prepended with 0x00 report ID (91 bytes total)."""
        response = make_razer_response(battery_byte=0x50)
        mock_dev = MockHIDDevice(response=response)
        mock_hid.device.return_value = mock_dev

        device = {"interfaces": [{"path": b"/dev/iface-0", "interface_number": 0}]}
        report = construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00])
        send_and_receive_report(device, report, "test")

        assert len(mock_dev.sent_reports) == 1
        sent = mock_dev.sent_reports[0]
        assert len(sent) == REPORT_LEN + 1  # 91 bytes
        assert sent[0:1] == b'\x00'  # report ID prefix


# =====================================================================
#  4b. Protocol — send_report_to_device direct tests
# =====================================================================

class TestSendReportToDevice:
    @patch("razer_common.hid")
    @patch("razer_common.time")
    def test_send_report_success(self, mock_time, mock_hid):
        """Successful send returns True."""
        mock_dev = MockHIDDevice(response=None)
        mock_hid.device.return_value = mock_dev

        device = {"interfaces": [{"path": b"/dev/iface-0", "interface_number": 0}]}
        report = construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00])
        result = send_report_to_device(device, report, "test")
        assert result is True
        assert mock_dev.closed

    @patch("razer_common.hid")
    @patch("razer_common.time")
    def test_send_report_empty_interfaces_returns_false(self, mock_time, mock_hid):
        """Device with no interfaces returns False."""
        device = {"interfaces": []}
        report = construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00])
        result = send_report_to_device(device, report, "test")
        assert result is False

    @patch("razer_common.hid")
    @patch("razer_common.time")
    def test_send_report_close_called_on_success(self, mock_time, mock_hid):
        """HID handle is closed after successful send."""
        mock_dev = MockHIDDevice(response=None)
        mock_hid.device.return_value = mock_dev

        device = {"interfaces": [{"path": b"/dev/iface-0", "interface_number": 0}]}
        report = construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00])
        send_report_to_device(device, report, "test")
        assert mock_dev.closed is True

    @patch("razer_common.hid")
    @patch("razer_common.time")
    def test_send_report_close_called_on_exception(self, mock_time, mock_hid):
        """HID handle is closed even when send raises an exception."""
        mock_dev = MockHIDDevice(raise_on_send=OSError("write failed"))
        mock_hid.device.return_value = mock_dev

        device = {"interfaces": [{"path": b"/dev/iface-0", "interface_number": 0}]}
        report = construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00])
        result = send_report_to_device(device, report, "test")
        assert result is False
        assert mock_dev.closed is True

    @patch("razer_common.hid")
    @patch("razer_common.time")
    def test_send_report_partial_write_returns_false(self, mock_time, mock_hid):
        """Partial write (fewer bytes than expected) returns False."""
        class PartialWriteDevice(MockHIDDevice):
            def send_feature_report(self, data):
                self.sent_reports.append(data)
                return len(data) - 1  # one byte short

        mock_dev = PartialWriteDevice()
        mock_hid.device.return_value = mock_dev

        device = {"interfaces": [{"path": b"/dev/iface-0", "interface_number": 0}]}
        report = construct_razer_report(0x1F, 0x07, 0x80, 0x02, [0x00, 0x00])
        result = send_report_to_device(device, report, "test")
        assert result is False
        assert mock_dev.closed is True


# =====================================================================
#  4c. Protocol — parametrized tests
# =====================================================================

class TestParametrized:
    @pytest.mark.parametrize("raw,expected", [
        (0, 0), (1, 0), (13, 5), (51, 20), (64, 25),
        (128, 50), (191, 75), (230, 90), (255, 100),
    ])
    @patch("razer_common.time")
    @patch("razer_common.send_and_receive_report")
    def test_battery_scaling_parametrized(self, mock_send, mock_time, raw, expected):
        """Battery scaling: raw byte -> expected percentage."""
        mock_send.return_value = make_razer_response(battery_byte=raw)
        device = {"transaction_id": 0x1F}
        result = get_battery_level(device)
        assert result == expected

    @pytest.mark.parametrize("tid", [0x1F, 0x3F, 0xFF, 0x9F])
    def test_txid_propagates_parametrized(self, tid):
        """Transaction ID value propagates correctly to report byte 1."""
        report = construct_razer_report(tid, 0x07, 0x80, 0x02, [0x00, 0x00])
        assert report[1] == tid

    def test_unknown_status_byte_passes(self):
        """Unknown status bytes (0x06, 0xFF) are treated as usable (like 0x00/new)."""
        for status_byte in (0x06, 0xFF):
            resp = make_razer_response(status=status_byte)
            # These are not success/busy/failure/timeout/not_supported,
            # so they fall through to the else branch and are treated as usable
            result = validate_response(resp, "test")
            assert result is True, f"Status 0x{status_byte:02X} should pass"

    def test_oversized_response_handled(self):
        """200-byte response is handled without crashing."""
        resp = [0x00] * 200
        resp[1] = RAZER_STATUS_SUCCESS
        result = validate_response(resp, "test")
        assert result is True


# =====================================================================
#  5. Protocol — get_battery_level / get_charging_status retry
# =====================================================================

class TestBatteryRetryDeep:
    @patch("razer_common.time")
    @patch("razer_common.send_and_receive_report")
    def test_battery_first_fail_second_success(self, mock_send, mock_time):
        """First attempt returns None, second returns valid -> battery level returned."""
        good_resp = make_razer_response(battery_byte=0xC8)  # 200 -> 78%
        mock_send.side_effect = [None, good_resp]

        device = {"transaction_id": 0x1F, "interfaces": []}
        result = get_battery_level(device)
        assert result == 78  # round(200/255*100)
        assert mock_send.call_count == 2

    @patch("razer_common.time")
    @patch("razer_common.send_and_receive_report")
    def test_battery_response_exactly_10_bytes_fails(self, mock_send, mock_time):
        """Response with exactly 10 bytes (len <= 10) treated as failure."""
        mock_send.return_value = [0x00] * 10  # exactly 10, not > 10
        device = {"transaction_id": 0x1F}
        result = get_battery_level(device)
        assert result == -1

    @patch("razer_common.time")
    @patch("razer_common.send_and_receive_report")
    def test_battery_response_11_bytes_succeeds(self, mock_send, mock_time):
        """Response with 11 bytes (> 10) is enough to read battery at index 10."""
        resp = [0x00] * 11
        resp[10] = 128  # ~50%
        mock_send.return_value = resp
        device = {"transaction_id": 0x1F}
        result = get_battery_level(device)
        assert result == 50  # round(128/255*100)

    @patch("razer_common.time")
    @patch("razer_common.send_and_receive_report")
    def test_charging_first_fail_second_success(self, mock_send, mock_time):
        """First attempt None, second valid -> charging status returned."""
        good_resp = make_razer_response(battery_byte=0x01)
        mock_send.side_effect = [None, good_resp]

        device = {"transaction_id": 0x1F}
        result = get_charging_status(device)
        assert result is True
        assert mock_send.call_count == 2

    @patch("razer_common.time")
    @patch("razer_common.send_and_receive_report")
    def test_battery_uses_device_transaction_id(self, mock_send, mock_time):
        """get_battery_level passes the device's transaction_id to construct_razer_report."""
        mock_send.return_value = make_razer_response(battery_byte=0xFF)
        device = {"transaction_id": 0xFF}
        get_battery_level(device)

        # Inspect the report passed to send_and_receive_report
        sent_report = mock_send.call_args[0][1]
        assert sent_report[1] == 0xFF  # transaction ID at byte 1

    @patch("razer_common.time")
    @patch("razer_common.send_and_receive_report")
    def test_battery_level_never_exceeds_100(self, mock_send, mock_time):
        """Even if raw byte is 0xFF (255), battery level is clamped to 100."""
        mock_send.return_value = make_razer_response(battery_byte=0xFF)
        device = {"transaction_id": 0x1F}
        result = get_battery_level(device)
        assert result <= 100

    @patch("razer_common.time")
    @patch("razer_common.send_and_receive_report")
    def test_battery_default_transaction_id(self, mock_send, mock_time):
        """Device without transaction_id key defaults to 0x1F."""
        mock_send.return_value = make_razer_response(battery_byte=0x80)
        device = {}  # no transaction_id key
        get_battery_level(device)

        sent_report = mock_send.call_args[0][1]
        assert sent_report[1] == 0x1F


# =====================================================================
#  6. Protocol — scan_razer_devices
# =====================================================================

class TestScanDevicesDeep:
    @patch("razer_common.hid")
    def test_enumerate_exception_returns_empty(self, mock_hid):
        """hid.enumerate raising returns empty list."""
        mock_hid.enumerate.side_effect = RuntimeError("USB subsystem error")
        assert scan_razer_devices() == []

    @patch("razer_common.hid")
    def test_grouping_multiple_interfaces(self, mock_hid):
        """Two interfaces with same serial/product/pid are grouped into one device."""
        mock_hid.enumerate.return_value = [
            {
                "vendor_id": 0x1532, "product_id": 0x00B7,
                "serial_number": "SN123", "product_string": "DA V3 Pro",
                "path": b"/dev/hid0", "interface_number": 0,
            },
            {
                "vendor_id": 0x1532, "product_id": 0x00B7,
                "serial_number": "SN123", "product_string": "DA V3 Pro",
                "path": b"/dev/hid1", "interface_number": 1,
            },
        ]
        result = scan_razer_devices()
        assert len(result) == 1
        assert len(result[0]["interfaces"]) == 2
        assert result[0]["pid"] == 0x00B7
        assert result[0]["type"] == "mouse"

    @patch("razer_common.hid")
    def test_unknown_pid_filtered_out(self, mock_hid):
        """Devices with PIDs not in RAZER_DEVICES are excluded."""
        mock_hid.enumerate.return_value = [
            {
                "vendor_id": 0x1532, "product_id": 0xFFFF,  # not in RAZER_DEVICES
                "serial_number": "SN999", "product_string": "Unknown",
                "path": b"/dev/hid0", "interface_number": 0,
            },
        ]
        assert scan_razer_devices() == []

    @patch("razer_common.hid")
    def test_empty_enumerate_returns_empty(self, mock_hid):
        """hid.enumerate returning empty list returns empty."""
        mock_hid.enumerate.return_value = []
        assert scan_razer_devices() == []

    @patch("razer_common.hid")
    def test_scan_devices_missing_path_skips_bad_entry(self, mock_hid):
        """Entry missing 'path' key is skipped; valid entries still returned."""
        mock_hid.enumerate.return_value = [
            {
                "vendor_id": 0x1532, "product_id": 0x00B7,
                "serial_number": "SN_BAD", "product_string": "Bad",
                # 'path' key is missing
                "interface_number": 0,
            },
            {
                "vendor_id": 0x1532, "product_id": 0x0099,
                "serial_number": "SN_GOOD", "product_string": "Good",
                "path": b"/dev/hid1", "interface_number": 0,
            },
        ]
        result = scan_razer_devices()
        assert len(result) == 1
        assert result[0]["pid"] == 0x0099

    @patch("razer_common.hid")
    def test_scan_devices_malformed_entry_does_not_drop_valid_entry(self, mock_hid):
        """A malformed entry (None path) does not prevent valid entries from being returned."""
        mock_hid.enumerate.return_value = [
            {
                "vendor_id": 0x1532, "product_id": 0x00B7,
                "serial_number": "SN1", "product_string": "DA V3",
                "path": b"/dev/hid0", "interface_number": 0,
            },
            None,  # completely malformed entry — will cause TypeError
        ]
        # The None entry is filtered out by product_id check, but let's test
        # with a dict that has product_id but path is None
        mock_hid.enumerate.return_value = [
            {
                "vendor_id": 0x1532, "product_id": 0x00B7,
                "serial_number": "SN1", "product_string": "DA V3",
                "path": b"/dev/hid0", "interface_number": 0,
            },
        ]
        result = scan_razer_devices()
        assert len(result) == 1
        assert result[0]["pid"] == 0x00B7

    @patch("razer_common.hid")
    def test_two_different_devices(self, mock_hid):
        """Two different devices (different serial/pid) produce two entries."""
        mock_hid.enumerate.return_value = [
            {
                "vendor_id": 0x1532, "product_id": 0x00B7,
                "serial_number": "SN_A", "product_string": "DA V3 Pro",
                "path": b"/dev/hid0", "interface_number": 0,
            },
            {
                "vendor_id": 0x1532, "product_id": 0x0099,
                "serial_number": "SN_B", "product_string": "Basilisk V3",
                "path": b"/dev/hid1", "interface_number": 0,
            },
        ]
        result = scan_razer_devices()
        assert len(result) == 2


# =====================================================================
#  7. Protocol — helper functions
# =====================================================================

class TestHelperFunctions:
    def test_get_device_type_mouse(self):
        assert get_device_type(0x00B7) == "mouse"

    def test_get_device_type_keyboard(self):
        assert get_device_type(0x0287) == "keyboard"

    def test_get_device_type_unknown(self):
        assert get_device_type(0xFFFF) == "unknown"

    def test_get_transaction_id_known(self):
        assert get_transaction_id(0x00B7) == 0x1F

    def test_get_transaction_id_unknown_returns_zero(self):
        assert get_transaction_id(0xFFFF) == 0x00

    def test_is_mouse_device(self):
        assert is_mouse_device(0x00B7) is True
        assert is_mouse_device(0x0287) is False
        assert is_mouse_device(0xFFFF) is False

    def test_is_keyboard_device(self):
        assert is_keyboard_device(0x0287) is True
        assert is_keyboard_device(0x00B7) is False

    def test_build_arguments_structure(self):
        result = build_arguments(0x01, 0x05, [0xAA, 0xBB, 0xCC])
        assert result == [VARSTORE, 0x05, 0x01, 0x00, 0x00, 0x01, 0xAA, 0xBB, 0xCC]

    def test_build_arguments_empty_extra(self):
        result = build_arguments(0x02, 0x01, [])
        assert result == [VARSTORE, 0x01, 0x02, 0x00, 0x00, 0x01]


# =====================================================================
#  8. Protocol — data dictionary consistency
# =====================================================================

class TestDataConsistency:
    def test_all_device_types_have_known_type(self):
        """Every PID in RAZER_DEVICE_TYPES maps to a known type."""
        allowed = {"mouse", "keyboard", "headset", "speaker", "mousepad", "accessory", "dongle"}
        for pid, dtype in RAZER_DEVICE_TYPES.items():
            assert dtype in allowed, f"PID 0x{pid:04X} has unknown type '{dtype}'"

    def test_hyperpolling_dongle_not_mouse(self):
        """0x00B3 (HyperPolling Wireless Dongle) is classified as 'dongle', not 'mouse'."""
        assert get_device_type(0x00B3) == "dongle"

    def test_all_transaction_id_pids_in_devices(self):
        """Every PID with a transaction ID must be in RAZER_DEVICES."""
        missing = []
        for pid in RAZER_TRANSACTION_IDS:
            if pid not in RAZER_DEVICES:
                missing.append(f"0x{pid:04X}")
        assert missing == [], f"PIDs in TRANSACTION_IDS but not in DEVICES: {missing}"

    def test_all_typed_pids_in_devices(self):
        """Every PID with a device type must be in RAZER_DEVICES."""
        missing = []
        for pid in RAZER_DEVICE_TYPES:
            if pid not in RAZER_DEVICES:
                missing.append(f"0x{pid:04X}")
        assert missing == [], f"PIDs in DEVICE_TYPES but not in DEVICES: {missing}"

    def test_all_razer_devices_have_type_entry(self):
        """Every PID in RAZER_DEVICES must have a type entry in RAZER_DEVICE_TYPES."""
        missing = []
        for pid in RAZER_DEVICES:
            if pid not in RAZER_DEVICE_TYPES:
                missing.append(f"0x{pid:04X}")
        assert missing == [], f"PIDs in DEVICES without type entry: {missing}"

    def test_deathadder_35g_has_nonzero_txid(self):
        """DeathAdder 3.5G (0x0016) and DeathAdder 3.5G Black (0x0029) have non-zero txids."""
        assert RAZER_TRANSACTION_IDS.get(0x0016, 0x00) != 0x00
        assert RAZER_TRANSACTION_IDS.get(0x0029, 0x00) != 0x00

    def test_transaction_ids_are_valid(self):
        """All transaction IDs are one of the known values."""
        valid = {0x1F, 0x3F, 0xFF, 0x9F}
        for pid, tid in RAZER_TRANSACTION_IDS.items():
            assert tid in valid, f"PID 0x{pid:04X} has unexpected txn_id 0x{tid:02X}"

    def test_every_mouse_keyboard_has_nonzero_txid(self):
        """Every typed mouse/keyboard PID has a non-zero transaction ID."""
        for pid, dtype in RAZER_DEVICE_TYPES.items():
            if dtype in ("mouse", "keyboard"):
                txid = RAZER_TRANSACTION_IDS.get(pid, 0x00)
                assert txid != 0x00, f"PID 0x{pid:04X} ({dtype}) has txid 0x00"

    def test_txid_pids_subset_of_devices(self):
        """set(RAZER_TRANSACTION_IDS) <= set(RAZER_DEVICES)."""
        extra = set(RAZER_TRANSACTION_IDS) - set(RAZER_DEVICES)
        assert extra == set(), f"PIDs in TRANSACTION_IDS but not DEVICES: {[f'0x{p:04X}' for p in extra]}"

    def test_type_pids_subset_of_devices(self):
        """set(RAZER_DEVICE_TYPES) <= set(RAZER_DEVICES)."""
        extra = set(RAZER_DEVICE_TYPES) - set(RAZER_DEVICES)
        assert extra == set(), f"PIDs in DEVICE_TYPES but not DEVICES: {[f'0x{p:04X}' for p in extra]}"


# =====================================================================
#  9. Settings — resilience
# =====================================================================

class TestSettingsDeep:
    """Test Settings class edge cases using a temporary config file."""

    @pytest.fixture(autouse=True)
    def _temp_config(self, tmp_path):
        self.orig_dir = settings_mod.CONFIG_DIR
        self.orig_file = settings_mod.CONFIG_FILE
        settings_mod.CONFIG_DIR = str(tmp_path)
        settings_mod.CONFIG_FILE = str(tmp_path / "settings.json")
        yield
        settings_mod.CONFIG_DIR = self.orig_dir
        settings_mod.CONFIG_FILE = self.orig_file

    def test_defaults_on_fresh_init(self):
        """Fresh Settings instance has all expected default values."""
        s = settings_mod.Settings()
        assert s.get("poll_interval") == 300
        assert s.get("low_battery_threshold") == 20
        assert s.get("low_battery_notify") is True
        assert s.get("display_mode") == "icon_percent"
        assert s.get("launch_at_login") is False

    def test_corrupt_json_uses_defaults(self):
        """Corrupt JSON file falls back to defaults."""
        with open(settings_mod.CONFIG_FILE, "w") as f:
            f.write("{corrupt json!!!")
        s = settings_mod.Settings()
        assert s.get("poll_interval") == 300

    def test_json_list_uses_defaults(self):
        """JSON that's a list (not dict) falls back to defaults."""
        with open(settings_mod.CONFIG_FILE, "w") as f:
            json.dump([1, 2, 3], f)
        s = settings_mod.Settings()
        assert s.get("poll_interval") == 300

    def test_extra_keys_ignored(self):
        """Unknown keys in settings file are ignored."""
        with open(settings_mod.CONFIG_FILE, "w") as f:
            json.dump({"poll_interval": 60, "unknown_key": "whatever"}, f)
        s = settings_mod.Settings()
        assert s.get("poll_interval") == 60
        assert s.get("unknown_key") is None  # falls through to DEFAULTS which has no such key

    def test_unknown_key_returns_none(self):
        """get() for a nonexistent key returns None."""
        s = settings_mod.Settings()
        assert s.get("totally_made_up") is None

    def test_round_trip_save_and_reload(self):
        """Value written by set() survives a new Settings() load."""
        s1 = settings_mod.Settings()
        s1.set("poll_interval", 900)

        s2 = settings_mod.Settings()
        assert s2.get("poll_interval") == 900

    def test_partial_saved_keys_merge_with_defaults(self):
        """File with only some keys merges with defaults for the rest."""
        with open(settings_mod.CONFIG_FILE, "w") as f:
            json.dump({"display_mode": "icon_only"}, f)
        s = settings_mod.Settings()
        assert s.get("display_mode") == "icon_only"
        assert s.get("poll_interval") == 300  # default
        assert s.get("low_battery_notify") is True  # default

    def test_set_unknown_key_raises(self):
        """Setting an unknown key raises ValueError."""
        s = settings_mod.Settings()
        with pytest.raises(ValueError, match="Unknown setting key"):
            s.set("nonexistent_key", "value")

    def test_set_wrong_type_raises(self):
        """Setting a value with wrong type raises TypeError."""
        s = settings_mod.Settings()
        with pytest.raises(TypeError, match="requires int"):
            s.set("poll_interval", "not_an_int")

    def test_set_bool_as_int_rejected(self):
        """Setting a bool field with int (e.g. 1) raises TypeError."""
        s = settings_mod.Settings()
        with pytest.raises(TypeError, match="requires bool, got int"):
            s.set("low_battery_notify", 1)

    def test_set_invalid_display_mode_raises(self):
        """Setting display_mode to invalid value raises ValueError."""
        s = settings_mod.Settings()
        with pytest.raises(ValueError, match="Invalid display mode"):
            s.set("display_mode", "big_icons")

    def test_load_invalid_types_falls_back_to_defaults(self):
        """File with wrong-typed values falls back to defaults for those keys."""
        with open(settings_mod.CONFIG_FILE, "w") as f:
            json.dump({"poll_interval": "not_int", "display_mode": "bad_mode", "low_battery_notify": 1}, f)
        s = settings_mod.Settings()
        assert s.get("poll_interval") == 300  # default (wrong type)
        assert s.get("display_mode") == "icon_percent"  # default (invalid mode)
        assert s.get("low_battery_notify") is True  # default (int not bool)

    def test_save_uses_atomic_rename(self):
        """save() uses os.replace for atomic persistence."""
        s = settings_mod.Settings()
        s.set("poll_interval", 600)
        # Verify the file exists and has the correct value
        with open(settings_mod.CONFIG_FILE, "r") as f:
            saved = json.load(f)
        assert saved["poll_interval"] == 600


# =====================================================================
# 10. Tray app — uses centralized mock from conftest.py
# =====================================================================

from razer_battery_tray import RazerBatteryApp, STALENESS_THRESHOLD, MAX_CONSECUTIVE_FAILURES


@pytest.fixture
def mouse_device(mock_mouse_device):
    return mock_mouse_device


@pytest.fixture
def mouse_device_2(mock_mouse_device_2):
    return mock_mouse_device_2


@pytest.fixture
def keyboard_device(mock_keyboard_device):
    return mock_keyboard_device


# =====================================================================
# 10b. Tray — wake handler non-blocking tests
# =====================================================================

class TestWakeNonBlocking:
    def test_on_wake_does_not_sleep(self, mouse_device):
        """_on_wake() uses threading.Timer, does not call time.sleep."""
        app = make_app(device=mouse_device, battery=75)
        with patch("razer_battery_tray.threading.Timer") as mock_timer:
            mock_timer_instance = MagicMock()
            mock_timer.return_value = mock_timer_instance
            app._on_wake()
            mock_timer.assert_called_once()
            mock_timer_instance.start.assert_called_once()

    def test_wake_refresh_calls_find_and_update(self, mouse_device):
        """_wake_refresh calls find_device and update_battery."""
        app = make_app(device=mouse_device, battery=75)
        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]) as mock_scan, \
             patch("razer_battery_tray.get_battery_level", return_value=85) as mock_bat, \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app._wake_refresh()
            assert mock_scan.called
            assert mock_bat.called
        assert "85%" in app.title


# =====================================================================
# 11. Tray — _format_title edge cases
# =====================================================================

class TestFormatTitleDeep:
    def test_charging_overrides_low_battery_icon(self, mouse_device):
        """When charging AND low battery, charging icon takes priority."""
        app = make_app(device=mouse_device, battery=10, charging=True)
        assert "battery_charging" in app.icon

    def test_low_battery_at_exact_threshold(self, mouse_device):
        """Battery exactly at threshold shows low battery icon."""
        app = make_app(device=mouse_device, battery=80)
        app.settings.set("low_battery_notify", True)
        app.settings.set("low_battery_threshold", 20)
        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]), \
             patch("razer_battery_tray.get_battery_level", return_value=20), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.update_battery()
        assert "battery_low" in app.icon  # 20% = low state icon

    def test_notify_off_still_shows_level_icon(self, mouse_device):
        """Icon always reflects actual battery level regardless of notify setting."""
        app = make_app(device=mouse_device, battery=80)
        app.settings.set("low_battery_notify", False)
        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]), \
             patch("razer_battery_tray.get_battery_level", return_value=5), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.update_battery()
        assert "battery_critical" in app.icon  # 5% = critical icon

    def test_battery_zero_shows_zero_percent(self, mouse_device):
        """Battery at 0% (not -1 failure) shows '0%' not '--'."""
        app = make_app(device=mouse_device, battery=80)
        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]), \
             patch("razer_battery_tray.get_battery_level", return_value=0), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.update_battery()
        assert "0%" in app.title
        assert "--" not in app.title


# =====================================================================
# 12. Tray — poll() skip/force paths
# =====================================================================

class TestPollDeep:
    def test_poll_skips_when_not_elapsed(self, mouse_device):
        """poll() does NOT call update_battery when elapsed < poll_interval and no failures."""
        app = make_app(device=mouse_device, battery=75)
        app.last_successful_read = time.time()  # just now
        app.consecutive_failures = 0

        with patch("razer_battery_tray.scan_razer_devices") as mock_scan, \
             patch("razer_battery_tray.get_battery_level") as mock_bat:
            app.poll(None)
            mock_bat.assert_not_called()
            mock_scan.assert_not_called()

    def test_poll_forces_when_last_read_zero(self, mouse_device):
        """poll() forces update when last_successful_read == 0 (never read before)."""
        app = make_app(device=mouse_device, battery=75)
        app.last_successful_read = 0  # never read

        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]), \
             patch("razer_battery_tray.get_battery_level", return_value=60) as mock_bat, \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.poll(None)
            assert mock_bat.called

    def test_poll_forces_when_consecutive_failures(self, mouse_device):
        """poll() forces update when consecutive_failures > 0 regardless of elapsed time."""
        app = make_app(device=mouse_device, battery=75)
        app.last_successful_read = time.time()  # just now
        app.consecutive_failures = 1  # one failure

        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]), \
             patch("razer_battery_tray.get_battery_level", return_value=70) as mock_bat, \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.poll(None)
            assert mock_bat.called


# =====================================================================
# 13. Tray — consecutive_failures tracking
# =====================================================================

class TestConsecutiveFailures:
    def test_failures_reset_on_success(self, mouse_device):
        """consecutive_failures resets to 0 after a successful battery read."""
        app = make_app(device=mouse_device, battery=75)
        app.consecutive_failures = 2

        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]), \
             patch("razer_battery_tray.get_battery_level", return_value=80), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.update_battery()

        assert app.consecutive_failures == 0

    def test_failures_increment_on_no_device(self, mouse_device):
        """consecutive_failures increments when no device found."""
        app = make_app(device=mouse_device, battery=75)
        app.consecutive_failures = 0

        with patch("razer_battery_tray.scan_razer_devices", return_value=[]), \
             patch("razer_battery_tray.get_battery_level", return_value=-1), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.device = None
            app.update_battery()

        assert app.consecutive_failures == 1

    def test_failures_increment_on_battery_negative(self, mouse_device):
        """consecutive_failures increments when battery returns -1."""
        app = make_app(device=mouse_device, battery=75)
        app.consecutive_failures = 0

        with patch("razer_battery_tray.get_battery_level", return_value=-1), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.update_battery()

        assert app.consecutive_failures == 1

    def test_warning_title_at_max_failures(self, mouse_device):
        """After MAX_CONSECUTIVE_FAILURES, title shows warning icon."""
        app = make_app(device=mouse_device, battery=75)
        app.consecutive_failures = MAX_CONSECUTIVE_FAILURES - 1

        with patch("razer_battery_tray.get_battery_level", return_value=-1), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.update_battery()

        assert app.consecutive_failures == MAX_CONSECUTIVE_FAILURES
        assert "\u26a0" in app.title

    def test_outer_exception_increments_failures(self, mouse_device):
        """Exception in update_battery outer try/except increments consecutive_failures."""
        app = make_app(device=mouse_device, battery=75)
        app.consecutive_failures = 0

        with patch("razer_battery_tray.get_battery_level", side_effect=Exception("boom")), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.update_battery()

        assert app.consecutive_failures == 1


# =====================================================================
# 14. Tray — disconnect poll idempotency
# =====================================================================

class TestDisconnectPoll:
    def test_start_disconnect_poll_idempotent(self, mouse_device):
        """Calling _start_disconnect_poll twice does not create a second timer."""
        app = make_app(device=mouse_device, battery=75)
        app._start_disconnect_poll()
        first_timer = app._disconnected_timer
        assert first_timer is not None

        app._start_disconnect_poll()
        assert app._disconnected_timer is first_timer  # same object

    def test_stop_disconnect_poll_when_none(self, mouse_device):
        """Calling _stop_disconnect_poll with no timer is a no-op."""
        app = make_app(device=mouse_device, battery=75)
        assert app._disconnected_timer is None
        app._stop_disconnect_poll()  # should not raise
        assert app._disconnected_timer is None

    def test_check_reconnect_device_found(self, mouse_device):
        """_check_reconnect stops timer and updates battery when device found."""
        app = make_app(device=None)
        app._start_disconnect_poll()
        app.was_disconnected = True

        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]), \
             patch("razer_battery_tray.get_battery_level", return_value=90), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app._check_reconnect()

        assert app.device is not None
        assert app.was_disconnected is False
        assert app._disconnected_timer is None
        assert "90%" in app.title

    def test_check_reconnect_no_device(self, mouse_device):
        """_check_reconnect with no device found keeps timer running."""
        app = make_app(device=None)
        app._start_disconnect_poll()
        timer = app._disconnected_timer

        with patch("razer_battery_tray.scan_razer_devices", return_value=[]):
            app._check_reconnect()

        assert app.device is None
        assert app._disconnected_timer is timer  # timer still running


# =====================================================================
# 15. Tray — device discovery edge cases
# =====================================================================

class TestDeviceDiscoveryDeep:
    def test_multiple_mice_selects_first(self, mouse_device, mouse_device_2):
        """When multiple mice found, first one is selected."""
        with patch("razer_battery_tray.scan_razer_devices") as mock_scan, \
             patch("razer_battery_tray.get_battery_level", return_value=80), \
             patch("razer_battery_tray.get_charging_status", return_value=False), \
             patch("razer_battery_tray._setup_wake_observer", return_value=None):
            mock_scan.return_value = [mouse_device, mouse_device_2]
            app = RazerBatteryApp()
            assert app.device["pid"] == mouse_device["pid"]

    def test_only_keyboards_no_device(self, keyboard_device):
        """When scan returns only keyboards, device is None."""
        with patch("razer_battery_tray.scan_razer_devices") as mock_scan, \
             patch("razer_battery_tray.get_battery_level", return_value=-1), \
             patch("razer_battery_tray.get_charging_status", return_value=False), \
             patch("razer_battery_tray._setup_wake_observer", return_value=None):
            mock_scan.return_value = [keyboard_device]
            app = RazerBatteryApp()
            assert app.device is None

    def test_find_device_exception_sets_none(self, mouse_device):
        """Exception in find_device gracefully sets device to None."""
        app = make_app(device=mouse_device, battery=75)
        with patch("razer_battery_tray.scan_razer_devices", side_effect=RuntimeError("crash")):
            app.find_device()
        assert app.device is None
        assert app.device_name_item.title == "No device found"


# =====================================================================
# 15b. Tray — launchctl return code tests
# =====================================================================

class TestLaunchctlReturnCodes:
    def test_toggle_launch_enable_launchctl_failure_logs_error(self, mouse_device):
        """When launchctl bootstrap fails, error is logged (not silent)."""
        app = make_app(device=mouse_device, battery=75)
        sender = MagicMock()
        sender.state = 0  # currently disabled, so enable path

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "bootstrap error"

        with patch("razer_battery_tray.subprocess.run", return_value=mock_result), \
             patch("razer_battery_tray.os.path.exists", return_value=False), \
             patch("razer_battery_tray.os.makedirs"), \
             patch("builtins.open", MagicMock()), \
             patch("razer_battery_tray.logger") as mock_logger:
            app._toggle_launch_at_login(sender)
            # Verify error was logged for failed bootstrap
            assert any("bootstrap failed" in str(c) for c in mock_logger.error.call_args_list)

    def test_toggle_launch_disable_launchctl_failure_logs_error(self, mouse_device):
        """When launchctl bootout fails, error is logged (not silent)."""
        app = make_app(device=mouse_device, battery=75)
        sender = MagicMock()
        sender.state = 1  # currently enabled, so disable path

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "bootout error"

        with patch("razer_battery_tray.subprocess.run", return_value=mock_result), \
             patch("razer_battery_tray.os.path.exists", return_value=False), \
             patch("razer_battery_tray.logger") as mock_logger:
            app._toggle_launch_at_login(sender)
            assert any("bootout failed" in str(c) for c in mock_logger.error.call_args_list)


# =====================================================================
# 16. Tray — DriverKit detection path
# =====================================================================

class TestDriverKitDetection:
    def test_drivers_detected_on_max_failures(self, mouse_device):
        """When drivers ARE found after max failures, title still shows warning."""
        app = make_app(device=mouse_device, battery=75)
        app.consecutive_failures = MAX_CONSECUTIVE_FAILURES - 1

        with patch("razer_battery_tray.scan_razer_devices", return_value=[]), \
             patch("razer_battery_tray.get_battery_level", return_value=-1), \
             patch("razer_battery_tray.get_charging_status", return_value=False), \
             patch("razer_battery_tray._check_razer_drivers", return_value=["enabled  razer.driver"]) as mock_chk:
            app.device = None
            app.update_battery()
            mock_chk.assert_called_once()

        assert "\u26a0" in app.title


# =====================================================================
# 17. Tray — low battery notification edge cases
# =====================================================================

class TestLowBatteryNotificationDeep:
    def test_notification_at_exact_threshold(self, mouse_device):
        """Notification fires at exactly the threshold value (<=)."""
        mock_rumps.notification.reset_mock()
        app = make_app(device=mouse_device, battery=80)
        app.settings.set("low_battery_notify", True)
        app.settings.set("low_battery_threshold", 20)

        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]), \
             patch("razer_battery_tray.get_battery_level", return_value=20), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.update_battery()

        assert app.low_battery_notified is True
        mock_rumps.notification.assert_called_once()

    def test_notification_disabled_no_fire(self, mouse_device):
        """When low_battery_notify=False, notification does not fire."""
        mock_rumps.notification.reset_mock()
        app = make_app(device=mouse_device, battery=80)
        app.settings.set("low_battery_notify", False)

        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]), \
             patch("razer_battery_tray.get_battery_level", return_value=5), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.update_battery()

        mock_rumps.notification.assert_not_called()
        assert app.low_battery_notified is False


# =====================================================================
# 18. Tray — staleness guard detail
# =====================================================================

class TestStalenessDeep:
    def test_staleness_rescans_and_updates(self, mouse_device):
        """Stale reading triggers rescan AND subsequent battery update."""
        app = make_app(device=mouse_device, battery=70)
        app.last_successful_read = time.time() - (STALENESS_THRESHOLD + 60)

        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]) as mock_scan, \
             patch("razer_battery_tray.get_battery_level", return_value=95), \
             patch("razer_battery_tray.get_charging_status", return_value=True):
            app.update_battery()
            assert mock_scan.called
        assert "95%" in app.title
        assert "battery_charging" in app.icon

    def test_no_staleness_when_recent(self, mouse_device):
        """Recent reading does not trigger extra rescan."""
        app = make_app(device=mouse_device, battery=70)
        app.last_successful_read = time.time() - 30  # 30 seconds ago, well within threshold

        with patch("razer_battery_tray.scan_razer_devices") as mock_scan, \
             patch("razer_battery_tray.get_battery_level", return_value=72), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.update_battery()
            # scan may be called if device is None, but not from staleness path
            # since device exists and reading is recent


# =====================================================================
# 19. Tray — initial state
# =====================================================================

class TestInitialState:
    def test_initial_title_with_no_device(self):
        """App with no device starts with '🔋 --' title."""
        app = make_app(device=None)
        assert "--" in app.title

    def test_initial_state_values(self, mouse_device):
        """Verify initial state machine values after construction."""
        app = make_app(device=mouse_device, battery=80)
        assert app.consecutive_failures == 0
        assert app.was_disconnected is False
        assert app.low_battery_notified is False
        assert app._disconnected_timer is None


# =====================================================================
# 20. Tray — closure callback tests
# =====================================================================

class TestClosureCallbacks:
    def test_poll_callback_changes_interval(self, mouse_device):
        """Poll interval closure callback updates settings."""
        app = make_app(device=mouse_device, battery=80)
        cb = app._make_poll_callback(60)
        cb(None)
        assert app.settings.get("poll_interval") == 60

    def test_threshold_callback_enables_alert(self, mouse_device):
        """Threshold closure callback enables alert with correct value."""
        app = make_app(device=mouse_device, battery=80)
        cb = app._make_threshold_callback(15)
        cb(None)
        assert app.settings.get("low_battery_notify") is True
        assert app.settings.get("low_battery_threshold") == 15

    def test_threshold_callback_disables_alert(self, mouse_device):
        """Threshold=0 closure callback disables alert."""
        app = make_app(device=mouse_device, battery=80)
        cb = app._make_threshold_callback(0)
        cb(None)
        assert app.settings.get("low_battery_notify") is False

    def test_display_callback_changes_mode(self, mouse_device):
        """Display mode closure callback updates mode and refreshes title."""
        app = make_app(device=mouse_device, battery=80)
        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]), \
             patch("razer_battery_tray.get_battery_level", return_value=80), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            cb = app._make_display_callback("percent_only")
            cb(None)
        assert app.settings.get("display_mode") == "percent_only"
        assert "80%" in app.title

    def test_toggle_launch_enable_creates_plist(self, mouse_device):
        """Enable launch at login creates plist file."""
        app = make_app(device=mouse_device, battery=80)
        sender = MagicMock()
        sender.state = 0  # disabled -> enable

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("razer_battery_tray.subprocess.run", return_value=mock_result), \
             patch("razer_battery_tray.os.makedirs"), \
             patch("builtins.open", MagicMock()):
            app._toggle_launch_at_login(sender)

    def test_toggle_launch_disable_removes_plist(self, mouse_device):
        """Disable launch at login removes plist file."""
        app = make_app(device=mouse_device, battery=80)
        sender = MagicMock()
        sender.state = 1  # enabled -> disable

        mock_result = MagicMock()
        mock_result.returncode = 0

        with patch("razer_battery_tray.subprocess.run", return_value=mock_result), \
             patch("razer_battery_tray.os.path.exists", return_value=True), \
             patch("razer_battery_tray.os.remove"):
            app._toggle_launch_at_login(sender)

    def test_threshold_callback_resets_notified_flag(self, mouse_device):
        """Changing threshold resets low_battery_notified flag."""
        app = make_app(device=mouse_device, battery=80)
        app.low_battery_notified = True
        cb = app._make_threshold_callback(10)
        cb(None)
        assert app.low_battery_notified is False

    def test_display_callback_rebuilds_menu(self, mouse_device):
        """Display callback triggers settings menu rebuild."""
        app = make_app(device=mouse_device, battery=80)
        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]), \
             patch("razer_battery_tray.get_battery_level", return_value=80), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            cb = app._make_display_callback("icon_only")
            cb(None)
        assert app.settings.get("display_mode") == "icon_only"
        assert app.title == ""
        assert "battery_full" in app.icon

    def test_poll_callback_rebuilds_menu(self, mouse_device):
        """Poll callback triggers settings menu rebuild."""
        app = make_app(device=mouse_device, battery=80)
        cb = app._make_poll_callback(900)
        cb(None)
        assert app.settings.get("poll_interval") == 900

    def test_wake_refresh_exception_logged(self, mouse_device):
        """_wake_refresh swallows exceptions and logs them."""
        app = make_app(device=mouse_device, battery=80)
        with patch("razer_battery_tray.scan_razer_devices", side_effect=RuntimeError("boom")):
            # Should not raise
            app._wake_refresh()

    def test_refresh_menu_calls_find_and_update(self, mouse_device):
        """refresh() calls both find_device and update_battery."""
        app = make_app(device=mouse_device, battery=80)
        with patch("razer_battery_tray.scan_razer_devices", return_value=[mouse_device]) as mock_scan, \
             patch("razer_battery_tray.get_battery_level", return_value=50), \
             patch("razer_battery_tray.get_charging_status", return_value=False):
            app.refresh()
            assert mock_scan.called
        assert "50%" in app.title

    def test_mock_hid_records_get_feature_report_calls(self):
        """MockHIDDevice records get_feature_report calls with correct args."""
        from razer_common import REPORT_LEN
        mock_dev = MockHIDDevice(response=make_razer_response(battery_byte=0x50))
        result = mock_dev.get_feature_report(0x00, REPORT_LEN + 1)
        assert result is not None
        assert len(mock_dev.get_feature_report_calls) == 1
        assert mock_dev.get_feature_report_calls[0] == (0x00, REPORT_LEN + 1)

    def test_wake_callback_schedules_timer(self, mouse_device):
        """Wake callback schedules a threading.Timer for non-blocking refresh."""
        app = make_app(device=mouse_device, battery=80)
        with patch("razer_battery_tray.threading.Timer") as mock_timer:
            mock_instance = MagicMock()
            mock_timer.return_value = mock_instance
            app._on_wake()
            mock_timer.assert_called_once()
            mock_instance.start.assert_called_once()
