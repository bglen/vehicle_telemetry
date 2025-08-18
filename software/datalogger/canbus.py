import subprocess
import can
import cantools
import os
import sys

# Users can import:
#   import can
#   can.load_dbc()
#   can.setup_interface()
#   can.init_bus()
#   then access can.db, can.can_interface, can.signal_columns

# Configuration for CAN logging
DBC_DIR = os.path.expanduser('./dbc') # Directory for all DBC files
CHANNEL = 'can0'
BITRATE = 1000000

# Globals exposed to main
db = None
can_interface = None
signal_columns = ['RAW_MSG']  # will be extended after loading DBC


def load_dbc():
    """
    Build a single cantools Database from all .dbc files in DBC_DIR
    and populate signal_columns.
    Assumes no ID conflicts across files.
    """
    global db, signal_columns

    if not os.path.isdir(DBC_DIR):
        print(f"[CAN] DBC directory not found: {DBC_DIR}")
        sys.exit(1)

    dbc_files = sorted(
        f for f in (os.path.join(DBC_DIR, n) for n in os.listdir(DBC_DIR))
        if os.path.isfile(f) and f.lower().endswith('.dbc')
    )
    if not dbc_files:
        print(f"[CAN] No .dbc files found in: {DBC_DIR}")
        sys.exit(1)

    # Create an empty Database and add all files
    try:
        db = cantools.database.Database()
        for path in dbc_files:
            print(f"[CAN] Loading DBC: {path}")
            db.add_dbc_file(path)
    except Exception as e:
        print(f"[CAN] Failed while loading DBCs: {e}")
        sys.exit(1)

    # Build the flattened signal column list across all messages
    seen = set()
    for msg in db.messages:
        for sig in msg.signals:
            key = f"{msg.name}_{sig.name}"
            if key not in seen:
                signal_columns.append(key)
                seen.add(key)

    print(f"[CAN] Loaded {len(db.messages)} messages from {len(dbc_files)} DBC file(s).")
    print(f"[CAN] Total signal columns: {len(signal_columns)}")



def setup_interface():
    """
    Bring up the CAN interface at the specified bitrate.
    """
    try:
        subprocess.run(["sudo", "ip", "link", "set", CHANNEL, "down"], check=False)
        subprocess.run(
            ["sudo", "ip", "link", "set", CHANNEL, "up", "type", "can", "bitrate", str(BITRATE)],
            check=True
        )
        print(f"[CAN] Interface {CHANNEL} up @ {BITRATE} bps.")
    except subprocess.CalledProcessError as e:
        print(f"[CAN] Failed to bring up {CHANNEL}: {e}")
        sys.exit(1)


def init():
    """
    Initialize the python-can bus object.
    """
    global can_interface

    try:
        can_interface = can.interface.Bus(channel=CHANNEL, interface='socketcan')
    except Exception as e:
        print(f"[CAN] Bus init error: {e}")
        sys.exit(1)

def bring_down_interface():
    """
    Brings down the can interface on exit.
    """
    subprocess.run(["sudo", "ip", "link", "set", CHANNEL, "down"], check=False)
    print("CAN interface brought down.")
    