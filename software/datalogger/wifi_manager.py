#!/usr/bin/env python3

import json
import subprocess
import time
from pathlib import Path

# Auto-detect repo dir (wifi_manager.py is in software/datalogger)
REPO_DIR = Path(__file__).resolve().parent
NETWORK_SETUP_FILE = REPO_DIR / "setup" / "network_setup.json"

def scan_ssids():
    """
    Scan for nearby Wi-Fi SSIDs.
    """
    result = subprocess.run(["iwlist", "wlan0", "scan"], stdout=subprocess.PIPE)
    ssids = []
    for line in result.stdout.decode().split("\n"):
        line = line.strip()
        if line.startswith("ESSID:"):
            ssid = line.split(":")[1].strip('"')
            if ssid:
                ssids.append(ssid)
    return ssids

def load_config():
    """
    Load full JSON config (AP + trusted networks).
    """
    with open(NETWORK_SETUP_FILE) as f:
        return json.load(f)

def configure_wifi_client(ssid, psk=None):
    """
    Write wpa_supplicant.conf and reconnect.
    """
    # Make sure NM is running for client mode
    subprocess.run(["systemctl", "start", "NetworkManager"])
    # Delete any stale connection with same SSID (idempotent)
    subprocess.run(["nmcli", "connection", "delete", ssid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # Connect (no password if open)
    if psk:
        subprocess.run(["nmcli", "device", "wifi", "connect", ssid, "password", psk, "ifname", "wlan0"], check=False)
    else:
        subprocess.run(["nmcli", "device", "wifi", "connect", ssid, "ifname", "wlan0"], check=False)

def start_access_point():
    """
    Start hostapd + dnsmasq in AP mode.
    """
    # Stop NM & kill any supplicant on wlan0
    subprocess.run(["systemctl", "stop", "NetworkManager"])
    subprocess.run(["pkill", "-f", "wpa_supplicant"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Bring wlan0 up with static IP for AP
    subprocess.run(["ip", "link", "set", "wlan0", "up"])
    subprocess.run(["ip", "addr", "flush", "dev", "wlan0"])
    subprocess.run(["ip", "addr", "add", "192.168.4.1/24", "dev", "wlan0"])

    # Start services
    subprocess.run(["systemctl", "start", "hostapd"])
    subprocess.run(["systemctl", "start", "dnsmasq"])

def stop_access_point():
    """
    Stop AP services and restart NetworkManager.
    """
    subprocess.run(["systemctl", "stop", "hostapd"])
    subprocess.run(["systemctl", "stop", "dnsmasq"])
    subprocess.run(["systemctl", "start", "NetworkManager"])

def main():
    config = load_config()
    trusted_networks = config.get("trusted_networks", [])

    ssids = scan_ssids()
    print(f"Found networks: {ssids}")

    # Try connecting to trusted networks
    for entry in trusted_networks:
        if entry["ssid"] in ssids:
            print(f"Connecting to trusted network: {entry['ssid']}")
            stop_access_point()
            configure_wifi_client(entry["ssid"], entry.get("psk"))
            return

    # If no trusted networks found → AP mode
    print("No trusted networks found, starting access point")
    start_access_point()

if __name__ == "__main__":
    main()