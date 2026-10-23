"""Shared test doubles."""

import pytest


class FakeClicker:
    """Records taps and typed text; every action reports success."""

    def __init__(self):
        self.clicked = []
        self.typed = []

    def click(self, coords, duration=100):
        self.clicked.append(coords)
        return {"status": "sent", "device_acknowledged": False}

    def type(self, text):
        self.typed.append(text)
        return {"status": "sent", "device_acknowledged": False}

    def swipe(self, *args, **kwargs):
        return {"status": "sent", "device_acknowledged": False}


@pytest.fixture
def fake_clicker():
    return FakeClicker()
