# NomixClicker

Python automation for real iPhones.

The Clicker is a small hardware device that plugs into an iPhone and controls
it the way a person would — it taps, swipes, and types on the actual screen.
This library is its Python API.

```python
from nomix_clicker import Clicker, Agent, open_app, DEVICE_ID

clicker = Clicker(DEVICE_ID)
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

clicker = Clicker(DEVICE_ID)
open_app(clicker, "Calculator")

screen = parse_screen(clicker)     # returns None on network/timeout errors
if screen:
    print(screen.description)      # what the AI recognizer sees on screen
```

## Examples

Ready-made example scripts live in the [`examples/`](examples/) folder of the repository (not included in the pip package — clone the repo to get them). With the package installed, run one directly:

```commandline
python3 examples/notes.py
```

**Start here:**

- [**notes.py**](examples/notes.py) - Safe, offline reference — opens the Notes app, creates a note, and types into it.
- [**ai_agent.py**](examples/ai_agent.py) - Runs an autonomous AI agent task with real-time progress streaming — the agent drives the device on its own.

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

