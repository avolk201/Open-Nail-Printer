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

echo "🧹 Cleaning up old autostart methods..."
sudo systemctl stop nailprinter.service 2>/dev/null || true
sudo systemctl disable nailprinter.service 2>/dev/null || true
sudo rm -f /etc/systemd/system/nailprinter.service
sudo systemctl daemon-reload

sed -i '/nailprinter_ui = chromium/d' "$HOME/.config/wayfire.ini" 2>/dev/null || true
sed -i '/@chromium --kiosk/d' "$HOME/.config/lxsession/LXDE-pi/autostart" 2>/dev/null || true

echo "⚙️ Step 2: Setting up XDG Autostart for the desktop environment..."
# We use XDG Autostart because it waits for the graphical session to load, 
# making it significantly more reliable for browsers and resolving PATH issues.
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"

DESKTOP_FILE="$AUTOSTART_DIR/nailprinter.desktop"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Type=Application
Name=Open Nail Printer
Comment=Starts the Nail Printer API and UI
# Use a login shell (-l) to ensure npm/node are in PATH, run the servers, wait, then launch Chromium
Exec=bash -l -c "$PROJECT_ROOT/stop_server.sh; $PROJECT_ROOT/start_server.sh & sleep 8 && chromium-browser --kiosk --start-maximized --disable-infobars http://127.0.0.1:5173"
Terminal=false
X-GNOME-Autostart-enabled=true
EOF
chmod +x "$DESKTOP_FILE"

echo "🌐 Step 3: Configuring display sleep settings (Disabling screen blanking)..."
# Support for Raspberry Pi OS Bullseye and older (X11/LXDE)
AUTOSTART_DIR="$HOME/.config/lxsession/LXDE-pi"
AUTOSTART_FILE="$AUTOSTART_DIR/autostart"
mkdir -p "$AUTOSTART_DIR"
if ! grep -q "chromium" "$AUTOSTART_FILE" 2>/dev/null; then
    echo "@xset s off" >> "$AUTOSTART_FILE"
    echo "@xset -dpms" >> "$AUTOSTART_FILE"
    echo "@xset s noblank" >> "$AUTOSTART_FILE"
    echo "✅ Added to LXDE autostart (Bullseye and older)"
fi

echo ""
echo "🎉 Setup complete!"
echo "The application will now start automatically when the desktop loads."
echo "It will wait a few seconds for the servers to spin up, then open Chromium."
echo ""
echo "To test this right now without restarting, you can run: "
echo "bash -l -c \"$PROJECT_ROOT/stop_server.sh; $PROJECT_ROOT/start_server.sh & sleep 8 && chromium-browser --kiosk http://127.0.0.1:5173\""
echo "Or just reboot your Raspberry Pi: sudo reboot"
