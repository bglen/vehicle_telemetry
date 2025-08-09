#!/usr/bin/env python3

import json
import subprocess
from pathlib import Path

# Auto-detect repo dir (wifi_manager.py is in software/datalogger)
REPO_DIR = Path(__file__).resolve().parent
NETWORK_SETUP_FILE = REPO_DIR / "setup" / "network_setup.json"
AP_CONN_NAME = "vehicle-telemetry-ap"  # connection profile name for NM hotspot

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
    Configure for client-mode wifi connection.
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
    Start AP mode using NetworkManager
    """
    # Read AP settings from config
    cfg = load_config()
    ap_cfg = cfg.get("access_point", {}) or {}
    ap_ssid = ap_cfg.get("ssid", "vehicle-datalogger") # Default SSID: vehicle-datalogger
    ap_pass = ap_cfg.get("password", "") # Default password: none

    # Ensure NM is running and interface is free
    subprocess.run(["systemctl", "start", "NetworkManager"])
    subprocess.run(["nmcli", "device", "disconnect", "wlan0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Clean up any previous hotspot profile
    subprocess.run(["nmcli", "connection", "down", AP_CONN_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["nmcli", "connection", "delete", AP_CONN_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # Create the hotspot profile
    subprocess.run([
        "nmcli", "connection", "add",
        "type", "wifi",
        "ifname", "wlan0",
        "con-name", AP_CONN_NAME,
        "autoconnect", "no",
        "ssid", ap_ssid
    ], check=False)

    # Configure AP mode + shared IPv4 (does DHCP/NAT automatically)
    subprocess.run([
        "nmcli", "connection", "modify", AP_CONN_NAME,
        "802-11-wireless.mode", "ap",
        "802-11-wireless.band", "bg",
        "ipv4.method", "shared",
        "ipv6.method", "ignore"
    ], check=False)

    # Security: WPA2-PSK if password present and >= 8 chars; otherwise open
    if ap_pass and len(ap_pass) >= 8:
        subprocess.run([
            "nmcli", "connection", "modify", AP_CONN_NAME,
            "wifi-sec.key-mgmt", "wpa-psk",
            "wifi-sec.psk", ap_pass
        ], check=False)
    else:
        subprocess.run([
            "nmcli", "connection", "modify", AP_CONN_NAME,
            "wifi-sec.key-mgmt", "none"
        ], check=False)

    # Bring the hotspot up
    subprocess.run(["nmcli", "connection", "up", AP_CONN_NAME], check=False)

def stop_access_point():
    """
    Stop AP and ensure NetworkManager is restarted.
    """
    subprocess.run(["nmcli", "connection", "down", AP_CONN_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run(["nmcli", "connection", "delete", AP_CONN_NAME], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

    # If no trusted networks found -> AP mode
    print("No trusted networks found, starting access point")
    start_access_point()

if __name__ == "__main__":
    main()