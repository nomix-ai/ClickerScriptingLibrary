import requests

from utils.api_helper import headers
from utils.environment import API_URL


def main():
    devices = requests.get(f"{API_URL}/devices", headers=headers).json()

    for device_id in devices:
        result = requests.post(f"{API_URL}/{device_id}/restart", headers=headers).json()
        print(result)


if __name__ == '__main__':
    main()
