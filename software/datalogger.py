import subprocess
import can
import cantools
import csv
import os
import time
from datetime import datetime
from gpiozero import LED, Button
import threading
import sys
import select
import termios
import tty

# === GPIO Configuration ===
button = Button(6, pull_up = True, bounce_time = 0.05)
led = LED(5, initial_value=False)
led.off()

# === CAN Logger Config ===
OUTPUT_DIR = os.path.expanduser('~/can_logs')
DBC_FILE = os.path.expanduser('~/e36.dbc')

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

def load_dbc():
    global db

    try:
        db = cantools.database.load_file(DBC_FILE)
    except Exception as e:
        print(f"Failed to load DBC: {e}")
        led.off()
        exit(1)

def setup_can_interface():
    try:
        # Bring CAN interface down if it is already up
        subprocess.run(["sudo", "ip", "link", "set", "can0", "down"], check=False)

        # Bring CAN interface up
        subprocess.run(
            ["sudo", "ip", "link", "set", CHANNEL, "up", "type", "can", "bitrate", str(BITRATE)],
            check=True
        )
        print(f"CAN interface {CHANNEL} brought up at {BITRATE} bps.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to bring up CAN interface: {e}")
        led.off();
        exit(1)

def init_can():
    global can_interface

    try:
        can_interface = can.interface.Bus(channel=CHANNEL, interface='socketcan')
    except Exception as e:
        print(f"CAN Interface Error: {e}")
        led.off()
        exit(1)

def new_log_file():
    global csvfile, csv_writer, start_time
    timestamp_str = datetime.now().strftime('%Y-%m-%d_%I-%M-%S-%p')
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
        led.off()
        if csvfile:
            csvfile.flush()
            csvfile.close()
            csvfile = None
    else:
        print("Starting new logging session...")
        new_log_file()
        logging_active = True
        stop_logging = False
        led.on()

def confirm_clear():
    if logging_active:
        print("Cannot clear logs while logging is active.")
        return

    print("Are you sure you want to delete all .csv log files in can_logs? (Y/N): ", end="", flush=True)
    response = input().strip().lower()

    if response == 'y':
        deleted = 0
        for file in os.listdir(OUTPUT_DIR):
            if file.endswith('.csv'):
                file_path = os.path.join(OUTPUT_DIR, file)
                os.remove(file_path)
                deleted += 1
        print(f"{deleted} log file(s) deleted.")
    else:
        print("Clear canceled.")

def log_loop():
    global stop_logging, logging_active

    # CLI commands are only enabled if started from the terminal
    input_enabled = sys.stdin.isatty()
    if input_enabled:
        old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())

    try:
        while True:
            # Check for user input only when not logging
            if input_enabled and not logging_active and sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                cmd = sys.stdin.readline().strip().lower()
                if cmd == "clear":
                    confirm_clear()

            # Skips calling recv (which is blocking) if not logging, allowing CLI commands
            if not logging_active:
                time.sleep(0.1)
                continue

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
                    message_name = "RAW_MSG"
                    signals = msg.data.hex()
                    print(f"Decode error: ID {hex(msg.arbitration_id)} Data {msg.data.hex()} Error: {e}")

                # write data to the csv file
                csv_writer.writerow([
                    f"{rel_time:.6f}",
                    message_name,
                    hex(msg.arbitration_id),
                    signals
                ])
                csvfile.flush()

            except Exception as e:
                print(f"CAN receive error: {e}")
                led.off()
                time.sleep(1)
    finally:
        if input_enabled:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    load_dbc()
    setup_can_interface()
    init_can()
    print("Ready. Press the button to start/stop logging.")
    led.off();

    button.when_pressed = toggle_logging

    try:
        log_loop()
    except KeyboardInterrupt:
        print("Shutting down.")
    finally:
        if csvfile:
            csvfile.flush()
            csvfile.close()

        # Bring down the CAN interface on exit
        subprocess.run(["sudo", "ip", "link", "set", CHANNEL, "down"], check=False)
        print("CAN interface brought down.")

if __name__ == '__main__':
    main()