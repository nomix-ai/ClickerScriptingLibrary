"""Run an AI agent task on a device with real-time progress streaming.

Usage:
    python -m scripts.ai_agent "Open Settings and enable Wi-Fi"
    python -m scripts.ai_agent "Open Telegram and send hello to diary chat"
"""

import sys

from utils.api_helper import run_agent, stream_agent
from utils.environment import DEVICE_ID


def main():
    if len(sys.argv) < 2:
        print('Usage: python -m scripts.ai_agent "your task instruction"')
        print('Configure DEVICE_ID in config.json')
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    print(f"Device: {DEVICE_ID}")
    print(f"Task: {task}\n")

    # Start the agent
    result = run_agent(DEVICE_ID, task)
    task_id = result["task_id"]
    print(f"Task started: {task_id}\n")

    # Stream progress in real-time
    final_result = stream_agent(DEVICE_ID, task_id)

    if final_result:
        print(f"\nResult: {final_result}")


if __name__ == "__main__":
    main()
