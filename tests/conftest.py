"""Shared test doubles."""

import pytest


class FakeClicker:
    """Records taps and typed text; every action reports success."""

    def __init__(self):
        self.clicked = []
        self.typed = []

    def click(self, coords, duration=100):
        self.clicked.append(coords)
        return {"success": True}

    def type(self, text):
        self.typed.append(text)
        return {"success": True}

    def swipe(self, *args, **kwargs):
        return {"success": True}


@pytest.fixture
def fake_clicker():
    return FakeClicker()
