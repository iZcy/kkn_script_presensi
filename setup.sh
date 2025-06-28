#!/bin/bash
set -e

echo "Installing system dependencies..."
sudo apt update && sudo apt install -y tesseract-ocr python3-venv

# Create virtual environment if not exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

echo "Installing Python packages..."
pip install --upgrade pip
pip install -r requirements.txt

echo "Setup complete. To activate the environment manually, run:"
echo "  source .venv/bin/activate"
