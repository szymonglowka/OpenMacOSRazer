# Open Razer macOS Control 🎮

[![License](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)  
*Community-driven macOS utility for Razer peripherals*

---

## 🌟 Vision  
Become the ultimate open-source tool for managing Razer devices on macOS, offering RGB control, macros, profiles, and more — all community-powered!  

---

## 🚧 Current Status (March 2025)  
**Proof-of-concept Python script** supporting:  
- **Static RGB colors** for specific devices  
- Direct HID communication via `hidapi`  

---

## 📦 Supported Devices  
| Device Model               | PID      | Supported Features          |
|----------------------------|----------|-----------------------------|
| Razer Basilisk V3 X HyperSpeed | 0x00B9 | Scroll wheel LED color      |
| Razer BlackWidow V3 Pro (Wired) | 0x025A | Keyboard backlight color    |
| Razer BlackWidow V3 Pro (Wireless) | 0x025C | Keyboard backlight color    |

---

## 🗺️ Roadmap (Contributions Welcome!)  
- 🔍 **Expand Device Support**
- 🎨 **Advanced RGB Effects**: Breathing, spectrum, reactive typing  
- ⌨️ **Key Remapping & Macros**  
- 🔋 **Battery Monitoring** for wireless devices  
- 🖥️ **macOS Menu Bar GUI** (planned)  
- 🐍 **Code Refactoring** for stability  

---

## ⚙️ Features (Current Script)  
✅ Detects Razer devices (Vendor ID `0x1532`)  
✅ Sets **static RGB colors** via HID commands  
✅ Interactive device selection & color input  
✅ Basic success/failure feedback  

---

## 🔧 Requirements  
- **Python 3.8+**  
- **`hidapi` system library**  
  - macOS: `brew install hidapi`  
- **Python dependencies**:  
  ```bash
  pip install hidapi
  ```

---

## 🚀 Quick Start  
1. **Install dependencies**:  
   ```bash
   brew install hidapi && pip install hidapi
   ```
2. **Run the script**:  
   ```bash
   python main.py
   ```
3. **Permission issues?**  
   - macOS: Re-run with `sudo`  

---

## 🤝 Contributing  
We need your skills! Help with:  
- **Protocol reverse-engineering** (USB captures welcome!)  
- **Feature development** (GUI, macros, etc.)  
- **Testing** (report device compatibility!)  

**Steps**:  
1. Check/open [GitHub Issues](https://github.com/your-repo/issues)  
2. Submit PRs with clear descriptions  
3. Follow [PEP8](https://peps.python.org/pep-0008/) for Python code  

---

## ⚠️ Limitations  
- Only supports listed devices/PIDs  
- No Bluetooth support  
- Basic error handling only  
- **Use at your own risk** — hardware interactions can be risky!  

---

## 🐧 Credits 

This project is directly inspired  by the groundbreaking work of:   
OpenRazer for Linux
[OpenRazer](https://github.com/openrazer/openrazer)

---

## 📜 License  
[GNU General Public License v3.0](LICENSE)  
*Not affiliated with Razer, Inc.*  
