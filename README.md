# Open Razer macOS Control 🎮

[![License](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
*Community-driven macOS utility for Razer peripherals*

---

## 🌟 Vision
Become the ultimate open-source tool for managing Razer devices on macOS, offering RGB control, macros, profiles, and more — all community-powered!

---

## 🚧 Current Status
**Python application with a basic GUI (PyQt5)** offering generic support for Razer devices.
We have recently integrated hardware definitions from the OpenRazer project, enabling support for **over 250 devices**!

---

## ⚙️ Features
✅ **Extensive Device Support**: Now supports >250 Razer devices (Mice, Keyboards, Accessories, Laptops) using OpenRazer's hardware definitions.
✅ **Dynamic Protocol Handling**: Automatically detects device type and generation to use the correct communication protocol.
✅ **RGB Control**: Set **Static, Breathing, Wave, and Reactive** effects.
✅ **Graphical User Interface**: Easy-to-use GUI for device selection and configuration.
✅ **Direct HID Communication**: Uses `hidapi` for low-latency control.
✅ **Application Logging**: Diagnostics available in `~/Library/Logs/open_razer_macos_control_app.log`.

---

## 📦 Supported Devices
The application supports a vast range of devices, including but not limited to:
- **Mice**: DeathAdder (Chroma, Elite, V2, V3), Basilisk (V2, V3, Ultimate), Viper (Ultimate, Mini, 8K), Naga (Trinity, Pro, X), Mamba, Orochi, etc.
- **Keyboards**: BlackWidow (Chroma, Elite, V3, V4), Huntsman (Elite, Mini, V2), Ornata, Cynosa, DeathStalker.
- **Laptops**: Razer Blade Stealth, Blade 14/15/17 (various years).
- **Accessories**: Mouse Bungees, Headset Stands, Mouse Mats (Firefly, Goliathus).

*Note: While definitions for these devices are included, specific feature support (e.g. unique matrix effects) may vary.*

---

## 🔧 Requirements
- **macOS** (Tested on recent versions)
- **Python 3.8+**
- **`hidapi` system library**
    - Install via Homebrew: `brew install hidapi`
- **Python dependencies** (see `requirements.txt`):
    - `PyQt5>=5.15`
    - `hidapi>=0.14.0`

---

## 🚀 Quick Start

1.  **Install system dependency**:
    ```bash
    brew install hidapi
    ```

2.  **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/open-razer-macos-control.git
    cd open-razer-macos-control
    ```

3.  **(Recommended) Create and activate a virtual environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

4.  **Install Python dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

5.  **Run the application**:
    ```bash
    python3 main.py
    ```

    *Note: If you encounter permission errors accessing the device, you may need to grant "Input Monitoring" permissions to your terminal or IDE in System Settings -> Privacy & Security.*

---

## 🗺️ Roadmap
- 🔍 **Fine-tune Matrix Effects**: Improve custom effect support for advanced keyboards.
- ⌨️ **Key Remapping & Macros**: Implement software-side macro handling.
- 🔋 **Battery Monitoring**: Visualize battery levels for wireless devices.
- 🖥️ **Menu Bar App**: Minimize to tray for quick access.
- 🔄 **Auto-Updates**: Keep device definitions in sync with upstream.

---

## 🤝 Contributing
Contributions are welcome!
- **Testing**: Report which devices work perfectly and which need tweaks.
- **Code**: Submit PRs for new features or bug fixes.
- **Reverse Engineering**: Help decode protocols for unsupported features.

**Steps**:
1.  Fork the repository.
2.  Create a feature branch.
3.  Submit a Pull Request.

---

## 🐧 Credits & Acknowledgements

This project stands on the shoulders of giants.
Huge thanks to the **[OpenRazer](https://github.com/openrazer/openrazer)** project for their extensive reverse engineering and hardware definitions, which power the device support in this application.

---

## 📜 License
[GNU General Public License v3.0](LICENSE)
*This project is not affiliated with Razer Inc.*
