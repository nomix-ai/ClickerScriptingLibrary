from pathlib import Path
from time import monotonic

import requests
from urllib3.exceptions import NewConnectionError

from .environment import get_api_key, get_api_url
from .media_http import media_request

# API reference: https://panel.nomixclicker.com/docs

# The server queues a command, or types for up to 180 s, within its 240 s command deadline.
COMMAND_TIMEOUT = 250

session = requests.Session()


def _auth(request):
    # per request, so a rotated key in config.json takes effect on reload
    request.headers["X-API-Key"] = get_api_key()
    return request


session.auth = _auth


def _post_action(url, payload=None, screen=False):
    """POST to an action endpoint: never raises, network errors map to the fallback dict.

    With screen=True the server waits for the action to play out and adds a
    fresh "screen_state" to the result (one AI recognition request).
    """
    if screen:
        url += "?screen=true"
    try:
        response = session.post(url, json=payload, timeout=COMMAND_TIMEOUT)
        result = _parse_action_response(response)
    except requests.RequestException as e:
        result = {"success": False, "message": str(e), "outcome": _network_outcome(e)}
    # the AI quota is checked after the command has gone to the device
    if screen and result.get("status_code") == 429 and "outcome" not in result:
        result["outcome"] = "unknown"
    print({key: value for key, value in result.items() if key != "screen_state"})
    return result


def _network_outcome(error: requests.RequestException) -> str:
    """not_sent when the connection never opened, unknown once the request may have reached the server."""
    reason = getattr(error.args[0], "reason", None) if error.args else None
    if isinstance(error, (requests.ConnectTimeout, requests.exceptions.SSLError)) or isinstance(reason, NewConnectionError):
        return "not_sent"
    if isinstance(error, (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError)):
        return "unknown"
    return "not_sent"


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
    return _post_action(f"{get_api_url()}/{device_id}/restart")


def click(device_id, duration=300, *, screen=False):
    """Click at the current cursor position.

    Args:
        device_id: Device ID
        duration: Click duration in milliseconds
        screen: Return a fresh screen_state after the click
    """
    return _post_action(f"{get_api_url()}/{device_id}/click", {"duration": duration}, screen=screen)


def tap_parameters(coords: tuple[int, int], duration: int, randomize: bool) -> dict[str, int | bool]:
    left, top = coords
    params: dict[str, int | bool] = {"left": left, "top": top, "duration": duration}
    if randomize:
        params["randomize"] = True
    return params


def tap(
    device_id: str, coords: tuple[int, int], duration: int = 100,
    *, randomize: bool = False, screen: bool = False,
) -> dict:
    """Move to coordinates and click in one call (with a device-settle delay).

    Args:
        device_id: Device ID
        coords: Tuple of (x, y) coordinates
        duration: Hold duration in milliseconds
        randomize: Apply the server's tap variation
        screen: Return a fresh screen_state after the tap
    """
    return _post_action(f"{get_api_url()}/{device_id}/tap", tap_parameters(coords, duration, randomize), screen=screen)


def double_tap(
    device_id: str, coords: tuple[int, int], duration: int = 50, gap: int = 100,
    *, randomize: bool = False, screen: bool = False,
) -> dict:
    """Move to coordinates and double-tap with timing handled by the device.

    Args:
        device_id: Device ID
        coords: Tuple of (x, y) coordinates
        duration: Hold duration of each tap in milliseconds
        gap: Pause between taps in milliseconds
        randomize: Apply the server's double-tap variation
        screen: Return a fresh screen_state after the double tap
    """
    payload = tap_parameters(coords, duration, randomize)
    payload["gap"] = gap
    return _post_action(f"{get_api_url()}/{device_id}/double-tap", payload, screen=screen)


def swipe_direction(
    device_id: str, direction: str, *, distance: str | None = None, screen: bool = False,
) -> dict:
    payload = {"direction": direction}
    if distance is not None:
        payload["distance"] = distance
    return _post_action(f"{get_api_url()}/{device_id}/swipe", payload, screen=screen)


