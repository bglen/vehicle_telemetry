import subprocess
import can
import cantools
import os
import sys

# Users can import:
#   import can
#   can.load_dbc()
#   can.setup_interface()\#   can.init_bus()
#   then access can.db, can.can_interface, can.signal_columns

# === CAN Module ===
# Configuration for CAN logging
DBC_FILE = os.path.expanduser('~/e36.dbc')
CHANNEL = 'can0'
BITRATE = 1000000

# Globals exposed to main
db = None
can_interface = None
signal_columns = ['RAW_MSG']  # will be extended after loading DBC


def load_dbc():
    """
    Load the DBC file and populate signal_columns.
    """
    global db, signal_columns
    try:
        db = cantools.database.load_file(DBC_FILE)
    except Exception as e:
        print(f"[CAN] Failed to load DBC {DBC_FILE}: {e}")
        sys.exit(1)

    # Append signal names
    for msg in db.messages:
        for sig in msg.signals:
            signal_columns.append(f"{msg.name}_{sig.name}")


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
    Initialize the python-can Bus object.
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
    