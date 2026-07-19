import time

import requests

from .api_helper import run_agent, get_agent_task, cancel_agent_task


class Agent:
    """AI agent controller for a device."""

    def __init__(self, device_id: str):
        self.device_id = device_id
        self.current_task_id: str | None = None

    def execute(self, task: str) -> str:
        """Start a new agent task. Returns task_id and stores it internally."""
        self.current_task_id = run_agent(self.device_id, task).get("task_id")
        return self.current_task_id

    def _require_task_id(self, task_id: str | None) -> str:
        tid = task_id or self.current_task_id
        if not tid:
            raise ValueError("No task_id -- call execute() first or pass task_id")
        return tid

    def get_status(self, task_id: str | None = None) -> dict:
        """Get task status. Uses current_task_id if none provided."""
        return get_agent_task(self.device_id, self._require_task_id(task_id))

    def cancel(self, task_id: str | None = None) -> dict:
        """Cancel a running task."""
        # current_task_id is kept so get_status()/poll() can still inspect the task
        return cancel_agent_task(self.device_id, self._require_task_id(task_id))

    def poll(
        self,
        task_id: str | None = None,
        interval: float = 1.0,
    ) -> str | None:
        """Poll task until completion, printing events to stdout."""
        tid = self._require_task_id(task_id)

        seen_events = 0
        failures = 0
        while True:
            try:
                task = get_agent_task(self.device_id, tid)
                failures = 0
            except requests.RequestException as e:
                failures += 1
                if failures >= 3:  # transient blips are tolerated, persistent errors raise
                    raise
                print(f"WARNING: status poll failed ({e}) — retrying...")
                time.sleep(interval)
                continue
            events = task.get("events", [])

            for event in events[seen_events:]:
                step = event.get("step", "?")
                action = event.get("action", "?")
                result = event.get("result", "?")
                print(f"[{step}] {action} -> {result}")
            seen_events = len(events)

            status = task.get("status")
            if status not in ("pending", "running"):
                result = task.get("result")
                print(f"\n--- Agent {status}: {result}")
                return result

            time.sleep(interval)

    def run(self, task: str) -> str | None:
        """Convenience: execute a task and poll until done."""
        previous_task_id = self.current_task_id
        try:
            self.execute(task)
            return self.poll()
        except BaseException:  # cancel on Ctrl-C and errors alike, then re-raise
            # cancel only the task this run() created, never one from a previous run
            if self.current_task_id and self.current_task_id != previous_task_id:
                print("\n\nAborted — cancelling task...")
                try:
                    self.cancel()
                except requests.RequestException as e:
                    print(f"WARNING: could not cancel task: {e}")
            else:
                print(
                    "\n\nAborted while the task was being created — if it started "
                    "server-side, it may still be running (a new execute() may get 409 until it ends)."
                )
            raise
