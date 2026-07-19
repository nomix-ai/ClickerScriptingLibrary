"""post_comment: cached fast-path and first-call coordinate caching (no network)."""

from unittest.mock import MagicMock

from nomix_clicker import post_comment
from nomix_clicker import actions as actions_mod
from nomix_clicker.recognition import Element, Screen


def test_post_comment_uses_cached_coords(monkeypatch, fake_clicker):
    # With a populated cache, it must NOT re-parse the screen.
    parse_mock = MagicMock()
    monkeypatch.setattr(actions_mod, "parse_screen", parse_mock)
    monkeypatch.setattr(actions_mod, "sleep", lambda s: None)

    c = fake_clicker
    cache = {"comment_input": (10, 20), "comment_submit": (30, 40)}
    assert post_comment(c, "hi", ["add a comment"], "send", cached_coords=cache) is True

    parse_mock.assert_not_called()
    assert c.typed == ["hi"]
    assert c.clicked == [(10, 20), (30, 40)]  # input, submit


def test_post_comment_first_call_populates_cache(monkeypatch, fake_clicker):
    input_el = Element(0, "input", "Add a comment", True, (100, 200), (0, 0, 0, 0), "bottom-center")
    submit_el = Element(1, "button", "Send", True, (300, 400), (0, 0, 0, 0), "bottom-right")
    screen1 = Screen("App", "", [input_el], 0.0)     # first parse: find input
    screen2 = Screen("App", "", [submit_el], 0.0)    # second parse: find submit

    monkeypatch.setattr(actions_mod, "parse_screen", MagicMock(side_effect=[screen1, screen2]))
    monkeypatch.setattr(actions_mod, "sleep", lambda s: None)

    c = fake_clicker
    cache = {}
    assert post_comment(c, "nice", ["add a comment"], "send", cached_coords=cache) is True

    assert cache["comment_input"] == (100, 200)
    assert cache["comment_submit"] == (300, 400)
    assert c.typed == ["nice"]


def test_post_comment_returns_false_when_input_missing(monkeypatch, fake_clicker):
    screen = Screen("App", "", [], 0.0)              # no input field present
    monkeypatch.setattr(actions_mod, "parse_screen", MagicMock(return_value=screen))
    monkeypatch.setattr(actions_mod, "sleep", lambda s: None)

    c = fake_clicker
    assert post_comment(c, "x", ["add a comment"], "send", cached_coords={}) is False
    assert c.typed == []


def test_post_comment_accepts_tuple_submit_keyword(monkeypatch, fake_clicker):
    input_el = Element(0, "input", "Add a comment", True, (100, 200), (0, 0, 0, 0), "bottom-center")
    submit_el = Element(1, "button", "Send", True, (300, 400), (0, 0, 0, 0), "bottom-right")
    screens = [Screen("App", "", [input_el], 0.0), Screen("App", "", [submit_el], 0.0)]
    monkeypatch.setattr(actions_mod, "parse_screen", MagicMock(side_effect=screens))
    monkeypatch.setattr(actions_mod, "sleep", lambda s: None)
    assert post_comment(fake_clicker, "hi", ["add a comment"], ("send", "post")) is True


def test_post_comment_accepts_string_input_keywords(monkeypatch, fake_clicker):
    input_el = Element(0, "input", "Add a comment", True, (100, 200), (0, 0, 0, 0), "bottom-center")
    submit_el = Element(1, "button", "Send", True, (300, 400), (0, 0, 0, 0), "bottom-right")
    screens = [Screen("App", "", [input_el], 0.0), Screen("App", "", [submit_el], 0.0)]
    monkeypatch.setattr(actions_mod, "parse_screen", MagicMock(side_effect=screens))
    monkeypatch.setattr(actions_mod, "sleep", lambda s: None)
    c = fake_clicker
    assert post_comment(c, "hi", "add a comment", "send") is True
    assert c.clicked[0] == (100, 200)  # tapped the input, not a per-character match
