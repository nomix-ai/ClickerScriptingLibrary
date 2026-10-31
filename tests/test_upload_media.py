"""upload_media and the media endpoints — network mocked."""

import asyncio
import json
import os
from email.message import Message
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from time import monotonic, sleep
from typing import Any
from unittest.mock import MagicMock

import pycurl
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


def curl_options(client: MagicMock) -> dict[int, Any]:
    return {call.args[0]: call.args[1] for call in client.setopt.call_args_list}


def complete_curl_request(client: MagicMock) -> None:
    options = curl_options(client)
    options[pycurl.WRITEDATA].write(json.dumps(QUEUED).encode())
    options[pycurl.WRITEHEADER].write(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")


def curl_response_info(option: int) -> int | str:
    return 200 if option == pycurl.RESPONSE_CODE else "https://media.example/dev/media"


@pytest.fixture
def curl_client(monkeypatch):
    client = MagicMock()
    client.__enter__.return_value = client
    client.perform.side_effect = partial(complete_curl_request, client)
    client.getinfo.side_effect = curl_response_info
    monkeypatch.setattr(pycurl, "Curl", MagicMock(return_value=client))
    monkeypatch.setattr(media_http, "get_api_key", lambda: "test-api-key")
    return client


class UploadHandler(BaseHTTPRequestHandler):
    def log_message(self, *args: object) -> None:
        pass

    def do_POST(self) -> None:
        self.server.methods.append("POST")
        self.server.received = self.rfile.read(int(self.headers["Content-Length"]))
        if self.path == "/dev/media" and self.server.redirect:
            self.send_response(self.server.redirect)
            self.send_header("Location", "/accepted")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return
        self.respond()

    def do_GET(self) -> None:
        self.server.methods.append("GET")
        self.respond()

    def respond(self) -> None:
        body = json.dumps(QUEUED).encode()
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture
def upload_server(monkeypatch):
    server = ThreadingHTTPServer(("127.0.0.1", 0), UploadHandler)
    server.daemon_threads = True
    server.redirect = 0
    server.methods = []
    thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    monkeypatch.setattr(media_http, "get_api_url", lambda: f"http://127.0.0.1:{server.server_port}")
    monkeypatch.setattr(media_http, "get_api_key", lambda: "test-api-key")
    monkeypatch.setenv("NO_PROXY", "*")
    monkeypatch.setenv("no_proxy", "*")
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


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


@pytest.mark.parametrize("stage", ["upload", "status", "sleep", "zero", "upload_time"])
def test_timeout_withdraws_the_file(monkeypatch, stage):
    send = MagicMock(side_effect=stalled_request) if stage == "upload" else None
    send, list_, delete = _mock_media(monkeypatch, send=send)
    if stage == "status":
        list_.side_effect = stalled_request
    if stage == "upload_time":
        monkeypatch.setattr(actions_mod, "monotonic", MagicMock(side_effect=[0, 0, 80, 120]))
        monkeypatch.setattr(actions_mod, "sleep", MagicMock())
    timeout = 120 if stage == "upload_time" else 0 if stage == "zero" else 0.1
    interval = 60 if stage == "upload_time" else 0.001 if stage == "status" else 2
    started = monotonic()
    assert upload_media(Clicker("dev"), "a.jpg", timeout=timeout, interval=interval) is None
    assert monotonic() - started < 0.5
    if stage in ("upload", "zero"):
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


@pytest.mark.parametrize("filename", ["beach.jpg", "beach trip.jpg", "фото.jpg", "x+y.jpg"])
def test_send_media_posts_multipart(upload_server, tmp_path, filename):
    photo = tmp_path / filename
    photo.write_bytes(b"\xff\xd8\xff")
    result = api_helper.send_media("dev", photo)
    assert result["id"] == QUEUED["id"]
    body = upload_server.received
    disposition = next(line for line in body.split(b"\r\n") if line.startswith(b"Content-Disposition:"))
    header = Message()
    header["Content-Disposition"] = disposition.decode("utf-8").split(": ", 1)[1]
    assert header.get_filename() == filename.replace("\r", "%0D").replace("\n", "%0A")
    assert b"Content-Type: image/jpeg" in body
    assert b"\xff\xd8\xff" in body


@pytest.mark.parametrize("running_loop", [False, True])
def test_media_request_calling_modes(monkeypatch, curl_client, running_loop):
    monkeypatch.setattr(asyncio, "new_event_loop", MagicMock(side_effect=AssertionError("Transport must not create an event loop")))
    if running_loop:
        result = asyncio.run(media_request_in_running_loop())
    else:
        result = media_http.media_request("GET", "/dev/media", 1)
    assert result == QUEUED


@pytest.mark.parametrize("setting", ["requests", "curl", "precedence", "empty", "default", "directory"])
def test_media_ca_bundle(monkeypatch, tmp_path, curl_client, setting):
    bundle = tmp_path / "ca.pem"
    bundle.write_text("test CA bundle")
    if setting == "directory":
        bundle = tmp_path
    monkeypatch.delenv("REQUESTS_CA_BUNDLE", raising=False)
    monkeypatch.delenv("CURL_CA_BUNDLE", raising=False)
    if setting in ("requests", "precedence", "directory"):
        monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(bundle))
    if setting in ("curl", "empty"):
        monkeypatch.setenv("CURL_CA_BUNDLE", str(bundle))
    if setting == "precedence":
        monkeypatch.setenv("CURL_CA_BUNDLE", str(tmp_path / "missing.pem"))
    if setting == "empty":
        monkeypatch.setenv("REQUESTS_CA_BUNDLE", "")
    assert media_http.media_request("GET", "/dev/media", 1) == QUEUED
    options = curl_options(curl_client)
    if setting == "directory":
        assert options[pycurl.CAINFO] is None
        assert options[pycurl.PROXY_CAINFO] is None
        assert options[pycurl.CAPATH] == os.fsencode(bundle)
        assert options[pycurl.PROXY_CAPATH] == os.fsencode(bundle)
    else:
        expected = requests.certs.where() if setting == "default" else bundle
        assert options[pycurl.CAINFO] == os.fsencode(expected)
        assert options[pycurl.PROXY_CAINFO] == os.fsencode(expected)


