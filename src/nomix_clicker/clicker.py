from math import cos, sin, tau
from random import triangular, uniform
from typing import Literal, overload

from .api_helper import double_tap, get_screenshot, key_combo, move, swipe_direction, tap, type_text

HID_MAX = 32767
DEFAULT_SCREEN_ASPECT_RATIO = 1170 / 2532
SWIPE_MOVE_DURATION_MS = 300
TAP_POSITION_RADIUS_FRACTION = 1.5 / 390
TAP_DURATION_VARIATION_MS = 20
DOUBLE_TAP_DURATION_VARIATION_MS = 10
DOUBLE_TAP_GAP_VARIATION_MS = 15
MAX_TAP_DURATION_MS = 10000
MAX_DOUBLE_TAP_GAP_MS = 500

SwipeDirection = Literal["up", "down", "left", "right"]
SwipeDistance = Literal["short", "normal"]


def vary_tap_position(coords: tuple[int, int], aspect_ratio: float) -> tuple[int, int]:
    if not 0.25 <= aspect_ratio <= 4.0:
        raise ValueError("aspect_ratio must be between 0.25 and 4.0")
    x, y = coords
    if type(x) is not int or type(y) is not int or not (0 <= x <= HID_MAX and 0 <= y <= HID_MAX):
        return coords
    radius = HID_MAX * triangular(0, TAP_POSITION_RADIUS_FRACTION, TAP_POSITION_RADIUS_FRACTION / 2)
    angle = uniform(0, tau)
    x += int(radius * cos(angle) / max(1.0, aspect_ratio))
    y += int(radius * sin(angle) / max(1.0, 1 / aspect_ratio))
    return max(0, min(HID_MAX, x)), max(0, min(HID_MAX, y))


def vary_duration(duration_ms: int, variation_ms: int, maximum_ms: int) -> int:
    if type(duration_ms) is not int or not 0 <= duration_ms <= maximum_ms:
        return duration_ms
    minimum = max(0, duration_ms - variation_ms)
    maximum = min(maximum_ms, duration_ms + variation_ms)
    return round(triangular(minimum, maximum, duration_ms))


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
        distance: SwipeDistance = "normal",
        aspect_ratio: float = DEFAULT_SCREEN_ASPECT_RATIO,
    ) -> dict: ...

    @overload
    def swipe(
        self, coords: tuple[int, int],
        up: int = 0, down: int = 0, left: int = 0, right: int = 0,
        duration: int = SWIPE_MOVE_DURATION_MS,
    ) -> dict: ...

    def swipe(
        self, coords: tuple[int, int] | SwipeDirection,
        up: int = 0, down: int = 0, left: int = 0, right: int = 0,
        duration: int = SWIPE_MOVE_DURATION_MS,
        *,
        distance: SwipeDistance | None = None,
        aspect_ratio: float | None = None,
    ) -> dict:
        """Swipe in a direction or from exact coordinates.

        Pass a direction such as swipe("up", distance="short") for a
        randomized server gesture. The default distance is "normal".
        The aspect ratio is screen width divided by height.

        Pass coordinates such as swipe((x, y), up=6000, duration=300)
        for a straight swipe with offsets in HID units and duration in ms.
        """
        if isinstance(coords, str):
            if any((up, down, left, right)) or duration != SWIPE_MOVE_DURATION_MS:
                raise TypeError("Coordinate offsets and duration require start coordinates")
            return swipe_direction(
                self.device_id,
                coords,
                "normal" if distance is None else distance,
                DEFAULT_SCREEN_ASPECT_RATIO if aspect_ratio is None else aspect_ratio,
            )

        if distance is not None or aspect_ratio is not None:
            raise TypeError("distance and aspect_ratio require a swipe direction")
        start_x, start_y = coords
        end_x = start_x - left + right
        end_y = start_y - up + down
        end_coords = (end_x, end_y)

        return move(
            self.device_id,
            coords,
            end_coords,
            is_pressed=True,
            duration=duration
        )

    def click(
        self,
        coords: tuple[int, int],
        duration: int = 100,
        *,
        randomize: bool = False,
        aspect_ratio: float = DEFAULT_SCREEN_ASPECT_RATIO,
    ) -> dict:
        """Tap at coordinates (combined move+click in one call).

        Args:
            coords: Tap coordinates tuple (x, y)
            duration: Hold duration in milliseconds
            randomize: Vary position and hold duration around the requested values
            aspect_ratio: Screen width divided by height, used for position variation
        """
        if randomize:
            coords = vary_tap_position(coords, aspect_ratio)
            duration = vary_duration(duration, TAP_DURATION_VARIATION_MS, MAX_TAP_DURATION_MS)
        return tap(self.device_id, coords, duration=duration)

    def double_tap(
        self,
        coords: tuple[int, int],
        duration: int = 50,
        gap: int = 100,
        *,
        randomize: bool = False,
        aspect_ratio: float = DEFAULT_SCREEN_ASPECT_RATIO,
    ) -> dict:
        """Double-tap at coordinates with timing handled by the device.

        Args:
            coords: Tap coordinates tuple (x, y)
            duration: Hold duration of each tap in milliseconds
            gap: Pause between taps in milliseconds
            randomize: Vary the shared position, hold duration, and pause
            aspect_ratio: Screen width divided by height, used for position variation
        """
        if randomize:
            coords = vary_tap_position(coords, aspect_ratio)
            duration = vary_duration(duration, DOUBLE_TAP_DURATION_VARIATION_MS, MAX_TAP_DURATION_MS)
            gap = vary_duration(gap, DOUBLE_TAP_GAP_VARIATION_MS, MAX_DOUBLE_TAP_GAP_MS)
        return double_tap(self.device_id, coords, duration=duration, gap=gap)

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
