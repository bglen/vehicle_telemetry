import os
import csv
import time
import threading
import sys
import select
import termios
import tty
from datetime import datetime
from gpiozero import LED, Button

# Python modules
import canbus
import gps

# === VK-162 GPS ===
USE_GPS = True          # Set to False to disable GPS logging

# === GPIO ===
button = Button(6, pull_up = True, bounce_time = 0.05)
led = LED(5, initial_value=False)
led.off()

# === Logging === 
OUTPUT_DIR = os.path.expanduser('~/logs')

# === Global Variables ===
logging_active = False
csvfile = None
csv_writer = None
start_time = None

def new_log_file():
    """
    Create a new CSV log file and write header.
    """
    global csvfile, csv_writer, start_time

    os.makedirs(OUTPUT_DIR, exist_ok=True) # make output directory if it does not exist
    timestamp_str = datetime.now().strftime('%Y-%m-%d_%I-%M-%S-%p')
    filename = os.path.join(OUTPUT_DIR, f'can_log_{timestamp_str}.csv')
    csvfile = open(filename, mode='w', newline='')
    csv_writer = csv.writer(csvfile)

    # With the DBC loaded we can build our header from all the message declarations
    header = ['Time (s)', 'Message ID'] + canbus.signal_columns
    if USE_GPS:
        header += gps.GPS_COLUMNS

    csv_writer.writerow(header)
    start_time = time.time()

def toggle_logging():
    """
    Start or stop logging when button is pressed.
    """
    global logging_active, csvfile

    if logging_active:
        print("Stopping logging...")
        logging_active = False
        led.off()
        if csvfile:
            csvfile.flush()
            csvfile.close()
            csvfile = None
    else:
        print("Starting new logging session...")
        new_log_file()
        logging_active = True
        led.on()

def log_loop():
    """
    Logging loop to receive CAN frames, decode, append GPS, write to CSV, repeat.
    """
    global logging_active

    # Enable CLI commands if script was started from the terminal
    input_enabled = sys.stdin.isatty()
    if input_enabled:
        old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())

    try:
        while True:
            # Check for user input only when not logging
            if input_enabled and not logging_active and sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                if sys.stdin.readline().strip().lower() == "clear":
                    confirm_clear()

            # Skips calling recv (which is blocking) if not logging, allowing CLI commands
            if not logging_active:
                time.sleep(0.1)
                continue

            try:
                msg = canbus.can_interface.recv(timeout=1)
                if msg is None or not logging_active:
                    continue

                # Update the logging timestamp
                rel_time = time.time() - start_time

                # Try to decode the message with DBC
                vals = {col: '' for col in canbus.signal_columns}
                try:
                    decoded = canbus.db.decode_message(msg.arbitration_id, msg.data)
                    for name, val in decoded.items():
                        key = f"{canbus.db.get_message_by_frame_id(msg.arbitration_id).name}_{name}"
                        vals[key] = val
                except Exception:
                    vals['RAW_MSG'] = msg.data.hex()

                row = [f"{rel_time:.6f}", hex(msg.arbitration_id)]
                for col in canbus.signal_columns:
                    row.append(vals.get(col, ''))

                if USE_GPS:
                    row += [gps.gps_data['lat'], gps.gps_data['lon'], gps.gps_data['speed'], gps.gps_data['track']]

                csv_writer.writerow(row)
                csvfile.flush()

            except Exception as e:
                print(f"CAN receive error: {e}")
                led.off()
                time.sleep(1)
    finally:
        if input_enabled:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

def confirm_clear():
    """
    Delete all existing CSV logs, if user confirms.
    """
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

def main():
    # Initialize CAN bus
    canbus.load_dbc()
    canbus.setup_interface()
    canbus.init()

    # Start GPS thread if enabled
    if USE_GPS:
        threading.Thread(target=gps.gps_reader, daemon=True).start()

    print("Ready. Press the button to start/stop logging.")
    button.when_pressed = toggle_logging

    try:
        log_loop()
    except KeyboardInterrupt:
        print("Shutting down.")
    finally:
        if csvfile:
            csvfile.flush()
            csvfile.close()
        canbus.bring_down_interface()

if __name__ == '__main__':
    main()