"""Send a photo or video to the iPhone's Photos, then open Photos to see it.

NMX Viewer must be broadcasting on the phone — it saves the file into Photos.

Usage:
    python3 examples/upload_media.py path/to/photo.jpg
    python3 examples/upload_media.py path/to/clip.mp4
"""

import sys

from nomix_clicker import Clicker, open_app, upload_media, DEVICE_ID


def main():
    if len(sys.argv) != 2:
        sys.exit("Usage: python3 examples/upload_media.py <photo-or-video>")
    clicker = Clicker(DEVICE_ID)

    item = upload_media(clicker, sys.argv[1])
    if not item:
        print("Upload failed")
        return
    print(f"Saved {item['kind']} '{item['filename']}' ({item['size']} bytes)")

    # The new file is now the newest item in the library
    open_app(clicker, "Photos")


if __name__ == "__main__":
    main()
