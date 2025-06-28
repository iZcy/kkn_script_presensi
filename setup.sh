#!/bin/bash
set -e

SERVICE_NAME="kkn_server"
PROJECT_DIR="/home/adminarachnova/kkn/kkn_script_presensi"
PYTHON_BIN="$PROJECT_DIR/.venv/bin/python"
UVICORN_BIN="$PROJECT_DIR/.venv/bin/uvicorn"
MODULE_NAME="main:app"
USER="adminarachnova"
PORT=33002

echo "Installing system dependencies..."
sudo apt update && sudo apt install -y tesseract-ocr python3-venv

# Create virtual environment if not exists
if [ ! -d "$PROJECT_DIR/.venv" ]; then
    echo "Creating virtual environment at $PROJECT_DIR/.venv..."
    python3 -m venv "$PROJECT_DIR/.venv"
fi

# Activate and install Python packages
echo "Activating virtual environment and installing dependencies..."
source "$PROJECT_DIR/.venv/bin/activate"
pip install --upgrade pip
pip install -r "$PROJECT_DIR/requirements.txt"

# Create systemd service
echo "Creating systemd service: $SERVICE_NAME..."
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=UGM KKN Attendance Checker FastAPI Server
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$UVICORN_BIN $MODULE_NAME --host 0.0.0.0 --port $PORT
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# Enable and start the service
echo "Reloading systemd and starting $SERVICE_NAME..."
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable "$SERVICE_NAME"
sudo systemctl restart "$SERVICE_NAME"

echo "Setup complete. FastAPI is running as a systemd service on port $PORT."
echo "Check logs with: sudo journalctl -u $SERVICE_NAME -f"
