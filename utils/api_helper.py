import json

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


# --- Agent API ---

def run_agent(device_id, task):
    """Start an AI agent task on the device.

    Args:
        device_id: Device ID
        task: Task instruction string

    Returns:
        dict with task_id, status, etc.
    """
    response = requests.post(
        f"{API_URL}/{device_id}/agent/run",
        headers=HEADERS,
        json={"task": task},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def get_agent_task(device_id, task_id):
    """Get agent task status and result.

    Args:
        device_id: Device ID
        task_id: Task ID from run_agent()

    Returns:
        dict with status, result, events, etc.
    """
    response = requests.get(
        f"{API_URL}/{device_id}/agent/{task_id}",
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def cancel_agent_task(device_id, task_id):
    """Cancel a running agent task.

    Args:
        device_id: Device ID
        task_id: Task ID from run_agent()

    Returns:
        dict with updated task status
    """
    response = requests.delete(
        f"{API_URL}/{device_id}/agent/{task_id}",
        headers=HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def stream_agent(device_id, task_id, callback=None):
    """Stream agent task progress via SSE.

    Args:
        device_id: Device ID
        task_id: Task ID from run_agent()
        callback: Optional function(event_data: dict) called for each step.
                  If None, prints events to stdout.

    Returns:
        Final task result string or None
    """
    response = requests.get(
        f"{API_URL}/{device_id}/agent/{task_id}/stream",
        headers=HEADERS,
        stream=True,
        timeout=300,
    )
    response.raise_for_status()

    result = None
    try:
        for line in response.iter_lines(decode_unicode=True):
            if not line or line.startswith(":"):
                continue  # skip keepalive comments and empty lines

            if line.startswith("event: done"):
                continue  # next data line has the final result

            if line.startswith("data: "):
                data = json.loads(line[6:])

                # Final event
                if "status" in data and "step" not in data:
                    result = data.get("result")
                    if callback:
                        callback(data)
                    else:
                        status = data.get("status", "?")
                        print(f"\n--- Agent {status}: {result}")
                    break

                # Step event
                if callback:
                    callback(data)
                else:
                    step = data.get("step", "?")
                    max_steps = data.get("max_steps", "?")
                    action = data.get("action", "?")
                    res = data.get("result", "?")
                    print(f"[{step}/{max_steps}] {action} -> {res}")
    except (requests.exceptions.ChunkedEncodingError, requests.exceptions.ConnectionError):
        print("\n--- Stream disconnected. Fetching final status...")
        task = get_agent_task(device_id, task_id)
        result = task.get("result")
        status = task.get("status", "?")
        print(f"--- Agent {status}: {result}")

    return result
