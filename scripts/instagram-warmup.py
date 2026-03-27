"""Scroll Instagram Reels with configurable like and comment probabilities.

Usage:
    python3 -m scripts.instagram-warmup
"""

import random
from time import sleep

from utils.actions import (
    open_app, close_app, swipe_feed, post_comment, is_ad, chance_tap, random_sleep,
    find_and_click,
)
from utils.clicker import Clicker
from utils.environment import DEVICE_ID
from utils.recognition import parse_screen

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

COMMENT_SUBMIT_KEYWORD = ["send arrow", "send comment", "post comment", "send"]


def browse_reels(
        clicker: Clicker,
        count: int,
        like_chance: float,
        comment_chance: float,
) -> None:
    comment_coords = {}

    for i in range(count):
        if i > 0:
            swipe_feed(clicker)
            random_sleep(0.3, 0.8)

        print(f"--- Reel {i + 1}/{count} ---")

        sleep(1)
        screen = parse_screen(clicker)
        if not screen:
            continue

        if is_ad(screen):
            print("[Ad] Skipping...")
            if screen.find_and_click(clicker, "close", "back"):
                sleep(0.5)
            continue

        random_sleep(1.5, 6.0)

        if chance_tap(clicker, screen, "like", like_chance):
            random_sleep(0.5, 1.2)

        if chance_tap(clicker, screen, "comment", comment_chance):
            sleep(2)
            post_comment(
                clicker,
                text=random.choice(COMMENTS),
                input_keywords=COMMENT_INPUT_KEYWORDS,
                submit_keyword=COMMENT_SUBMIT_KEYWORD,
                cached_coords=comment_coords,
            )


def open_reels(clicker: Clicker, screen=None) -> bool:
    """Navigate to the Reels tab. Returns False if unsuccessful."""
    for attempt in range(3):
        print(f"Opening Reels (attempt {attempt + 1}/3)...")

        if attempt == 0 and screen:
            coords = screen.find("reels")
            if coords:
                clicker.click(coords)
        else:
            find_and_click(clicker, "reels")

        sleep(1.5)
        screen = parse_screen(clicker)
        if screen and "reel" in screen.description.lower():
            return True

        print(f"Reels not open yet (attempt {attempt + 1}/3)")
        clicker.click((16383, 16383))

    print("WARNING: Could not open Reels after 3 attempts.")
    return False


def main():
    clicker = Clicker(DEVICE_ID)

    screen = open_app(clicker, "instagram")
    if not screen:
        return

    if not open_reels(clicker, screen):
        return

    browse_reels(
        clicker,
        count=3,
        like_chance=0.5,
        comment_chance=0.3
    )

    close_app(clicker, retries=5)


if __name__ == "__main__":
    main()
