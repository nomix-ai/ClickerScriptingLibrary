import time

from .recognition import Screen, get_screen


def open_app(clicker, device_id: str, app_name: str) -> bool:
    """Open any app via iOS Spotlight search."""
    print("Opening Spotlight...")
    clicker.swipe((16000, 10000), down=8000, duration=300)

    print(f"Typing '{app_name}'...")
    clicker.type(app_name)
    time.sleep(2)

    screen = get_screen(device_id, "spotlight_search")
    btn = screen.find(app_name)
    if not btn:
        print(f"WARNING: '{app_name}' not found in Spotlight results")
        return False
    print(f"Tapping {app_name} at ({btn.x}, {btn.y})...")
    clicker.click(btn.center)
    time.sleep(3)
    return True


_AD_KEYWORDS = (
    "advertising", "advertisement", "sponsored",
    "contact us", "shop now", "learn more",
    "install now", "send message", "get quote",
)


def is_ad(screen: Screen) -> bool:
    """Return True if the current screen looks like an ad."""
    return (screen.contains_any(_AD_KEYWORDS)
            or any(el.content.lower() == "ad" for el in screen.elements))


def swipe_feed(clicker) -> None:
    """Swipe up to the next feed item."""
    clicker.swipe((16383, 26213), up=6553, duration=100)


def post_comment(
    clicker,
    device_id: str,
    text: str,
    input_keywords: list[str],
    submit_keywords: list[str],
) -> bool:
    """Find a comment input field, type text, and submit."""
    screen = get_screen(device_id, "comment_input")
    input_el = screen.find_any(input_keywords, interactive_only=False)
    if not input_el:
        print("WARNING: Comment input not found")
        return False

    clicker.click(input_el.center)
    clicker.type(text)

    screen = get_screen(device_id, "comment_submit")
    submit_el = screen.find_any(submit_keywords)
    if not submit_el:
        print("WARNING: Submit button not found")
        return False

    clicker.click(submit_el.center)
    return True
