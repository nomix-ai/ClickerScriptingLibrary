from utils.api_helper import move, click


class Clicker:
    """Tracks cursor position and provides convenient methods."""

    def __init__(self, device_id):
        """Initialize mouse controller.
        
        Args:
            device_id: Device ID
        """
        self.device_id = device_id
        self.current_coords = (0, 0)

    def swipe(self, coords, up=0, down=0, left=0, right=0, duration=300):
        """Swipe from coords in the specified direction.
        
        Args:
            coords: Start coordinates tuple (x, y)
            up: Swipe up distance in pixels
            down: Swipe down distance in pixels
            left: Swipe left distance in pixels
            right: Swipe right distance in pixels
            duration: Swipe duration in milliseconds
        """
        # Move to initial position first
        move(
            self.device_id,
            self.current_coords,
            coords,
            is_pressed=False,
            duration=duration
        )
        self.current_coords = coords

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

    def click(self, duration=300):
        """Click at current cursor position.

        Args:
            duration: Click duration in milliseconds
        """
        # Perform click
        result = click(self.device_id, duration=duration)
        return result

    def move_to(self, coords, duration=0):
        """Move cursor to coordinates.

        Args:
            coords: Target coordinates tuple (x, y)
            duration: Movement duration in milliseconds
        """
        result = move(
            self.device_id,
            self.current_coords,
            coords,
            is_pressed=False,
            duration=duration
        )
        self.current_coords = coords
        return result

