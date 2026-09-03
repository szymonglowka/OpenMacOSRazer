"""Persistent settings for Razer Battery Tray."""

import json
import logging
import os
import tempfile

logger = logging.getLogger("razer_battery_tray")

CONFIG_DIR = os.path.expanduser("~/.config/razer-battery")
CONFIG_FILE = os.path.join(CONFIG_DIR, "settings.json")

DEFAULTS = {
    "poll_interval": 300,
    "low_battery_threshold": 20,
    "low_battery_notify": True,
    "display_mode": "icon_percent",  # icon_percent | percent_only | icon_only
    "launch_at_login": False,
}

SETTING_TYPES = {
    "poll_interval": int,
    "low_battery_threshold": int,
    "low_battery_notify": bool,
    "display_mode": str,
    "launch_at_login": bool,
}

VALID_DISPLAY_MODES = {"icon_percent", "percent_only", "icon_only"}


class Settings:
    def __init__(self):
        self._data = dict(DEFAULTS)
        self.load()

    def load(self):
        """Load settings from disk, merging with defaults for missing keys."""
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r") as f:
                saved = json.load(f)
            if isinstance(saved, dict):
                for key in DEFAULTS:
                    if key in saved:
                        val = saved[key]
                        expected_type = SETTING_TYPES.get(key)
                        if expected_type and not isinstance(val, expected_type):
                            logger.warning("Setting '%s' has wrong type %s, using default",
                                           key, type(val).__name__)
                            continue
                        if key == "display_mode" and val not in VALID_DISPLAY_MODES:
                            logger.warning("Setting 'display_mode' has invalid value '%s', using default", val)
                            continue
                        self._data[key] = val
                logger.info("Settings loaded from %s", CONFIG_FILE)
            else:
                logger.warning("Settings file has invalid structure, using defaults")
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("Corrupt settings file (%s), using defaults", e)
        except Exception as e:
            logger.error("Error loading settings: %s", e)

    def save(self):
        """Write current settings to disk atomically via temp file + os.replace()."""
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(dir=CONFIG_DIR, suffix=".tmp")
            try:
                with os.fdopen(fd, "w") as f:
                    json.dump(self._data, f, indent=2)
                os.replace(tmp_path, CONFIG_FILE)
            except Exception:
                # Clean up temp file on failure
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise
            logger.debug("Settings saved to %s", CONFIG_FILE)
        except Exception as e:
            logger.error("Error saving settings: %s", e)

    def get(self, key):
        return self._data.get(key, DEFAULTS.get(key))

    def set(self, key, value):
        if key not in SETTING_TYPES:
            raise ValueError(f"Unknown setting key: {key!r}")
        expected_type = SETTING_TYPES[key]
        if expected_type is bool and isinstance(value, int) and not isinstance(value, bool):
            raise TypeError(f"Setting '{key}' requires bool, got int")
        if not isinstance(value, expected_type):
            raise TypeError(f"Setting '{key}' requires {expected_type.__name__}, got {type(value).__name__}")
        if key == "display_mode" and value not in VALID_DISPLAY_MODES:
            raise ValueError(f"Invalid display mode: {value!r}")
        self._data[key] = value
        self.save()
