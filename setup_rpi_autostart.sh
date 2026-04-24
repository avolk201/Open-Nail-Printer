#!/bin/bash

# This script sets up the Raspberry Pi to automatically start the backend server
# and open the Chromium web browser in full-screen kiosk mode on boot.

# Exit on error
set -e

# Get the absolute path to the project root
PROJECT_ROOT=$(cd "$(dirname "$0")" && pwd)
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "📦 Step 1: Building the frontend UI..."
cd "$FRONTEND_DIR"
if ! command -v npm &> /dev/null; then
    echo "❌ Error: npm is not installed. Please install Node.js first."
    exit 1
fi
npm install
npm run build

echo "⚙️ Step 2: Creating a systemd service for the backend server..."
SERVICE_FILE="/etc/systemd/system/nailprinter.service"
sudo bash -c "cat > $SERVICE_FILE" << EOF
[Unit]
Description=Open Nail Printer API Server
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$PROJECT_ROOT
ExecStart=$PROJECT_ROOT/start_server.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable nailprinter.service
sudo systemctl start nailprinter.service

echo "🌐 Step 3: Configuring Chromium to open automatically on the desktop..."

# Support for Raspberry Pi OS Bookworm (Wayland/Wayfire)
WAYFIRE_DIR="$HOME/.config"
WAYFIRE_CONFIG="$WAYFIRE_DIR/wayfire.ini"
if [ -d "$WAYFIRE_DIR" ]; then
    # Create the file if it doesn't exist
    touch "$WAYFIRE_CONFIG"
    # Append the autostart section if it isn't there, and add chromium
    if ! grep -q "chromium" "$WAYFIRE_CONFIG"; then
        echo -e "\n[autostart]\nnailprinter_ui = chromium --kiosk --start-maximized --disable-infobars http://127.0.0.1:8000" >> "$WAYFIRE_CONFIG"
        echo "✅ Added to Wayfire autostart (Bookworm+)"
    fi
fi

# Support for Raspberry Pi OS Bullseye and older (X11/LXDE)
AUTOSTART_DIR="$HOME/.config/lxsession/LXDE-pi"
AUTOSTART_FILE="$AUTOSTART_DIR/autostart"
mkdir -p "$AUTOSTART_DIR"
if ! grep -q "chromium" "$AUTOSTART_FILE" 2>/dev/null; then
    echo "@xset s off" >> "$AUTOSTART_FILE"
    echo "@xset -dpms" >> "$AUTOSTART_FILE"
    echo "@xset s noblank" >> "$AUTOSTART_FILE"
    echo "@chromium --kiosk --start-maximized --disable-infobars http://127.0.0.1:8000" >> "$AUTOSTART_FILE"
    echo "✅ Added to LXDE autostart (Bullseye and older)"
fi

echo ""
echo "🎉 Setup complete!"
echo "The backend will now start silently in the background on every boot."
echo "Once the desktop loads, Chromium will open full-screen and point to the frontend."
echo ""
echo "To test this right now without restarting, you can run: "
echo "chromium --kiosk http://127.0.0.1:8000"
echo "Or just reboot your Raspberry Pi: sudo reboot"
