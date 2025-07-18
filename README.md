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

## Software Setup

### Clone repository

### Install Dependencies

## Usage

### Logging Output

## License
MIT License