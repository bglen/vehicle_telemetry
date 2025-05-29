# Raspberry Pi CAN Logger

A simple CAN bus datalogger built for the Raspberry Pi 3 Model B+ using an Innomaker USB2CAN adapter. This project logs decoded CAN messages to timestamped CSV files using a provided DBC file.

### Features
- Starts and stops logging with a physical button
- LED indicates active logging status
- Logs decoded CAN messages to timestamped CSV files
- Handles sudden power loss gracefully
- Supports 1 Mbps CAN using `socketcan`
- Designed for Raspberry Pi 3 Model B+, can be easilly modified to work with other Pi models 

### To Do:
- improve csv file naming
- Make it boot faster
- Create PCB to eliminate internal wire harness
- DJI Action Camera auto start/stop via GPS and Bluetooth
- Connect to the internet via Phone USB hotspot
- Automatically upload time-stamped data to a server when connected to the internet
- With no phone connection, auto-start local WiFi network & server for local data download
- Dual CAN bus monitoring
- Switch Pi to Pi Zero 2W & external antenna to reduce BOM cost
- Update enclosure to AMP Superseal 1.0
- Enclosure heat-sinking

---

## Hardware Requirements

- Raspberry Pi 3 Model B+
- Innomaker USB2CAN adapter
- Momentary push button for log start/stop (connected to GPIO 27)
- LED + series resistor (connected to GPIO 17)
- CAN bus connection
- DBC file for decoding

---

## Software Setup

### Clone repository
Open terminal on your Raspberyy Pi and type:
```bash
# Clone the repository
git clone https://github.com/bglen/can_datalogger
```

### Install Dependencies

```bash
# Update and install system dependencies
sudo apt update
sudo apt install -y python3-pip python3-venv python3-rpi.gpio can-utils

# Navigate to your project directory
cd can_datalogger  # or wherever your repo is cloned

# Create and activate a virtual environment
python3 -m venv venv --system-site-packages
source venv/bin/activate

# Install required Python packages inside the virtual environment
pip install python-can cantools
```

### Auto-Start on Boot
Place the can_datalogger@.service file at
```bash
/etc/systemd/system/can_datalogger@.service
```
Reload systemd and enable the service:
```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable datalogger@USER
sudo systemctl start datalogger@USER
```
Where @USER is the username of your Pi. To verify it is working:
```bash
sudo systemctl start datalogger@USER
```


This will start the can_logger script on power up.

## Usage
Place your Place your DBC file in the project directory and update the path in can_logger_gpio.py:
```
DBC_FILE = '/home/pi/rpi-can-logger/your_file.dbc'
```
You can choose the directory where CSV logs are saved:
```
OUTPUT_DIR = '/home/pi/can_logs'
```

### Logging Output
CAN Messages are decoded with the DBC file and logged. Each log is saved as a CSV file:
```
Time (s), Message Name, Arbitration ID, Signals
0.012341, SteeringAngle, 0x123, {'angle': 3.4, 'valid': True}
...
```
Each time the CAN logger boots up, or logging is started with the GPIO input, it will start logging under a new file.

## License
MIT License