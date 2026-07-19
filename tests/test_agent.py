"""Agent task lifecycle — api_helper mocked, no network."""

from unittest.mock import MagicMock

import requests

import pytest

from nomix_clicker import Agent
from nomix_clicker import agent as agent_mod


def test_execute_stores_and_returns_task_id(monkeypatch):
    monkeypatch.setattr(agent_mod, "run_agent", MagicMock(return_value={"task_id": "t-123"}))
    a = Agent("dev")
    assert a.execute("do something") == "t-123"
    assert a.current_task_id == "t-123"


def test_get_status_without_task_id_raises():
    with pytest.raises(ValueError):
        Agent("dev").get_status()


def test_cancel_without_task_id_raises():
    with pytest.raises(ValueError):
        Agent("dev").cancel()


def test_poll_without_task_id_raises():
    with pytest.raises(ValueError):
        Agent("dev").poll()


def test_get_status_uses_current_task_id(monkeypatch):
    mock = MagicMock(return_value={"status": "running"})
    monkeypatch.setattr(agent_mod, "get_agent_task", mock)
    a = Agent("dev")
    a.current_task_id = "t-9"
    assert a.get_status() == {"status": "running"}
    mock.assert_called_once_with("dev", "t-9")


def test_cancel_keeps_task_id_for_status_checks(monkeypatch):
    monkeypatch.setattr(agent_mod, "cancel_agent_task", MagicMock(return_value={"status": "cancelled"}))
    a = Agent("dev")
    a.current_task_id = "t-1"
    assert a.cancel() == {"status": "cancelled"}
    assert a.current_task_id == "t-1"   # still addressable after cancel


def test_cancel_with_explicit_id_keeps_current(monkeypatch):
    monkeypatch.setattr(agent_mod, "cancel_agent_task", MagicMock(return_value={}))
    a = Agent("dev")
    a.current_task_id = "current"
    a.cancel("other")                       # cancelling a different task
    assert a.current_task_id == "current"   # our tracked task is untouched


def test_poll_returns_result_on_completion(monkeypatch):
    mock = MagicMock(side_effect=[
        {"status": "running", "events": [
            {"step": 1, "action": "tap", "result": "ok"}]},
        {"status": "completed", "events": [
            {"step": 1, "action": "tap", "result": "ok"}], "result": "done"},
    ])
    monkeypatch.setattr(agent_mod, "get_agent_task", mock)
    a = Agent("dev")
    a.current_task_id = "t-1"
    assert a.poll(interval=0) == "done"
    assert mock.call_count == 2


def test_run_cancels_on_keyboard_interrupt(monkeypatch):
    monkeypatch.setattr(agent_mod, "run_agent", MagicMock(return_value={"task_id": "t-1"}))
    monkeypatch.setattr(agent_mod, "get_agent_task", MagicMock(side_effect=KeyboardInterrupt))
    cancel_mock = MagicMock(return_value={})
    monkeypatch.setattr(agent_mod, "cancel_agent_task", cancel_mock)
    a = Agent("dev")
    with pytest.raises(KeyboardInterrupt):   # re-raised after cancelling
        a.run("task")
    cancel_mock.assert_called_once_with("dev", "t-1")


def test_poll_tolerates_transient_errors(monkeypatch):
    responses = [requests.ConnectionError("blip"), requests.ConnectionError("blip"),
                 {"status": "completed", "result": "done", "events": []}]

    def fake_get(device_id, task_id):
        item = responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    monkeypatch.setattr(agent_mod, "get_agent_task", fake_get)
    monkeypatch.setattr(agent_mod.time, "sleep", lambda s: None)
    a = Agent("dev")
    a.current_task_id = "t1"
    assert a.poll() == "done"


def test_poll_raises_after_persistent_errors(monkeypatch):
    monkeypatch.setattr(agent_mod, "get_agent_task",
                        MagicMock(side_effect=requests.ConnectionError("down")))
    monkeypatch.setattr(agent_mod.time, "sleep", lambda s: None)
    a = Agent("dev")
    a.current_task_id = "t1"
    with pytest.raises(requests.ConnectionError):
        a.poll()


def test_run_survives_cancel_failure_on_interrupt(monkeypatch):
    monkeypatch.setattr(agent_mod, "run_agent", MagicMock(return_value={"task_id": "t-9"}))
    monkeypatch.setattr(agent_mod, "cancel_agent_task",
                        MagicMock(side_effect=requests.HTTPError("404")))
    monkeypatch.setattr(agent_mod, "get_agent_task", MagicMock(side_effect=KeyboardInterrupt))
    a = Agent("dev")
    with pytest.raises(KeyboardInterrupt):
        a.run("x")


def test_run_cancels_when_poll_fails(monkeypatch):
    monkeypatch.setattr(agent_mod, "run_agent", MagicMock(return_value={"task_id": "t-1"}))
    monkeypatch.setattr(agent_mod, "get_agent_task",
                        MagicMock(side_effect=requests.ConnectionError("down")))
    monkeypatch.setattr(agent_mod.time, "sleep", lambda s: None)
    cancel_mock = MagicMock(return_value={})
    monkeypatch.setattr(agent_mod, "cancel_agent_task", cancel_mock)
    a = Agent("dev")
    with pytest.raises(requests.ConnectionError):
        a.run("task")
    cancel_mock.assert_called_once_with("dev", "t-1")


def test_run_does_not_cancel_previous_task_when_execute_fails(monkeypatch):
    monkeypatch.setattr(agent_mod, "run_agent", MagicMock(side_effect=requests.HTTPError("409")))
    cancel_mock = MagicMock()
    monkeypatch.setattr(agent_mod, "cancel_agent_task", cancel_mock)
    a = Agent("dev")
    a.current_task_id = "old-task"   # left over from a previous run
    with pytest.raises(requests.HTTPError):
        a.run("new task")
    cancel_mock.assert_not_called()              # the old task must not be touched
    assert a.current_task_id == "old-task"       # ...and its handle must survive
