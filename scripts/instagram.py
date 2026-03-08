import logging
import random
import time
from time import sleep

from utils.api_helper import find_element, get_screen_state
from utils.clicker import Clicker
from utils.environment import DEVICE_ID

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
    level=logging.INFO,
)
log = logging.getLogger(__name__)


def screen_state(context=""):
    """Get screen state with timing and detailed logging."""
    log.info("screen-state request (%s)...", context)
    start = time.monotonic()
    screen = get_screen_state(DEVICE_ID)
    elapsed = time.monotonic() - start
    log.info(
        "screen-state done in %.1fs | app=%s | %s | %d elements",
        elapsed,
        screen.get("app_name", "?"),
        screen.get("screen_description", "?"),
        len(screen.get("elements", [])),
    )
    for el in screen.get("elements", []):
        log.debug(
            "  [%s] %s | interactive=%s | center=%s",
            el.get("type", "?"),
            el.get("content", "?"),
            el.get("interactivity"),
            el.get("center"),
        )
    return screen


def open_instagram(clicker):
    """Open Instagram from iOS home screen via Spotlight search."""
    log.info("Opening Spotlight...")
    clicker.swipe((16000, 16000), down=8000, duration=300)
    sleep(0.5)

    log.info("Typing 'instagram'...")
    clicker.type("instagram")
    sleep(1.0)

    screen = screen_state("spotlight_search")
    btn = find_element(screen, "instagram")
    if not btn:
        log.warning("Instagram not found in Spotlight results")
        return False
    x, y = btn["center"]
    log.info("Tapping Instagram at (%d, %d)...", x, y)
    clicker.click((x, y))
    sleep(2.0)
    return True


def open_reels(clicker):
    screen = screen_state("open_reels")

    elements = screen.get("elements", [])
    home_idx = None
    for idx, el in enumerate(elements):
        content = (el.get("content") or "").lower()
        if "home" in content:
            home_idx = idx
            break

    if home_idx is None:
        log.warning(
            "Home tab not found, elements: %s", [e.get("content") for e in elements]
        )
        return False

    # Reels = next interactive button after Home
    for el in elements[home_idx + 1 :]:
        if el.get("interactivity"):
            x, y = el["center"]
            log.info("Reels tab (after Home) at (%d, %d), tapping...", x, y)
            clicker.click((x, y))
            sleep(1.5)
            return True

    log.warning("No interactive element found after Home")
    return False


def next_reel(clicker):
    """Swipe up to go to next reel with slight horizontal jitter."""
    start_x = random.randint(14000, 18000)
    start_y = random.randint(26000, 30000)
    swipe_dist = random.randint(14000, 20000)
    duration = random.randint(100, 250)
    clicker.swipe((start_x, start_y), up=swipe_dist, duration=duration)


def like_reel(clicker, coords):
    """Tap the like (heart) button at cached coordinates."""
    x, y = coords
    log.info("Liking at (%d, %d)...", x, y)
    clicker.click((x, y))


def follow_account(clicker, coords):
    """Tap the follow button at cached coordinates."""
    x, y = coords
    log.info("Following at (%d, %d)...", x, y)
    clicker.click((x, y))


COMMENTS = [
    "fire",
    "amazing",
    "love this",
    "wow",
    "so good",
    "this is great",
    "nice",
    "cool",
    "awesome",
    "beautiful",
]


def open_comments(clicker, coords):
    """Tap the comment icon at cached coordinates."""
    x, y = coords
    log.info("Opening comments at (%d, %d)...", x, y)
    clicker.click((x, y))
    sleep(1.5)
    return True


_comment_input_coords = None
_comment_post_coords = None


