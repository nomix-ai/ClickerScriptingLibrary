"""Clicker swipe math and tap dispatch (api_helper mocked)."""

from unittest.mock import Mock

import pytest

from nomix_clicker import Clicker
from nomix_clicker import api_helper
from nomix_clicker import clicker as clicker_mod


@pytest.fixture
def gesture_post(monkeypatch: pytest.MonkeyPatch) -> Mock:
    response = Mock()
    response.json.return_value = {"success": True}
    post = Mock(return_value=response)
    monkeypatch.setattr(api_helper, "get_api_url", lambda: "https://example.invalid/clicker/v1")
    monkeypatch.setattr(api_helper.session, "post", post)
    return post


def _record(monkeypatch):
    calls = []
    monkeypatch.setattr(clicker_mod, "move",
                        lambda *a, **k: calls.append(("move", a, k)) or {"success": True})
    monkeypatch.setattr(clicker_mod, "tap",
                        lambda *a, **k: calls.append(("tap", a, k)) or {"success": True})
    monkeypatch.setattr(clicker_mod, "double_tap",
                        lambda *a, **k: calls.append(("double_tap", a, k)) or {"success": True})
    return calls


def test_swipe_computes_end_coords(monkeypatch):
    calls = _record(monkeypatch)
    c = Clicker("dev")
    c.swipe(coords=(10000, 10000), up=6000, duration=300)
    # end_y = start_y - up = 4000; end_x unchanged
    _, args, kwargs = calls[0]
    device_id, start, end = args
    assert device_id == "dev"
    assert start == (10000, 10000)
    assert end == (10000, 4000)
    assert kwargs == {"is_pressed": True, "duration": 300, "screen": False}


def test_swipe_combines_directions(monkeypatch):
    calls = _record(monkeypatch)
    c = Clicker("dev")
    c.swipe((10000, 10000), down=2000, right=3000)
    _, args, _ = calls[0]
    _, _, end = args
    assert end == (13000, 12000)  # x + right, y + down


@pytest.mark.parametrize(
    ("options", "payload"),
    [
        ({}, {"direction": "up"}),
        ({"distance": "short"}, {"direction": "up", "distance": "short"}),
    ],
)
def test_directional_swipe_sends_profile_parameters(gesture_post: Mock, options: dict, payload: dict) -> None:
    assert Clicker("dev").swipe("up", **options) == {"success": True}
    gesture_post.assert_called_once_with(
        "https://example.invalid/clicker/v1/dev/swipe", json=payload, timeout=api_helper.COMMAND_TIMEOUT,
    )


@pytest.mark.parametrize(
    ("start", "options"),
    [
        ("up", {"duration": 300}),
        ("up", {"up": 0}),
        ("up", {"duration": None}),
        ((10000, 10000), {"distance": "short"}),
    ],
)
def test_swipe_rejects_parameters_from_the_other_mode(gesture_post: Mock, start: str | tuple[int, int], options: dict) -> None:
    with pytest.raises(TypeError):
        Clicker("dev").swipe(start, **options)
    gesture_post.assert_not_called()


@pytest.mark.parametrize(
    ("method", "route", "timing"),
    [("click", "tap", {"duration": 100}), ("double_tap", "double-tap", {"duration": 50, "gap": 100})],
)
@pytest.mark.parametrize(
    ("options", "extra"),
    [
        ({}, {}),
        ({"randomize": True}, {"randomize": True}),
    ],
)
def test_tap_variation_is_an_opt_in_server_parameter(
    gesture_post: Mock, method: str, route: str, timing: dict, options: dict, extra: dict,
) -> None:
    gesture = getattr(Clicker("dev"), method)
    assert gesture((500, 700), **options) == {"success": True}
    payload = {"left": 500, "top": 700, **timing, **extra}
    gesture_post.assert_called_once_with(
        f"https://example.invalid/clicker/v1/dev/{route}", json=payload, timeout=api_helper.COMMAND_TIMEOUT,
    )


@pytest.mark.parametrize(
    ("action", "route", "payload"),
    [
        (lambda c: c.click((500, 700), screen=True), "tap", {"left": 500, "top": 700, "duration": 100}),
        (lambda c: c.swipe("up", screen=True), "swipe", {"direction": "up"}),
        (lambda c: c.type("hi", screen=True), "keyboard/type", {"text": "hi"}),
        (lambda c: c.show_keyboard(screen=True), "keyboard/show", None),
    ],
)
def test_screen_option_asks_for_a_fresh_screen(gesture_post: Mock, action, route: str, payload: dict | None) -> None:
    action(Clicker("dev"))
    gesture_post.assert_called_once_with(
        f"https://example.invalid/clicker/v1/dev/{route}?screen=true", json=payload, timeout=api_helper.COMMAND_TIMEOUT,
    )


def test_airplane_mode_pulse_sends_the_switch_position(gesture_post: Mock) -> None:
    api_helper.airplane_mode_pulse("dev", (6523, 6689))
    gesture_post.assert_called_once_with(
        "https://example.invalid/clicker/v1/dev/airplane-mode/pulse",
        json={"left": 6523, "top": 6689}, timeout=api_helper.COMMAND_TIMEOUT,
    )


@pytest.mark.parametrize(("delay", "payload"), [(0, {"text": "hi"}), (120, {"text": "hi", "delay": 120})])
def test_type_waits_for_the_server_typing_deadline(gesture_post: Mock, delay: int, payload: dict) -> None:
    Clicker("dev").type("hi", delay)
    gesture_post.assert_called_once_with(
        "https://example.invalid/clicker/v1/dev/keyboard/type", json=payload, timeout=api_helper.COMMAND_TIMEOUT,
    )


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
