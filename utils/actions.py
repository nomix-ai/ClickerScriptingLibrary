import random
from time import sleep

from .clicker import Clicker
from .recognition import Screen, parse_screen


def open_app(clicker: Clicker, app_name: str) -> bool:
    """Open any app via iOS Spotlight search."""
    print("Opening Spotlight...")
    clicker.swipe((16000, 10000), down=8000, duration=300)
    sleep(0.5)

    print(f"Typing '{app_name}'...")
    clicker.type(app_name)
    sleep(2)

    screen = parse_screen(clicker)
    if not screen or not screen.find_and_click(clicker, app_name):
        print(f"WARNING: '{app_name}' not found in Spotlight results")
        return False
    sleep(3)
    return True


_AD_KEYWORDS = [
    "advertising", "advertisement", "sponsored",
    "contact us", "shop now", "learn more",
    "install now", "send message", "get quote",
]


def is_ad(screen: Screen) -> bool:
    """Return True if the current screen looks like an ad."""
    return (screen.contains(*_AD_KEYWORDS)
            or any(el.content.lower() == "ad" for el in screen.elements))


def chance_tap(clicker: Clicker, screen: Screen, name: str, chance: float) -> bool:
    """Roll the dice and tap a button found on screen. Returns True if tapped."""
    if random.random() >= chance:
        return False
    return screen.find_and_click(clicker, name)


def random_sleep(min_s: float = 0.3, max_s: float = 0.8) -> None:
    """Sleep for a random duration to simulate human behavior."""
    sleep(random.uniform(min_s, max_s))


def swipe_back(clicker: Clicker) -> None:
    """iOS swipe-back gesture (swipe right from left edge)."""
    clicker.swipe((5000, 16000), right=20000, duration=300)


def swipe_feed(clicker: Clicker) -> None:
    """Swipe up to the next feed item."""
    clicker.swipe((16383, 26213), up=6553, duration=100)


def find_and_click(clicker: Clicker, *keywords: str, interactive_only: bool = True) -> bool:
    """Get screen, find element by keywords, and click it. Returns True if clicked."""
    screen = parse_screen(clicker)
    if not screen:
        return False
    return screen.find_and_click(clicker, *keywords, interactive_only=interactive_only)


def post_comment(
    clicker: Clicker,
    text: str,
    input_keywords: list[str],
    submit_keyword: str,
    cached_coords: dict | None = None,
) -> bool:
    """Find a comment input field, type text, and submit."""
    if cached_coords and "comment_input" in cached_coords and "comment_submit" in cached_coords:
        clicker.click(cached_coords["comment_input"])
        clicker.type(text)
        sleep(0.5)
        clicker.click(cached_coords["comment_submit"])
        return True

    screen = parse_screen(clicker)
    if not screen:
        return False
    input_coords = screen.find(*input_keywords, interactive_only=False)
    if not input_coords:
        print("WARNING: Comment input not found")
        return False

    clicker.click(input_coords)
    clicker.type(text)
    sleep(2)

    screen = parse_screen(clicker)
    if not screen:
        return False
    submit_coords = screen.find(submit_keyword, interactive_only=False)
    if not submit_coords:
        print(f"WARNING: Submit button not found, elements: {[e.content for e in screen.elements]}")
        return False

    if cached_coords is not None:
        cached_coords["comment_input"] = input_coords
        cached_coords["comment_submit"] = submit_coords
        print(f"Cached comment_input at {input_coords}, comment_submit at {submit_coords}")

    clicker.click(submit_coords)
    return True
