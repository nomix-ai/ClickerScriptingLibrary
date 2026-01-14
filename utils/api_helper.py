import requests

from .environment import API_KEY, API_URL

HEADERS = {"X-API-Key": API_KEY}


def set_coordinates(device_id, coords, is_pressed=False):
    """Set absolute cursor position.
    
    Args:
        device_id: Device ID
        coords: Tuple of (x, y) coordinates
        is_pressed: Whether mouse button is pressed
    """
    x, y = coords
    payload = {
        "left": x,
        "top": y,
        "is_pressed": is_pressed
    }
    response = requests.post(
        f"{API_URL}/{device_id}/coordinates",
        headers=HEADERS,
        json=payload
    )
    return response.json()


def move_to(device_id, start, end, is_pressed=False, duration=300):
    """Move mouse from start to end coordinates. Mouse released at end if pressed.
    
    Args:
        device_id: Device ID
        start: Tuple of (x, y) start coordinates
        end: Tuple of (x, y) end coordinates
        is_pressed: Whether mouse button is pressed during movement
        duration: Movement duration in milliseconds (50-5000)
    """
    start_x, start_y = start
    end_x, end_y = end
    payload = {
        "start_left": start_x,
        "start_top": start_y,
        "end_left": end_x,
        "end_top": end_y,
        "is_pressed": is_pressed,
        "duration": duration
    }
    response = requests.post(
        f"{API_URL}/{device_id}/move",
        headers=HEADERS,
        json=payload
    )
    return response.json()
