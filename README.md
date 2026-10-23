# NomixClicker

Python automation for real iPhones.

The Clicker is a small hardware device that plugs into an iPhone and controls
it the way a person would — it taps, swipes, and types on the actual screen.
This library is its Python API.

```python
from nomix_clicker import Clicker, Agent, open_app, DEVICE_ID

with Clicker(DEVICE_ID) as clicker:
    open_app(clicker, "Notes")
    clicker.type("Hello from Python")

# or hand the whole task to the AI agent
Agent(DEVICE_ID).run("Open Settings and enable Dark Mode")
```

- **Real devices.** Works with any app on a physical iPhone — no simulators,
  no test frameworks, nothing installed on the phone's OS.
- **AI screen recognition.** Find and tap elements by what they mean
  ("the like button"), not by selectors or view hierarchies.
- **Autonomous agent.** Describe a task in plain language — the agent looks
  at the screen, decides, and acts, step by step.

[Get a Clicker](https://panel.nomixclicker.com/payment) · [nomixclicker.com](https://nomixclicker.com/) · [API docs](https://panel.nomixclicker.com/docs)

## Installation

Requires Python 3.10+. Install from PyPI:

```commandline
pip install nomix-clicker
```

Don't have a Clicker yet? [Get one on the official site](https://panel.nomixclicker.com/payment) — worldwide delivery in about two weeks. Then open the [Panel](https://panel.nomixclicker.com/choose_device) and grab your API token.

## Configuration

Provide your API token and device id in either of two ways (environment variables take precedence):

**Environment variables:**

```commandline
export NOMIX_API_KEY="your-api-key"
export NOMIX_DEVICE_ID="your-device-id"
```

**Or a `config.json`** in your working directory or next to the script (copy `config.example.json`):

```json
{
  "API_KEY": "your-api-key",
  "DEVICE_ID": "your-device-id",
  "API_URL": "https://panel.nomixclicker.com/clicker/v1"
}
```

## Quick start

```python
from nomix_clicker import Clicker, parse_screen, open_app, DEVICE_ID

with Clicker(DEVICE_ID) as clicker:
    open_app(clicker, "Calculator")
    screen = parse_screen(clicker)
    if screen:
        print(screen.description)
```

### Control sessions

`Clicker(device_id).click((x, y))` and the existing `api_helper` command functions use HTTP: no connection setup is required. The server claims the device for each command and returns 409 when another controller owns it. Commands use the same names, parameters and execution service as the live panel.

For a multi-step workflow, `with Clicker(device_id)` (or explicit `connect()` / `close()`) holds exclusive control over WebSocket until exit. This prevents another client from moving the phone between steps. `connect(takeover=True)` is an explicit takeover; a failed session never falls back to HTTP or replays input.

Commands return `{"status": "sent", "device_acknowledged": false}`. This confirms dispatch, not execution on the phone. Failures raise `ControlError` with `code` and `outcome` (`not_sent`, `partial`, or `unknown`). An interrupted session never reconnects or replays input automatically; create a new session only after checking the phone. Closing releases control and cancels unsent input. Device input is best effort without execution acknowledgments; input already transmitted may continue or overlap later actions on the phone.

The multi-step examples below use an exclusive `clicker` context. For direct protocol access use `clicker.control.request(method, params)`. Discover the endpoint with `GET /clicker/v1/{device_id}/control`; method schemas are at `GET /clicker/v1/control-schema`. HTTP command endpoints and the WebSocket contract are both available. SDK 0.2 raises errors instead of returning an unchecked failure dictionary, so a failed command stops the caller’s workflow. Typing is bounded to 180 seconds per command.

### Double tap

Use `double_tap` when an app requires two taps close enough together to like,
zoom, or select content:

```python
clicker.double_tap((16383, 16383))
```

The default hold duration is 50 ms per tap with a 100 ms gap. Both taps are
timed by the Clicker device in one API action, avoiding network delay between
separate `click()` calls. You can override either value:

```python
clicker.double_tap((16383, 16383), duration=60, gap=120)
```

### Upload photos and videos

`upload_media` sends a photo (JPEG, PNG, HEIC) or video (MP4, MOV, up to
500 MB) to the iPhone's Photos and waits until the phone has saved it — so
the file is the newest item in the gallery, ready to post:

```python
from nomix_clicker import open_app, upload_media

item = upload_media(clicker, "videos/clip.mp4")   # None if rejected, failed or timed out
if item:
    open_app(clicker, "Instagram")                # pick the newest item from the gallery
```

NMX Viewer must be broadcasting on the phone — it collects the file from the
device's queue. If the phone hasn't saved it within `timeout` seconds
(default 300), the file is withdrawn so it can't appear in Photos later.

## Examples

Ready-made example scripts live in the [`examples/`](examples/) folder of the repository (not included in the pip package — clone the repo to get them). With the package installed, run one directly:

```commandline
python3 examples/notes.py
```

**Start here:**

- [**notes.py**](examples/notes.py) - Safe, offline reference — opens the Notes app, creates a note, and types into it.
- [**ai_agent.py**](examples/ai_agent.py) - Runs an autonomous AI agent task with real-time progress streaming — the agent drives the device on its own.
- [**upload_media.py**](examples/upload_media.py) - Sends a photo or video to the iPhone's Photos, then opens Photos to show it.

**Device utilities** live in [`tools/`](tools/) — ⚠️ these change connectivity or the stream; running them may drop the device's broadcast:

- [**restart_all_devices.py**](tools/restart_all_devices.py) - Restarts all devices associated with your account.
- [**wake-up-phone.py**](tools/wake-up-phone.py) - Wakes, unlocks, and restarts the screen broadcast on a locked device.
- [**airplane-mode-iphone-12.py**](tools/airplane-mode-iphone-12.py) - Toggles airplane mode on and off on iPhone 12.
- [**switch-screen-viewing-iphone-12.py**](tools/switch-screen-viewing-iphone-12.py) - Turns Clicker screen viewing on/off.

## Local development

To work on the library itself, install it in editable mode:

```commandline
pip install -e .
```

