import logging
import math
import random
from pathlib import Path
from time import monotonic, sleep

import requests

from .api_helper import delete_media, list_media, send_media
from .clicker import Clicker
from .recognition import Screen, parse_screen

logger = logging.getLogger(__name__)

MEDIA_POLL_TIMEOUT = 15.0
MEDIA_CLEANUP_TIMEOUT = 5.0


def open_app(clicker: Clicker, app_name: str, retries: int = 3) -> Screen | None:
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
        if screen and screen.app_name.lower() == "home screen":
            print("App closed successfully.")
            return True
        if screen:
            print(f"App still open after attempt {attempt} (screen: '{screen.app_name}'), retrying...")
        else:
            print(f"WARNING: could not verify the Home Screen after attempt {attempt}, retrying...")
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
        input_keywords: str | list[str],
        submit_keyword: str | list[str],
        cached_coords: dict | None = None,
) -> bool:
    """Find a comment input field, type text, and submit.

    On the first call, parses the screen twice: once to find the input field,
    and again after typing to find the send button (which only appears once the
    keyboard is open). Coords are stored in `cached_coords` so subsequent calls
    skip both parses entirely.

    The comments sheet is left open after submitting — dismissing it is
    app-specific and up to the caller (e.g. swipe_back or a targeted tap).
    """
    if isinstance(input_keywords, str):
        input_keywords = [input_keywords]
    if isinstance(submit_keyword, str):
        submit_keyword = [submit_keyword]

    if cached_coords and "comment_input" in cached_coords and "comment_submit" in cached_coords:
        if not clicker.click(cached_coords["comment_input"]).get("success"):
            return False
        if not clicker.type(text).get("success"):
            return False
        sleep(0.5)
        return bool(clicker.click(cached_coords["comment_submit"]).get("success"))

    screen = parse_screen(clicker)
    if not screen:
        return False

    input_coords = screen.find(*input_keywords, interactive_only=False)
    if not input_coords:
        print("WARNING: Comment input not found")
        return False

    if not clicker.click(input_coords).get("success"):
        return False
    if not clicker.type(text).get("success"):
        return False
    sleep(1)

    screen = parse_screen(clicker)
    if not screen:
        return False

    submit_coords = screen.find(*submit_keyword, interactive_only=False)
    if not submit_coords:
        print(f"WARNING: Submit button not found, elements: {[e.content for e in screen.elements]}")
        return False

    if cached_coords is not None:
        cached_coords["comment_input"] = input_coords
        cached_coords["comment_submit"] = submit_coords
        print(f"Cached comment_input at {input_coords}, comment_submit at {submit_coords}")

    return bool(clicker.click(submit_coords).get("success"))


def media_error_detail(error: requests.RequestException) -> str:
    if error.response is None:
        return str(error)
    try:
        body = error.response.json()
    except ValueError:
        body = None
    detail = body.get("detail") if isinstance(body, dict) else None
    return f"HTTP {error.response.status_code}: {detail or error.response.reason}"


def upload_media(
        clicker: Clicker,
        path: str | Path,
        timeout: float = 300,
        interval: float = 2.0,
) -> dict | None:
    """Send a photo or video to the iPhone's Photos and wait until it is saved.

    NMX Viewer must be broadcasting on the phone — it collects the file from
    the device's queue and saves it, so it becomes the newest item in Photos.

    `timeout` covers uploading and waiting for Photos together. On timeout,
    withdrawing a queued file can take up to 5 additional seconds. Withdrawal
    is best effort: if it fails or the upload response is lost, the file may
    still appear in Photos later.

    Returns the saved item or None on failure or timeout. Zero timeout skips
    the upload. Negative or non-finite timeout, or non-positive/non-finite
    interval, raises ValueError. A missing file raises FileNotFoundError.
    """
    deadline = monotonic() + timeout
    if not math.isfinite(timeout) or timeout < 0:
        raise ValueError("timeout must be finite and non-negative")
    if not math.isfinite(interval) or interval <= 0:
        raise ValueError("interval must be finite and positive")
    if timeout == 0:
        return None
    name = Path(path).name
    logger.info("Uploading '%s'...", name)
    try:
        item = send_media(clicker.device_id, path, timeout=max(0, deadline - monotonic()))
    except requests.RequestException as error:
        logger.error("Upload of '%s' failed: %s", name, media_error_detail(error))
        if error.response is None:
            logger.warning("No media ID received for '%s'; if the server accepted it, it may still appear in Photos", name)
        return None

    media_id = item.get("id")
    if not media_id:
        logger.error("No media ID received for '%s'; the file may still appear in Photos", name)
        return None
    logger.info("Waiting for the phone to save '%s'...", name)
    try:
        while item.get("status") not in ("saved", "failed"):
            remaining = deadline - monotonic()
            if remaining <= 0:
                break
            sleep(min(interval, remaining))
            remaining = deadline - monotonic()
            if remaining <= 0:
                break
            try:
                items = list_media(clicker.device_id, timeout=min(MEDIA_POLL_TIMEOUT, remaining)).get("items", [])
            except requests.RequestException as error:
                logger.warning("Media status check failed (%s), retrying", media_error_detail(error))
                continue
            item = next((entry for entry in items if entry.get("id") == media_id), item)
        if item.get("status") == "saved" and monotonic() <= deadline:
            logger.info("'%s' saved to Photos", name)
            return item
        if item.get("status") == "failed":
            logger.error("The phone could not save '%s': %s", name, item.get("error"))
        else:
            logger.error("'%s' was not saved within %.3gs", name, timeout)
        return None
    finally:
        if item.get("status") == "queued":
            try:
                delete_media(clicker.device_id, media_id, timeout=MEDIA_CLEANUP_TIMEOUT)
            except requests.RequestException as error:
                logger.warning("Could not withdraw '%s' (%s), it may still appear in Photos", name, media_error_detail(error))
