from utils.api_helper import move_to
from utils.environment import DEVICE_ID


def main():
    # Move mouse to (28813, 931) without pressing
    result = move_to(DEVICE_ID, 28813, 931)
    print(result)
    result = move_to(DEVICE_ID, 29000, 931, is_pressed=True)
    print(result)


if __name__ == '__main__':
    main()
