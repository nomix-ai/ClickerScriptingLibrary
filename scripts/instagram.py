import random
import time

from utils.recognition import Screen, get_screen
from utils.clicker import Clicker
from utils.environment import DEVICE_ID


def screen_state(context=""):
    """Get screen state with timing and detailed logging."""
    print(f"screen-state request ({context})...")
    start = time.monotonic()
    screen = get_screen(DEVICE_ID)
    elapsed = time.monotonic() - start
    print(f"screen-state done in {elapsed:.1f}s | app={screen.app_name} | {screen.description} | {len(screen.elements)} elements")
    return screen


def open_instagram(clicker):
    """Open Instagram from iOS home screen via Spotlight search."""
    print("Opening Spotlight...")
    clicker.swipe((16000, 16000), down=8000, duration=300)
    time.sleep(0.5)

    print("Typing 'instagram'...")
    clicker.type("instagram")
    time.sleep(1.0)

    screen = screen_state("spotlight_search")
    btn = screen.find("instagram")
    if not btn:
        print("WARNING: Instagram not found in Spotlight results")
        return False
    print(f"Tapping Instagram at ({btn.x}, {btn.y})...")
    clicker.click(btn.center)
    time.sleep(2.0)
    return True


def open_reels(clicker):
    screen = screen_state("open_reels")

    # Try to find Reels tab directly by label
    reels_btn = screen.find("reels")
    if reels_btn:
        print(f"Reels tab at ({reels_btn.x}, {reels_btn.y}), tapping...")
        clicker.click(reels_btn.center)
        time.sleep(1.5)
        return True

    # Fallback: first interactive button after Home tab
    home_idx = None
    for idx, el in enumerate(screen.elements):
        if "home" in el.content.lower():
            home_idx = idx
            break

    if home_idx is None:
        print(f"WARNING: Home tab not found, elements: {[e.content for e in screen.elements]}")
        return False

    for el in screen.elements[home_idx + 1:]:
        if el.is_interactive:
            print(f"Reels tab (after Home) at ({el.x}, {el.y}), tapping...")
            clicker.click(el.center)
            time.sleep(1.5)
            return True

    print("WARNING: No interactive element found after Home")
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
    print(f"Liking at {coords}...")
    clicker.click(coords)


def follow_account(clicker, coords):
    """Tap the follow button at cached coordinates."""
    print(f"Following at {coords}...")
    clicker.click(coords)


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
    print(f"Opening comments at {coords}...")
    clicker.click(coords)
    time.sleep(1.5)
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
            el = screen.find(kw, interactive_only=False)
            if el:
                _comment_input_coords = el.center
                print(f"Cached comment input at {_comment_input_coords}")
                break
        if _comment_input_coords is None:
            print("WARNING: Comment input not found, skipping")
            return

    print(f"Tapping comment input at {_comment_input_coords}...")
    clicker.click(_comment_input_coords)
    time.sleep(1.0)

    text = random.choice(COMMENTS)
    print(f"Typing: {text}")
    clicker.type(text)
    time.sleep(0.5)

    # First call: find and cache post button position
    if _comment_post_coords is None:
        screen = screen_state("comment_post_init")
        post_btn = screen.find("post") or screen.find("send")
        if post_btn:
            _comment_post_coords = post_btn.center
            print(f"Cached post button at {_comment_post_coords}")
        else:
            print("WARNING: Post button not found, skipping")
            _comment_input_coords = None  # reset both so next call re-discovers
            return

    print(f"Posting comment at {_comment_post_coords}...")
    clicker.click(_comment_post_coords)
    time.sleep(1.0)


def close_comments(clicker):
    """Tap above the comments sheet to dismiss it."""
    clicker.click((16000, 3000))
    time.sleep(0.5)


def _cache_button_coords(screen):
    """Extract like/follow/comment button coordinates from screen state."""
    coords = {}
    for name in ("like", "follow", "comment"):
        btn = screen.find(name)
        if btn:
            coords[name] = btn.center
            print(f"Cached {name} button at {btn.center}")
        else:
            print(f"WARNING: Button '{name}' not found in first reel")
    return coords


def is_ad(screen: Screen) -> bool:
    """Return True if the current reel is an ad."""
    desc = screen.description.lower()
    if any(kw in desc for kw in ("advertising", "advertisement", "sponsored")):
        return True
    for el in screen.elements:
        content = el.content.lower()
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
        print(f"--- Reel {i + 1}/{count} ---")

        try:
            # One screen_state per reel: ad check + cache buttons on first reel
            screen = screen_state(f"reel_{i + 1}")
        except Exception as e:
            print(f"ERROR: screen_state failed: {e}, skipping reel")
            next_reel(clicker)
            time.sleep(random.uniform(0.3, 0.8))
            continue

        if is_ad(screen):
            print("[Ad] Skipping...")
            # Close webview if opened
            btn = screen.find("close") or screen.find("back")
            if btn:
                clicker.click(btn.center)
                time.sleep(0.5)
            next_reel(clicker)
            time.sleep(random.uniform(0.3, 0.8))
            continue

        if not btn_coords:
            btn_coords = _cache_button_coords(screen)

        # Watch for a random duration (1.5-6s)
        watch_time = random.uniform(1.5, 6.0)
        print(f"Watching for {watch_time:.1f}s...")
        time.sleep(watch_time)

        # ~25% chance to like
        if random.random() < 0.25 and "like" in btn_coords:
            like_reel(clicker, btn_coords["like"])
            time.sleep(random.uniform(0.5, 1.2))

        # ~10% chance to follow
        if random.random() < 0.10 and "follow" in btn_coords:
            follow_account(clicker, btn_coords["follow"])
            time.sleep(random.uniform(0.5, 1.0))

        # ~15% chance to interact with comments
        if random.random() < 0.15 and "comment" in btn_coords:
            open_comments(clicker, btn_coords["comment"])
            if random.random() < 0.5:
                write_comment(clicker)
                time.sleep(random.uniform(0.5, 1.0))
            close_comments(clicker)

        # Swipe to next reel, pause before next action
        next_reel(clicker)
        time.sleep(random.uniform(0.3, 0.8))


def main():
    clicker = Clicker(DEVICE_ID)

    if not open_instagram(clicker):
        return

    if not open_reels(clicker):
        return

    browse_reels(clicker, count=10)


if __name__ == "__main__":
    main()
