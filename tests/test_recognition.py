"""Screen/Element parsing and lookup helpers (no network)."""

from nomix_clicker import Element, Screen

SCREEN_DICT = {
    "app_name": "Calculator",
    "screen_description": "The Calculator app showing a numeric keypad and the result 0.",
    "latency": 1.2,
    "elements": [
        {"idx": 0, "type": "button", "content": "AC", "interactivity": True,
         "center": [100, 200], "bbox": [1, 2, 3, 4], "location": "top-left"},
        {"idx": 1, "type": "text", "content": "Portrait Orientation Locked", "interactivity": False,
         "center": [50, 60], "bbox": [5, 6, 7, 8], "location": "status-bar"},
    ],
}


def test_element_from_dict():
    el = Element.from_dict(SCREEN_DICT["elements"][0])
    assert el.type == "button"
    assert el.content == "AC"
    assert el.is_interactive is True
    assert el.center == (100, 200)
    assert el.x == 100 and el.y == 200
    assert el.bbox == (1, 2, 3, 4)


def test_screen_from_dict():
    screen = Screen.from_dict(SCREEN_DICT)
    assert screen.app_name == "Calculator"
    assert "numeric keypad" in screen.description
    assert len(screen.elements) == 2


def test_find_is_case_insensitive():
    screen = Screen.from_dict(SCREEN_DICT)
    assert screen.find("ac") == (100, 200)


def test_find_interactive_only_skips_noninteractive():
    screen = Screen.from_dict(SCREEN_DICT)
    # The status-bar text is not interactive -> not returned by default
    assert screen.find("portrait") is None
    # but returned when interactive_only=False
    assert screen.find("portrait", interactive_only=False) == (50, 60)


def test_find_returns_none_when_absent():
    screen = Screen.from_dict(SCREEN_DICT)
    assert screen.find("nonexistent") is None


def test_contains_checks_description_and_elements():
    screen = Screen.from_dict(SCREEN_DICT)
    assert screen.contains("numeric keypad") is True   # in description
    assert screen.contains("portrait") is True         # in an element
    assert screen.contains("banana") is False


def test_find_and_click_taps_when_found(fake_clicker):
    screen = Screen.from_dict(SCREEN_DICT)
    fake = fake_clicker
    assert screen.find_and_click(fake, "ac") is True
    assert fake.clicked == [(100, 200)]


def test_find_and_click_returns_false_when_absent(fake_clicker):
    screen = Screen.from_dict(SCREEN_DICT)
    fake = fake_clicker
    assert screen.find_and_click(fake, "nope") is False
    assert fake.clicked == []


class _FailingClicker:
    def click(self, coords, duration=100):
        return {"success": False, "message": "network down"}


def test_find_and_click_returns_false_when_tap_fails():
    screen = Screen.from_dict(SCREEN_DICT)
    assert screen.find_and_click(_FailingClicker(), "ac") is False


def test_null_content_tolerated():
    screen = Screen.from_dict({
        "app_name": "App",
        "screen_description": "",
        "elements": [{"content": None, "center": [1, 2], "bbox": [0, 0, 1, 1], "interactivity": True}],
    })
    assert screen.contains("anything") is False
    assert screen.find("anything") is None


def test_empty_keyword_matches_nothing():
    screen = Screen.from_dict(SCREEN_DICT)
    assert screen.find("") is None


def test_contains_empty_keyword_is_false():
    screen = Screen.from_dict(SCREEN_DICT)
    assert screen.contains("") is False
