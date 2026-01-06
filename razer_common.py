#!/usr/bin/env python3

import time
import hid

RAZER_VID = 0x1532

RAZER_DEVICES = {
    0x0013: "Razer Orochi 2011",
    0x0015: "Razer Naga",
    0x0016: "Razer DeathAdder 3.5G",
    0x001F: "Razer Naga Epic",
    0x0020: "Razer Abyssus 1800",
    0x0024: "Razer Mamba 2012 (Wired)",
    0x0025: "Razer Mamba 2012 (Wireless)",
    0x0029: "Razer DeathAdder 3.5G Black",
    0x002E: "Razer Naga 2012",
    0x002F: "Razer Imperator 2012",
    0x0032: "Razer Ouroboros",
    0x0034: "Razer Taipan",
    0x0036: "Razer Naga Hex (Red)",
    0x0037: "Razer DeathAdder 2013",
    0x0038: "Razer DeathAdder 1800",
    0x0039: "Razer Orochi 2013",
    0x003E: "Razer Naga Epic Chroma (Wired)",
    0x003F: "Razer Naga Epic Chroma (Wireless)",
    0x0040: "Razer Naga 2014",
    0x0041: "Razer Naga Hex",
    0x0042: "Razer Abyssus",
    0x0043: "Razer DeathAdder Chroma",
    0x0044: "Razer Mamba Chroma (Wired)",
    0x0045: "Razer Mamba Chroma (Wireless)",
    0x0046: "Razer Mamba Tournament Edition",
    0x0048: "Razer Orochi (Wired)",
    0x004C: "Razer Diamondback Chroma",
    0x004F: "Razer DeathAdder 2000",
    0x0050: "Razer Naga Hex V2",
    0x0053: "Razer Naga Chroma",
    0x0054: "Razer DeathAdder 3500",
    0x0059: "Razer Lancehead (Wired)",
    0x005A: "Razer Lancehead (Wireless)",
    0x005B: "Razer Abyssus V2",
    0x005C: "Razer DeathAdder Elite",
    0x005E: "Razer Abyssus 2000",
    0x0060: "Razer Lancehead Tournament Edition",
    0x0062: "Razer Atheris (Receiver)",
    0x0064: "Razer Basilisk",
    0x0065: "Razer Basilisk Essential",
    0x0067: "Razer Naga Trinity",
    0x0068: "Razer Firefly Hyperflux (2018)",
    0x006A: "Razer Abyssus Elite (D.Va Edition)",
    0x006B: "Razer Abyssus Essential",
    0x006C: "Razer Mamba Elite",
    0x006E: "Razer DeathAdder Essential",
    0x006F: "Razer Lancehead Wireless (Receiver)",
    0x0070: "Razer Lancehead Wireless (Wired)",
    0x0071: "Razer DeathAdder Essential (White Edition)",
    0x0072: "Razer Mamba Wireless (Receiver)",
    0x0073: "Razer Mamba Wireless (Wired)",
    0x0077: "Razer Pro Click (Receiver)",
    0x0078: "Razer Viper",
    0x007A: "Razer Viper Ultimate (Wired)",
    0x007B: "Razer Viper Ultimate (Wireless)",
    0x007C: "Razer DeathAdder V2 Pro (Wired)",
    0x007D: "Razer DeathAdder V2 Pro (Wireless)",
    0x007E: "Razer Mouse Dock",
    0x0080: "Razer Pro Click (Wired)",
    0x0083: "Razer Basilisk X HyperSpeed",
    0x0084: "Razer DeathAdder V2",
    0x0085: "Razer Basilisk V2",
    0x0086: "Razer Basilisk Ultimate",
    0x0088: "Razer Basilisk Ultimate (Receiver)",
    0x008A: "Razer Viper Mini",
    0x008C: "Razer DeathAdder V2 Mini",
    0x008D: "Razer Naga Left Handed Edition 2020",
    0x008F: "Razer Naga Pro (Wired)",
    0x0090: "Razer Naga Pro (Wireless)",
    0x0091: "Razer Viper 8KHz",
    0x0094: "Razer Orochi V2 (Receiver)",
    0x0095: "Razer Orochi V2 (Bluetooth)",
    0x0096: "Razer Naga X",
    0x0098: "Razer DeathAdder Essential (2021)",
    0x0099: "Razer Basilisk V3",
    0x009A: "Razer Pro Click Mini (Receiver)",
    0x009C: "Razer DeathAdder V2 X HyperSpeed",
    0x009E: "Razer Viper Mini SE (Wired)",
    0x009F: "Razer Viper Mini SE (Wireless)",
    0x00A1: "Razer DeathAdder V2 Lite",
    0x00A3: "Razer Cobra",
    0x00A5: "Razer Viper V2 Pro (Wired)",
    0x00A6: "Razer Viper V2 Pro (Wireless)",
    0x00A7: "Razer Naga V2 Pro (Wired)",
    0x00A8: "Razer Naga V2 Pro (Wireless)",
    0x00AA: "Razer Basilisk V3 Pro (Wired)",
    0x00AB: "Razer Basilisk V3 Pro (Wireless)",
    0x00AF: "Razer Cobra Pro (Wired)",
    0x00B0: "Razer Cobra Pro (Wireless)",
    0x00B2: "Razer DeathAdder V3",
    0x00B3: "Razer HyperPolling Wireless Dongle",
    0x00B4: "Razer Naga V2 HyperSpeed (Receiver)",
    0x00B6: "Razer DeathAdder V3 Pro (Wired)",
    0x00B7: "Razer DeathAdder V3 Pro (Wireless)",
    0x00B8: "Razer Viper V3 HyperSpeed",
    0x00B9: "Razer Basilisk V3 X HyperSpeed",
    0x00C0: "Razer Viper V3 Pro (Wired)",
    0x00C1: "Razer Viper V3 Pro (Wireless)",
    0x00C2: "Razer DeathAdder V3 Pro (Wired)",
    0x00C3: "Razer DeathAdder V3 Pro (Wireless)",
    0x00C4: "Razer DeathAdder V3 HyperSpeed (Wired)",
    0x00C5: "Razer DeathAdder V3 HyperSpeed (Wireless)",
    0x00C7: "Razer Pro Click V2 Vertical Edition (Wired)",
    0x00C8: "Razer Pro Click V2 Vertical Edition (Wireless)",
    0x00CB: "Razer Basilisk V3 35K",
    0x00CC: "Razer Basilisk V3 Pro 35K (Wired)",
    0x00CD: "Razer Basilisk V3 Pro 35K (Wireless)",
    0x00D0: "Razer Pro Click V2 (Wired)",
    0x00D1: "Razer Pro Click V2 (Wireless)",
    0x00D6: "Razer Basilisk V3 Pro 35K Phantom Green Edition (Wired)",
    0x00D7: "Razer Basilisk V3 Pro 35K Phantom Green Edition (Wireless)",
    0x010D: "Razer BlackWidow Ultimate 2012",
    0x010E: "Razer BlackWidow Stealth Edition",
    0x010F: "Razer Anansi",
    0x0111: "Razer Nostromo",
    0x0113: "Razer Orbweaver",
    0x0118: "Razer DeathStalker/DeathStalker Essential",
    0x011A: "Razer BlackWidow Ultimate 2013",
    0x011B: "Razer BlackWidow (Classic)",
    0x011C: "Razer BlackWidow Tournament Edition 2014",
    0x0201: "Razer Tartarus",
    0x0202: "Razer DeathStalker Expert",
    0x0203: "Razer BlackWidow Chroma",
    0x0204: "Razer DeathStalker Chroma",
    0x0205: "Razer Blade Stealth",
    0x0207: "Razer Orbweaver Chroma",
    0x0208: "Razer Tartarus Chroma",
    0x0209: "Razer BlackWidow Tournament Edition Chroma",
    0x020F: "Razer Blade (QHD)",
    0x0210: "Razer Blade Pro (Late 2016)",
    0x0211: "Razer BlackWidow Chroma (Overwatch)",
    0x0214: "Razer BlackWidow Ultimate 2016",
    0x0215: "Razer Core",
    0x0216: "Razer BlackWidow X Chroma",
    0x0217: "Razer BlackWidow X Ultimate",
    0x021A: "Razer BlackWidow X Tournament Edition Chroma",
    0x021E: "Razer Ornata Chroma",
    0x021F: "Razer Ornata",
    0x0220: "Razer Blade Stealth (Late 2016)",
    0x0221: "Razer BlackWidow Chroma V2",
    0x0224: "Razer Blade (Late 2016)",
    0x0225: "Razer Blade Pro (2017)",
    0x0226: "Razer Huntsman Elite",
    0x0227: "Razer Huntsman",
    0x0228: "Razer BlackWidow Elite",
    0x022A: "Razer Cynosa Chroma",
    0x022B: "Razer Tartarus V2",
    0x022C: "Razer Cynosa Chroma Pro",
    0x022D: "Razer Blade Stealth (Mid 2017)",
    0x022F: "Razer Blade Pro FullHD (2017)",
    0x0232: "Razer Blade Stealth (Late 2017)",
    0x0233: "Razer Blade 15 (2018)",
    0x0234: "Razer Blade Pro 17 (2019)",
    0x0235: "Razer BlackWidow Lite",
    0x0237: "Razer BlackWidow Essential",
    0x0239: "Razer Blade Stealth (2019)",
    0x023A: "Razer Blade 15 (2019) Advanced",
    0x023B: "Razer Blade 15 (2018) Base Model",
    0x023F: "Razer Cynosa Lite",
    0x0240: "Razer Blade 15 (2018) Mercury",
    0x0241: "Razer BlackWidow 2019",
    0x0243: "Razer Huntsman Tournament Edition",
    0x0245: "Razer Blade 15 (Mid 2019) Mercury",
    0x0246: "Razer Blade 15 (Mid 2019) Base Model",
    0x024A: "Razer Blade Stealth (Late 2019)",
    0x024B: "Razer Blade Advanced (Late 2019)",
    0x024C: "Razer Blade Pro (Late 2019)",
    0x024D: "Razer Blade 15 Studio Edition (2019)",
    0x024E: "Razer BlackWidow V3",
    0x0252: "Razer Blade Stealth (Early 2020)",
    0x0253: "Razer Blade 15 Advanced (2020)",
    0x0255: "Razer Blade Base (Early 2020)",
    0x0256: "Razer Blade Pro (Early 2020)",
    0x0257: "Razer Huntsman Mini",
    0x0258: "Razer BlackWidow V3 Mini HyperSpeed (Wired)",
    0x0259: "Razer Blade Stealth (Late 2020)",
    0x025A: "Razer BlackWidow V3 Pro Wired",
    0x025C: "Razer BlackWidow V3 Pro 2.4 Ghz Wireless",
    0x025D: "Razer Ornata V2",
    0x025E: "Razer Cynosa V2",
    0x0266: "Razer Huntsman V2 Analog",
    0x0268: "Razer Blade Late 2020 Base",
    0x0269: "Razer Huntsman Mini JP",
    0x026A: "Razer Book (2020)",
    0x026B: "Razer Huntsman V2 Tenkeyless",
    0x026C: "Razer Huntsman V2",
    0x026D: "Razer Blade 15 Advanced (Early 2021)",
    0x026E: "Razer Blade 17 Pro (Early 2021)",
    0x026F: "Razer Blade Base (Early 2021)",
    0x0270: "Razer Blade 14 (2021)",
    0x0271: "Razer BlackWidow V3 Mini HyperSpeed (Wireless)",
    0x0276: "Razer Blade 15 Advanced (Mid 2021)",
    0x0279: "Razer Blade 17 Pro (Mid 2021)",
    0x027A: "Razer Blade Base (Early 2022)",
    0x0282: "Razer Huntsman Mini Analog",
    0x0287: "Razer BlackWidow V4",
    0x028A: "Razer Blade 15 Advanced (Early 2022)",
    0x028B: "Razer Blade 17 (2022)",
    0x028C: "Razer Blade 14 (2022)",
    0x028D: "Razer BlackWidow V4 Pro",
    0x028F: "Razer Ornata V3 (Alternate)",
    0x0290: "Razer DeathStalker V2 Pro (Wireless)",
    0x0292: "Razer DeathStalker V2 Pro (Wired)",
    0x0293: "Razer BlackWidow V4 X",
    0x0294: "Razer Ornata V3 X",
    0x0295: "Razer DeathStalker V2",
    0x0296: "Razer DeathStalker V2 Pro TKL (Wireless)",
    0x0298: "Razer DeathStalker V2 Pro TKL (Wired)",
    0x029D: "Razer Blade 14 (2023)",
    0x029E: "Razer Blade 15 (2023)",
    0x029F: "Razer Blade 16 (2023)",
    0x02A0: "Razer Blade 18 (2023)",
    0x02A1: "Razer Ornata V3",
    0x02A2: "Razer Ornata V3 X (Alternate)",
    0x02A3: "Razer Ornata V3 Tenkeyless",
    0x02A5: "Razer BlackWidow V4 75%",
    0x02A6: "Razer Huntsman V3 Pro",
    0x02A7: "Razer Huntsman V3 Pro TKL",
    0x02B6: "Razer Blade 14 (2024)",
    0x02B8: "Razer Blade 18 (2024)",
    0x02B9: "Razer BlackWidow V4 Mini HyperSpeed (Wired)",
    0x02BA: "Razer BlackWidow V4 Mini HyperSpeed (Wireless)",
    0x0501: "Razer Kraken 7.1",
    0x0504: "Razer Kraken 7.1 Chroma",
    0x0506: "Razer Kraken 7.1 (Alternate)",
    0x0510: "Razer Kraken 7.1 V2",
    0x0517: "Razer Nommo Chroma (Speakers)",
    0x0518: "Razer Nommo Pro (Speakers)",
    0x0527: "Razer Kraken Ultimate",
    0x0560: "Razer Kraken Kitty V2",
    0x0A24: "Razer BlackWidow V3 TK",
    0x0C00: "Razer Firefly (2013)",
    0x0C01: "Razer Goliathus (2018)",
    0x0C02: "Razer Goliathus Extended (2018)",
    0x0C04: "Razer Firefly V2",
    0x0C05: "Razer Strider Chroma",
    0x0C06: "Razer Goliathus Chroma 3XL",
    0x0C08: "Razer Firefly V2 Pro",
    0x0F07: "Razer Chroma Mug Holder",
    0x0F08: "Razer Base Station Chroma (Headphone Stand)",
    0x0F09: "Razer Chroma Hardware Development Kit (HDK)",
    0x0F0D: "Razer Laptop Stand Chroma",
    0x0F12: "Razer Raptor 27",
    0x0F17: "Razer Tomahawk ATX",
    0x0F19: "Razer Kraken Kitty Edition",
    0x0F1A: "Razer Core X Chroma",
    0x0F1D: "Razer Mouse Bungee V3 Chroma",
    0x0F1F: "Razer Chroma Addressable RGB Controller",
    0x0F20: "Razer Base Station V2 Chroma",
    0x0F21: "Razer Thunderbolt 4 Dock Chroma",
    0x0F26: "Razer Charging Pad Chroma",
    0x0F2B: "Razer Laptop Stand Chroma V2",
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