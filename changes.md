# Changes Since Last Upstream Commit

All changes made after szymonglowka's last commit (`e08753d` - Merge PR #15: Add Tartarus Pro support).

---

## New: Battery Menu Bar App

A standalone macOS menu bar app (`razer_battery_tray.py`) that monitors your Razer wireless mouse battery level in real time.

- **Smart polling** - checks battery every 5 minutes when connected, switches to 30-second polling when disconnected
- **Exponential backoff** - avoids hammering the HID bus when the device is unreachable
- **Background threading** - all HID I/O runs off the main thread so the menu bar never freezes
- **Color-coded battery icons** - 7 distinct PNG icons for every battery state:
  - Red (critical, 0-10%)
  - Orange (low, 11-30%)
  - Yellow-green (medium, 31-60%)
  - Green (full, 61-100%)
  - Orange bolt (charging under 30%)
  - Green + white bolt (charging above 30%)
  - Gray (disconnected)
- **Native macOS menu bar integration** via `rumps`
- **Battery percentage shown in menu bar title** alongside the icon

## New: Custom App Icon

- Custom `.icns` app icon for the battery tray app
- Full iconset at all required macOS resolutions (16x16 through 512x512 @2x)
- Icon generation script (`scripts/generate_icon.py`) using AppKit

## New: Battery Icon Generation

- `scripts/generate_battery_icons.py` - programmatically generates all 7 battery state PNG icons
- Icons are macOS menu bar optimized (22x22 base with @2x support)

## New: Settings Module

- `settings.py` - centralized configuration for polling intervals, battery thresholds, icon paths, and log settings

## New: Build Script

- `scripts/build-release.sh` - builds the `.app` bundle using py2app

## New: Comprehensive Test Suite

- `tests/test_battery.py` - battery level reading and threshold tests (244 lines)
- `tests/test_tray.py` - menu bar app behavior, polling, icon selection tests (258 lines)
- `tests/test_ui.py` - RGB control GUI tests (130 lines)
- `tests/test_main.py` - entry point tests (50 lines)
- `tests/test_deep.py` - deep integration and edge case tests (1,366 lines)
- `tests/conftest.py` - shared test fixtures
- `tests/helpers.py` - test utility functions

## Updated: HID Protocol (`razer_common.py`)

- Improved HID communication reliability
- Better error handling for device queries
- +296 lines of protocol improvements

## Updated: RGB Control GUI (`razer_ui.py`)

- Streamlined UI code
- Minor fixes and cleanup

## New: SVG Comic Documentation

4 illustrated comic strips explaining how the battery indicator works, featuring a school teacher character walking through each battery state:

1. **Lesson 1: Critical Battery** - what happens at 0-10% (red alert)
2. **Lesson 2: Battery Levels** - orange, yellow-green, and green states
3. **Lesson 3: Mouse Disconnected** - gray icon, fast polling, reconnection
4. **Lesson 4: Charging Indicators** - orange bolt, white bolt, fully charged

## Updated: README.md

- Complete rewrite with structured documentation
- Comics displayed full-width at the top
- Architecture overview, installation steps, and device compatibility
- Badge bar (license, platform, Python version, device count, test count)

## Replaced: requirements.txt → requirements.md

- Replaced plain `requirements.txt` with a detailed `requirements.md` documenting all dependencies with descriptions

---

### File Summary

| Category | Files |
|----------|-------|
| New files | 37 |
| Modified files | 4 |
| Deleted files | 1 (`requirements.txt`) |
| Lines added | ~4,933 |
| Lines removed | ~219 |
