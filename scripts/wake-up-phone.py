"""Wake, unlock, and restart the screen broadcast on a sleeping/locked device.

Copy of the backend wake_up_the_phone / reconnect_broadcast recovery flow.

Usage:
    python3 -m scripts.wake-up-phone
"""

from time import sleep

from utils.clicker import Clicker
from utils.environment import DEVICE_ID

# HID absolute coordinate space (0–32767)
HID_MAX = 32767
HID_CENTER = HID_MAX // 2

# Blind wake/unlock targets (wake.py)
WAKE_TAP = (HID_CENTER, HID_CENTER)              # neutral spot on the lock screen
UNLOCK_FROM = (HID_CENTER, HID_MAX)              # bottom edge
UNLOCK_TO = (HID_CENTER, HID_MAX * 25 // 100)    # swipe up to unlock (no passcode)

# Broadcast restart sequence (reconnect.py)
APP_NAME = "NMX Viewer"
SPOTLIGHT_COMBO = ["MetaLeft", "Space"]
KILL_COMBO = ["MetaLeft", "KeyE"]
BROADCAST_COMBO = ["MetaLeft", "KeyB"]
HOME_COMBO = ["MetaLeft", "KeyH"]
START_BROADCAST_OK = (16600, 19300)
STOP_DIALOG_CANCEL = (22586, 18662)
STOPPED_DIALOG_OK = (16384, 18000)


def reconnect_broadcast(clicker: Clicker) -> None:
    # Clear a possible modal system alert
    clicker.click(STOP_DIALOG_CANCEL)
    sleep(1)
    clicker.click(STOPPED_DIALOG_OK)
    sleep(1)

    # Dismiss leftovers of a failed previous attempt (Spotlight is a toggle)
    clicker.key_combo(["Escape"])
    sleep(1)
    clicker.key_combo(["Escape"])
    sleep(1)

    # Open the app via Spotlight
    clicker.key_combo(SPOTLIGHT_COMBO)
    sleep(3)
    clicker.type(APP_NAME)
    sleep(3)
    clicker.key_combo(["Enter"])
    sleep(3)

    # Stop a half-alive broadcast so the picker always offers "Start"
    clicker.key_combo(KILL_COMBO)
    sleep(3)

    # Open the picker and confirm
    clicker.key_combo(BROADCAST_COMBO)
    sleep(3)
    clicker.click(START_BROADCAST_OK)
    sleep(30)

    # Leave the device on the Home Screen (broadcast keeps running in the background)
    clicker.key_combo(HOME_COMBO)
    sleep(1)
    clicker.key_combo(HOME_COMBO)


def wake_up_the_phone(clicker: Clicker) -> None:
    """Wake, unlock, and (re)start the stream."""
    if clicker.get_screenshot() is not None:
        print("Stream already up — skipping")
        return

    # Tap to light up the sleeping screen -> the lock screen appears
    clicker.click(WAKE_TAP)
    sleep(1.5)
    # Swipe up from the bottom edge to unlock (assumes no passcode)
    clicker.swipe(UNLOCK_FROM, up=UNLOCK_FROM[1] - UNLOCK_TO[1], duration=250)
    sleep(2)

    # Start the broadcast via the existing, production-tested sequence
    reconnect_broadcast(clicker)


def main():
    clicker = Clicker(DEVICE_ID)
    wake_up_the_phone(clicker)


if __name__ == '__main__':
    main()
