#!/bin/bash
set -e

# Detect repo root (two levels up from setup/)
SETUP_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(dirname "$(dirname "$(dirname "$SETUP_DIR")")")"
SETUP_JSON="$SETUP_DIR/network_setup.json"

echo "[*] Using repo directory: $REPO_DIR"
echo "[*] Using setup directory: $SETUP_DIR"

# ---------- Prompt for WiFi configuration ----------
echo ""
echo "=== Wi-Fi configuration ==="
read -p "Access Point SSID (default vehicle-datalogger if blank): " AP_SSID
AP_SSID=${AP_SSID:-vehicle-datalogger}

read -p "Access Point password (no password if left blank): " AP_PASSWORD
AP_PASSWORD=${AP_PASSWORD:-}

echo ""
echo "Add trusted networks (client mode). Leave password blank for open networks."
TRUSTED_SSIDS=()
TRUSTED_PSKS=()
while true; do
  read -p "Add a trusted network? (y/N): " yn
  case "$yn" in
    [yY]*)
      read -p "  SSID: " SSID
      [ -z "$SSID" ] && { echo "  (empty SSID skipped)"; continue; }
      read -p "  Password (blank if open): " PSK
      TRUSTED_SSIDS+=("$SSID")
      TRUSTED_PSKS+=("$PSK")
      ;;
    *) break ;;
  esac
done

SETUP_JSON="$SETUP_DIR/network_setup.json"
echo "[*] Writing Wi-Fi config to $SETUP_JSON"

# Build trusted_networks array in JSON file
TRUSTED_JSON='[]'
for i in "${!TRUSTED_SSIDS[@]}"; do
  ssid="${TRUSTED_SSIDS[$i]}"
  psk="${TRUSTED_PSKS[$i]}"
  if [ -n "$psk" ]; then
    TRUSTED_JSON=$(echo "$TRUSTED_JSON" | jq --arg ssid "$ssid" --arg psk "$psk" '. + [{"ssid":$ssid,"psk":$psk}]')
  else
    TRUSTED_JSON=$(echo "$TRUSTED_JSON" | jq --arg ssid "$ssid" '. + [{"ssid":$ssid}]')
  fi
done

jq -n --arg ap_ssid "$AP_SSID" --arg ap_pass "$AP_PASSWORD" --argjson trusted "$TRUSTED_JSON" \
  '{access_point:{ssid:$ap_ssid, password:$ap_pass}, trusted_networks:$trusted}' > "$SETUP_JSON"

echo "[*] Saved."

# ---------- Install Packages ----------
echo "[*] Installing required packages..."
sudo apt update
sudo apt install -y iw network-manager python3-venv git jq

# Install fileserver mDNS so we can reach the Pi at datalogger.local
sudo apt install -y avahi-daemon libnss-mdns

# ---------- Python Environment Setup ----------
echo "[*] Creating Python virtual environment..."
cd "$REPO_DIR/software/datalogger"
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
fi
source .venv/bin/activate

# Sanity check: confirm we're in the venv
if [ -z "$VIRTUAL_ENV" ]; then
    echo "[ERROR] Virtual environment is not active. Aborting." >&2
    deactivate || true
    exit 1
fi

echo "[*] Virtual environment active: $VIRTUAL_ENV"
echo "[*] Using Python: $(which python3)"
echo "[*] Pip version: $(pip --version)"

# Upgrade pip and install any requirements
pip install --upgrade pip
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi
deactivate

# ---------- WiFi Manager Setup ----------

echo "[*] Setting up WiFi manager..."

# Grab the AP settings from network_setup.json
AP_SSID=$(jq -r '.access_point.ssid' "$SETUP_DIR/network_setup.json")
AP_PASSWORD=$(jq -r '.access_point.password' "$SETUP_DIR/network_setup.json")

# Replaces the placeholder in wifi_manager.service with repo path
TMP_WIFI_SERVICE=$(mktemp)
sed "s|{{REPO_DIR}}|$REPO_DIR/software/datalogger|g" \
    "$SETUP_DIR/wifi_manager.service" > "$TMP_WIFI_SERVICE"
sudo cp "$TMP_WIFI_SERVICE" /etc/systemd/system/wifi-manager.service
rm "$TMP_WIFI_SERVICE"

echo "[*] Enabling wifi-manager systemd service..."
sudo systemctl daemon-reexec
sudo systemctl enable wifi-manager.service

# ---------- Datalogger Service Setup ----------
echo "[*] Setting up datalogger service..."
# Ensure the datalogger user exists
if ! id -u datalogger >/dev/null 2>&1; then
    sudo useradd -m -s /bin/bash datalogger
fi

# Replate path placeholders and copy service file
TMP_DATALOGGER_SERVICE=$(mktemp)
sed "s|{{REPO_DIR}}|$REPO_DIR/software/datalogger|g" "$SETUP_DIR/datalogger.service" > "$TMP_DATALOGGER_SERVICE"
sudo cp "$TMP_DATALOGGER_SERVICE" /etc/systemd/system/datalogger.service
rm "$TMP_DATALOGGER_SERVICE"

echo "[*] Enabling datalogger systemd service..."
sudo systemctl daemon-reexec
sudo systemctl enable datalogger.service


# ---------- File Server Setup ----------
echo "[*] Setting up file server..."
sudo chown -R datalogger:datalogger "$REPO_DIR/software/datalogger/logs"

# Path to the fileserver.py (one directory above SETUP_DIR)
FILES_PY="$(dirname "$SETUP_DIR")/fileserver.py"
if [ ! -f "$FILES_PY" ]; then
  echo "[ERROR] Expected fileserver.py at: $FILES_PY" >&2
  exit 1
fi

# Install/enable Avahi (mDNS) already done above; set hostname to 'datalogger'
HOSTNAME_CHANGED=0
if [ "$(hostname)" != "datalogger" ]; then
  echo "[*] Setting hostname to 'datalogger' for mDNS (datalogger.local)..."
  echo datalogger | sudo tee /etc/hostname >/dev/null
  sudo sed -i 's/^\(127\.0\.1\.1\s*\).*/\1datalogger/' /etc/hosts
  sudo hostnamectl set-hostname datalogger
  HOSTNAME_CHANGED=1
fi

# Replate path placeholders and copy service file
TMP_FILESERVER_SERVICE=$(mktemp)
sed "s|{{REPO_DIR}}|$REPO_DIR/software/datalogger|g" "$SETUP_DIR/fileserver.service" > "$TMP_FILESERVER_SERVICE"
sudo cp "$TMP_FILESERVER_SERVICE" /etc/systemd/system/fileserver.service
rm "$TMP_FILESERVER_SERVICE"

echo "[*] Enabling fileserver systemd service..."
sudo systemctl daemon-reexec
sudo systemctl enable fileserver.service
sudo systemctl restart avahi-daemon || true
sudo systemctl start fileserver.service

# ---------- Prompt for reboot ----------
echo "[*] Setup complete."
read -p "Do you want to reboot now? (y/N): " REBOOT_ANSWER
case "$REBOOT_ANSWER" in
    [yY]|[yY][eE][sS])
        echo "[*] Rebooting..."
        sudo reboot
        ;;
    *)
        echo "[*] Reboot skipped. You need to reboot for changes to take effect."
        ;;
esac