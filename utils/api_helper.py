import time

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
    """Click at specified coordinates.

    Args:
        device_id: Device ID
        coords: Tuple of (x, y) coordinates
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
    response = session.post(
        f"{API_URL}/{device_id}/keyboard/type",
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
    response = session.post(
        f"{API_URL}/{device_id}/agent/run",
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
    response = session.get(
        f"{API_URL}/{device_id}/agent/{task_id}",
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
    response = session.delete(
        f"{API_URL}/{device_id}/agent/{task_id}",
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def poll_agent(device_id, task_id, callback=None):
    """Poll agent task progress until completion.

    Args:
        device_id: Device ID
        task_id: Task ID from run_agent()
        callback: Optional function(event_data: dict) called for each new event.
                  If None, prints events to stdout.
    Returns:
        Final task result string or None
    """
    seen_events = 0

    while True:
        task = get_agent_task(device_id, task_id)
        events = task.get("events", [])

        for event in events[seen_events:]:
            if callback:
                callback(event)
            else:
                step = event.get("step", "?")
                max_steps = event.get("max_steps", "?")
                action = event.get("action", "?")
                result = event.get("result", "?")
                print(f"[{step}/{max_steps}] {action} -> {result}")
        seen_events = len(events)

        status = task.get("status")
        if status not in ("pending", "running"):
            result = task.get("result")
            if callback:
                callback({"status": status, "result": result})
            else:
                print(f"\n--- Agent {status}: {result}")
            return result

        time.sleep(1)
