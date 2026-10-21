from types import TracebackType

from .api_helper import get_screenshot
from .control import ControlSession


class Clicker:
    """One explicit control session; commands are never replayed after disconnect."""

    device_id: str
    control: ControlSession

    def __init__(self, device_id: str, *, timeout: float = 10):
        self.device_id = device_id
        self.control = ControlSession(device_id, timeout=timeout)

    def __enter__(self) -> "Clicker":
        self.connect()
        return self

    def __exit__(self, kind: type | None, value: BaseException | None, traceback: TracebackType | None) -> None:
        self.close()

    def connect(self, *, takeover: bool = False) -> None:
        self.control.connect()
        try:
            self.control.request("control.acquire", {"takeover": takeover})
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        self.control.close()

    def swipe(self, coords: tuple[int, int], up: int = 0, down: int = 0,
              left: int = 0, right: int = 0, duration: int = 300) -> dict:
        x, y = coords
        return self.control.request("input.move", {
            "start_left": x, "start_top": y, "end_left": x - left + right,
            "end_top": y - up + down, "pressed": True, "duration": duration,
        }, timeout=self.control.timeout + duration / 1000 + 1)

    def click(self, coords: tuple[int, int], duration: int = 100) -> dict:
        x, y = coords
        return self.control.request("input.tap", {"left": x, "top": y, "duration": duration},
                                    timeout=self.control.timeout + duration / 1000)

    def double_tap(self, coords: tuple[int, int], duration: int = 50, gap: int = 100) -> dict:
        x, y = coords
        return self.control.request("input.doubleTap", {"left": x, "top": y, "duration": duration, "gap": gap},
                                    timeout=self.control.timeout + (2 * duration + gap) / 1000)

    def type(self, text: str, delay: int = 20) -> dict:
        return self.control.request("input.text", {"text": text, "delay": delay}, timeout=self.control.timeout + 132)

    def key_combo(self, codes: list[str]) -> dict:
        return self.control.request("input.keyCombo", {"codes": codes})

    def restart(self) -> dict:
        return self.control.request("device.restart")

    def get_screenshot(self) -> bytes | None:
        return get_screenshot(self.device_id)
