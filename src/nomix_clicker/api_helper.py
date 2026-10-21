import mimetypes
from pathlib import Path

import requests

from .environment import get_api_key, get_api_url

# API reference: https://panel.nomixclicker.com/docs

session = requests.Session()


def _auth(request):
    # per request, so a rotated key in config.json takes effect on reload
    request.headers["X-API-Key"] = get_api_key()
    return request


session.auth = _auth


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


def get_screen_state(device_id):
    """Get current screen state with all UI elements.

    Returns:
        dict with app_name, screen_description, elements[]
        Each element has: type, content, interactivity, center [x, y], bbox
    """
    response = session.post(f"{get_api_url()}/{device_id}/screen-state", timeout=60)
    response.raise_for_status()
    return response.json()


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


def send_media(device_id, path):
    """Send a photo (JPEG, PNG, HEIC) or video (MP4, MOV) to the device's Photos.

    The file waits in the device's queue until NMX Viewer, broadcasting on the
    phone, saves it — poll list_media() to see when it is saved.

    Args:
        device_id: Device ID
        path: Path to the local file (max 500 MB)
    Returns:
        dict with id, kind, filename, sha256, size, status ("queued"), created_at
    """
    path = Path(path)
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    with path.open("rb") as f:
        response = session.post(
            f"{get_api_url()}/{device_id}/media",
            files={"file": (path.name, f, content_type)},
            timeout=300,
        )
    response.raise_for_status()
    return response.json()


def list_media(device_id):
    """List the latest files sent to the device, newest first.

    Args:
        device_id: Device ID
    Returns:
        dict with items[] (each queued, saved or failed) and max_bytes
    """
    response = session.get(f"{get_api_url()}/{device_id}/media", timeout=15)
    response.raise_for_status()
    return response.json()


def delete_media(device_id, media_id):
    """Withdraw a file the phone has not collected yet.

    Args:
        device_id: Device ID
        media_id: Media ID returned by send_media()
    """
    response = session.delete(f"{get_api_url()}/{device_id}/media/{media_id}", timeout=15)
    response.raise_for_status()
    return response.json()


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
