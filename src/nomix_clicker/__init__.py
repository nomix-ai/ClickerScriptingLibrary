"""nomix_clicker — iOS device automation via the Nomix Clicker API.

Simulate touch input and use AI screen recognition to navigate apps.

    from nomix_clicker import Clicker, parse_screen, open_app

    with Clicker("your-device-id") as clicker:
        open_app(clicker, "Calculator")
        screen = parse_screen(clicker)
"""

from importlib.metadata import PackageNotFoundError, version as _dist_version

from .actions import (
    chance_tap,
    close_app,
    find_and_click,
    is_ad,
    open_app,
    post_comment,
    random_sleep,
    swipe_back,
    swipe_feed,
    upload_media,
)
from .agent import Agent
from .clicker import Clicker
from .control import ControlError, ControlSession
from .environment import API_KEY, API_URL, DEVICE_ID
from .recognition import Element, Screen, parse_screen

try:
    __version__ = _dist_version("nomix-clicker")
except PackageNotFoundError:  # running from a source tree without installation
    __version__ = "0.0.0"

__all__ = [
    # core
    "Clicker",
    "ControlSession",
    "ControlError",
    "Agent",
    "Screen",
    "Element",
    "parse_screen",
    # actions
    "open_app",
    "close_app",
    "find_and_click",
    "swipe_feed",
    "swipe_back",
    "is_ad",
    "chance_tap",
    "post_comment",
    "random_sleep",
    "upload_media",
    # config
    "API_URL",
    "API_KEY",
    "DEVICE_ID",
    "__version__",
]