def move(device_id, start, end, is_pressed=False, duration=300, *, screen=False):
    """Move mouse from start to end coordinates. Mouse released at end if pressed.

    Args:
        device_id: Device ID
        start: Tuple of (x, y) start coordinates
        end: Tuple of (x, y) end coordinates
        is_pressed: Whether mouse button is pressed during movement
        duration: Movement duration in milliseconds (0-5000)
        screen: Return a fresh screen_state after the movement
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
    return _post_action(f"{get_api_url()}/{device_id}/move", payload, screen=screen)


def get_screen_state(device_id):
    """Get current screen state with all UI elements.

    Returns:
        dict with app_name, screen_description, elements[]
        Each element has: type, content, interactivity, center [x, y], bbox
    """
    response = session.post(f"{get_api_url()}/{device_id}/screen-state", timeout=60)
    response.raise_for_status()
    return response.json()


def scroll(device_id, direction, distance=300, duration=500, *, screen=False):
    """Scroll at the current cursor position.

    Args:
        device_id: Device ID
        direction: "up" or "down"
        distance: Scroll distance (1-1000)
        duration: Scroll duration in milliseconds
        screen: Return a fresh screen_state after the scroll
    """
    payload = {"direction": direction, "distance": distance, "duration": duration}
    return _post_action(f"{get_api_url()}/{device_id}/scroll", payload, screen=screen)


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


def type_text(device_id: str, text: str, delay: int = 0, *, screen: bool = False) -> dict:
    """Type text on the device; returns once the device has been sent all of it.

    Args:
        device_id: Device ID
        text: Text string to type (1-10000 characters, at most 180 s of typing)
        delay: Milliseconds between characters (0-1000); 0 uses the fastest safe pace
        screen: Return a fresh screen_state after typing
    """
    payload: dict[str, str | int] = {"text": text}
    if delay:
        payload["delay"] = delay
    return _post_action(f"{get_api_url()}/{device_id}/keyboard/type", payload, screen=screen)


def key_combo(device_id, codes, *, screen=False):
    """Press keys in order and release them in reverse (e.g. Cmd+Space).

    Args:
        device_id: Device ID
        codes: List of up to 4 key codes, e.g. ["MetaLeft", "Space"]
        screen: Return a fresh screen_state after the combo
    """
    return _post_action(f"{get_api_url()}/{device_id}/keyboard/combo", {"codes": codes}, screen=screen)


def show_keyboard(device_id: str, *, screen: bool = False) -> dict:
    """Toggle the iOS on-screen keyboard, e.g. to tap emoji the hardware keyboard can't type.

    Args:
        device_id: Device ID
        screen: Return a fresh screen_state after the toggle
    """
    return _post_action(f"{get_api_url()}/{device_id}/keyboard/show", screen=screen)


def airplane_mode_pulse(device_id: str, coords: tuple[int, int]) -> dict:
    """Tap the visible Airplane Mode switch twice, 10 seconds apart, timed on the Clicker.

    Args:
        device_id: Device ID
        coords: (x, y) of the Airplane Mode switch, e.g. in an open Control Center
    """
    left, top = coords
    return _post_action(f"{get_api_url()}/{device_id}/airplane-mode/pulse", {"left": left, "top": top})


def get_stream(device_id: str) -> dict:
    """Get a LiveKit URL and a subscribe-only token for the device's live screen.

    Returns:
        dict with url and token; the token admits one join within fifteen minutes
    """
    response = session.post(f"{get_api_url()}/{device_id}/stream", timeout=15)
    response.raise_for_status()
    return response.json()


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


def send_media(device_id: str, path: str | Path, timeout: float = 300) -> dict:
    """Send a photo (JPEG, PNG, HEIC) or video (MP4, MOV) to the device's Photos.

    The file waits in the device's queue until NMX Viewer, broadcasting on the
    phone, saves it — poll list_media() to see when it is saved.

    Args:
        device_id: Device ID
        path: Path to the local file (max 500 MB)
        timeout: Total request budget in seconds
    Returns:
        dict with id, kind, filename, sha256, size, status ("queued"), created_at
    """
    deadline = monotonic() + timeout
    path = Path(path)
    path.stat()
    return media_request("POST", f"/{device_id}/media", deadline - monotonic(), file=path)


def list_media(device_id: str, timeout: float = 15) -> dict:
    """List the latest files sent to the device, newest first.

    Args:
        device_id: Device ID
    Returns:
        dict with items[] (each queued, saved or failed) and max_bytes
    """
    return media_request("GET", f"/{device_id}/media", timeout)


def delete_media(device_id: str, media_id: str, timeout: float = 15) -> dict:
    """Withdraw a file the phone has not collected yet.

    Args:
        device_id: Device ID
        media_id: Media ID returned by send_media()
    """
    return media_request("DELETE", f"/{device_id}/media/{media_id}", timeout)


def run_agent(device_id: str, task: str, timezone: str | None = None) -> dict:
    """Start a new agent task.

    Args:
        device_id: Device ID
        task: Task instruction string
        timezone: IANA name the agent reads the time in (e.g. "Europe/Moscow"); the server defaults to UTC
    """
    payload = {"task": task}
    if timezone is not None:
        payload["timezone"] = timezone
    response = session.post(
        f"{get_api_url()}/{device_id}/agent/run",
        json=payload,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_active_agent_task(device_id: str) -> dict | None:
    """Get the agent task currently running on the device, or None if there is none."""
    response = session.get(f"{get_api_url()}/{device_id}/agent", timeout=10)
    if response.status_code == 404:
        return None
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
    """Parse a response from an action endpoint into a dict with "success" and "message".

    A refused command (HTTP 4xx/5xx) becomes {"success": False, "message", "status_code"},
    plus the server's "code" and "outcome" when it names them.
    """
    try:
        body = response.json()
    except ValueError:
        if response.ok:
            # a 2xx with an unparseable body is still an accepted action
            return {"success": True, "message": f"Empty or invalid response (HTTP {response.status_code})"}
        result = _action_error(response.status_code, None)
        if response.status_code >= 500:
            # a proxy error page: the command may have reached the device
            result["outcome"] = "unknown"
        return result
    if response.ok:
        return body
    return _action_error(response.status_code, body)


def _action_error(status_code: int, body) -> dict:
    detail = body.get("detail") if isinstance(body, dict) else body
    result = {"success": False, "message": f"HTTP {status_code}", "status_code": status_code}
    if isinstance(detail, dict):
        result["message"] = detail.get("message") or detail.get("error") or result["message"]
        for key in ("code", "outcome"):
            if key in detail:
                result[key] = detail[key]
    elif isinstance(detail, list):
        # FastAPI validation errors
        result["message"] = "; ".join(str(item.get("msg", item)) if isinstance(item, dict) else str(item) for item in detail)
    elif detail:
        result["message"] = str(detail)
    return result
