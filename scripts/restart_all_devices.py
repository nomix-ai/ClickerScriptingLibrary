import requests

from utils.api_helper import HEADERS
from utils.environment import API_URL


def main():
    devices = requests.get(f"{API_URL}/devices", headers=HEADERS).json()

    for device_id in devices:
        result = requests.post(f"{API_URL}/{device_id}/restart", headers=HEADERS).json()
        print(result)


if __name__ == '__main__':
    main()
