"""_parse_action_response: JSON body vs. safe fallback (no network)."""

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


def test_returns_parsed_json():
    assert _parse_action_response(_Resp(data={"success": True})) == {"success": True}


def test_falls_back_on_invalid_json():
    result = _parse_action_response(_Resp(raises=True, status=502))
    assert result["success"] is False
    assert "502" in result["message"]


def test_empty_2xx_body_counts_as_success():
    result = _parse_action_response(_Resp(raises=True, status=200))
    assert result["success"] is True


def test_post_action_swallows_network_errors(monkeypatch):
    import requests
    from unittest.mock import MagicMock
    from nomix_clicker import api_helper
    monkeypatch.setattr(api_helper.session, "post",
                        MagicMock(side_effect=requests.ConnectionError("down")))
    result = api_helper._post_action("http://x/click")
    assert result["success"] is False
    assert "down" in result["message"]
