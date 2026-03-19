import random
import time

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

COMMENT_SUBMIT_KEYWORDS = ["post", "send"]


BUTTON_NAMES = ("like", "follow", "comment")


def cache_buttons(screen) -> dict:
    coords = {}
    for name in BUTTON_NAMES:
        btn = screen.find(name)
        if btn:
            coords[name] = btn.center
            print(f"Cached {name} button at {btn.center}")
        else:
            print(f"WARNING: Button '{name}' not found in first reel")
    return coords


def maybe_act(clicker, btn_coords: dict, name: str, chance: float) -> bool:
    """Roll the dice and tap a cached button if it exists. Returns True if tapped."""
    if random.random() >= chance or name not in btn_coords:
        return False
    print(f"{name.capitalize()} at {btn_coords[name]}...")
    clicker.click(btn_coords[name])
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

    # Reels is the second interactive button after Home
    count = 0
    for el in screen.elements[home_idx + 1:]:
        if el.is_interactive:
            count += 1
            if count == 2:
                print(f"Reels tab (2nd after Home) at ({el.x}, {el.y}), tapping...")
                clicker.click(el.center)
                time.sleep(1.5)
                return True

    print("WARNING: Not enough interactive elements after Home")
    return False


def browse_reels(
    clicker,
    count: int = 100,
    like_chance: float = 0.25,
    follow_chance: float = 0.10,
    comment_chance: float = 0.15,
) -> None:
    btn_coords = {}

    for i in range(count):
        print(f"--- Reel {i + 1}/{count} ---")

        try:
            screen = get_screen(DEVICE_ID, f"reel_{i + 1}")
        except Exception as e:
            print(f"ERROR: get_screen failed: {e}, skipping reel")
            swipe_feed(clicker)
            time.sleep(random.uniform(0.3, 0.8))
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

        if not btn_coords:
            btn_coords = cache_buttons(screen)

        watch_time = random.uniform(1.5, 6.0)
        print(f"Watching for {watch_time:.1f}s...")
        time.sleep(watch_time)

        if maybe_act(clicker, btn_coords, "like", like_chance):
            time.sleep(random.uniform(0.5, 1.2))

        if maybe_act(clicker, btn_coords, "follow", follow_chance):
            time.sleep(random.uniform(0.5, 1.0))

        if maybe_act(clicker, btn_coords, "comment", comment_chance):
            time.sleep(1.5)
            if random.random() < 0.5:
                post_comment(
                    clicker,
                    DEVICE_ID,
                    text=random.choice(COMMENTS),
                    input_keywords=COMMENT_INPUT_KEYWORDS,
                    submit_keywords=COMMENT_SUBMIT_KEYWORDS,
                )
                time.sleep(random.uniform(0.5, 1.0))
            clicker.click((16000, 3000))  # dismiss comments sheet
            time.sleep(0.5)

        swipe_feed(clicker)
        time.sleep(random.uniform(0.3, 0.8))


def main():
    clicker = Clicker(DEVICE_ID)

    if not open_app(clicker, DEVICE_ID, "instagram"):
        return

    time.sleep(1)

    if not open_reels(clicker):
        return

    browse_reels(clicker, count=10)


if __name__ == "__main__":
    main()
