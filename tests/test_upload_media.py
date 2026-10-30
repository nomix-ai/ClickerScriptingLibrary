"""upload_media and the media endpoints — network mocked."""

import asyncio
import socket
import ssl
from collections.abc import Callable
from functools import partial
from threading import get_ident
from time import monotonic, sleep
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import aiohttp
import pytest
import requests

from nomix_clicker import Clicker, api_helper, media_http, upload_media
from nomix_clicker import actions as actions_mod

QUEUED = {"id": "m-1", "kind": "photo", "filename": "a.jpg", "status": "queued"}
SAVED = {**QUEUED, "status": "saved"}
FAILED = {**QUEUED, "status": "failed", "error": "disk full"}


@pytest.fixture(autouse=True)
def local_photo(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "a.jpg").write_bytes(b"\xff\xd8\xff")


def _mock_media(monkeypatch, send=None, lists=(), delete=None):
    send = send or MagicMock(return_value=QUEUED)
    list_ = MagicMock(side_effect=list(lists))
    delete = delete or MagicMock(return_value={"status": "deleted"})
    monkeypatch.setattr(actions_mod, "send_media", send)
    monkeypatch.setattr(actions_mod, "list_media", list_)
    monkeypatch.setattr(actions_mod, "delete_media", delete)
    return send, list_, delete


def _http_error(status, body):
    error = requests.HTTPError(f"{status} Error")
    error.response = MagicMock(status_code=status, reason="Error")
    error.response.json.return_value = body
    return error


def stalled_request(*args: object, timeout: float, **kwargs: object) -> dict:
    sleep(timeout)
    raise requests.Timeout("stalled")


def stalled_resolution(*args: object, **kwargs: object) -> list:
    sleep(1)
    return []


def capture_upload(method: str, path: str, timeout: float, data: aiohttp.FormData) -> dict:
    writer = AsyncMock()
    asyncio.run(data().write(writer))
    return {**QUEUED, "body": b"".join(call.args[0] for call in writer.write.await_args_list)}


def check_loop_thread(operation: Callable, owner: int, *args: Any) -> Any:
    assert get_ident() == owner
    return operation(*args)


def thread_checked_loop() -> asyncio.AbstractEventLoop:
    loop = asyncio.SelectorEventLoop()
    owner = get_ident()
    loop.run_until_complete = partial(check_loop_thread, loop.run_until_complete, owner)
    loop.close = partial(check_loop_thread, loop.close, owner)
    return loop


async def media_request_in_running_loop() -> dict:
    return media_http.media_request("GET", "/dev/media", 1)


def test_waits_until_saved(monkeypatch):
    send, list_, _ = _mock_media(monkeypatch, lists=[
        {"items": [QUEUED]},
        {"items": [SAVED]},
    ])
    assert upload_media(Clicker("dev"), "a.jpg", interval=0.001) == SAVED
    send.assert_called_once()
    assert send.call_args.args == ("dev", "a.jpg")
    assert 0 < send.call_args.kwargs["timeout"] <= 300
    assert list_.call_count == 2


def test_finds_its_item_among_others(monkeypatch):
    other = {**SAVED, "id": "m-0"}
    _mock_media(monkeypatch, lists=[{"items": [other, QUEUED]}, {"items": [SAVED, other]}])
    assert upload_media(Clicker("dev"), "a.jpg", interval=0.001)["id"] == "m-1"


def test_returns_none_when_phone_fails(monkeypatch):
    _mock_media(monkeypatch, lists=[{"items": [FAILED]}])
    assert upload_media(Clicker("dev"), "a.jpg", interval=0.001) is None


def test_rejected_upload_returns_none(monkeypatch, caplog):
    send = MagicMock(side_effect=_http_error(415, {"detail": "not JPEG, PNG, HEIC, MP4 or MOV"}))
    _, list_, _ = _mock_media(monkeypatch, send=send)
    assert upload_media(Clicker("dev"), "a.jpg") is None
    list_.assert_not_called()
    assert "HTTP 415: not JPEG" in caplog.text


def test_tolerates_transient_poll_errors(monkeypatch):
    _mock_media(monkeypatch, lists=[requests.ConnectionError("blip"), {"items": [SAVED]}])
    assert upload_media(Clicker("dev"), "a.jpg", interval=0.001) == SAVED


