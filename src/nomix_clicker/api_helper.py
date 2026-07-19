import requests

from .environment import get_api_key, get_api_url

# API reference: https://panel.nomixclicker.com/docs

session = requests.Session()


def _auth(request):
    # per request, so a rotated key in config.json takes effect on reload
    request.headers["X-API-Key"] = get_api_key()
    return request


session.auth = _auth


def _post_action(url, payload=None, timeout=30):
    """POST to an action endpoint: never raises, network errors map to the fallback dict."""
    try:
        response = session.post(url, json=payload, timeout=timeout)
        result = _parse_action_response(response)
    except requests.RequestException as e:
        result = {"success": False, "message": str(e)}
    print(result)
    return result


def get_devices():
    """Get list of connected devices.

    Returns:
        List of device IDs
    """
    response = session.get(f"{get_api_url()}/devices", timeout=15)
    response.raise_for_status()
    result = response.json()
    print(result)
    return result


def restart(device_id):
    """Restart device.

    Args:
        device_id: Device ID
    """
    return _post_action(f"{get_api_url()}/{device_id}/restart", timeout=60)


def click(device_id, duration=300):
    """Click at the current cursor position.

    Args:
        device_id: Device ID
        duration: Click duration in milliseconds
    """
    return _post_action(f"{get_api_url()}/{device_id}/click", {"duration": duration})


def tap(device_id, coords, duration=100):
    """Move to coordinates and click in one call (with a device-settle delay).

    Args:
        device_id: Device ID
        coords: Tuple of (x, y) coordinates
        duration: Hold duration in milliseconds
    """
    x, y = coords
    return _post_action(f"{get_api_url()}/{device_id}/tap", {"left": x, "top": y, "duration": duration})


def move(device_id, start, end, is_pressed=False, duration=300):
    """Move mouse from start to end coordinates. Mouse released at end if pressed.

    Args:
        device_id: Device ID
        start: Tuple of (x, y) start coordinates
        end: Tuple of (x, y) end coordinates
        is_pressed: Whether mouse button is pressed during movement
        duration: Movement duration in milliseconds (0-5000)
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
    return _post_action(f"{get_api_url()}/{device_id}/move", payload)


def get_screen_state(device_id):
    """Get current screen state with all UI elements.

    Returns:
        dict with app_name, screen_description, elements[]
        Each element has: type, content, interactivity, center [x, y], bbox
    """
    response = session.post(f"{get_api_url()}/{device_id}/screen-state", timeout=60)
    response.raise_for_status()
    return response.json()


def scroll(device_id, direction, distance=300, duration=500):
    """Scroll at the current cursor position.

    Args:
        device_id: Device ID
        direction: "up" or "down"
        distance: Scroll distance (1-1000)
        duration: Scroll duration in milliseconds
    """
    payload = {"direction": direction, "distance": distance, "duration": duration}
    return _post_action(f"{get_api_url()}/{device_id}/scroll", payload)


def get_status(device_id):
    """Check device connection status.

    Args:
        device_id: Device ID
    Returns:
        dict with connection status info
    """
    response = session.get(f"{get_api_url()}/{device_id}/status", timeout=15)
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
    return _post_action(f"{get_api_url()}/{device_id}/keyboard/type", {"text": text})


def key_combo(device_id, codes):
    """Press keys in order and release them in reverse (e.g. Cmd+Space).

    Args:
        device_id: Device ID
        codes: List of key codes, e.g. ["MetaLeft", "Space"]
    """
    return _post_action(f"{get_api_url()}/{device_id}/keyboard/combo", {"codes": codes})


def get_screenshot(device_id):
    """Fetch the latest JPEG frame from the device stream.

    Args:
        device_id: Device ID
    Returns:
        Raw JPEG bytes, or None if no frame is available (e.g. stream down).
    Raises:
        requests.HTTPError: on 401/403 — an auth problem, not a missing frame.
    """
    try:
        response = session.get(f"{get_api_url()}/{device_id}/screenshot", timeout=15)
    except requests.RequestException:
        return None
    if response.status_code in (401, 403):
        response.raise_for_status()
    if response.status_code == 200:
        return response.content
    return None


def run_agent(device_id, task):
    """Start a new agent task.

    Args:
        device_id: Device ID
        task: Task instruction string
    """
    response = session.post(
        f"{get_api_url()}/{device_id}/agent/run",
        json={"task": task},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_agent_task(device_id, task_id):
    """Get agent task status.

    Args:
        device_id: Device ID
        task_id: Task ID
    """
    response = session.get(
        f"{get_api_url()}/{device_id}/agent/{task_id}",
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def cancel_agent_task(device_id, task_id):
    """Cancel a running agent task.

    Args:
        device_id: Device ID
        task_id: Task ID
    """
    response = session.delete(
        f"{get_api_url()}/{device_id}/agent/{task_id}",
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _parse_action_response(response):
    """Safely parse a response from an action endpoint.

    Action endpoints don't raise on failure and may return an empty body.
    Falls back to a minimal dict so callers always get a consistent value.
    """
    try:
        return response.json()
    except Exception:
        # a 2xx with an unparseable body is still an accepted action
        return {"success": response.ok, "message": f"Empty or invalid response (HTTP {response.status_code})"}
