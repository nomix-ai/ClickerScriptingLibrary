## NomixClicker Scripting Library

This is a library of ready-made scripts written in Python and using the free [Clicker API](https://panel.nomixclicker.com/docs).

### What Is Clicker?

NomixClicker is a controlling dongle for iOS. It allows manual control, automatic control via API, and fully autonomous AI mode.

Part of the features are work-in-progress, see the [Roadmap](https://nomixclicker.com/).

### Installation

Requires Python 3.10+. Install from PyPI:

```commandline
pip install nomix-clicker
```

Buy a Clicker device if you don't have it (delivery takes ~2 weeks to any place in the world), then open the [Panel](https://panel.nomixclicker.com/choose_device) and get your API token.

[Purchase on the official site only.](https://panel.nomixclicker.com/payment)

### Configuration

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

### Quick start

```python
from nomix_clicker import Clicker, parse_screen, open_app, DEVICE_ID

clicker = Clicker(DEVICE_ID)
open_app(clicker, "Calculator")

screen = parse_screen(clicker)     # returns None on network/timeout errors
if screen:
    print(screen.description)      # what the AI recognizer sees on screen
```

Manual control of iPhones will work out-of-the-box, no setup needed.

### Examples

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

### Local development

To work on the library itself, install it in editable mode:

```commandline
pip install -e .
```

