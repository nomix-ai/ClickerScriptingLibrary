import time
from dataclasses import dataclass
from typing import Self

from .api_helper import get_screen_state


@dataclass(frozen=True)
class Element:
    """A single UI element on screen."""

    idx: int
    type: str
    content: str
    interactivity: bool
    center: tuple
    bbox: tuple
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
    def from_dict(cls, d: dict) -> Self:
        return cls(
            idx=d.get("idx", 0),
            type=d.get("type", ""),
            content=d.get("content") or "",
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

    def find(self, keyword: str, *, interactive_only: bool = True) -> Element | None:
        """Find first element whose content contains keyword (case-insensitive)."""
        kw = keyword.lower()
        for el in self.elements:
            if kw in el.content.lower():
                if interactive_only and not el.is_interactive:
                    continue
                return el
        return None

    def find_any(self, keywords: list[str], *, interactive_only: bool = True) -> Element | None:
        """Find first element matching any of the keywords."""
        for kw in keywords:
            el = self.find(kw, interactive_only=interactive_only)
            if el:
                return el
        return None

    def contains(self, keyword: str) -> bool:
        """Check if keyword appears in description or any element (substring)."""
        kw = keyword.lower()
        if kw in self.description.lower():
            return True
        return any(kw in el.content.lower() for el in self.elements)

    def contains_any(self, keywords: list[str]) -> bool:
        """Check if any keyword appears anywhere on screen."""
        return any(self.contains(kw) for kw in keywords)

    def find_all(self, keyword: str, *, interactive_only: bool = False) -> list[Element]:
        """Find all elements whose content contains keyword."""
        kw = keyword.lower()
        return [
            el for el in self.elements
            if kw in el.content.lower()
            and (not interactive_only or el.is_interactive)
        ]

    @classmethod
    def from_dict(cls, d: dict) -> Self:
        return cls(
            app_name=d.get("app_name", ""),
            description=d.get("screen_description", ""),
            elements=[Element.from_dict(e) for e in d.get("elements", [])],
            latency=d.get("latency", 0.0),
        )


def get_screen(device_id: str, context: str = "") -> Screen:
    """Get current screen state as a Screen object."""
    print(f"screen-state request ({context})..." if context else "screen-state request...")
    start = time.monotonic()
    screen = Screen.from_dict(get_screen_state(device_id))
    elapsed = time.monotonic() - start
    print(f"screen-state done in {elapsed:.1f}s | app={screen.app_name} | {screen.description} | {len(screen.elements)} elements")
    return screen
