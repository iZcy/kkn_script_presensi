#!/bin/bash
set -e

# === CONFIG ===
FASTAPI_SERVICE="kkn_attendance_simaster"
FASTAPI_DIR="$(pwd)/kkn_attendance"
FASTAPI_PY="$FASTAPI_DIR/.venv/bin/python"
FASTAPI_UVICORN="$FASTAPI_DIR/.venv/bin/uvicorn"
FASTAPI_MODULE="main:app"
PORT=33002

WA_SERVICE="kkn_attendance_wa_bot"
WA_DIR="$(pwd)/whatsapp"
WA_START_CMD="node index.js"

USER="${SUDO_USER:-$(whoami)}"

# === SYSTEM DEPENDENCIES ===
echo "Installing system dependencies..."
sudo apt update
sudo apt install -y tesseract-ocr python3-venv
echo "Installing Node.js (via NodeSource)..."
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# === FASTAPI SETUP ===
if [ ! -d "$FASTAPI_DIR" ]; then
    echo "Error: FastAPI project directory $FASTAPI_DIR does not exist."
    exit 1
fi

if ! id "$USER" &>/dev/null; then
    echo "Error: User '$USER' does not exist."
    exit 1
fi

if [ ! -d "$FASTAPI_DIR/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$FASTAPI_DIR/.venv"
fi

echo "Installing Python dependencies..."
source "$FASTAPI_DIR/.venv/bin/activate"
pip install --upgrade pip
REQ_FILE="$FASTAPI_DIR/requirements.txt"
if [ ! -f "$REQ_FILE" ]; then
    echo "Error: requirements.txt not found in $FASTAPI_DIR"
    exit 1
fi
pip install -r "$REQ_FILE"

# Wrapper script to run FastAPI with venv
FASTAPI_RUN="$FASTAPI_DIR/run_server.sh"
cat > "$FASTAPI_RUN" <<EOF
#!/bin/bash
source "$FASTAPI_DIR/.venv/bin/activate"
exec uvicorn "$FASTAPI_MODULE" --host 0.0.0.0 --port $PORT
EOF
chmod +x "$FASTAPI_RUN"

# systemd unit for FastAPI
FASTAPI_SERVICE_FILE="/etc/systemd/system/${FASTAPI_SERVICE}.service"
sudo bash -c "cat > $FASTAPI_SERVICE_FILE" <<EOF
[Unit]
Description=UGM KKN Attendance Checker FastAPI Server
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$FASTAPI_DIR
ExecStart=$FASTAPI_RUN
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# === WHATSAPP BOT SETUP ===
if [ ! -d "$WA_DIR" ]; then
    echo "Error: WhatsApp bot directory $WA_DIR does not exist."
    exit 1
fi

echo "Installing Node.js dependencies for WhatsApp bot..."
cd "$WA_DIR"
npm install

WA_SERVICE_FILE="/etc/systemd/system/${WA_SERVICE}.service"
sudo bash -c "cat > $WA_SERVICE_FILE" <<EOF
[Unit]
Description=KKN WhatsApp Bot Service
After=network.target

[Service]
User=$USER
Group=$USER
WorkingDirectory=$WA_DIR
ExecStart=$(which node) index.js
Restart=always
RestartSec=5
EnvironmentFile=$WA_DIR/.env
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# === PERMISSIONS AND STARTUP ===
echo "Setting ownership for $USER..."
sudo chown -R "$USER:$USER" "$FASTAPI_DIR" "$WA_DIR"

echo "Reloading systemd and enabling services..."
sudo systemctl daemon-reload
sudo systemctl enable "$FASTAPI_SERVICE"
sudo systemctl enable "$WA_SERVICE"
sudo systemctl restart "$FASTAPI_SERVICE"
sudo systemctl restart "$WA_SERVICE"

echo "✅ All services set up successfully."
echo "📄 Check logs with:"
echo "  sudo journalctl -u $FASTAPI_SERVICE -f"
echo "  sudo journalctl -u $WA_SERVICE -f"
