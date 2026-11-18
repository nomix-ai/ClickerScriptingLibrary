"""Toggle airplane mode on and off on iPhone 12.

Usage:
    python3 tools/airplane-mode-iphone-12.py
"""

from time import sleep

from nomix_clicker.api_helper import airplane_mode_pulse
from nomix_clicker.clicker import Clicker
from nomix_clicker.environment import DEVICE_ID

RECONNECT_S = 10


def main():
    clicker = Clicker(DEVICE_ID)

    clicker.swipe((28813, 1000), down=10000)
    # both taps and the 10 s between them are timed on the Clicker
    result = airplane_mode_pulse(DEVICE_ID, (6523, 6689))
    if not result.get("success"):
        raise SystemExit(f"Airplane Mode pulse failed: {result.get('message')}")
    sleep(result.get("device_wait_ms", 0) / 1000 + RECONNECT_S)
    clicker.click((16700, 26000))


if __name__ == '__main__':
    main()
