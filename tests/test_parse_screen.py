"""parse_screen success/retry/failure behavior — get_screen_state mocked."""

from unittest.mock import MagicMock

import requests

from nomix_clicker import Clicker, Screen, parse_screen
from nomix_clicker import recognition as rec

SCREEN = {"app_name": "Calculator", "screen_description": "desc", "elements": [], "latency": 0.1}


def test_parse_screen_success(monkeypatch):
    monkeypatch.setattr(rec, "get_screen_state", MagicMock(return_value=SCREEN))
    screen = parse_screen("dev")
    assert isinstance(screen, Screen)
    assert screen.app_name == "Calculator"


def test_parse_screen_accepts_clicker(monkeypatch):
    mock = MagicMock(return_value=SCREEN)
    monkeypatch.setattr(rec, "get_screen_state", mock)
    parse_screen(Clicker("dev-77"))
    mock.assert_called_once_with("dev-77")   # device_id extracted from the Clicker


def test_parse_screen_retries_then_succeeds(monkeypatch):
    mock = MagicMock(side_effect=[requests.RequestException("boom"), SCREEN])
    monkeypatch.setattr(rec, "get_screen_state", mock)
    screen = parse_screen("dev", retries=3, retry_delay=0)
    assert screen is not None
    assert mock.call_count == 2


def test_parse_screen_returns_none_after_all_retries(monkeypatch):
    mock = MagicMock(side_effect=requests.RequestException("down"))
    monkeypatch.setattr(rec, "get_screen_state", mock)
    assert parse_screen("dev", retries=2, retry_delay=0) is None
    assert mock.call_count == 2


def test_parse_screen_does_not_retry_auth_errors(monkeypatch):
    err = requests.HTTPError("401 Client Error")
    err.response = MagicMock(status_code=401)
    mock = MagicMock(side_effect=err)
    monkeypatch.setattr(rec, "get_screen_state", mock)
    assert parse_screen("dev", retries=3, retry_delay=0) is None
    assert mock.call_count == 1   # no pointless retries on auth/quota errors
