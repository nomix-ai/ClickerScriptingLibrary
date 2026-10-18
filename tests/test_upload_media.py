"""upload_media and the media endpoints — network mocked."""

from unittest.mock import MagicMock

import pytest
import requests

from nomix_clicker import Clicker, upload_media
from nomix_clicker import actions as actions_mod
from nomix_clicker import api_helper

QUEUED = {"id": "m-1", "kind": "photo", "filename": "a.jpg", "status": "queued"}
SAVED = {**QUEUED, "status": "saved"}
FAILED = {**QUEUED, "status": "failed", "error": "disk full"}


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(actions_mod, "sleep", lambda s: None)


def _mock_media(monkeypatch, send=None, lists=(), delete=None):
    send = send or MagicMock(return_value=QUEUED)
    list_ = MagicMock(side_effect=list(lists))
    delete = delete or MagicMock(return_value={"status": "deleted"})
    monkeypatch.setattr(actions_mod, "send_media", send)
    monkeypatch.setattr(actions_mod, "list_media", list_)
    monkeypatch.setattr(actions_mod, "delete_media", delete)
    return send, list_, delete


def _http_error(status, body):
    err = requests.HTTPError(f"{status} Error")
    err.response = MagicMock(status_code=status, reason="Error")
    err.response.json.return_value = body
    return err


def test_waits_until_saved(monkeypatch):
    send, list_, _ = _mock_media(monkeypatch, lists=[
        {"items": [QUEUED]},
        {"items": [SAVED]},
    ])
    assert upload_media(Clicker("dev"), "a.jpg") == SAVED
    send.assert_called_once_with("dev", "a.jpg")
    assert list_.call_count == 2


def test_finds_its_item_among_others(monkeypatch):
    other = {**SAVED, "id": "m-0"}
    _mock_media(monkeypatch, lists=[{"items": [other, QUEUED]}, {"items": [SAVED, other]}])
    assert upload_media(Clicker("dev"), "a.jpg")["id"] == "m-1"


def test_returns_none_when_phone_fails(monkeypatch):
    _mock_media(monkeypatch, lists=[{"items": [FAILED]}])
    assert upload_media(Clicker("dev"), "a.jpg") is None


def test_rejected_upload_returns_none(monkeypatch, capsys):
    send = MagicMock(side_effect=_http_error(415, {"detail": "not JPEG, PNG, HEIC, MP4 or MOV"}))
    _, list_, _ = _mock_media(monkeypatch, send=send)
    assert upload_media(Clicker("dev"), "a.gif") is None
    list_.assert_not_called()
    assert "HTTP 415: not JPEG" in capsys.readouterr().out


def test_tolerates_transient_poll_errors(monkeypatch):
    _mock_media(monkeypatch, lists=[requests.ConnectionError("blip"), {"items": [SAVED]}])
    assert upload_media(Clicker("dev"), "a.jpg") == SAVED


def test_timeout_withdraws_the_file(monkeypatch):
    _, list_, delete = _mock_media(monkeypatch)
    assert upload_media(Clicker("dev"), "a.jpg", timeout=0) is None
    delete.assert_called_once_with("dev", "m-1")
    list_.assert_not_called()


def test_timeout_survives_failed_withdraw(monkeypatch):
    delete = MagicMock(side_effect=_http_error(404, {"detail": "No such file waiting for the phone"}))
    _mock_media(monkeypatch, delete=delete)
    assert upload_media(Clicker("dev"), "a.jpg", timeout=0) is None


def test_send_media_posts_multipart(monkeypatch, tmp_path):
    photo = tmp_path / "beach.jpg"
    photo.write_bytes(b"\xff\xd8\xff")
    post = MagicMock(return_value=MagicMock(json=MagicMock(return_value=QUEUED)))
    monkeypatch.setattr(api_helper.session, "post", post)

    assert api_helper.send_media("dev", photo) == QUEUED
    url = post.call_args.args[0]
    filename, _, content_type = post.call_args.kwargs["files"]["file"]
    assert url.endswith("/dev/media")
    assert filename == "beach.jpg"
    assert content_type == "image/jpeg"
