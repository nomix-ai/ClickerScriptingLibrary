"""Run an AI agent task on a device with real-time progress streaming.

Usage:
    python3 examples/ai_agent.py "Open the Calculator and compute 12 times 12"
    python3 examples/ai_agent.py "Open the Clock app and start a 5 minute timer"
"""

import sys

from nomix_clicker.agent import Agent
from nomix_clicker.environment import DEVICE_ID


DEFAULT_TASK = """
Open the Calculator, compute 25 times 4, then return to the Home Screen.
""".strip()


def main():
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_TASK
    print(f"Device: {DEVICE_ID}")
    print(f"Task: {task}\n")

    agent = Agent(DEVICE_ID)
    result = agent.run(task)

    if result:
        print(f"\nResult: {result}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)  # run() already cancelled the task
