import random
import time

import requests

from utils.actions import open_app, swipe_feed, post_comment, is_ad
from utils.recognition import get_screen
from utils.clicker import Clicker
from utils.environment import DEVICE_ID


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

COMMENT_INPUT_KEYWORDS = [
    "add a comment",
    "add comment",
    "join the conversation",
    "comment as",
    "what do you think",
]

COMMENT_SUBMIT_KEYWORDS = ["send comment"]


def try_tap(screen, clicker, name: str, chance: float) -> bool:
    """Roll the dice and tap a button found on screen. Returns True if tapped."""
    if random.random() >= chance:
        return False
    btn = screen.find(name)
    if not btn:
        return False
    print(f"{name.capitalize()} at {btn.center}...")
    clicker.click(btn.center)
    return True


def open_reels(clicker) -> bool:
    screen = get_screen(DEVICE_ID, "open_reels")

    home_idx = None
    for idx, el in enumerate(screen.elements):
        if "home" in el.content.lower():
            home_idx = idx
            break

    if home_idx is None:
        print(f"WARNING: Home tab not found, elements: {[e.content for e in screen.elements]}")
        return False

    # Reels is the first interactive button after Home
    for el in screen.elements[home_idx + 1:]:
        if el.is_interactive:
            print(f"Reels tab (after Home) at ({el.x}, {el.y}), tapping...")
            clicker.click(el.center)
            time.sleep(1.5)
            return True

    print("WARNING: No interactive element found after Home")
    return False


def browse_reels(
    clicker,
    count: int = 100,
    like_chance: float = 0.25,
    follow_chance: float = 0.10,
    comment_chance: float = 0.15,
) -> None:
    comment_coords = {}

    for i in range(count):
        print(f"--- Reel {i + 1}/{count} ---")

        time.sleep(1)
        try:
            screen = get_screen(DEVICE_ID, f"reel_{i + 1}")
        except (requests.RequestException, TimeoutError) as e:
            print(f"ERROR: get_screen failed: {e}, skipping reel")
            swipe_feed(clicker)
            time.sleep(random.uniform(0.3, 0.8))
            continue

        if not screen.description.lower().startswith("a vertical video") and "reel" not in screen.description.lower():
            print(f"[Not a reel] {screen.description}, swiping back...")
            clicker.swipe((5000, 16000), right=20000, duration=300)
            time.sleep(1)
            continue

        if is_ad(screen):
            print("[Ad] Skipping...")
            btn = screen.find("close") or screen.find("back")
            if btn:
                clicker.click(btn.center)
                time.sleep(0.5)
            swipe_feed(clicker)
            time.sleep(random.uniform(0.3, 0.8))
            continue

        watch_time = random.uniform(1.5, 6.0)
        print(f"Watching for {watch_time:.1f}s...")
        time.sleep(watch_time)

        if try_tap(screen, clicker, "like", like_chance):
            time.sleep(random.uniform(0.5, 1.2))

        if try_tap(screen, clicker, "follow", follow_chance):
            time.sleep(random.uniform(0.5, 1.0))

        if try_tap(screen, clicker, "comment", comment_chance):
            time.sleep(2)
            if random.random() < 0.5:
                post_comment(
                    clicker,
                    DEVICE_ID,
                    text=random.choice(COMMENTS),
                    input_keywords=COMMENT_INPUT_KEYWORDS,
                    submit_keywords=COMMENT_SUBMIT_KEYWORDS,
                    cached_coords=comment_coords,
                )
                time.sleep(random.uniform(0.5, 1.0))
            else:
                time.sleep(random.uniform(1.0, 3.0))  # just browse comments
            clicker.click((16000, 7000))  # dismiss comments sheet
            time.sleep(0.5)

        swipe_feed(clicker)
        time.sleep(random.uniform(0.3, 0.8))


def main():
    clicker = Clicker(DEVICE_ID)

    if not open_app(clicker, DEVICE_ID, "instagram"):
        return

    time.sleep(2)

    if not open_reels(clicker):
        return

    browse_reels(clicker, count=10)


if __name__ == "__main__":
    main()
