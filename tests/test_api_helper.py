"""_parse_action_response: JSON body vs. safe fallback (no network)."""

from unittest.mock import MagicMock

import requests

from nomix_clicker import api_helper
from nomix_clicker.api_helper import _parse_action_response


class _Resp:
    def __init__(self, data=None, raises=False, status=500):
        self._data = data
        self._raises = raises
        self.status_code = status
        self.ok = status < 400

    def json(self):
        if self._raises:
            raise ValueError("no json body")
        return self._data

    def raise_for_status(self):
        pass


def test_returns_parsed_json():
    assert _parse_action_response(_Resp(data={"success": True}, status=200)) == {"success": True}


def test_falls_back_on_invalid_json():
    result = _parse_action_response(_Resp(raises=True, status=502))
    assert result["success"] is False
    assert "502" in result["message"]


def test_empty_2xx_body_counts_as_success():
    result = _parse_action_response(_Resp(raises=True, status=200))
    assert result["success"] is True


def test_refused_command_reports_the_server_reason():
    body = {"detail": {"code": -32004, "message": "Device is offline", "outcome": "not_sent"}}
    assert _parse_action_response(_Resp(data=body, status=503)) == {
        "success": False, "message": "Device is offline", "status_code": 503, "code": -32004, "outcome": "not_sent",
    }


def test_validation_error_joins_messages():
    body = {"detail": [{"msg": "Input should be 'up' or 'down'"}, {"msg": "Field required"}]}
    result = _parse_action_response(_Resp(data=body, status=422))
    assert result["success"] is False
    assert result["message"] == "Input should be 'up' or 'down'; Field required"


def test_plain_error_detail_becomes_the_message():
    result = _parse_action_response(_Resp(data={"detail": "Invalid API key"}, status=401))
    assert result == {"success": False, "message": "Invalid API key", "status_code": 401}


def test_unreachable_node_names_the_error():
    body = {"detail": {"error": "remote_unreachable", "host": "us.nomixclicker.com"}}
    assert _parse_action_response(_Resp(data=body, status=503))["message"] == "remote_unreachable"


def test_no_active_agent_task_is_none(monkeypatch):
    monkeypatch.setattr(api_helper.session, "get", MagicMock(return_value=_Resp(status=404)))
    assert api_helper.get_active_agent_task("dev") is None


def test_run_agent_sends_timezone_only_when_given(monkeypatch):
    post = MagicMock(return_value=_Resp(data={"task_id": "t"}, status=200))
    monkeypatch.setattr(api_helper.session, "post", post)
    api_helper.run_agent("dev", "task")
    api_helper.run_agent("dev", "task", timezone="Europe/Moscow")
    assert [call.kwargs["json"] for call in post.call_args_list] == [
        {"task": "task"}, {"task": "task", "timezone": "Europe/Moscow"},
    ]


def test_read_timeout_leaves_the_outcome_unknown(monkeypatch):
    monkeypatch.setattr(api_helper.session, "post", MagicMock(side_effect=requests.ReadTimeout("slow")))
    assert api_helper._post_action("http://x/tap")["outcome"] == "unknown"


def test_ai_quota_refusal_after_dispatch_leaves_the_outcome_unknown(monkeypatch):
    response = _Resp(data={"detail": "AI quota exceeded"}, status=429)
    monkeypatch.setattr(api_helper.session, "post", MagicMock(return_value=response))
    assert api_helper._post_action("http://x/tap", screen=True)["outcome"] == "unknown"
    assert "outcome" not in api_helper._post_action("http://x/tap")


def test_post_action_swallows_network_errors(monkeypatch):
    monkeypatch.setattr(api_helper.session, "post",
                        MagicMock(side_effect=requests.ConnectionError("down")))
    result = api_helper._post_action("http://x/click")
    assert result["success"] is False
    assert "down" in result["message"]
