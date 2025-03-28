# Raspberry Pi CAN Logger

A simple CAN bus datalogger built for the Raspberry Pi 3 Model B+ using an Innomaker USB2CAN adapter. This project logs decoded CAN messages to timestamped CSV files using a provided DBC file.

### Features
- Starts and stops logging with a physical button
- LED indicates active logging status
- Logs decoded CAN messages to timestamped CSV files
- Handles sudden power loss gracefully
- Supports 1 Mbps CAN using `socketcan`
- Designed for Raspberry Pi 3 Model B+, can be easilly modified to work with other Pi models 

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

### Install Dependencies

```bash
sudo apt update
sudo apt install -y python3-pip python3-rpi.gpio can-utils bluetooth bluez
pip3 install python-can cantools
```
### Auto-Start on Boot
Place the can_datalogger.service file at
```
/etc/systemd/system/can_datalogger.service
```
Reload systemd and enable the service:
```
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable canlogger.service
sudo systemctl start canlogger.service
```
This will enable the CAN bus at 1 Mbps and then start the can_logger script on power up.
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