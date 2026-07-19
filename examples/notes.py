"""Write a note in the iOS Notes app.

Usage:
    python3 examples/notes.py
    python3 examples/notes.py "Your own note text here"
"""

import sys

from nomix_clicker import Clicker, open_app, random_sleep, DEVICE_ID

DEFAULT_NOTE = "Hello from Nomix Clicker — this note was typed by a script."


def main():
    text = " ".join(sys.argv[1:]) or DEFAULT_NOTE
    clicker = Clicker(DEVICE_ID)

    screen = open_app(clicker, "Notes")
    if not screen:
        print("Could not open the Notes app")
        return
    random_sleep(0.8, 1.5)

    # Start a new note. The compose control is an icon, so try a few labels.
    if not screen.find_and_click(clicker, "new note", "compose", "create note"):
        print("Could not find the New Note button")
        return
    random_sleep(0.8, 1.5)

    if not clicker.type(text).get("success"):
        print("Could not type the note")
        return
    print(f"Note written:\n  {text}")


if __name__ == "__main__":
    main()
