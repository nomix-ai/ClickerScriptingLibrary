# ClickerScriptingLibrary

iOS device automation via Nomix Clicker API. Scripts simulate touch input and use AI screen recognition to navigate apps.

## Running scripts

```bash
python3 -m scripts.instagram
```

## Project structure

```
utils/
  __init__.py        — re-exports all public API
  clicker.py         — Clicker class (swipe, click, type)
  recognition.py     — Screen, Element, get_screen()
  actions.py         — high-level helpers (open_app, chance_tap, post_comment, etc.)
  agent.py           — Agent class (autonomous AI task runner)
  api_helper.py      — low-level HTTP calls to Nomix API (don't use directly)
  environment.py     — config values (API_URL, API_KEY, DEVICE_ID)
  config_handler.py  — config.json loader with auto-reload every 300s
scripts/
  instagram.py       — reference implementation
config.json          — API_URL, API_KEY, DEVICE_ID
```

## Imports

All public symbols are re-exported from `utils`:

```python
from utils import (
    Clicker, Agent, Screen, Element, get_screen, DEVICE_ID,
    open_app, swipe_feed, swipe_back, is_ad, chance_tap, post_comment,
    random_sleep, find_and_click,
)
```

## Coordinate system

HID absolute coordinates: **0–32767** on both axes. Device-independent, same for all screen sizes.

| Point | Coords |
|---|---|
| Top-left | (0, 0) |
| Center | (16383, 16383) |
| Bottom-right | (32767, 32767) |

- Swipe distance: typically 6000–8000 units
- `Element.center` and `Element.bbox` are already in this coordinate space
- `bbox` format from API: `[y_min, x_min, y_max, x_max]`

## API reference

### Clicker

```python
clicker = Clicker(device_id: str)
clicker.device_id: str                        # stored device ID

clicker.click(coords: tuple[int, int], duration: int = 100)
# Moves cursor to coords, then clicks. duration = hold time in ms.

clicker.swipe(coords: tuple[int, int], up: int = 0, down: int = 0, left: int = 0, right: int = 0, duration: int = 300)
# Swipe from coords in given direction(s). Distance in HID units.

clicker.type(text: str)
# Type text on device keyboard. Max 10000 chars.
```

Under the hood `click` calls `POST /{device_id}/click` (duration-based press at current cursor position) and `move` calls `POST /{device_id}/move` (absolute coordinate movement). Action endpoints don't raise on failure — they return `{"success": bool, "message": str}`.

### Screen recognition

```python
screen = get_screen(device: str | Clicker, context: str = "") -> Screen | None
# Calls POST /{device_id}/screen-state. Timeout: 60s.
# Uses AI vision to parse the current screen into structured elements.
# Returns None on network/timeout errors (no try/except needed in scripts).

screen.app_name: str           # e.g. "Instagram"
screen.description: str        # natural language screen description
screen.elements: list[Element] # all detected UI elements
screen.latency: float          # API processing time in seconds

screen.find(*keywords: str, interactive_only: bool = True) -> tuple | None
# Find first element whose content contains any keyword (case-insensitive).
# Returns center coords (x, y) or None.

screen.find_and_click(clicker: Clicker, *keywords: str, interactive_only: bool = True) -> bool
# Find element and tap it. Returns True if found and tapped.

screen.contains(*keywords: str) -> bool
# Check if any keyword appears in description or any element content.
```

### Element

```python
@dataclass(frozen=True)
class Element:
    idx: int              # index in elements list
    type: str             # "icon" | "button" | "text" | "input" | "image" | "toggle" | "tab" | "other"
    content: str          # text/label of the element
    interactivity: bool   # whether it's tappable
    center: tuple         # (x, y) in HID coords
    bbox: tuple           # (y_min, x_min, y_max, x_max) in HID coords
    location: str         # "status-bar" | "top-left" | "top-center" | "top-right" |
                          # "center" | "bottom-left" | "bottom-center" | "bottom-right" | "navigation-bar"

    is_interactive: bool  # property, same as interactivity
    x: int                # property, center[0]
    y: int                # property, center[1]
```

### High-level actions

