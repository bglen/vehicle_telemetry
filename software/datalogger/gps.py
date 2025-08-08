import serial
import pynmea2

# === GPS CONFIGURATION ===
GPS_PORT = '/dev/ttyACM0'  # Adjust if your GPS appears on a different device
GPS_BAUD = 9600

gps_data = {
    'lat': '',
    'lon': '',
    'speed': '',      # in m/s
    'track': ''       # heading in degrees
}

def gps_reader():
    """
    Continuously read NMEA RMC sentences and update gps_data.
    """
    try:
        ser = serial.Serial(GPS_PORT, GPS_BAUD, timeout=1)
    except Exception as e:
        print(f"Failed to open GPS port: {e}")
        return

    while True:
        try:
            line = ser.readline().decode('ascii', errors='replace')
            if line.startswith('$GPRMC') or line.startswith('$GNRMC'):
                msg = pynmea2.parse(line)
                if msg.status == 'A':  # Data valid
                    gps_data['lat'] = f"{msg.latitude:.6f}"
                    gps_data['lon'] = f"{msg.longitude:.6f}"
                    # Convert speed from knots to m/s
                    gps_data['speed'] = f"{float(msg.spd_over_grnd) * 0.514444:.2f}"
                    gps_data['track'] = f"{msg.true_course:.2f}"
        except Exception:
            continue