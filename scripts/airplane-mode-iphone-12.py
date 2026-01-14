from utils.api_helper import set_coordinates, move_to
from utils.environment import DEVICE_ID


def main():
    # Set coordinates to first position (28813, 931)
    result = set_coordinates(DEVICE_ID, (28813, 931))
    print(result)
    
    # Move with button pressed to second position (29000, 931)
    result = move_to(DEVICE_ID, (28813, 931), (29000, 931), is_pressed=True)
    print(result)


if __name__ == '__main__':
    main()
