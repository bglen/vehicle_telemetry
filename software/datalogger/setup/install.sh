#!/bin/bash
set -e

# Detect repo root (two levels up from setup/)
SETUP_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$(dirname "$SETUP_DIR")")"
echo "[*] Using repo directory: $REPO_DIR"

echo "[*] Installing required packages..."
sudo apt update
sudo apt install -y hostapd dnsmasq iw network-manager python3-venv git jq

echo "[*] Disabling services to be manually controlled..."
sudo systemctl disable hostapd || true
sudo systemctl disable dnsmasq || true

# ---------- Python Environment ----------
echo "[*] Creating Python virtual environment..."
cd "$REPO_DIR/software/datalogger"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate
pip install --upgrade pip
# If you have a requirements.txt in repo
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi
deactivate

# ---------- WiFi Manager Setup ----------
echo "[*] Setting up WiFi manager..."

# Grab the AP settings from trusted_networks.json
AP_SSID=$(jq -r '.access_point.ssid' "$SETUP_DIR/trusted_networks.json")
AP_PASSWORD=$(jq -r '.access_point.password' "$SETUP_DIR/trusted_networks.json")

# Replace placeholders in hostapd.conf
TMP_HOSTAPD=$(mktemp)
sed "s|{{AP_SSID}}|$AP_SSID|g; s|{{AP_PASSWORD}}|$AP_PASSWORD|g" \
    "$SETUP_DIR/hostapd.conf" > "$TMP_HOSTAPD"
sudo cp "$TMP_HOSTAPD" /etc/hostapd/hostapd.conf
rm "$TMP_HOSTAPD"

# Copy dnsmasq.conf over
sudo cp "$SETUP_DIR/dnsmasq.conf" /etc/dnsmasq.conf

# Replace placeholder in wifi_manager.service with repo path
TMP_WIFI_SERVICE=$(mktemp)
sed "s|{{REPO_DIR}}|$REPO_DIR/software/datalogger|g" \
    "$SETUP_DIR/wifi_manager.service" > "$TMP_WIFI_SERVICE"
sudo cp "$TMP_WIFI_SERVICE" /etc/systemd/system/wifi-manager.service
rm "$TMP_WIFI_SERVICE"

# Static IP for AP mode
echo "[*] Setting static IP for AP mode..."
if ! grep -q "interface wlan0" /etc/dhcpcd.conf; then
cat <<EOF | sudo tee -a /etc/dhcpcd.conf

interface wlan0
    static ip_address=192.168.4.1/24
EOF
fi

echo "[*] Enabling wifi-manager systemd service..."
sudo systemctl daemon-reexec
sudo systemctl enable wifi-manager.service

# ---------- Datalogger Service Setup ----------
echo "[*] Setting up datalogger service..."
# Ensure the datalogger user exists
if ! id -u datalogger >/dev/null 2>&1; then
    sudo useradd -m -s /bin/bash datalogger
fi

# Copy service file
TMP_DATALOGGER_SERVICE=$(mktemp)
sed "s|{{REPO_DIR}}|$REPO_DIR/software/datalogger|g" "$SETUP_DIR/datalogger.service" > "$TMP_DATALOGGER_SERVICE"
sudo cp "$TMP_DATALOGGER_SERVICE" /etc/systemd/system/datalogger.service
rm "$TMP_DATALOGGER_SERVICE"

echo "[*] Enabling datalogger systemd service..."
sudo systemctl daemon-reexec
sudo systemctl enable datalogger.service

echo "[*] Setup complete. Reboot to take effect."