@pytest.mark.parametrize("stage", ["upload", "status", "sleep", "zero", "dns", "upload_time"])
def test_timeout_withdraws_the_file(monkeypatch, stage):
    send = MagicMock(side_effect=stalled_request) if stage == "upload" else None
    send, list_, delete = _mock_media(monkeypatch, send=send)
    if stage == "status":
        list_.side_effect = stalled_request
    if stage == "dns":
        monkeypatch.setattr(actions_mod, "send_media", api_helper.send_media)
        monkeypatch.setattr("nomix_clicker.media_http.get_api_url", lambda: "http://deadline.invalid")
        monkeypatch.setattr(socket, "getaddrinfo", stalled_resolution)
    if stage == "upload_time":
        monkeypatch.setattr(actions_mod, "monotonic", MagicMock(side_effect=[0, 0, 80, 120]))
        monkeypatch.setattr(actions_mod, "sleep", MagicMock())
    timeout = 120 if stage == "upload_time" else 0 if stage == "zero" else 0.1
    interval = 60 if stage == "upload_time" else 0.001 if stage == "status" else 2
    started = monotonic()
    assert upload_media(Clicker("dev"), "a.jpg", timeout=timeout, interval=interval) is None
    assert monotonic() - started < 0.5
    if stage in ("upload", "zero", "dns"):
        delete.assert_not_called()
    else:
        delete.assert_called_once_with("dev", "m-1", timeout=actions_mod.MEDIA_CLEANUP_TIMEOUT)
    if stage != "status":
        list_.assert_not_called()
    if stage == "zero":
        send.assert_not_called()
    if stage == "upload_time":
        actions_mod.sleep.assert_called_once_with(40)


@pytest.mark.parametrize("error", ["404", "stall"])
def test_timeout_survives_failed_withdraw(monkeypatch, error):
    effect = stalled_request if error == "stall" else _http_error(404, {"detail": "No such file waiting for the phone"})
    delete = MagicMock(side_effect=effect)
    _mock_media(monkeypatch, delete=delete)
    monkeypatch.setattr(actions_mod, "MEDIA_CLEANUP_TIMEOUT", 0.05)
    started = monotonic()
    assert upload_media(Clicker("dev"), "a.jpg", timeout=0.1) is None
    assert monotonic() - started < 0.5


def test_send_media_posts_multipart(monkeypatch, tmp_path):
    photo = tmp_path / "beach.jpg"
    photo.write_bytes(b"\xff\xd8\xff")
    request = MagicMock(side_effect=capture_upload)
    monkeypatch.setattr(api_helper, "media_request", request)

    result = api_helper.send_media("dev", photo)
    assert result["id"] == QUEUED["id"]
    assert b'name="file"; filename="beach.jpg"' in result["body"]
    assert b"Content-Type: image/jpeg" in result["body"]
    assert b"\xff\xd8\xff" in result["body"]
    assert request.call_args.args[:2] == ("POST", "/dev/media")
    assert 0 < request.call_args.args[2] <= 300


@pytest.mark.parametrize("running_loop", [False, True])
def test_media_loop_thread_ownership(monkeypatch, running_loop):
    monkeypatch.setattr(asyncio, "new_event_loop", thread_checked_loop)
    monkeypatch.setattr(media_http, "fetch_media", AsyncMock(return_value=QUEUED))
    if running_loop:
        result = asyncio.run(media_request_in_running_loop())
    else:
        result = media_http.media_request("GET", "/dev/media", 1)
    assert result == QUEUED


@pytest.mark.parametrize("setting", ["requests", "curl", "precedence", "empty", "default"])
def test_media_ca_bundle(monkeypatch, tmp_path, setting):
    certificate = ssl.create_default_context(cafile=requests.certs.where()).get_ca_certs(binary_form=True)[0]
    bundle = tmp_path / "ca.pem"
    bundle.write_text(ssl.DER_cert_to_PEM_cert(certificate))
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("CURL_CA_BUNDLE", raising=False)
    if setting in ("requests", "precedence"):
        monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(bundle))
    if setting in ("curl", "empty"):
        monkeypatch.setenv("CURL_CA_BUNDLE", str(bundle))
    if setting == "precedence":
        monkeypatch.setenv("CURL_CA_BUNDLE", str(tmp_path / "missing.pem"))
    if setting == "empty":
        monkeypatch.setenv("REQUESTS_CA_BUNDLE", "")
    fetch = AsyncMock(return_value=QUEUED)
    monkeypatch.setattr(media_http, "fetch_media", fetch)
    assert media_http.media_request("GET", "/dev/media", 1) == QUEUED
    context = fetch.call_args.args[-1]
    if setting == "default":
        assert context is True
    else:
        assert context.get_ca_certs(binary_form=True) == [certificate]
