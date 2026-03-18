import time
from collections.abc import Callable

import requests

from .environment import API_KEY, API_URL

session = requests.Session()
session.headers.update({"X-API-Key": API_KEY})


def _run_agent(device_id, task):
    response = session.post(
        f"{API_URL}/{device_id}/agent/run",
        json={"task": task},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _get_agent_task(device_id, task_id):
    response = session.get(
        f"{API_URL}/{device_id}/agent/{task_id}",
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def _cancel_agent_task(device_id, task_id):
    response = session.delete(
        f"{API_URL}/{device_id}/agent/{task_id}",
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


class Agent:
    """AI agent controller for a device."""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.current_task_id: str | None = None

    def run(self, task: str) -> str:
        """Start a new agent task. Returns task_id and stores it internally."""
        result = _run_agent(self.device_id, task)
        self.current_task_id = result["task_id"]
        return self.current_task_id

    def get_status(self, task_id: str | None = None) -> dict:
        """Get task status. Uses current_task_id if none provided."""
        tid = task_id or self.current_task_id
        if not tid:
            raise ValueError("No task_id -- call run() first or pass task_id")
        return _get_agent_task(self.device_id, tid)

    def cancel(self, task_id: str | None = None) -> dict:
        """Cancel a running task."""
        tid = task_id or self.current_task_id
        if not tid:
            raise ValueError("No task_id -- call run() first or pass task_id")
        result = _cancel_agent_task(self.device_id, tid)
        if tid == self.current_task_id:
            self.current_task_id = None
        return result

    def poll(
        self,
        task_id: str | None = None,
        callback: Callable[[dict], None] | None = None,
        interval: float = 1.0,
    ) -> str | None:
        """Poll task until completion, printing or calling back on events."""
        tid = task_id or self.current_task_id
        if not tid:
            raise ValueError("No task_id -- call run() first or pass task_id")

        seen_events = 0
        while True:
            task = _get_agent_task(self.device_id, tid)
            events = task.get("events", [])

            for event in events[seen_events:]:
                if callback:
                    callback(event)
                else:
                    step = event.get("step", "?")
                    max_steps = event.get("max_steps", "?")
                    action = event.get("action", "?")
                    result = event.get("result", "?")
                    print(f"[{step}/{max_steps}] {action} -> {result}")
            seen_events = len(events)

            status = task.get("status")
            if status not in ("pending", "running"):
                result = task.get("result")
                if callback:
                    callback({"status": status, "result": result})
                else:
                    print(f"\n--- Agent {status}: {result}")
                return result

            time.sleep(interval)

    def run_and_wait(
        self,
        task: str,
        callback: Callable[[dict], None] | None = None,
    ) -> str | None:
        """Convenience: run a task and poll until done."""
        self.run(task)
        return self.poll(callback=callback)
