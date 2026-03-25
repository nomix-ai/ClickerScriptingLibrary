import random
from time import sleep

from utils.clicker import Clicker
from utils.recognition import get_screen
from utils.environment import DEVICE_ID
from utils.actions import (
    open_app, swipe_feed, post_comment, is_ad, chance_tap, random_sleep,
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
        screen = get_screen(clicker)
        if not screen:
            swipe_feed(clicker)
            random_sleep(0.3, 0.8)
            continue

        if is_ad(screen):
            print("[Ad] Skipping...")
            if screen.find_and_click(clicker, "close", "back"):
                sleep(0.5)
            swipe_feed(clicker)
            random_sleep(0.3, 0.8)
            continue

        random_sleep(1.5, 6.0)

        if chance_tap(clicker, screen, "like", like_chance):
            random_sleep(0.5, 1.2)

        if chance_tap(clicker, screen, "follow", follow_chance):
            random_sleep(0.5, 1.0)

        if chance_tap(clicker, screen, "comment", comment_chance):
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
