#!/usr/bin/env python3

import time
import hid

RAZER_VID = 0x1532

RAZER_DEVICES = {
    0x00B9: "Razer Basilisk V3 X HyperSpeed",
    0x025A: "Razer BlackWidow V3 Pro Wired",
    0x025C: "Razer BlackWidow V3 Pro Wireless",
    0x0A00: "Razer DeathAdder Chroma",
    0x0A01: "Razer Mamba Chroma",
    0x0A02: "Razer Cynosa Chroma",
    0x0A03: "Razer Tartarus Chroma",
}

REPORT_LEN = 90
VARSTORE = 0x01

MOUSE_EFFECT_STATIC = 0x01
MOUSE_EFFECT_BREATHING = 0x02
MOUSE_EFFECT_WAVE = 0x03
MOUSE_EFFECT_REACTIVE = 0x04
KBD_EFFECT_STATIC = 0x01
KBD_EFFECT_BREATHING = 0x02
KBD_EFFECT_WAVE = 0x03
KBD_EFFECT_REACTIVE = 0x04

MOUSE_TARGET_PID = 0x00B9
MOUSE_SCROLL_WHEEL_LED = 0x01
MOUSE_CMD_CLASS = 0x0F
MOUSE_CMD_ID = 0x02
MOUSE_DATA_SIZE = 9
MOUSE_TRANSACTION_ID = 0x1F

MOUSE_DEATHADDER_CHROMA_PID = 0x0A00
MOUSE_MAMBA_CHROMA_PID = 0x0A01

BW3PRO_WIRED_PID = 0x025A
BW3PRO_WIRELESS_PID = 0x025C
KBD_BACKLIGHT_LED = 0x05
KBD_CMD_CLASS = 0x0F
KBD_CMD_ID = 0x02
KBD_DATA_SIZE = 9
KBD_WIRED_TRANSACTION_ID = 0x3F
KBD_WIRELESS_TRANSACTION_ID = 0x9F

KBD_CYNOSA_CHROMA_PID = 0x0A02
KBD_TARTARUS_CHROMA_PID = 0x0A03

def calculate_crc(report_data: bytes) -> int:
    crc = 0
    for i in range(2, 88):
        if i < len(report_data):
            crc ^= report_data[i]
    return crc

def construct_razer_report(transaction_id: int, command_class: int, command_id: int,
                           data_size: int, arguments: list) -> bytes:
    if len(arguments) > 80:
        raise ValueError("Arguments list too long (max 80 bytes)")
    report = bytearray(REPORT_LEN)
    report[0] = 0x00
    report[1] = transaction_id & 0xFF
    report[2] = 0x00
    report[3] = 0x00
    report[4] = 0x00
    report[5] = data_size & 0xFF
    report[6] = command_class & 0xFF
    report[7] = command_id & 0xFF
    arg_len = min(len(arguments), 80)
    report[8:8 + arg_len] = bytes(arguments)
    report[88] = calculate_crc(report)
    report[89] = 0x00
    return bytes(report)

def scan_razer_devices() -> list:
    devices_grouped = {}
    try:
        all_devices = hid.enumerate(RAZER_VID, 0x0)
        if not all_devices:
            return []
        parameterized_pids = set(RAZER_DEVICES.keys())
        enumerated = [d for d in all_devices if d['product_id'] in parameterized_pids]
        if not enumerated:
            return []
        for dev in enumerated:
            pid = dev['product_id']
            name = RAZER_DEVICES.get(pid, f"Unknown (PID: 0x{pid:04X})")
            interface_num = dev.get('interface_number', -1)
            path = dev['path']
            serial = dev.get('serial_number', 'N/A')
            prod_str = dev.get('product_string', 'N/A')
            key = (serial, prod_str, pid)
            if key not in devices_grouped:
                devices_grouped[key] = {
                    'name': name,
                    'pid': pid,
                    'interfaces': []
                }
            devices_grouped[key]['interfaces'].append({
                'path': path,
                'interface_number': interface_num
            })
    except Exception as e:
        print("Error scanning devices:", e)
        return []
    return list(devices_grouped.values())

def build_arguments(effect_code: int, led_id: int, extra_params: list) -> list:
    return [VARSTORE, led_id, effect_code, 0x00, 0x00, 0x01] + extra_params

def send_report_to_device(selected_device: dict, report: bytes, command_desc: str) -> bool:
    report_with_id = b'\x00' + report
    success = False
    for iface in selected_device.get('interfaces', []):
        path = iface['path']
        try:
            dev = hid.device()
            dev.open_path(path)
            time.sleep(0.05)
            bytes_written = dev.send_feature_report(report_with_id)
            if bytes_written == len(report_with_id):
                success = True
            dev.close()
        except Exception as e:
            print(f"Error on interface {path}: {e}")
    return success

def is_mouse_device(pid: int) -> bool:
    return pid in [MOUSE_TARGET_PID, MOUSE_DEATHADDER_CHROMA_PID, MOUSE_MAMBA_CHROMA_PID]

def is_keyboard_device(pid: int) -> bool:
    return pid in [BW3PRO_WIRED_PID, BW3PRO_WIRELESS_PID, KBD_CYNOSA_CHROMA_PID, KBD_TARTARUS_CHROMA_PID]