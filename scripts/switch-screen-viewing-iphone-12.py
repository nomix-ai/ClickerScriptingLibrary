from utils.clicker import Clicker
from utils.environment import DEVICE_ID


def main():
    clicker = Clicker(DEVICE_ID)

    # Close possible opened dialog
    clicker.click((16600, 32500))

    # Swipe-up to close current app
    clicker.swipe((16600, 32500), up=10000)

    # Reset in case Recent apps were opened
    clicker.click((31000, 30000))

    # Swipe to the end most right of home screens
    clicker.swipe((31000, 27500), left=20000)
    clicker.swipe((31000, 27500), left=20000)
    clicker.swipe((31000, 27500), left=20000)

    # App Library
    clicker.click((16600, 3500))

    # Open NMX Viewer
    clicker.type("NMX Viewer")
    clicker.click((4200, 6800))

    # Switch screen viewing
    clicker.click((16600, 24000))
    clicker.click((16600, 19300))
    clicker.click((16600, 24000))


if __name__ == '__main__':
    main()
