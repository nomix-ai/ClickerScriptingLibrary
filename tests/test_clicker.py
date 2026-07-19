"""Clicker swipe math and tap dispatch (api_helper mocked)."""

from nomix_clicker import Clicker
from nomix_clicker import clicker as clicker_mod


def _record(monkeypatch):
    calls = []
    monkeypatch.setattr(clicker_mod, "move",
                        lambda *a, **k: calls.append(("move", a, k)) or {"success": True})
    monkeypatch.setattr(clicker_mod, "tap",
                        lambda *a, **k: calls.append(("tap", a, k)) or {"success": True})
    return calls


def test_swipe_computes_end_coords(monkeypatch):
    calls = _record(monkeypatch)
    c = Clicker("dev")
    c.swipe((10000, 10000), up=6000, duration=300)
    # end_y = start_y - up = 4000; end_x unchanged
    _, args, kwargs = calls[0]
    device_id, start, end = args
    assert device_id == "dev"
    assert start == (10000, 10000)
    assert end == (10000, 4000)
    assert kwargs["is_pressed"] is True


def test_swipe_combines_directions(monkeypatch):
    calls = _record(monkeypatch)
    c = Clicker("dev")
    c.swipe((10000, 10000), down=2000, right=3000)
    _, args, _ = calls[0]
    _, _, end = args
    assert end == (13000, 12000)  # x + right, y + down


def test_click_taps_once(monkeypatch):
    calls = _record(monkeypatch)
    c = Clicker("dev")
    c.click((500, 700))
    assert len(calls) == 1
    kind, args, kwargs = calls[0]
    assert kind == "tap"
    assert args == ("dev", (500, 700))
    assert kwargs["duration"] == 100


def test_click_returns_action_result(monkeypatch):
    monkeypatch.setattr(clicker_mod, "tap",
                        lambda *a, **k: {"success": False, "message": "boom"})
    assert Clicker("dev").click((1, 2))["success"] is False


def test_device_id_stored():
    assert Clicker("abc123").device_id == "abc123"
