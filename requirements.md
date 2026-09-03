## Open Razer macOS Control - Requirements Guide

This document expands the plain `requirements.txt` list into a practical setup guide for development, runtime, and release builds.

## Core dependencies (all features)
hidapi>=0.14.0
pyobjc-core>=10.0
pyobjc-framework-Cocoa>=10.0

## Battery tray menu bar app
rumps>=0.4.0

## RGB control GUI (main.py / razer_ui.py)
PyQt5>=5.15

## Development / testing
pytest>=8.0
pytest-mock>=3.12

## Scope

- Project: `OpenMacOSRazer`
- Platforms: macOS only
- Python: `3.8+` (recommended: `3.11`)
- App entry points:
  - GUI app: `main.py`
  - Menu bar battery app: `razer_battery_tray.py`

## System Prerequisites (macOS)

Install the HID system library first:

```bash
brew install hidapi
```

Why this matters:
- Python package `hidapi` binds to native HID libraries and is used for direct device communication in `razer_common.py`.

## Python Dependency Matrix

| Package | Minimum | Type | Used By | Purpose | Required |
|---|---:|---|---|---|---|
| `hidapi` | `0.14.0` | Runtime | `razer_common.py` (`import hid`) | Direct HID communication with Razer devices | Yes |
| `pyobjc-core` | `10.0` | Runtime | `razer_battery_tray.py`, icon scripts | Objective-C bridge runtime on macOS | Yes (tray + helper scripts) |
| `pyobjc-framework-Cocoa` | `10.0` | Runtime | `razer_battery_tray.py`, icon scripts (`AppKit`, `Foundation`) | macOS framework bindings for wake notifications, UI integration, icon generation | Yes (tray + helper scripts) |
| `rumps` | `0.4.0` | Runtime | `razer_battery_tray.py` | Menu bar app framework | Yes (tray app) |
| `PyQt5` | `5.15` | Runtime | `main.py`, `razer_ui.py` | Desktop GUI for RGB/effect control | Yes (GUI app) |
| `pytest` | `8.0` | Dev/Test | `tests/` | Test runner | Dev only |
| `pytest-mock` | `3.12` | Dev/Test | `tests/` | Mocking helpers for tests | Dev only |
| `py2app` | (latest stable) | Build | `setup.py`, `scripts/build-release.sh` | Build signed/packaged `.app` bundle for tray app release | Optional (release packaging) |

## Install Profiles

### 1) Full project (recommended for contributors)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 2) Tray app only (minimal runtime)

```bash
pip install "hidapi>=0.14.0" "pyobjc-core>=10.0" "pyobjc-framework-Cocoa>=10.0" "rumps>=0.4.0"
```

### 3) GUI app only (no tray menu app)

```bash
pip install "hidapi>=0.14.0" "PyQt5>=5.15"
```

### 4) Development + tests

```bash
pip install -r requirements.txt
pytest -q
```

### 5) Release build for tray app

```bash
pip install -r requirements.txt py2app
./scripts/build-release.sh
```

## Runtime Notes and macOS Permissions

### Input Monitoring permission (tray app)

`Razer Battery` may require **Input Monitoring** access to read HID battery reports:

- macOS: `System Settings -> Privacy & Security -> Input Monitoring`
- Enable access for your terminal/IDE (source run) or `Razer Battery.app` (bundled run).

### Razer DriverKit conflict

If battery reads fail or app shows warning state continuously, remove conflicting Razer system extensions:

```bash
sudo systemextensionsctl uninstall R2H967U7J8 com.razer.appengine.driver
sudo systemextensionsctl uninstall R2H967U7J8 com.razer.appengine.virtual.driver
```

## Quick Verification

Run this from an activated virtual environment:

```bash
python - <<'PY'
import hid
import rumps
import objc
from AppKit import NSWorkspace
from Foundation import NSObject
from PyQt5.QtWidgets import QApplication
print("Dependency import check: OK")
PY
```

Then validate app entry points:

```bash
python main.py
python razer_battery_tray.py
```

## Dependency Hygiene Guidelines

- Keep `requirements.txt` as the machine-readable install source.
- Update this `requirements.md` whenever package floors, install flow, or runtime caveats change.
- Prefer minimum version floors (`>=`) unless reproducibility requires lock files.
- For reproducible releases, generate and commit a pinned lock file separately (for example with `pip-tools`).

## Source of Truth (Current `requirements.txt`)

```txt
# Core dependencies (all features)
hidapi>=0.14.0
pyobjc-core>=10.0
pyobjc-framework-Cocoa>=10.0

# Battery tray menu bar app
rumps>=0.4.0

# RGB control GUI (main.py / razer_ui.py)
PyQt5>=5.15

# Development / testing
pytest>=8.0
pytest-mock>=3.12
```
