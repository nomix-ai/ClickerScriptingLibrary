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
    bbox: list
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
            bbox=d.get("bbox", []),
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


def get_screen(device_id: str) -> Screen:
    """Get current screen state as a Screen object."""
    raw = get_screen_state(device_id)
    return Screen.from_dict(raw)
