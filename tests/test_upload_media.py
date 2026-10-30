"""upload_media and the media endpoints — network mocked."""

import asyncio
import socket
from time import monotonic, sleep
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest

from nomix_clicker import Clicker, api_helper, upload_media
from nomix_clicker.media_upload import MediaUpload

QUEUED = {"id": "m-1", "kind": "photo", "filename": "a.jpg", "status": "queued"}
SAVED = {**QUEUED, "status": "saved"}
FAILED = {**QUEUED, "status": "failed", "error": "disk full"}


@pytest.fixture(autouse=True)
def local_photo(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.jpg").write_bytes(b"\xff\xd8\xff")


async def mocked_request(upload, session, method, deadline, suffix="", data=None):
    if method == "POST":
        return await upload.transport[method](upload.device_id, str(upload.path))
    if method == "DELETE":
        return await upload.transport[method](upload.device_id, suffix.lstrip("/"))
    return await upload.transport[method](upload.device_id)


def _mock_media(monkeypatch, send=None, lists=(), delete=None):
    send = send or AsyncMock(return_value=QUEUED)
    list_ = AsyncMock(side_effect=list(lists))
    delete = delete or AsyncMock(return_value={"status": "deleted"})
    monkeypatch.setattr(MediaUpload, "transport", {"POST": send, "GET": list_, "DELETE": delete}, raising=False)
    monkeypatch.setattr(MediaUpload, "request", mocked_request)
    return send, list_, delete


def _http_error(status, body):
    return aiohttp.ClientResponseError(MagicMock(), (), status=status, message=body["detail"])


async def stalled_request(*args):
    await asyncio.sleep(10)


def stalled_resolution(*args, **kwargs):
    sleep(1)
    return []


def test_waits_until_saved(monkeypatch):
    send, list_, _ = _mock_media(monkeypatch, lists=[
        {"items": [QUEUED]},
        {"items": [SAVED]},
    ])
    assert upload_media(Clicker("dev"), "a.jpg", interval=0.001) == SAVED
    send.assert_called_once_with("dev", "a.jpg")
    assert list_.call_count == 2


def test_finds_its_item_among_others(monkeypatch):
    other = {**SAVED, "id": "m-0"}
    _mock_media(monkeypatch, lists=[{"items": [other, QUEUED]}, {"items": [SAVED, other]}])
    assert upload_media(Clicker("dev"), "a.jpg", interval=0.001)["id"] == "m-1"


def test_returns_none_when_phone_fails(monkeypatch):
    _mock_media(monkeypatch, lists=[{"items": [FAILED]}])
    assert upload_media(Clicker("dev"), "a.jpg", interval=0.001) is None


def test_rejected_upload_returns_none(monkeypatch, caplog):
    send = AsyncMock(side_effect=_http_error(415, {"detail": "not JPEG, PNG, HEIC, MP4 or MOV"}))
    _, list_, _ = _mock_media(monkeypatch, send=send)
    assert upload_media(Clicker("dev"), "a.jpg") is None
    list_.assert_not_called()
    assert "415" in caplog.text
    assert "not JPEG" in caplog.text


def test_tolerates_transient_poll_errors(monkeypatch):
    _mock_media(monkeypatch, lists=[aiohttp.ClientConnectionError("blip"), {"items": [SAVED]}])
    assert upload_media(Clicker("dev"), "a.jpg", interval=0.001) == SAVED


@pytest.mark.parametrize("stage", ["upload", "status", "sleep", "zero", "dns"])
def test_timeout_withdraws_the_file(monkeypatch, stage):
    original_request = MediaUpload.request
    send = AsyncMock(side_effect=stalled_request) if stage == "upload" else None
    send, list_, delete = _mock_media(monkeypatch, send=send)
    if stage == "status":
        list_.side_effect = stalled_request
    if stage == "dns":
        monkeypatch.setattr(MediaUpload, "request", original_request)
        monkeypatch.setattr("nomix_clicker.media_upload.get_api_url", lambda: "http://deadline.invalid")
        monkeypatch.setattr(socket, "getaddrinfo", stalled_resolution)
    started = monotonic()
    assert upload_media(Clicker("dev"), "a.jpg", timeout=0 if stage == "zero" else 0.1,
                        interval=0.001 if stage == "status" else 2) is None
    assert monotonic() - started < 0.5
    if stage in ("upload", "zero", "dns"):
        delete.assert_not_called()
    else:
        delete.assert_called_once_with("dev", "m-1")
    if stage != "status":
        list_.assert_not_called()
    if stage == "zero":
        send.assert_not_called()


@pytest.mark.parametrize("error", ["404", "stall"])
def test_timeout_survives_failed_withdraw(monkeypatch, error):
    effect = stalled_request if error == "stall" else _http_error(404, {"detail": "No such file waiting for the phone"})
    delete = AsyncMock(side_effect=effect)
    _mock_media(monkeypatch, delete=delete)
    started = monotonic()
    assert upload_media(Clicker("dev"), "a.jpg", timeout=0.1) is None
    assert monotonic() - started < 0.5


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
