"""High-level action helpers that need no network."""

import pytest

from nomix_clicker import chance_tap, is_ad
from nomix_clicker.recognition import Element, Screen


def _screen(description="", elements=()):
    return Screen(app_name="App", description=description, elements=list(elements), latency=0.0)


def test_is_ad_detects_keyword_in_description():
    assert is_ad(_screen(description="Sponsored content, shop now")) is True


def test_is_ad_false_for_normal_screen():
    assert is_ad(_screen(description="A photo of a cat")) is False


def test_chance_tap_never_taps_with_zero_chance(fake_clicker):
    el = Element(0, "button", "AC", True, (1, 2), (0, 0, 0, 0), "center")
    screen = _screen(elements=[el])
    fake = fake_clicker
    assert chance_tap(fake, screen, "ac", 0.0) is False
    assert fake.clicked == []


def test_chance_tap_always_taps_with_full_chance(fake_clicker):
    el = Element(0, "button", "AC", True, (1, 2), (0, 0, 0, 0), "center")
    screen = _screen(elements=[el])
    fake = fake_clicker
    assert chance_tap(fake, screen, "ac", 1.0) is True
    assert fake.clicked == [(1, 2)]


def test_open_app_goes_home_then_searches_spotlight(monkeypatch, fake_clicker):
    from nomix_clicker import actions as actions_mod

    monkeypatch.setattr(actions_mod, "sleep", lambda s: None)
    monkeypatch.setattr(actions_mod, "parse_screen", lambda c: _screen())
    assert actions_mod.open_app(fake_clicker, "App") is not None
    assert fake_clicker.combos == [
        ["MetaLeft", "KeyH"], ["MetaLeft", "Space"], ["MetaLeft", "KeyA"], ["Backspace"], ["Enter"],
    ]
    assert fake_clicker.typed == ["App"]


def test_open_app_retries_until_the_app_is_in_front(monkeypatch, fake_clicker):
    from nomix_clicker import actions as actions_mod

    screens = [Screen("Home Screen", "", [], 0.0), _screen()]
    monkeypatch.setattr(actions_mod, "sleep", lambda s: None)
    monkeypatch.setattr(actions_mod, "parse_screen", lambda c: screens.pop(0))
    assert actions_mod.open_app(fake_clicker, "App", retries=2).app_name == "App"
    assert fake_clicker.typed == ["App", "App"]


def test_open_app_stops_an_attempt_when_a_step_is_refused(monkeypatch, fake_clicker):
    from nomix_clicker import actions as actions_mod

    monkeypatch.setattr(actions_mod, "sleep", lambda s: None)
    monkeypatch.setattr(fake_clicker, "key_combo", lambda codes: {"success": False})
    monkeypatch.setattr(actions_mod, "parse_screen", lambda c: pytest.fail("no screen without a launch"))
    assert actions_mod.open_app(fake_clicker, "App", retries=2) is None
    assert fake_clicker.typed == []


def test_close_app_unconfirmed_when_screen_unavailable(monkeypatch, fake_clicker):
    from nomix_clicker.actions import close_app
    from nomix_clicker import actions as actions_mod

    monkeypatch.setattr(actions_mod, "parse_screen", lambda c: None)
    monkeypatch.setattr(actions_mod, "sleep", lambda s: None)
    assert close_app(fake_clicker, retries=2) is False  # never confirmed
