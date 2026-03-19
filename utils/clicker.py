from .api_helper import move, click, type_text


class Clicker:
    """Tracks cursor position and provides convenient methods."""

    def __init__(self, device_id: str):
        """Initialize mouse controller.

        Args:
            device_id: Device ID
        """
        self.device_id = device_id
        self.current_coords: tuple[int, int] = (0, 0)

    def swipe(
        self, coords: tuple[int, int],
        up: int = 0, down: int = 0, left: int = 0, right: int = 0,
        duration: int = 300,
    ):
        """Swipe from coords in the specified direction.

        Args:
            coords: Start coordinates tuple (x, y)
            up: Swipe up distance in pixels
            down: Swipe down distance in pixels
            left: Swipe left distance in pixels
            right: Swipe right distance in pixels
            duration: Swipe duration in milliseconds
        """
        # Calculate end position and perform swipe
        start_x, start_y = coords
        end_x = start_x - left + right
        end_y = start_y - up + down
        end_coords = (end_x, end_y)

        result = move(
            self.device_id,
            coords,
            end_coords,
            is_pressed=True,
            duration=duration
        )
        self.current_coords = end_coords
        return result

    def click(self, coords: tuple[int, int], duration: int = 100):
        """Move to coordinates and click.

        Args:
            coords: Click coordinates tuple (x, y)
            duration: Click duration in milliseconds
        """
        # Move to click position first
        move(
            self.device_id,
            self.current_coords,
            coords,
            is_pressed=False,
            duration=0
        )
        self.current_coords = coords

        # Perform click
        result = click(self.device_id, duration=duration)
        return result

    def type(self, text: str):
        """Type text on the device.

        Args:
            text: Text string to type
        """
        result = type_text(self.device_id, text)
        return result
