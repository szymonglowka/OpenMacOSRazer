# Open Razer macOS Control 🎮

[![License](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
*Community-driven macOS utility for Razer peripherals*

---

## 🌟 Vision
Become the ultimate open-source tool for managing Razer devices on macOS, offering RGB control, macros, profiles, and more — all community-powered!

---

## 🚧 Current Status (April 2025)
**Python application with a basic GUI (PyQt5)** supporting:
- Device scanning and selection
- Setting **Static, Breathing, Wave, and Reactive** RGB effects for supported devices
- Direct HID communication via `hidapi`
- Basic application logging

---

## 📦 Supported Devices
The application attempts to communicate with the following devices. Functionality may vary.

| Device Model                   | PID      | Supported Features (Tested Effects)       |
|--------------------------------|----------|-------------------------------------------|
| Razer Basilisk V3 X HyperSpeed | 0x00B9   | Scroll wheel LED (Static, Breathing, etc.)|
| Razer BlackWidow V3 Pro (Wired)| 0x025A   | Keyboard backlight (Static, Breathing, etc.)|
| Razer BlackWidow V3 Pro (Wireless)| 0x025C | Keyboard backlight (Static, Breathing, etc.)|
| Razer DeathAdder Chroma        | 0x0A00   | *Untested* - Likely mouse LEDs            |
| Razer Mamba Chroma             | 0x0A01   | *Untested* - Likely mouse LEDs            |
| Razer Cynosa Chroma            | 0x0A02   | *Untested* - Likely keyboard backlight    |
| Razer Tartarus Chroma          | 0x0A03   | *Untested* - Likely keypad backlight      |

*Testing and feedback on untested devices are welcome!*

---

## 🗺️ Roadmap (Contributions Welcome!)
- 🔍 **Expand Device Support & Testing**
- 🎨 **Refine RGB Effects**: Customize parameters, improve compatibility
- ⌨️ **Key Remapping & Macros**
- 🔋 **Battery Monitoring** for wireless devices
- 🖥️ **Improve GUI**: Enhance usability, potentially move to Menu Bar
- 🐍 **Code Refactoring** for stability and maintainability

---

## ⚙️ Features (Current Application)
✅ Detects known Razer devices (Vendor ID `0x1532`, specific PIDs) via `hidapi`
✅ Graphical User Interface (GUI) for device selection and effect configuration
✅ Sets **Static, Breathing, Wave, and Reactive** RGB effects via HID commands
✅ Option to reset/turn off effects
✅ **Developer Mode**: Verbose logging and scanning of all connected Razer devices (supported or not) to aid in adding new hardware support.
✅ Basic application logging (`~/Library/Logs/open_razer_macos_control_app.log` or `~/open_razer_macos_control_app.log`)

---

## 🔧 Requirements
- **macOS** (Tested setup)
- **Python 3.8+**
- **`hidapi` system library**
    - macOS: `brew install hidapi`
- **Python dependencies** (see `requirements.txt`): [cite: 1]
    - `PyQt5>=5.15` [cite: 1]
    - `hidapi>=0.14.0` [cite: 1]

---

## 🚀 Quick Start
1.  **Install system dependency**:
    ```bash
    brew install hidapi
    ```
2.  **Clone the repository (or ensure you have the code files)**
    ```bash
    # Example cloning command if you have a repository URL:
    # git clone <repository_URL> open-razer-macos-control
    ```
3.  **Navigate to the project directory (e.g., `open-razer-macos-control`)**
    ```bash
    cd open-razer-macos-control
    ```
4.  **(Recommended) Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
5.  **Install Python dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
6.  **Run the application**:
    ```bash
    # Standard Mode (Logs to file only)
    python3 main.py

    # Developer Mode (Verbose console logs + Lists ALL Razer devices)
    # Use this if your device is not showing up!
    python3 main.py --debug
    ```
7.  **Permission issues?**
    - Accessing HID devices on macOS might require special permissions or occasionally running with `sudo python3 main.py`, though this is generally discouraged. Ensure your user has the necessary permissions first. Check System Settings -> Privacy & Security -> Input Monitoring if issues persist.

---

## 🔍 Diagnosing Unsupported Devices
If your Razer device is connected but not showing up in the list:
1. Run the application in **Debug Mode**:
   ```bash
   python3 main.py --debug
   ```
2. Check the terminal output. Look for lines starting with `Device found:`.
   - Example: `Device found: PID=0x025A, Product='Razer BlackWidow V3 Pro Wired', Interface=0, ...`
3. Note the **PID** (e.g., `0x025A`) of your device.
4. Open an Issue (or create a Pull Request) with this PID and the device name so we can add support!

---

## 🤝 Contributing
We need your skills! Help with:
- **Protocol reverse-engineering** (USB captures welcome!)
- **Feature development** (GUI improvements, macros, etc.)
- **Testing** (report device compatibility and bugs!)
- **Code cleanup and documentation**

**Steps**:
1.  Check/open [GitHub Issues](https://github.com/your-repo/issues) (Replace with your actual repo link if available)
2.  Fork the repository and create a feature branch.
3.  Submit Pull Requests with clear descriptions of changes.
4.  Follow [PEP8](https://peps.python.org/pep-0008/) for Python code style.

---

## ⚠️ Limitations
- Only supports devices explicitly listed or using similar protocols.
- Tested primarily on macOS.
- No Bluetooth support.
- Error handling is basic.
- Effect appearance might differ slightly between device models.
- **Use at your own risk** — interacting directly with hardware carries inherent risks!

---

## 🐧 Credits

This project is directly inspired by the groundbreaking work of:
OpenRazer for Linux
[OpenRazer](https://github.com/openrazer/openrazer)

---

## 📜 License
[GNU General Public License v3.0](LICENSE) (Assuming you have a LICENSE file with GPLv3)
*This project is not affiliated with Razer Inc.*