```python
open_app(clicker: Clicker, app_name: str) -> bool
# Opens Spotlight, types app name, taps result. Returns False if not found.

find_and_click(clicker: Clicker, *keywords: str, context: str = "", interactive_only: bool = True) -> bool
# Get screen + find element + tap in one call. Returns False if not found.

swipe_feed(clicker: Clicker) -> None
# Swipe up to the next feed item (vertical scroll).

swipe_back(clicker: Clicker) -> None
# iOS swipe-back gesture (swipe right from left edge).

random_sleep(min_s: float = 0.3, max_s: float = 0.8) -> None
# Sleep for a random duration to simulate human behavior.

is_ad(screen: Screen) -> bool
# Returns True if screen contains ad indicators.

chance_tap(clicker: Clicker, screen: Screen, name: str, chance: float) -> bool
# With probability `chance`, finds button `name` on screen and taps it.
# Returns True if tapped.

post_comment(
    clicker: Clicker,
    text: str,
    input_keywords: list[str],    # keywords to find the input field
    submit_keyword: str,          # keyword to find the submit button
    cached_coords: dict | None = None,  # pass {} to cache across calls
) -> bool
# Finds comment input, types text, submits. Caches coords for repeat use.
```

### Agent (autonomous AI)

```python
agent = Agent(device_id: str)

agent.run(task: str) -> str
# Start a new autonomous task. Returns task_id.
# Only one task per device at a time (409 if already running).

agent.get_status(task_id: str | None = None) -> dict
# Get task status. Uses current_task_id if none provided.

agent.cancel(task_id: str | None = None) -> dict

agent.poll(task_id=None, interval: float = 1.0, timeout: float = 300.0) -> str | None
# Poll until completion, printing step events. Returns result or None on timeout.

agent.run_and_wait(task: str) -> str | None
# Convenience: run + poll. Auto-cancels on timeout.
```

Task statuses: `pending` → `running` → `completed` | `failed` | `cancelled`. Max 100 steps per task.

### Environment

```python
DEVICE_ID: str   # from config.json
API_URL: str     # default: https://panel.nomixclicker.com/clicker/v1
API_KEY: str     # sent as X-API-Key header
```

### Low-level API (utils/api_helper.py)

Available but rarely needed directly — `Clicker` wraps these:

```python
click(device_id, duration=300)                              # POST /{id}/click
move(device_id, start, end, is_pressed=False, duration=300) # POST /{id}/move
type_text(device_id, text)                                  # POST /{id}/keyboard/type
scroll(device_id, x, y, direction, distance=300, duration=500) # POST /{id}/scroll
get_screen_state(device_id)                                 # POST /{id}/screen-state
get_devices()                                               # GET /devices
get_status(device_id)                                       # GET /{id}/status
restart(device_id)                                          # POST /{id}/restart
```

## HTTP API error codes

| Code | Meaning |
|---|---|
| 200 | Success |
| 401 | Invalid API key |
| 403 | Device belongs to another user |
| 404 | Device not connected |
| 409 | Agent: device already has a running task |
| 429 | AI request quota exceeded |
| 502 | Vision API unavailable / no frame |

## Script template

```python
from time import sleep

from utils import (
    Clicker, get_screen, DEVICE_ID,
    open_app, swipe_feed, swipe_back, is_ad, chance_tap, random_sleep, find_and_click,
)


def main():
    clicker = Clicker(DEVICE_ID)

    if not open_app(clicker, "app_name"):
        return

    sleep(2)

    for i in range(count):
        screen = get_screen(clicker, f"step_{i}")
        if not screen:
            continue

        # screen.find("button_name") -> (x, y) or None
        # screen.contains("keyword") -> bool
        # is_ad(screen) -> bool
        # chance_tap(clicker, screen, "like", 0.25) -> bool
        # find_and_click(clicker, "button", context="step") -> bool
        # swipe_back(clicker)

        random_sleep(0.5, 2.0)


if __name__ == "__main__":
    main()
```

## Conventions

- **No `raise_for_status()`** on action endpoints (click, swipe, type). Only use on read/query endpoints (get_screen, get_status, get_devices).
- **Error handling**: `get_screen()` returns `None` on error — just check `if not screen:`.
- **Timing**: always add `random_sleep()` between interactions for human-like variance.
- **`get_screen()` context**: always pass a descriptive string for debug logs (e.g., `"reel_5"`, `"open_reels"`).
- **Reference implementation**: `scripts/instagram.py`.
