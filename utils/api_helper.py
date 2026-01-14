import requests

from .environment import API_KEY, API_URL

headers = {"X-API-Key": API_KEY}


def move_to(device_id, x, y, is_pressed=False):
    """Move mouse to specified coordinates without pressing (by default)."""
    payload = {
        "left": x,
        "top": y,
        "is_pressed": is_pressed
    }
    response = requests.post(
        f"{API_URL}/{device_id}/coordinates",
        headers=headers,
        json=payload
    )
    return response.json()
