from time import sleep

from utils.clicker import Clicker
from utils.environment import DEVICE_ID


def main():
    clicker = Clicker(DEVICE_ID)

    clicker.swipe((28813, 1000), down=10000)
    clicker.click((6523, 6689))
    sleep(10)
    clicker.click((6523, 6689))
    sleep(10)
    clicker.click((16700, 26000))


if __name__ == '__main__':
    main()
