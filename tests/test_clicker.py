from unittest.mock import MagicMock

import pytest

from nomix_clicker import Clicker, ControlError


def client() -> Clicker:
    clicker = Clicker("device")
    clicker.control = MagicMock(timeout=10)
    clicker.control.request.return_value = {"status": "sent", "device_acknowledged": False}
    return clicker


def test_context_acquires_without_takeover_and_releases_on_error():
    clicker = client()
    with pytest.raises(ValueError), clicker:
        raise ValueError("stop")
    clicker.control.connect.assert_called_once()
    clicker.control.request.assert_called_once_with("control.acquire", {"takeover": False})
    clicker.control.close.assert_called_once()


def test_busy_session_closes_without_sending_input():
    clicker = client()
    clicker.control.request.side_effect = ControlError(-32002, "busy")
    with pytest.raises(ControlError):
        clicker.connect()
    clicker.control.close.assert_called_once()
    assert clicker.control.request.call_count == 1


def test_swipe_uses_one_atomic_movement():
    clicker = client()
    clicker.swipe((10000, 10000), up=6000, right=3000)
    clicker.control.request.assert_called_once_with("input.move", {
        "start_left": 10000, "start_top": 10000, "end_left": 13000, "end_top": 4000,
        "pressed": True, "duration": 300,
    }, timeout=11.3)


def test_click_reports_sent_not_phone_execution():
    clicker = client()
    assert clicker.click((500, 700)) == {"status": "sent", "device_acknowledged": False}
    clicker.control.request.assert_called_once_with("input.tap", {"left": 500, "top": 700, "duration": 100}, timeout=10.1)


def test_errors_propagate_and_stop_the_callers_macro():
    clicker = client()
    clicker.control.request.side_effect = ControlError(-32007, "lost", "unknown")
    with pytest.raises(ControlError) as error:
        clicker.click((1, 2))
    assert error.value.outcome == "unknown"
