"""Run an AI agent task on a device with real-time progress streaming.

Usage:
    python -m scripts.ai_agent "Open Settings and enable Wi-Fi"
    python -m scripts.ai_agent "Open Telegram and send hello to Dan"
"""

import sys

from utils.agent import Agent
from utils.environment import DEVICE_ID


DEFAULT_TASK = """
Open Reddit, find a sub about surfing, swipe a few posts.
Then open some post, upvote it, and write a hilarious comment relevant to
the content. Then close the app. 
""".strip()


def main():
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else DEFAULT_TASK
    print(f"Device: {DEVICE_ID}")
    print(f"Task: {task}\n")

    agent = Agent(DEVICE_ID)
    try:
        result = agent.run(task)
    except KeyboardInterrupt:
        print("\n\nInterrupted — cancelling task...")
        agent.cancel()
        return

    if result:
        print(f"\nResult: {result}")


if __name__ == "__main__":
    main()
