from typing import Any, Literal, overload

from .api_helper import double_tap, get_screenshot, key_combo, move, show_keyboard, swipe_direction, tap, type_text

SWIPE_MOVE_DURATION_MS = 300

SwipeDirection = Literal["up", "down", "left", "right"]
SwipeDistance = Literal["short", "normal"]


def swipe_from(
    device_id: str, coords: tuple[int, int],
    up: int = 0, down: int = 0, left: int = 0, right: int = 0,
    duration: int = SWIPE_MOVE_DURATION_MS,
    *, screen: bool = False,
) -> dict:
    x, y = coords
    return move(device_id, coords, (x - left + right, y - up + down), is_pressed=True, duration=duration, screen=screen)


class Clicker:
    """Convenient tap/swipe/type wrapper around the low-level API.

    Every action takes screen=True to get a fresh "screen_state" in its result
    once the action has played out (one AI recognition request); turn it into a
    Screen with Screen.from_dict(result["screen_state"]) when it is not None.
    """

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
        screen: bool = False,
    ) -> dict: ...

    @overload
    def swipe(
        self, coords: tuple[int, int],
        up: int = 0, down: int = 0, left: int = 0, right: int = 0,
        duration: int = SWIPE_MOVE_DURATION_MS,
        *,
        screen: bool = False,
    ) -> dict: ...

    def swipe(self, coords: tuple[int, int] | SwipeDirection, *args: Any, **kwargs: Any) -> dict:
        """Swipe in a direction or from exact coordinates.

        Pass a direction such as swipe("up", distance="short") for a
        randomized server gesture. The default distance is "normal".

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
        screen: bool = False,
    ) -> dict:
        """Tap at coordinates (combined move+click in one call).

        Args:
            coords: Tap coordinates tuple (x, y)
            duration: Hold duration in milliseconds
            randomize: Apply the server's variation to position and hold duration
            screen: Return a fresh screen_state after the tap
        """
        return tap(self.device_id, coords, duration=duration, randomize=randomize, screen=screen)

    def double_tap(
        self,
        coords: tuple[int, int],
        duration: int = 50,
        gap: int = 100,
        *,
        randomize: bool = False,
        screen: bool = False,
    ) -> dict:
        """Double-tap at coordinates with timing handled by the device.

        Args:
            coords: Tap coordinates tuple (x, y)
            duration: Hold duration of each tap in milliseconds
            gap: Pause between taps in milliseconds
            randomize: Apply the server's variation to the shared position, hold duration, and pause
            screen: Return a fresh screen_state after the double tap
        """
        return double_tap(self.device_id, coords, duration=duration, gap=gap, randomize=randomize, screen=screen)

    def type(self, text: str, delay: int = 0, *, screen: bool = False) -> dict:
        """Type text on the device.

        Args:
            text: Text string to type (at most 180 s of typing)
            delay: Milliseconds between characters; 0 uses the fastest safe pace
            screen: Return a fresh screen_state after typing
        """
        return type_text(self.device_id, text, delay, screen=screen)

    def key_combo(self, codes: list[str], *, screen: bool = False) -> dict:
        """Press a key combination (e.g. ["MetaLeft", "Space"] to open Spotlight).

        Args:
            codes: Up to 4 key codes, pressed in order and released in reverse
            screen: Return a fresh screen_state after the combo
        """
        return key_combo(self.device_id, codes, screen=screen)

    def show_keyboard(self, *, screen: bool = False) -> dict:
        """Toggle the iOS on-screen keyboard, e.g. to tap emoji the hardware keyboard can't type."""
        return show_keyboard(self.device_id, screen=screen)

    def get_screenshot(self):
        """Fetch the latest JPEG frame from the device stream.

        Returns:
            Raw JPEG bytes, or None if the stream has no frame available.
        Raises:
            requests.HTTPError: on 401/403 (auth problem, not a missing frame).
        """
        return get_screenshot(self.device_id)
