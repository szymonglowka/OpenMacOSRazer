#!/usr/bin/env python3

import time
import logging
import hid

logger = logging.getLogger("razer_common")

# Razer response status codes (byte index 0 in the 90-byte report, index 1 with report ID prefix)
RAZER_STATUS_NEW = 0x00
RAZER_STATUS_BUSY = 0x01
RAZER_STATUS_SUCCESS = 0x02
RAZER_STATUS_FAILURE = 0x03
RAZER_STATUS_TIMEOUT = 0x04
RAZER_STATUS_NOT_SUPPORTED = 0x05

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
    0x00BE: "Razer DeathAdder V4 Pro (Wired)",
    0x00BF: "Razer DeathAdder V4 Pro (Wireless)",
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
    0x0244: "Razer Tartarus Pro",
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
    0x02C5: "Razer Blade 14 (2025)",
    0x02C6: "Razer Blade 16 (2025)",
    0x02C7: "Razer Blade 18 (2025)",
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
    0x0A00: "Razer DeathAdder Chroma",
    0x0A01: "Razer Mamba Chroma",
    0x0A02: "Razer Cynosa Chroma",
    0x0A03: "Razer Tartarus Chroma",
    0x0F2B: "Razer Laptop Stand Chroma V2",
}

RAZER_DEVICE_TYPES = {
    0x010D: 'keyboard',
    0x010E: 'keyboard',
    0x010F: 'keyboard',
    0x0111: 'keyboard',
    0x0113: 'keyboard',
    0x0118: 'keyboard',
    0x011A: 'keyboard',
    0x011B: 'keyboard',
    0x011C: 'keyboard',
    0x0201: 'keyboard',
    0x0202: 'keyboard',
    0x0203: 'keyboard',
    0x0204: 'keyboard',
    0x0205: 'keyboard',
    0x0207: 'keyboard',
    0x0208: 'keyboard',
    0x0209: 'keyboard',
    0x020F: 'keyboard',
    0x0210: 'keyboard',
    0x0211: 'keyboard',
    0x0214: 'keyboard',
    0x0216: 'keyboard',
    0x0217: 'keyboard',
    0x021A: 'keyboard',
    0x021E: 'keyboard',
    0x021F: 'keyboard',
    0x0220: 'keyboard',
    0x0221: 'keyboard',
    0x0224: 'keyboard',
    0x0225: 'keyboard',
    0x0226: 'keyboard',
    0x0227: 'keyboard',
    0x0228: 'keyboard',
    0x022A: 'keyboard',
    0x022B: 'keyboard',
    0x022C: 'keyboard',
    0x022D: 'keyboard',
    0x022F: 'keyboard',
    0x0232: 'keyboard',
    0x0233: 'keyboard',
    0x0234: 'keyboard',
    0x0235: 'keyboard',
    0x0237: 'keyboard',
    0x0239: 'keyboard',
    0x023A: 'keyboard',
    0x023B: 'keyboard',
    0x023F: 'keyboard',
    0x0240: 'keyboard',
    0x0241: 'keyboard',
    0x0243: 'keyboard',
    0x0244: 'keyboard',
    0x0245: 'keyboard',
    0x0246: 'keyboard',
    0x024A: 'keyboard',
    0x024B: 'keyboard',
    0x024C: 'keyboard',
    0x024D: 'keyboard',
    0x024E: 'keyboard',
    0x0252: 'keyboard',
    0x0253: 'keyboard',
    0x0255: 'keyboard',
    0x0256: 'keyboard',
    0x0257: 'keyboard',
    0x0258: 'keyboard',
    0x0259: 'keyboard',
    0x025A: 'keyboard',
    0x025C: 'keyboard',
    0x025D: 'keyboard',
    0x025E: 'keyboard',
    0x0266: 'keyboard',
    0x0268: 'keyboard',
    0x0269: 'keyboard',
    0x026A: 'keyboard',
    0x026B: 'keyboard',
    0x026C: 'keyboard',
    0x026D: 'keyboard',
    0x026E: 'keyboard',
    0x026F: 'keyboard',
    0x0270: 'keyboard',
    0x0271: 'keyboard',
    0x0276: 'keyboard',
    0x0279: 'keyboard',
    0x027A: 'keyboard',
    0x0282: 'keyboard',
    0x0287: 'keyboard',
    0x028A: 'keyboard',
    0x028B: 'keyboard',
    0x028C: 'keyboard',
    0x028D: 'keyboard',
    0x028F: 'keyboard',
    0x0290: 'keyboard',
    0x0292: 'keyboard',
    0x0293: 'keyboard',
    0x0294: 'keyboard',
    0x0295: 'keyboard',
    0x0296: 'keyboard',
    0x0298: 'keyboard',
    0x029D: 'keyboard',
    0x029E: 'keyboard',
    0x029F: 'keyboard',
    0x02A0: 'keyboard',
    0x02A1: 'keyboard',
    0x02A2: 'keyboard',
    0x02A3: 'keyboard',
    0x02A5: 'keyboard',
    0x02A6: 'keyboard',
    0x02A7: 'keyboard',
    0x02B6: 'keyboard',
    0x02B8: 'keyboard',
    0x02B9: 'keyboard',
    0x02BA: 'keyboard',
    0x02C5: 'keyboard',
    0x02C6: 'keyboard',
    0x02C7: 'keyboard',
    0x0A24: 'keyboard',
    0x0A00: 'mouse',
    0x0A01: 'mouse',
    0x0A02: 'keyboard',
    0x0A03: 'keyboard',
    0x0013: 'mouse',
    0x0015: 'mouse',
    0x0016: 'mouse',
    0x001F: 'mouse',
    0x0020: 'mouse',
    0x0024: 'mouse',
    0x0025: 'mouse',
    0x0029: 'mouse',
    0x002E: 'mouse',
    0x002F: 'mouse',
    0x0032: 'mouse',
    0x0034: 'mouse',
    0x0036: 'mouse',
    0x0037: 'mouse',
    0x0038: 'mouse',
    0x0039: 'mouse',
    0x003E: 'mouse',
    0x003F: 'mouse',
    0x0040: 'mouse',
    0x0041: 'mouse',
    0x0042: 'mouse',
    0x0043: 'mouse',
    0x0044: 'mouse',
    0x0045: 'mouse',
    0x0046: 'mouse',
    0x0048: 'mouse',
    0x004C: 'mouse',
    0x004F: 'mouse',
    0x0050: 'mouse',
    0x0053: 'mouse',
    0x0054: 'mouse',
    0x0059: 'mouse',
    0x005A: 'mouse',
    0x005B: 'mouse',
    0x005C: 'mouse',
    0x005E: 'mouse',
    0x0060: 'mouse',
    0x0062: 'mouse',
    0x0064: 'mouse',
    0x0065: 'mouse',
    0x0067: 'mouse',
    0x006A: 'mouse',
    0x006B: 'mouse',
    0x006C: 'mouse',
    0x006E: 'mouse',
    0x006F: 'mouse',
    0x0070: 'mouse',
    0x0071: 'mouse',
    0x0072: 'mouse',
    0x0073: 'mouse',
    0x0077: 'mouse',
    0x0078: 'mouse',
    0x007A: 'mouse',
    0x007B: 'mouse',
    0x007C: 'mouse',
    0x007D: 'mouse',
    0x0080: 'mouse',
    0x0083: 'mouse',
    0x0084: 'mouse',
    0x0085: 'mouse',
    0x0086: 'mouse',
    0x0088: 'mouse',
    0x008A: 'mouse',
    0x008C: 'mouse',
    0x008D: 'mouse',
    0x008F: 'mouse',
    0x0090: 'mouse',
    0x0091: 'mouse',
    0x0094: 'mouse',
    0x0095: 'mouse',
    0x0096: 'mouse',
    0x0098: 'mouse',
    0x0099: 'mouse',
    0x009A: 'mouse',
    0x009C: 'mouse',
    0x009E: 'mouse',
    0x009F: 'mouse',
    0x00A1: 'mouse',
    0x00A3: 'mouse',
    0x00A5: 'mouse',
    0x00A6: 'mouse',
    0x00A7: 'mouse',
    0x00A8: 'mouse',
    0x00AA: 'mouse',
    0x00AB: 'mouse',
    0x00AF: 'mouse',
    0x00B0: 'mouse',
    0x00B2: 'mouse',
    0x00B3: 'dongle',
    0x00B4: 'mouse',
    0x00B6: 'mouse',
    0x00B7: 'mouse',
    0x00B8: 'mouse',
    0x00B9: 'mouse',
    0x00BE: 'mouse',
    0x00BF: 'mouse',
    0x00C0: 'mouse',
    0x00C1: 'mouse',
    0x00C2: 'mouse',
    0x00C3: 'mouse',
    0x00C4: 'mouse',
    0x00C5: 'mouse',
    0x00C7: 'mouse',
    0x00C8: 'mouse',
    0x00CB: 'mouse',
    0x00CC: 'mouse',
    0x00CD: 'mouse',
    0x00D0: 'mouse',
    0x00D1: 'mouse',
    0x00D6: 'mouse',
    0x00D7: 'mouse',
    # Mousepads
    0x0068: 'mousepad',
    0x0C00: 'mousepad',
    0x0C01: 'mousepad',
    0x0C02: 'mousepad',
    0x0C04: 'mousepad',
    0x0C05: 'mousepad',
    0x0C06: 'mousepad',
    0x0C08: 'mousepad',
    # Headsets
    0x0501: 'headset',
    0x0504: 'headset',
    0x0506: 'headset',
    0x0510: 'headset',
    0x0527: 'headset',
    0x0560: 'headset',
    0x0F19: 'headset',
    # Speakers
    0x0517: 'speaker',
    0x0518: 'speaker',
    # Accessories
    0x007E: 'accessory',
    0x0215: 'accessory',
    0x0F07: 'accessory',
    0x0F08: 'accessory',
    0x0F09: 'accessory',
    0x0F0D: 'accessory',
    0x0F12: 'accessory',
    0x0F17: 'accessory',
    0x0F1A: 'accessory',
    0x0F1D: 'accessory',
    0x0F1F: 'accessory',
    0x0F20: 'accessory',
    0x0F21: 'accessory',
    0x0F26: 'accessory',
    0x0F2B: 'accessory',
}