def write_comment(clicker):
    """Tap the comment input, type a random comment, and post it."""
    global _comment_input_coords, _comment_post_coords

    # First call: find and cache comment input position
    if _comment_input_coords is None:
        screen = screen_state("comment_input_init")
        input_keywords = [
            "add a comment",
            "add comment",
            "join the conversation",
            "comment as",
            "what do you think",
        ]
        for kw in input_keywords:
            el = find_element(screen, kw, only_interactive=False)
            if el:
                _comment_input_coords = tuple(el["center"])
                log.info("Cached comment input at (%d, %d)", *_comment_input_coords)
                break
        if _comment_input_coords is None:
            log.warning("Comment input not found, skipping")
            return

    x, y = _comment_input_coords
    log.info("Tapping comment input at (%d, %d)...", x, y)
    clicker.click((x, y))
    sleep(1.0)

    text = random.choice(COMMENTS)
    log.info("Typing: %s", text)
    clicker.type(text)
    sleep(0.5)

    # First call: find and cache post button position
    if _comment_post_coords is None:
        screen = screen_state("comment_post_init")
        post_btn = find_element(screen, "post") or find_element(screen, "send")
        if post_btn:
            _comment_post_coords = tuple(post_btn["center"])
            log.info("Cached post button at (%d, %d)", *_comment_post_coords)
        else:
            log.warning("Post button not found, skipping")
            return

    x, y = _comment_post_coords
    log.info("Posting comment at (%d, %d)...", x, y)
    clicker.click((x, y))
    sleep(1.0)


def close_comments(clicker):
    """Tap above the comments sheet to dismiss it."""
    clicker.click((16000, 3000))
    sleep(0.5)


def _cache_button_coords(screen):
    """Extract like/follow/comment button coordinates from screen state."""
    coords = {}
    for name in ("like", "follow", "comment"):
        btn = find_element(screen, name)
        if btn:
            coords[name] = tuple(btn["center"])
            log.info("Cached %s button at (%d, %d)", name, *btn["center"])
        else:
            log.warning("Button '%s' not found in first reel", name)
    return coords


def is_ad(screen) -> bool:
    """Return True if the current reel is an ad."""
    desc = (screen.get("screen_description") or "").lower()
    if any(kw in desc for kw in ("advertising", "advertisement", "sponsored")):
        return True
    for el in screen.get("elements", []):
        content = (el.get("content") or "").lower()
        if content in ("ad", "sponsored"):
            return True
        if any(
            kw in content
            for kw in (
                "contact us",
                "shop now",
                "learn more",
                "install now",
                "send message",
                "get quote",
            )
        ):
            return True
    return False


def browse_reels(clicker, count=100):
    btn_coords = {}  # cached from first non-ad reel

    for i in range(count):
        log.info("--- Reel %d/%d ---", i + 1, count)

        try:
            # One screen_state per reel: ad check + cache buttons on first reel
            screen = screen_state(f"reel_{i + 1}")
        except Exception as e:
            log.error("screen_state failed: %s, skipping reel", e)
            next_reel(clicker)
            sleep(random.uniform(0.3, 0.8))
            continue

        if is_ad(screen):
            log.info("[Ad] Skipping...")
            # Close webview if opened
            btn = find_element(screen, "close") or find_element(screen, "back")
            if btn:
                clicker.click(tuple(btn["center"]))
                sleep(0.5)
            next_reel(clicker)
            sleep(random.uniform(0.3, 0.8))
            continue

        if not btn_coords:
            btn_coords = _cache_button_coords(screen)

        # Watch for a random duration (1.5–6s)
        watch_time = random.uniform(1.5, 6.0)
        log.info("Watching for %.1fs...", watch_time)
        sleep(watch_time)

        # ~25% chance to like (TEST: 100%)
        if random.random() < 1 and "like" in btn_coords:
            like_reel(clicker, btn_coords["like"])
            sleep(random.uniform(0.5, 1.2))

        # ~10% chance to follow (TEST: 100%)
        if random.random() < 1 and "follow" in btn_coords:
            follow_account(clicker, btn_coords["follow"])
            sleep(random.uniform(0.5, 1.0))

        # ~15% chance to interact with comments (TEST: 100%)
        if random.random() < 1 and "comment" in btn_coords:
            open_comments(clicker, btn_coords["comment"])
            if random.random() < 1:
                write_comment(clicker)
                sleep(random.uniform(0.5, 1.0))
            close_comments(clicker)

        # Swipe to next reel, pause before next action
        next_reel(clicker)
        sleep(random.uniform(0.3, 0.8))


def main():
    clicker = Clicker(DEVICE_ID)

    if not open_instagram(clicker):
        return

    if not open_reels(clicker):
        return

    browse_reels(clicker, count=10)


if __name__ == "__main__":
    main()
