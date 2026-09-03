"""Safety net tests for main.py — verifies entrypoint error paths."""

import sys
import pytest
from unittest.mock import patch, MagicMock


class TestMainImportFailure:
    def test_import_error_exits_with_message(self):
        """ImportError during startup produces a clear error message and sys.exit."""
        # Remove any cached main module
        if "main" in sys.modules:
            del sys.modules["main"]

        # Make PyQt5 import fail
        original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

        def mock_import(name, *args, **kwargs):
            if name == "PyQt5.QtWidgets" or name.startswith("PyQt5"):
                raise ImportError("No module named 'PyQt5'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import), \
             patch("logging.basicConfig"), \
             patch("logging.info"), \
             patch("logging.critical") as mock_critical:
            with pytest.raises(SystemExit) as exc_info:
                # Re-exec main.py module body
                exec(open("main.py").read(), {"__name__": "__test__", "__builtins__": __builtins__})
            assert "Import error" in str(exc_info.value)

    def test_unexpected_exception_exits_cleanly(self):
        """Unexpected exception during startup produces sys.exit with error message."""
        if "main" in sys.modules:
            del sys.modules["main"]

        original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

        def mock_import(name, *args, **kwargs):
            if name == "PyQt5.QtWidgets":
                raise RuntimeError("Unexpected crash")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import), \
             patch("logging.basicConfig"), \
             patch("logging.info"), \
             patch("logging.critical") as mock_critical:
            with pytest.raises(SystemExit) as exc_info:
                exec(open("main.py").read(), {"__name__": "__test__", "__builtins__": __builtins__})
            assert "Critical error" in str(exc_info.value)
