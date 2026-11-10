from typing import Any, Literal, overload

from .api_helper import double_tap, get_screenshot, key_combo, move, swipe_direction, tap, type_text

SWIPE_MOVE_DURATION_MS = 300

SwipeDirection = Literal["up", "down", "left", "right"]
SwipeDistance = Literal["short", "normal"]


def swipe_from(
    device_id: str, coords: tuple[int, int],
    up: int = 0, down: int = 0, left: int = 0, right: int = 0,
    duration: int = SWIPE_MOVE_DURATION_MS,
) -> dict:
    x, y = coords
    return move(device_id, coords, (x - left + right, y - up + down), is_pressed=True, duration=duration)


class Clicker:
    """Convenient tap/swipe/type wrapper around the low-level API."""

    def __init__(self, device_id: str):
        """Initialize mouse controller.

        Args:
            device_id: Device ID
        """
        self.device_id = device_id

    @overload
    def swipe(
        self,
        direction: SwipeDirection,
        /,
        *,
        distance: SwipeDistance | None = None,
        aspect_ratio: float | None = None,
    ) -> dict: ...

    @overload
    def swipe(
        self, coords: tuple[int, int],
        up: int = 0, down: int = 0, left: int = 0, right: int = 0,
        duration: int = SWIPE_MOVE_DURATION_MS,
    ) -> dict: ...

    def swipe(self, coords: tuple[int, int] | SwipeDirection, *args: Any, **kwargs: Any) -> dict:
        """Swipe in a direction or from exact coordinates.

        Pass a direction such as swipe("up", distance="short") for a
        randomized server gesture. The default distance is "normal".
        The aspect ratio is screen width divided by height and defaults to
        the server's portrait profile.

        Pass coordinates such as swipe((x, y), up=6000, duration=300)
        for a straight swipe with offsets in HID units and duration in ms.
        """
        if isinstance(coords, str):
            return swipe_direction(self.device_id, coords, *args, **kwargs)
        return swipe_from(self.device_id, coords, *args, **kwargs)

    def click(
        self,
        coords: tuple[int, int],
        duration: int = 100,
        *,
        randomize: bool = False,
        aspect_ratio: float | None = None,
    ) -> dict:
        """Tap at coordinates (combined move+click in one call).

        Args:
            coords: Tap coordinates tuple (x, y)
            duration: Hold duration in milliseconds
            randomize: Apply the server's variation to position and hold duration
            aspect_ratio: Screen width divided by height for randomized taps
        """
        return tap(self.device_id, coords, duration=duration, randomize=randomize, aspect_ratio=aspect_ratio)

    def double_tap(
        self,
        coords: tuple[int, int],
        duration: int = 50,
        gap: int = 100,
        *,
        randomize: bool = False,
        aspect_ratio: float | None = None,
    ) -> dict:
        """Double-tap at coordinates with timing handled by the device.

        Args:
            coords: Tap coordinates tuple (x, y)
            duration: Hold duration of each tap in milliseconds
            gap: Pause between taps in milliseconds
            randomize: Apply the server's variation to the shared position, hold duration, and pause
            aspect_ratio: Screen width divided by height for randomized taps
        """
        return double_tap(self.device_id, coords, duration=duration, gap=gap, randomize=randomize, aspect_ratio=aspect_ratio)

    def type(self, text: str):
        """Type text on the device.

        Args:
            text: Text string to type
        """
        result = type_text(self.device_id, text)
        return result

    def key_combo(self, codes: list[str]):
        """Press a key combination (e.g. ["MetaLeft", "Space"] to open Spotlight).

        Args:
            codes: List of key codes, pressed in order and released in reverse
        """
        return key_combo(self.device_id, codes)

    def get_screenshot(self):
        """Fetch the latest JPEG frame from the device stream.

        Returns:
            Raw JPEG bytes, or None if the stream has no frame available.
        Raises:
            requests.HTTPError: on 401/403 (auth problem, not a missing frame).
        """
        return get_screenshot(self.device_id)
