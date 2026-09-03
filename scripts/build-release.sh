#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
VERSION="1.0.0"

cd "$PROJECT_DIR"

echo "=== Building Razer Battery v${VERSION} ==="

# Activate venv
source .venv/bin/activate

# Clean previous builds
rm -rf build dist

# Build .app bundle
python setup.py py2app

# Verify the .app exists
APP_PATH="dist/Razer Battery.app"
if [ ! -d "$APP_PATH" ]; then
    echo "ERROR: Build failed — $APP_PATH not found"
    exit 1
fi

# Create release zip
cd dist
zip -r "Razer-Battery-v${VERSION}-macOS.zip" "Razer Battery.app"
echo ""
echo "=== Build complete ==="
echo "App:     dist/Razer Battery.app"
echo "Release: dist/Razer-Battery-v${VERSION}-macOS.zip"
echo ""
echo "To test: open \"dist/Razer Battery.app\""
