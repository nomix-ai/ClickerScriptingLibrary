import requests

from utils.api_helper import headers
from utils.environment import API_URL

devices = requests.get(f"{API_URL}/devices", headers=headers).json()

for device_id in devices:
    requests.post(f"{API_URL}/{device_id}/restart", headers=headers)
    print(f"Restarted device {device_id}")
