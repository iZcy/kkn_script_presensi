#!/bin/bash
set -e

# === CONFIG ===
FASTAPI_SERVICE="kkn_attendance_simaster"
WA_SERVICE="kkn_attendance_wa_bot"

echo "🔁 Reloading and restarting services..."

# Reload systemd to ensure it picks up any unit changes
sudo systemctl daemon-reload

# Enable services if not already enabled
sudo systemctl enable "$FASTAPI_SERVICE"
sudo systemctl enable "$WA_SERVICE"

# Restart both services
sudo systemctl restart "$FASTAPI_SERVICE"
sudo systemctl restart "$WA_SERVICE"

echo "✅ Services refreshed."
echo "📄 Check logs with:"
echo "  sudo journalctl -u $FASTAPI_SERVICE -f"
echo "  sudo journalctl -u $WA_SERVICE -f"
