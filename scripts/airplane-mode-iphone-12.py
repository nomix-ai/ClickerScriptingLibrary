from time import sleep

from utils.environment import DEVICE_ID
from utils.mouse_controller import MouseController


def main():
    mouse = MouseController(DEVICE_ID)

    mouse.swipe((28813, 1000), down=10000)
    mouse.click((6523, 6689))
    sleep(10)
    mouse.click((6523, 6689))
    sleep(10)
    mouse.click((16700, 26000))


if __name__ == '__main__':
    main()
