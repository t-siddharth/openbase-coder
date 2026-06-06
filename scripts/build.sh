#!/bin/bash

# Exit on error
set -e

# Ensure we're in the project root
cd "$(dirname "$0")/.."

# Install development dependencies if they're not already installed
pip install -e ".[dev]"

# Clean any previous builds
rm -rf build dist

# Run PyInstaller with optimizations
pyinstaller --name multi \
    --onedir \
    --noconfirm \
    --clean \
    --strip \
    --noupx \
    --target-architecture universal2 \
    openbase_coder_cli/cli.py \
    --collect-all click

# Code sign the binary for better macOS performance
if command -v codesign &> /dev/null; then
    echo "Code signing binary..."
    codesign --force --deep --sign - "dist/multi/multi"
else
    echo "Warning: codesign not found. First run of binary may be slower on macOS."
fi

# Remove quarantine attribute if present
if command -v xattr &> /dev/null; then
    echo "Removing quarantine attribute..."
    xattr -d com.apple.quarantine "dist/multi/multi" 2>/dev/null || true
fi
