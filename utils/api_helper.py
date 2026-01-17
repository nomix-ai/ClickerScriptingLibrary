import requests

from .environment import API_KEY, API_URL

HEADERS = {"X-API-Key": API_KEY}


def get_devices():
    """Get list of connected devices.
    
    Returns:
        List of device IDs
    """
    response = requests.get(f"{API_URL}/devices", headers=HEADERS)
    result = response.json()
    print(result)
    return result


def restart(device_id):
    """Restart device.
    
    Args:
        device_id: Device ID
    """
    response = requests.post(f"{API_URL}/{device_id}/restart", headers=HEADERS)
    result = response.json()
    print(result)
    return result


def click(device_id, duration=300):
    """Click at current cursor position.

    Args:
        device_id: Device ID
        duration: Click duration in milliseconds
    """
    payload = {
        "duration": duration
    }
    response = requests.post(
        f"{API_URL}/{device_id}/click",
        headers=HEADERS,
        json=payload
    )
    result = response.json()
    print(result)
    return result


def move(device_id, start, end, is_pressed=False, duration=300):
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
    result = response.json()
    print(result)
    return result
