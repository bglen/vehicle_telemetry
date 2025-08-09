# Vehicle Telemetry System

*Note: This is a work in progress and many features are not implemented yet.*

The Vehicle Telemetry System is an offline-first, containerized CAN data logging system. The system is designed to provide live telemetry and data logging for race cars, but can easilly be adapted to any mobile vehicle or robotic platform that uses CAN networks.

# Architecture Overview
![Telemetry Architecture](/docs/Telemetry%20Architecture%20Diagram/Telemetry%20Architecture.png)

### Features
- Logs CAN messages and actively decodes with a provided DBC file
- Logging capability with and without internet access
- Stores data to local influxDB database when logging offline. Syncs data to cloud database when internet access is detected.
- Bluetooth control of action cameras (GoPro, DJI Action)
- Access and download decoded log files on the logger's local WiFi hotspot
- Handles sudden power loss gracefully
- Supports two CAN 2.0B networks up to 1 Mbps

## Hardware Overview

This repo contains the hardware design for an open-source Raspberry Pi based CAN data logger.

- Raspberry Pi 4 Model B
- 12V nominal power
- Can log two CAN networks
- GPIO for remote button for log start/stop and logging status LEDs
- Real time clock for accurate data time-stamps when not connected to internet
- Temperature, pressure, and humidity SPI sensor
- Bus voltage logging

---

## Datalogger Software Setup

1. Create a fresh install of Raspberry Pi OS on your Pi 4B
2. Connect to your Pi via SSH or other methods. Ensure it has an internet connection.
3. Update apt and install git and jq: `sudo apt update && sudo apt upgrade -y && sudo apt install -y git jq`
4. Clone the repo: `git clone https://github.com/bglen/vehicle_telemetry`
5. Go to the setup folder: `cd vehicle_telemetry/software/datalogger/setup`
6. Lets edit the **network_setup.json** file: `nano network_setup.json`
   1. In here, you can set the Wifi name and password when the datalogger is broadcasting an access point, and add any trusted Wifi networks to connect to first:
   
    > *Note: if you forget to edit this and reboot the Pi, you will not be able to SSH into it!*

   ```
   {
        "access_point": {
            "ssid": "racecar",
            "password": "my_datalogger_password"
        },
        "trusted_networks": [
            { "ssid": "my_network", "psk": "my_password" }
        ]
    }
7. Make **install.sh** executable: `chmod +x install.sh`
8. Run the installer: `./install.sh`
9. Reboot the Pi: `sudo reboot`

## License
MIT License