import requests

from .environment import API_KEY, API_URL

# API reference: https://panel.nomixclicker.com/docs

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
    """Click at specified coordinates.

    Args:
        device_id: Device ID
        coords: Tuple of (x, y) coordinates
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


def get_screen_state(device_id):
    """Get current screen state with all UI elements.

    Returns:
        dict with app_name, screen_description, elements[]
        Each element has: type, content, interactivity, center [x, y], bbox
    """
    response = requests.post(f"{API_URL}/{device_id}/screen-state", headers=HEADERS, timeout=60)
    response.raise_for_status()
    return response.json()


def find_element(screen_state, keyword, only_interactive=True):
    """Find first element whose content contains keyword.

    Args:
        screen_state: Result of get_screen_state()
        keyword: Text to search for (case-insensitive)
        only_interactive: If True, skip non-tappable elements
    Returns:
        Element dict or None
    """
    for el in screen_state.get("elements", []):
        content = el.get("content") or ""
        if keyword.lower() in content.lower():
            if only_interactive and not el.get("interactivity"):
                continue
            return el
    return None


def type_text(device_id, text):
    """Type text on the device.

    Args:
        device_id: Device ID
        text: Text string to type (1-10000 characters)
    """
    payload = {
        "text": text
    }
    response = requests.post(
        f"{API_URL}/{device_id}/keyboard/type",
        headers=HEADERS,
        json=payload
    )
    result = response.json()
    print(result)
    return result
