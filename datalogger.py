import subprocess
import can
import cantools
import csv
import os
import time
from datetime import datetime
import RPi.GPIO as GPIO
import threading

# === GPIO Configuration ===
BUTTON_PIN = 0
LED_PIN = 5

# === CAN Logger Config ===
OUTPUT_DIR = os.path.expanduser('~/can_logs')
DBC_FILE = os.path.expanduser('~/can_logs/e36.dbc')

CHANNEL = 'can0'
BITRATE = 1000000

# === Global Variables ===
logging_active = False
stop_logging = False
csvfile = None
csv_writer = None
start_time = None
can_interface = None
db = None

def setup_gpio():
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(LED_PIN, GPIO.OUT)
    GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    GPIO.remove_event_detect(BUTTON_PIN)
    GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, callback=toggle_logging, bouncetime=300)

def load_dbc():
    global db
    try:
        db = cantools.database.load_file(DBC_FILE)
    except Exception as e:
        print(f"Failed to load DBC: {e}")
        GPIO.output(LED_PIN, GPIO.LOW)
        exit(1)

def setup_can_interface():
    try:
        subprocess.run(
            ["sudo", "ip", "link", "set", CHANNEL, "up", "type", "can", "bitrate", str(BITRATE)],
            check=True
        )
        print(f"CAN interface {CHANNEL} brought up at {BITRATE} bps.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to bring up CAN interface: {e}")
        GPIO.output(LED_PIN, GPIO.LOW)
        exit(1)

def init_can():
    global can_interface
    try:
        can_interface = can.interface.Bus(channel=CHANNEL, bustype='socketcan')
    except Exception as e:
        print(f"CAN Interface Error: {e}")
        GPIO.output(LED_PIN, GPIO.LOW)
        exit(1)

def new_log_file():
    global csvfile, csv_writer, start_time
    timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = os.path.join(OUTPUT_DIR, f'can_log_{timestamp_str}.csv')
    csvfile = open(filename, mode='w', newline='')
    csv_writer = csv.writer(csvfile)
    csv_writer.writerow(['Time (s)', 'Message Name', 'Arbitration ID', 'Signals'])
    start_time = time.time()

def toggle_logging(channel):
    global logging_active, stop_logging, csvfile
    if logging_active:
        print("Stopping logging...")
        logging_active = False
        stop_logging = True
        GPIO.output(LED_PIN, GPIO.LOW)
        if csvfile:
            csvfile.flush()
            csvfile.close()
            csvfile = None
    else:
        print("Starting new logging session...")
        new_log_file()
        logging_active = True
        stop_logging = False
        GPIO.output(LED_PIN, GPIO.HIGH)

def log_loop():
    global stop_logging, logging_active
    while True:
        try:
            msg = can_interface.recv(timeout=1)
            if msg is None or not logging_active:
                continue

            # Update the logging timestamp
            rel_time = time.time() - start_time

            # Try to decode message with DBC
            try:
                decoded = db.decode_message(msg.arbitration_id, msg.data)
                message_name = db.get_message_by_frame_id(msg.arbitration_id).name
                signals = decoded

            except Exception as e:
                # Log the raw data if the DBC cannot decode message
                message_name = "RAW_MSG"
                signals = msg.data.hex()
                print(f"Decode error: ID {hex(msg.arbitration_id)} Data {msg.data.hex()} Error: {e}")

            # Write to CSV
            csv_writer.writerow([
                f"{rel_time:.6f}",
                message_name,
                hex(msg.arbitration_id),
                signals
            ])
            csvfile.flush()

        except Exception as e:
            print(f"CAN receive error: {e}")
            GPIO.output(LED_PIN, GPIO.LOW)
            time.sleep(1)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    setup_gpio()
    load_dbc()
    setup_can_interface()
    init_can()
    print("Ready. Press the button to start/stop logging.")
    GPIO.output(LED_PIN, GPIO.LOW)

    try:
        log_loop()
    except KeyboardInterrupt:
        print("Shutting down.")
    finally:
        if csvfile:
            csvfile.flush()
            csvfile.close()
        GPIO.cleanup()

if __name__ == '__main__':
    main()
