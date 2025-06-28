#!/bin/bash
set -e

echo "Installing system dependencies..."
sudo apt update && sudo apt install -y tesseract-ocr

echo "Installing Python packages..."
pip install -r requirements.txt
