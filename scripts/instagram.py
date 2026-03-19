import random
from time import sleep

import requests

from utils import (
    Clicker, get_screen, DEVICE_ID,
    open_app, swipe_feed, swipe_back, post_comment, is_ad, chance_tap, random_sleep,
    find_and_click,
)


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

COMMENT_SUBMIT_KEYWORD = "send comment"


def browse_reels(
    clicker: Clicker,
    count: int = 100,
    like_chance: float = 0.25,
    follow_chance: float = 0.10,
    comment_chance: float = 0.15,
) -> None:
    comment_coords = {}

    for i in range(count):
        print(f"--- Reel {i + 1}/{count} ---")

        sleep(1)
        try:
            screen = get_screen(clicker.device_id, f"reel_{i + 1}")
        except (requests.RequestException, TimeoutError) as e:
            print(f"ERROR: get_screen failed: {e}, skipping reel")
            swipe_feed(clicker)
            random_sleep(0.3, 0.8)
            continue

        if not screen.description.lower().startswith("a vertical video") and "reel" not in screen.description.lower():
            print(f"[Not a reel] {screen.description}, swiping back...")
            swipe_back(clicker)
            sleep(1)
            continue

        if is_ad(screen):
            print("[Ad] Skipping...")
            if screen.find_and_click(clicker, "close", "back"):
                sleep(0.5)
            swipe_feed(clicker)
            random_sleep(0.3, 0.8)
            continue

        random_sleep(1.5, 6.0)

        if chance_tap(screen, clicker, "like", like_chance):
            random_sleep(0.5, 1.2)

        if chance_tap(screen, clicker, "follow", follow_chance):
            random_sleep(0.5, 1.0)

        if chance_tap(screen, clicker, "comment", comment_chance):
            sleep(2)
            if random.random() < 0.5:
                post_comment(
                    clicker,
                    text=random.choice(COMMENTS),
                    input_keywords=COMMENT_INPUT_KEYWORDS,
                    submit_keyword=COMMENT_SUBMIT_KEYWORD,
                    cached_coords=comment_coords,
                )
                random_sleep(0.5, 1.0)
            else:
                random_sleep(1.0, 3.0)  # just browse comments
            clicker.click((16000, 7000))  # dismiss comments sheet
            sleep(0.5)

        swipe_feed(clicker)
        random_sleep(0.3, 0.8)


def main():
    clicker = Clicker(DEVICE_ID)

    if not open_app(clicker, "instagram"):
        return

    sleep(2)

    if not find_and_click(clicker, "reels", context="open_reels"):
        return

    sleep(1.5)
    browse_reels(clicker, count=10)


if __name__ == "__main__":
    main()
