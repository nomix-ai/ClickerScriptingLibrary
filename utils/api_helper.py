import requests

from .environment import API_KEY, API_URL

# API reference: https://panel.nomixclicker.com/docs

session = requests.Session()
session.headers.update({"X-API-Key": API_KEY})


def get_devices():
    """Get list of connected devices.

    Returns:
        List of device IDs
    """
    response = session.get(f"{API_URL}/devices")
    response.raise_for_status()
    result = response.json()
    print(result)
    return result


def restart(device_id):
    """Restart device.

    Args:
        device_id: Device ID
    """
    response = session.post(f"{API_URL}/{device_id}/restart")
    result = response.json()
    print(result)
    return result


def click(device_id, duration=300):
    """Click at the current cursor position.

    Args:
        device_id: Device ID
        duration: Click duration in milliseconds
    """
    payload = {
        "duration": duration
    }
    response = session.post(
        f"{API_URL}/{device_id}/click",
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
    response = session.post(
        f"{API_URL}/{device_id}/move",
        json=payload
    )
    result = response.json()
    print(result)
    return result


def get_screen_state(device_id):
    """Get current screen state with all UI elements.

    Returns:
        dict with app_name, screen_description, elements[]
        Each element has: type, content, interactivity, center [x, y], bbox
    """
    response = session.post(f"{API_URL}/{device_id}/screen-state", timeout=60)
    response.raise_for_status()
    return response.json()


def scroll(device_id, x, y, direction, distance=300, duration=500):
    """Scroll in a direction at the given coordinates.

    Args:
        device_id: Device ID
        x: X coordinate of scroll start
        y: Y coordinate of scroll start
        direction: "up" or "down"
        distance: Scroll distance in pixels
        duration: Scroll duration in milliseconds
    """
    payload = {"left": x, "top": y, "direction": direction, "distance": distance, "duration": duration}
    response = session.post(f"{API_URL}/{device_id}/scroll", json=payload)
    result = response.json()
    print(result)
    return result


def get_status(device_id):
    """Check device connection status.

    Args:
        device_id: Device ID
    Returns:
        dict with connection status info
    """
    response = session.get(f"{API_URL}/{device_id}/status")
    response.raise_for_status()
    result = response.json()
    print(result)
    return result


def type_text(device_id, text):
    """Type text on the device.

    Args:
        device_id: Device ID
        text: Text string to type (1-10000 characters)
    """
    payload = {"text": text}
    response = session.post(
        f"{API_URL}/{device_id}/keyboard/type",
        json=payload
    )
    result = response.json()
    print(result)
    return result
