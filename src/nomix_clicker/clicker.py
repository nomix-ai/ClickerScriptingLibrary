import math
from types import TracebackType

from .api_helper import get_screenshot, send_command
from .control import ControlError, ControlSession


class Clicker:
    """HTTP commands by default; a context holds exclusive control across a workflow."""

    device_id: str
    control: ControlSession | None
    timeout: float
    closed: bool

    def __init__(self, device_id: str, *, timeout: float = 10):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive")
        self.device_id = device_id
        self.control = None
        self.timeout = timeout
        self.closed = False

    def __enter__(self) -> "Clicker":
        self.connect()
        return self

    def __exit__(self, kind: type | None, value: BaseException | None, traceback: TracebackType | None) -> None:
        self.close()

    def connect(self, *, takeover: bool = False) -> None:
        if self.closed:
            raise ControlError(-32004, "Create a new Clicker after closing")
        if self.control is None:
            self.control = ControlSession(self.device_id, timeout=self.timeout)
        self.control.connect()
        try:
            self.control.request("control.acquire", {"takeover": takeover})
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        self.closed = True
        if self.control is not None:
            self.control.close()

    def request(self, method: str, params: dict | None = None, *, timeout: float | None = None) -> dict:
        if self.closed:
            raise ControlError(-32004, "Create a new Clicker after closing")
        if self.control is not None:
            return self.control.request(method, params, timeout=timeout)
        return send_command(self.device_id, method, params, timeout=self.timeout if timeout is None else timeout)

    def swipe(self, coords: tuple[int, int], up: int = 0, down: int = 0,
              left: int = 0, right: int = 0, duration: int = 300) -> dict:
        x, y = coords
        return self.request("move", {
            "start_left": x, "start_top": y, "end_left": x - left + right,
            "end_top": y - up + down, "is_pressed": True, "duration": duration,
        }, timeout=self.timeout + duration / 1000 + 1)

    def click(self, coords: tuple[int, int], duration: int = 100) -> dict:
        x, y = coords
        return self.request("tap", {"left": x, "top": y, "duration": duration},
                            timeout=self.timeout + duration / 1000)

    def double_tap(self, coords: tuple[int, int], duration: int = 50, gap: int = 100) -> dict:
        x, y = coords
        return self.request("double-tap", {"left": x, "top": y, "duration": duration, "gap": gap},
                            timeout=self.timeout + (2 * duration + gap) / 1000)

    def type(self, text: str, delay: int = 0) -> dict:
        return self.request("keyboard/type", {"text": text, "delay": delay}, timeout=self.timeout + 198)

    def key_combo(self, codes: list[str]) -> dict:
        return self.request("keyboard/combo", {"codes": codes})

    def restart(self) -> dict:
        return self.request("restart")

    def get_screenshot(self) -> bytes | None:
        return get_screenshot(self.device_id)
