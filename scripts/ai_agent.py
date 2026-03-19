"""Run an AI agent task on a device with real-time progress streaming.

Usage:
    python -m scripts.ai_agent "Open Settings and enable Wi-Fi"
    python -m scripts.ai_agent "Open Telegram and send hello to diary chat"
"""

import sys

from utils.agent import Agent
from utils.environment import DEVICE_ID


def main():
    if len(sys.argv) < 2:
        print('Usage: python -m scripts.ai_agent "your task instruction"')
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    print(f"Device: {DEVICE_ID}")
    print(f"Task: {task}\n")

    agent = Agent(DEVICE_ID)
    result = agent.run_and_wait(task)

    if result:
        print(f"\nResult: {result}")


if __name__ == "__main__":
    main()
