#!/usr/bin/env python3
import time
from datetime import datetime

LOG_FILE = "/tmp/datalogger_test.log"

def main():
    print("[TEST] datalogger.py started. Logging to", LOG_FILE)
    with open(LOG_FILE, "a") as f:
        f.write(f"[{datetime.now()}] datalogger.py service started successfully\n")
        f.flush()
        while True:
            now = datetime.now()
            message = f"[{now}] datalogger.py is running...\n"
            print(message, end="")
            f.write(message)
            f.flush()
            time.sleep(5)

if __name__ == "__main__":
    main()