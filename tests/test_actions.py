"""High-level action helpers that need no network."""

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


def test_close_app_unconfirmed_when_screen_unavailable(monkeypatch, fake_clicker):
    from nomix_clicker.actions import close_app
    from nomix_clicker import actions as actions_mod

    monkeypatch.setattr(actions_mod, "parse_screen", lambda c: None)
    monkeypatch.setattr(actions_mod, "sleep", lambda s: None)
    assert close_app(fake_clicker, retries=2) is False  # never confirmed