@pytest.mark.parametrize("setting", ["http", "https", "all", "bypass", "cidr", "credentials"])
def test_media_proxy_settings(monkeypatch, curl_client, setting):
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "NO_PROXY"):
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(name.lower(), raising=False)
    url = "http://192.0.2.1" if setting == "cidr" else "https://media.example"
    proxy = "https://user:password@proxy.example:8443" if setting == "credentials" else "https://proxy.example:8443"
    monkeypatch.setenv("ALL_PROXY" if setting == "all" else "HTTPS_PROXY", proxy)
    if setting == "http":
        url = "http://media.example"
        monkeypatch.setenv("HTTP_PROXY", proxy)
    if setting == "bypass":
        monkeypatch.setenv("NO_PROXY", "media.example")
    if setting == "cidr":
        monkeypatch.setenv("HTTP_PROXY", proxy)
        monkeypatch.setenv("NO_PROXY", "192.0.2.0/24")
    monkeypatch.setattr(media_http, "get_api_url", lambda: url)
    assert media_http.media_request("GET", "/dev/media", 1) == QUEUED
    expected = "" if setting in ("bypass", "cidr") else proxy
    assert curl_options(curl_client)[pycurl.PROXY] == expected.encode()


@pytest.mark.parametrize("status", [301, 302, 307, 308])
def test_media_upload_redirects(upload_server, tmp_path, status):
    photo = tmp_path / "photo.jpg"
    photo.write_bytes(b"photo")
    upload_server.redirect = status
    assert api_helper.send_media("dev", photo)["id"] == QUEUED["id"]
    assert upload_server.methods == ["POST", "GET" if status in (301, 302) else "POST"]
