from .api_helper import move, tap, type_text, key_combo, get_screenshot


class Clicker:
    """Convenient tap/swipe/type wrapper around the low-level API."""

    def __init__(self, device_id: str):
        """Initialize mouse controller.

        Args:
            device_id: Device ID
        """
        self.device_id = device_id

    def swipe(
        self, coords: tuple[int, int],
        up: int = 0, down: int = 0, left: int = 0, right: int = 0,
        duration: int = 300,
    ):
        """Swipe from coords in the specified direction.

        Args:
            coords: Start coordinates tuple (x, y)
            up: Swipe up distance in HID units (0-32767)
            down: Swipe down distance in HID units
            left: Swipe left distance in HID units
            right: Swipe right distance in HID units
            duration: Swipe duration in milliseconds
        """
        # Calculate end position and perform swipe
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

    def click(self, coords: tuple[int, int], duration: int = 100):
        """Tap at coordinates (combined move+click in one call).

        Args:
            coords: Tap coordinates tuple (x, y)
            duration: Hold duration in milliseconds
        """
        return tap(self.device_id, coords, duration=duration)

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
