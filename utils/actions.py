import random
from time import sleep
from typing import Optional

from .clicker import Clicker
from .recognition import Screen, parse_screen

COMMENT_SECTION_KEYWORDS = [
    "close comments",
    "filter comments",
    "add comment",
    "add a comment",
    "join the conversation",
]


def open_app(clicker: Clicker, app_name: str, retries: int = 3) -> Optional[Screen]:
    """Open any app via iOS Spotlight search. Retries up to `retries` times.

    Returns the parsed screen on success, or None on failure.
    """
    for attempt in range(1, retries + 1):
        print(f"Opening Spotlight (attempt {attempt}/{retries})...")
        clicker.swipe((16000, 10000), down=8000, duration=300)
        sleep(0.5)

        print(f"Typing '{app_name}'...")
        clicker.type(app_name)
        sleep(2)

        screen = parse_screen(clicker)
        if not screen or not screen.find_and_click(clicker, app_name):
            print(f"WARNING: '{app_name}' not found in Spotlight results")
            close_app(clicker)
            continue

        sleep(3)

        screen = parse_screen(clicker)
        if screen and app_name.lower() in screen.app_name.lower():
            return screen

        print(f"WARNING: '{app_name}' did not open (current app: '{screen.app_name if screen else 'None'}')")
        close_app(clicker)

    print(f"ERROR: Failed to open '{app_name}' after {retries} attempts.")
    return None


def _do_close_app(clicker: Clicker) -> None:
    # Slow swipe up from bottom edge to open app switcher
    sleep(1)
    clicker.swipe((16384, 32767), up=4767, duration=1000)
    sleep(5)
    # Swipe up on the last app card to dismiss it
    clicker.swipe((26500, 20000), up=10000, duration=300)
    sleep(5)
    # Tap home area to exit app switcher
    clicker.click((16384, 30000), duration=100)


def close_app(clicker: Clicker, retries: int = 3) -> bool:
    """Open app switcher, dismiss the last app, then tap home.

    Verifies the device returned to the Home Screen after closing.
    Retries up to `retries` times if the app is still in the foreground.
    Returns True if the Home Screen is confirmed, False otherwise.
    """
    for attempt in range(1, retries + 1):
        print(f"Closing app (attempt {attempt}/{retries})...")
        _do_close_app(clicker)
        sleep(3)
        screen = parse_screen(clicker)
        if not screen or screen.app_name.lower() == "home screen":
            print("App closed successfully.")
            return True
        print(f"App still open after attempt {attempt} (screen: '{screen.app_name}'), retrying...")
    print(f"Warning: could not confirm app was closed after {retries} attempts.")
    return False


_AD_KEYWORDS = [
    "advertising", "advertisement", "sponsored",
    "contact us", "shop now", "learn more",
    "install now", "send message", "get quote",
]


def is_ad(screen: Screen) -> bool:
    """Return True if the current screen looks like an ad."""
    return (screen.contains(*_AD_KEYWORDS)
            or any(el.content.lower() == "ad" for el in screen.elements))


def is_comment_section_opened(screen: Screen) -> bool:
    """Return True if the comments sheet is currently pulled up."""
    return screen.contains(*COMMENT_SECTION_KEYWORDS)


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
        submit_keyword: str | list[str],
        cached_coords: Optional[dict] = None,
) -> bool:
    """Find a comment input field, type text, and submit.

    On the first call, parses the screen twice: once to find the input field,
    and again after typing to find the send button (which only appears once the
    keyboard is open). Coords are stored in `cached_coords` so subsequent calls
    skip both parses entirely.
    """
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
    sleep(1)

    screen = parse_screen(clicker)
    if not screen:
        return False

    keywords = submit_keyword if isinstance(submit_keyword, list) else [submit_keyword]
    submit_coords = screen.find(*keywords, interactive_only=False)
    if not submit_coords:
        print(f"WARNING: Submit button not found, elements: {[e.content for e in screen.elements]}")
        return False

    if cached_coords is not None:
        cached_coords["comment_input"] = input_coords
        cached_coords["comment_submit"] = submit_coords
        print(f"Cached comment_input at {input_coords}, comment_submit at {submit_coords}")

    clicker.click(submit_coords)
    sleep(1)
    clicker.click((16383, 4096))  # dismiss comments sheet
    sleep(0.5)

    return True
