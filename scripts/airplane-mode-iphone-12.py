from time import sleep

from utils.clicker import Clicker
from utils.environment import DEVICE_ID


def main():
    clicker = Clicker(DEVICE_ID)

    clicker.swipe((28813, 1000), down=10000)
    clicker.move_to((6523, 6689))
    clicker.click()
    sleep(10)
    clicker.move_to((6523, 6689))
    clicker.click()
    sleep(10)
    clicker.move_to((16700, 26000))
    clicker.click()


if __name__ == '__main__':
    main()