RAZER_TRANSACTION_IDS = {
    0x0013: 0xFF,
    0x0015: 0x3F,
    0x0016: 0x3F,
    0x001F: 0x3F,
    0x0020: 0x3F,
    0x0024: 0x3F,
    0x0025: 0x3F,
    0x0029: 0x3F,
    0x002E: 0x3F,
    0x002F: 0x3F,
    0x0032: 0x3F,
    0x0034: 0x3F,
    0x0036: 0x3F,
    0x0037: 0x3F,
    0x0038: 0x3F,
    0x0039: 0x3F,
    0x003E: 0x3F,
    0x003F: 0x3F,
    0x0040: 0xFF,
    0x0041: 0x3F,
    0x0042: 0x3F,
    0x0043: 0x3F,
    0x0044: 0x3F,
    0x0045: 0x3F,
    0x0046: 0x3F,
    0x0048: 0x3F,
    0x004C: 0x3F,
    0x004F: 0x3F,
    0x0050: 0x3F,
    0x0053: 0x3F,
    0x0054: 0x3F,
    0x0059: 0x3F,
    0x005A: 0x3F,
    0x005B: 0x3F,
    0x005C: 0x3F,
    0x005E: 0x3F,
    0x0060: 0x3F,
    0x0062: 0x1F,
    0x0064: 0x3F,
    0x0065: 0x3F,
    0x0067: 0x1F,
    0x006A: 0x3F,
    0x006B: 0x3F,
    0x006C: 0x1F,
    0x006E: 0x3F,
    0x006F: 0x1F,
    0x0070: 0x1F,
    0x0071: 0x3F,
    0x0072: 0x3F,
    0x0073: 0x3F,
    0x0077: 0x1F,
    0x0078: 0x3F,
    0x007A: 0x3F,
    0x007B: 0x3F,
    0x007C: 0x3F,
    0x007D: 0x3F,
    0x0080: 0x1F,
    0x0083: 0xFF,
    0x0084: 0x3F,
    0x0085: 0x1F,
    0x0086: 0x1F,
    0x0088: 0x1F,
    0x008A: 0x3F,
    0x008C: 0x3F,
    0x008D: 0x1F,
    0x008F: 0x1F,
    0x0090: 0x1F,
    0x0091: 0x1F,
    0x0094: 0x1F,
    0x0095: 0x1F,
    0x0096: 0x1F,
    0x0098: 0x3F,
    0x0099: 0x1F,
    0x009A: 0x1F,
    0x009C: 0x1F,
    0x009E: 0x1F,
    0x009F: 0x1F,
    0x00A1: 0x1F,
    0x00A3: 0x1F,
    0x00A5: 0x1F,
    0x00A6: 0x1F,
    0x00A7: 0x1F,
    0x00A8: 0x1F,
    0x00AA: 0x1F,
    0x00AB: 0x1F,
    0x00AF: 0x1F,
    0x00B0: 0x1F,
    0x00B2: 0x1F,
    0x00B3: 0x1F,
    0x00B4: 0x1F,
    0x00B6: 0x1F,
    0x00B7: 0x1F,
    0x00B8: 0x1F,
    0x00B9: 0x1F,
    0x00BE: 0x1F,
    0x00BF: 0x1F,
    0x00C0: 0x1F,
    0x00C1: 0x1F,
    0x00C2: 0x1F,
    0x00C3: 0x1F,
    0x00C4: 0x1F,
    0x00C5: 0x1F,
    0x00C7: 0x1F,
    0x00C8: 0x1F,
    0x00CB: 0x1F,
    0x00CC: 0x1F,
    0x00CD: 0x1F,
    0x00D0: 0x1F,
    0x00D1: 0x1F,
    0x00D6: 0x1F,
    0x00D7: 0x1F,
    0x010D: 0xFF,
    0x010E: 0xFF,
    0x010F: 0xFF,
    0x0111: 0xFF,
    0x0113: 0xFF,
    0x0118: 0xFF,
    0x011A: 0xFF,
    0x011B: 0xFF,
    0x011C: 0xFF,
    0x0201: 0xFF,
    0x0202: 0xFF,
    0x0203: 0xFF,
    0x0204: 0xFF,
    0x0205: 0xFF,
    0x0207: 0x3F,
    0x0208: 0xFF,
    0x0209: 0xFF,
    0x020F: 0xFF,
    0x0210: 0xFF,
    0x0211: 0xFF,
    0x0214: 0xFF,
    0x0216: 0xFF,
    0x0217: 0xFF,
    0x021A: 0xFF,
    0x021E: 0x3F,
    0x021F: 0x3F,
    0x0220: 0xFF,
    0x0221: 0x3F,
    0x0224: 0x3F,
    0x0225: 0xFF,
    0x0226: 0x3F,
    0x0227: 0x3F,
    0x0228: 0x1F,
    0x022A: 0x3F,
    0x022B: 0x1F,
    0x022C: 0x3F,
    0x022D: 0xFF,
    0x022F: 0xFF,
    0x0232: 0xFF,
    0x0233: 0xFF,
    0x0234: 0xFF,
    0x0235: 0x3F,
    0x0237: 0x3F,
    0x0239: 0xFF,
    0x023A: 0xFF,
    0x023B: 0xFF,
    0x023F: 0x3F,
    0x0240: 0xFF,
    0x0241: 0x3F,
    0x0243: 0x3F,
    0x0244: 0x1F,
    0x0245: 0xFF,
    0x0246: 0xFF,
    0x024A: 0xFF,
    0x024B: 0xFF,
    0x024C: 0xFF,
    0x024D: 0xFF,
    0x024E: 0x1F,
    0x0252: 0xFF,
    0x0253: 0xFF,
    0x0255: 0xFF,
    0x0256: 0xFF,
    0x0257: 0x3F,
    0x0258: 0x1F,
    0x0259: 0xFF,
    0x025A: 0x1F,
    0x025C: 0x9F,
    0x025D: 0x1F,
    0x025E: 0x1F,
    0x0266: 0x1F,
    0x0268: 0xFF,
    0x0269: 0x3F,
    0x026A: 0xFF,
    0x026B: 0x1F,
    0x026C: 0x1F,
    0x026D: 0xFF,
    0x026E: 0xFF,
    0x026F: 0xFF,
    0x0270: 0xFF,
    0x0271: 0x9F,
    0x0276: 0xFF,
    0x0279: 0xFF,
    0x027A: 0x1F,
    0x0282: 0x1F,
    0x0287: 0x1F,
    0x028A: 0xFF,
    0x028B: 0xFF,
    0x028C: 0xFF,
    0x028D: 0x1F,
    0x028F: 0x1F,
    0x0290: 0x9F,
    0x0292: 0x1F,
    0x0293: 0x1F,
    0x0294: 0x1F,
    0x0295: 0x1F,
    0x0296: 0x9F,
    0x0298: 0x1F,
    0x029D: 0xFF,
    0x029E: 0xFF,
    0x029F: 0xFF,
    0x02A0: 0xFF,
    0x02A1: 0x1F,
    0x02A2: 0x1F,
    0x02A3: 0x1F,
    0x02A5: 0x1F,
    0x02A6: 0x1F,
    0x02A7: 0x1F,
    0x02B6: 0xFF,
    0x02B8: 0xFF,
    0x02B9: 0x1F,
    0x02BA: 0x9F,
    0x02C5: 0xFF,
    0x02C6: 0xFF,
    0x02C7: 0xFF,
    0x0A00: 0x1F,
    0x0A01: 0x1F,
    0x0A02: 0x3F,
    0x0A03: 0x3F,
    0x0A24: 0x1F,
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

MOUSE_SCROLL_WHEEL_LED = 0x01
MOUSE_CMD_CLASS = 0x0F
MOUSE_CMD_ID = 0x02
MOUSE_DATA_SIZE = 9

KBD_BACKLIGHT_LED = 0x05
KBD_CMD_CLASS = 0x0F
KBD_CMD_ID = 0x02
KBD_DATA_SIZE = 9

def get_device_type(pid: int) -> str:
    return RAZER_DEVICE_TYPES.get(pid, 'unknown')

def get_transaction_id(pid: int) -> int:
    return RAZER_TRANSACTION_IDS.get(pid, 0x00)

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
    try:
        arg_bytes = bytes(arguments)
    except (TypeError, ValueError) as e:
        raise ValueError(f"Arguments must be byte-like integers (0-255): {e}") from e
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
    report[8:8 + arg_len] = arg_bytes[:arg_len]
    report[88] = calculate_crc(report)
    report[89] = 0x00
    return bytes(report)

def scan_razer_devices() -> list:
    devices_grouped = {}
    try:
        all_devices = hid.enumerate(RAZER_VID, 0x0)
    except Exception as e:
        logger.error("Error enumerating HID devices: %s", e)
        return []
    if not all_devices:
        return []
    parameterized_pids = set(RAZER_DEVICES.keys())
    enumerated = [d for d in all_devices if d.get('product_id') in parameterized_pids]
    if not enumerated:
        return []
    for dev in enumerated:
        try:
            pid = dev['product_id']
            path = dev['path']
            name = RAZER_DEVICES.get(pid, f"Unknown (PID: 0x{pid:04X})")
            device_type = get_device_type(pid)
            transaction_id = get_transaction_id(pid)
            interface_num = dev.get('interface_number', -1)
            serial = dev.get('serial_number', 'N/A')
            prod_str = dev.get('product_string', 'N/A')
            key = (serial, prod_str, pid)
            if key not in devices_grouped:
                devices_grouped[key] = {
                    'name': name,
                    'pid': pid,
                    'type': device_type,
                    'transaction_id': transaction_id,
                    'interfaces': []
                }
            # Deduplicate: only add each unique path once (HID enumerate
            # returns multiple entries per path for different usage pages)
            existing_paths = {i['path'] for i in devices_grouped[key]['interfaces']}
            if path not in existing_paths:
                devices_grouped[key]['interfaces'].append({
                    'path': path,
                    'interface_number': interface_num
                })
        except (KeyError, TypeError) as e:
            logger.warning("Skipping malformed HID entry: %s", e)
            continue
    return list(devices_grouped.values())

def build_arguments(effect_code: int, led_id: int, extra_params: list) -> list:
    return [VARSTORE, led_id, effect_code, 0x00, 0x00, 0x01] + extra_params

def send_report_to_device(selected_device: dict, report: bytes, command_desc: str) -> bool:

    report_with_id = b'\x00' + report
    success = False
    for iface in selected_device.get('interfaces', []):
        path = iface['path']
        dev = None
        try:
            dev = hid.device()
            dev.open_path(path)
            time.sleep(0.05)
            bytes_written = dev.send_feature_report(report_with_id)
            if bytes_written == len(report_with_id):
                success = True
            else:
                logger.warning("[%s] Partial write on %s: %d/%d bytes",
                               command_desc, path, bytes_written, len(report_with_id))
        except (OSError, IOError) as e:
            logger.warning("[%s] I/O error on interface %s: %s", command_desc, path, e)
        except Exception as e:
            logger.error("[%s] Unexpected error on interface %s: %s", command_desc, path, e)
        finally:
            if dev is not None:
                try:
                    dev.close()
                except Exception:
                    pass
    return success

def validate_response(response, command_desc: str = "") -> bool:
    """Validate a Razer HID response: check status byte and CRC.
    Returns True if response is usable, False otherwise.
    Logs warnings for issues but only returns False for hard failures.
    """
    if not response or len(response) <= 9:
        logger.warning("[%s] Response too short: %d bytes", command_desc, len(response) if response else 0)
        return False

    # Status byte is at index 1 (after report ID prefix byte at index 0)
    status = response[1] if len(response) > 1 else 0xFF
    status_names = {
        RAZER_STATUS_NEW: "new/pending",
        RAZER_STATUS_BUSY: "busy",
        RAZER_STATUS_SUCCESS: "success",
        RAZER_STATUS_FAILURE: "failure",
        RAZER_STATUS_TIMEOUT: "timeout",
        RAZER_STATUS_NOT_SUPPORTED: "not supported",
    }

    if status == RAZER_STATUS_SUCCESS:
        pass  # expected
    elif status == RAZER_STATUS_BUSY:
        logger.warning("[%s] Device busy (status 0x%02X)", command_desc, status)
        return False
    elif status in (RAZER_STATUS_FAILURE, RAZER_STATUS_TIMEOUT, RAZER_STATUS_NOT_SUPPORTED):
        logger.warning("[%s] Device returned %s (status 0x%02X)", command_desc,
                       status_names.get(status, "unknown"), status)
        return False
    else:
        # 0x00 (new) or unknown — device may not set status; treat as usable
        logger.debug("[%s] Response status 0x%02X (%s)", command_desc, status,
                     status_names.get(status, "unknown"))

    # CRC validation: XOR of bytes 2-87 in the report (indices 3-88 with report ID prefix)
    if len(response) >= 90:
        expected_crc = response[89]  # byte 88 of report = index 89 with prefix
        computed_crc = 0
        for i in range(3, 89):  # bytes 2-87 of report = indices 3-88 with prefix
            computed_crc ^= response[i]
        if computed_crc != expected_crc:
            logger.warning("[%s] CRC mismatch: computed 0x%02X, expected 0x%02X (non-fatal)",
                           command_desc, computed_crc, expected_crc)
            # Non-fatal: still return True and let caller use the data

    return True


def send_and_receive_report(selected_device: dict, report: bytes, command_desc: str = "") -> list:
    """Send a feature report and read the device response.
    Returns response bytes or None. Retries once per interface on failure.
    """
    report_with_id = b'\x00' + report
    # Prefer the interface that worked last, then interface 0, then others.
    preferred_path = selected_device.get('preferred_interface_path')
    interfaces = list(selected_device.get('interfaces', []))
    interfaces.sort(key=lambda iface: (
        0 if preferred_path is not None and iface.get('path') == preferred_path else 1,
        0 if iface.get('interface_number', -1) == 0 else 1,
        iface.get('interface_number', 999),
    ))

    attempted_ifaces = []
    io_errors = []
    open_failed_count = 0

    for iface in interfaces:
        path = iface['path']
        iface_num = iface.get('interface_number', -1)
        attempted_ifaces.append(iface_num)
        for attempt in range(2):  # max 2 attempts per interface
            dev = None
            try:
                dev = hid.device()
                dev.open_path(path)
                time.sleep(0.05)
                dev.send_feature_report(report_with_id)
                time.sleep(0.08)
                response = dev.get_feature_report(0x00, REPORT_LEN + 1)
                dev.close()
                dev = None
                if validate_response(response, command_desc):
                    selected_device['preferred_interface_path'] = path
                    selected_device['_diag_last_ok'] = True
                    selected_device['_diag_last_command'] = command_desc
                    selected_device['_diag_last_interface'] = iface_num
                    selected_device['_diag_last_attempted_interfaces'] = attempted_ifaces
                    selected_device['_diag_last_io_errors'] = io_errors[-5:]
                    selected_device['_diag_last_open_failed_count'] = open_failed_count
                    return response
                # Invalid response — try next interface (don't retry same one for bad data)
                break
            except (OSError, IOError) as e:
                msg = str(e)
                io_errors.append(msg)
                if "open failed" in msg.lower():
                    open_failed_count += 1
                logger.warning("[%s] iface %d attempt %d: device I/O error: %s",
                               command_desc, iface_num, attempt + 1, e)
                if dev:
                    try:
                        dev.close()
                    except Exception:
                        pass
                if attempt == 0:
                    time.sleep(0.2)  # backoff before retry
                continue
            except ValueError as e:
                io_errors.append(str(e))
                logger.warning("[%s] iface %d: malformed report: %s", command_desc, iface_num, e)
                if dev:
                    try:
                        dev.close()
                    except Exception:
                        pass
                break  # don't retry malformed data
            except Exception as e:
                io_errors.append(str(e))
                logger.error("[%s] iface %d attempt %d: unexpected error: %s",
                             command_desc, iface_num, attempt + 1, e)
                if dev:
                    try:
                        dev.close()
                    except Exception:
                        pass
                if attempt == 0:
                    time.sleep(0.2)
                continue
    selected_device['_diag_last_ok'] = False
    selected_device['_diag_last_command'] = command_desc
    selected_device['_diag_last_attempted_interfaces'] = attempted_ifaces
    selected_device['_diag_last_io_errors'] = io_errors[-5:]
    selected_device['_diag_last_open_failed_count'] = open_failed_count
    return None


def get_battery_level(device: dict) -> int:
    """Query battery level. Returns 0-100 percentage, or -1 on failure.
    Retries once on failure with 500ms backoff.
    """
    tid = device.get('transaction_id', 0x1F)
    report = construct_razer_report(tid, 0x07, 0x80, 0x02, [0x00, 0x00])

    for attempt in range(2):
        response = send_and_receive_report(device, report, "get_battery_level")
        if response and len(response) > 10:
            raw = response[10]  # arguments[1] at offset 10 (get_feature_report prepends report ID byte)
            level = min(max(round(raw / 255 * 100), 0), 100)
            logger.debug("Battery raw=0x%02X (%d%%)", raw, level)
            return level
        if attempt == 0:
            logger.debug("get_battery_level: first attempt failed, retrying in 500ms")
            time.sleep(0.5)

    logger.warning("get_battery_level: all attempts failed")
    return -1


def get_charging_status(device: dict) -> bool:
    """Query charging status. Returns True if charging, False otherwise.
    Retries once on failure with 500ms backoff.
    """
    tid = device.get('transaction_id', 0x1F)
    report = construct_razer_report(tid, 0x07, 0x84, 0x02, [0x00, 0x00])

    for attempt in range(2):
        response = send_and_receive_report(device, report, "get_charging_status")
        if response and len(response) > 10:
            charging = response[10] > 0
            logger.debug("Charging status raw=0x%02X (charging=%s)", response[10], charging)
            return charging
        if attempt == 0:
            logger.debug("get_charging_status: first attempt failed, retrying in 500ms")
            time.sleep(0.5)

    logger.warning("get_charging_status: all attempts failed")
    return False


def is_mouse_device(pid: int) -> bool:
    return get_device_type(pid) == 'mouse'

def is_keyboard_device(pid: int) -> bool:
    return get_device_type(pid) == 'keyboard'
