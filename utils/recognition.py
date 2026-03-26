import time
from dataclasses import dataclass

import requests

from .api_helper import get_screen_state
from .clicker import Clicker


@dataclass(frozen=True)
class Element:
    """A single UI element on screen."""

    idx: int
    type: str
    content: str
    interactivity: bool
    center: tuple[int, int]
    bbox: tuple[int, int, int, int]
    location: str

    @property
    def is_interactive(self) -> bool:
        return self.interactivity

    @property
    def x(self) -> int:
        return self.center[0]

    @property
    def y(self) -> int:
        return self.center[1]

    def __str__(self) -> str:
        return f"[{self.type}] {self.content} @ {self.center}"

    @classmethod
    def from_dict(cls, d: dict) -> "Element":
        return cls(
            idx=d.get("idx", 0),
            type=d.get("type", ""),
            content=d.get("content", ""),
            interactivity=bool(d.get("interactivity", False)),
            center=tuple(d.get("center", (0, 0))),
            bbox=tuple(d.get("bbox", ())),
            location=d.get("location", ""),
        )


@dataclass
class Screen:
    """Snapshot of the device screen."""

    app_name: str
    description: str
    elements: list[Element]
    latency: float

    def find(self, *keywords: str, interactive_only: bool = True) -> tuple | None:
        """Find first element matching keyword(s). Returns center coords."""
        for kw in keywords:
            kw_lower = kw.lower()
            for el in self.elements:
                if kw_lower in el.content.lower():
                    if interactive_only and not el.is_interactive:
                        continue
                    return el.center
        return None

    def find_and_click(self, clicker: Clicker, *keywords: str, interactive_only: bool = True) -> bool:
        """Find element by keywords and click it. Returns True if clicked."""
        coords = self.find(*keywords, interactive_only=interactive_only)
        if not coords:
            return False
        clicker.click(coords)
        return True

    def contains(self, *keywords: str) -> bool:
        """Check if any keyword appears in description or any element (substring)."""
        for kw in keywords:
            kw_lower = kw.lower()
            if kw_lower in self.description.lower():
                return True
            if any(kw_lower in el.content.lower() for el in self.elements):
                return True
        return False

    @classmethod
    def from_dict(cls, d: dict) -> "Screen":
        return cls(
            app_name=d.get("app_name", ""),
            description=d.get("screen_description", ""),
            elements=[Element.from_dict(e) for e in d.get("elements", [])],
            latency=d.get("latency", 0.0),
        )


def parse_screen(device: "str | Clicker") -> Screen | None:
    """Get current screen state. Returns None on error."""
    device_id = device.device_id if isinstance(device, Clicker) else device
    print("Parsing screen...")
    try:
        start = time.monotonic()
        screen = Screen.from_dict(get_screen_state(device_id))
        elapsed = time.monotonic() - start
        print(
            f"Parsing done in {elapsed:.1f}s | app={screen.app_name}"
            f" | {screen.description} | {len(screen.elements)} elements"
        )
        return screen
    except (requests.RequestException, TimeoutError) as e:
        print(f"ERROR: parse_screen failed: {e}")
        return None
