"""Restart all devices associated with the account.

Usage:
    python3 tools/restart_all_devices.py
"""

from nomix_clicker.api_helper import get_devices, restart


def main():
    devices = get_devices()

    for device_id in devices:
        restart(device_id)


if __name__ == '__main__':
    main()
