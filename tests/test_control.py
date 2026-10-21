import json
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Event, Thread

import pytest
from websockets.exceptions import ConnectionClosed
from websockets.sync.server import serve

from nomix_clicker import ControlError, ControlSession


class Discovery(BaseHTTPRequestHandler):
    def do_GET(self):
        self.server.paths.append(self.path)
        self.server.keys.append(self.headers.get("X-API-Key"))
        payload = json.dumps({"protocol_version": 1, "websocket_url": self.server.control_url}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *args):
        pass


class Server:
    def __init__(self):
        self.connections = 0
        self.messages = []
        self.keys = []
        self.origins = []
        self.mode = "normal"
        self.received = Event()
        self.release = Event()

    def handler(self, socket):
        self.connections += 1
        self.keys.append(socket.request.headers.get("X-API-Key"))
        self.origins.append(socket.request.headers.get("Origin"))
        try:
            for message in socket:
                request = json.loads(message)
                self.messages.append(request)
                self.received.set()
                for _ in range(3):
                    socket.send(json.dumps({"jsonrpc": "2.0", "method": "control.state", "params": {"online": True}}))
                if self.mode == "disconnect":
                    socket.close()
                    return
                if self.mode == "timeout":
                    self.release.wait(2)
                    return
                if self.mode == "malformed":
                    socket.send('{"jsonrpc":"2.0","id":true,"result":{}}')
                elif self.mode == "error":
                    socket.send(json.dumps({"jsonrpc": "2.0", "id": request["id"], "error": {
                        "code": -32002, "message": "busy", "data": {"outcome": "not_sent"},
                    }}))
                elif self.mode == "reverse" and request["id"] % 2:
                    continue
                else:
                    targets = self.messages[-2:][::-1] if self.mode == "reverse" else [request]
                    for target in targets:
                        socket.send(json.dumps({"jsonrpc": "2.0", "id": target["id"], "result": {
                            "status": "sent", "device_acknowledged": False, "method": target["method"],
                        }}))
        except ConnectionClosed:
            pass


@pytest.fixture
def service():
    fixture = Server()
    with serve(fixture.handler, "127.0.0.1", 0) as socket_server:
        socket_thread = Thread(target=socket_server.serve_forever, daemon=True)
        socket_thread.start()
        http = ThreadingHTTPServer(("127.0.0.1", 0), Discovery)
        http.control_url = f"ws://127.0.0.1:{socket_server.socket.getsockname()[1]}/control/Device"
        http.paths, http.keys = [], []
        http_thread = Thread(target=http.serve_forever, daemon=True)
        http_thread.start()
        client = ControlSession("Device", api_key="test-key", api_url=f"http://127.0.0.1:{http.server_port}/clicker/v1", timeout=.3)
        try:
            client.connect()
            yield client, fixture, http
        finally:
            fixture.release.set()
            client.close()
            http.shutdown()
            http.server_close()
            http_thread.join(2)
            socket_server.shutdown()
            socket_thread.join(2)
        assert not client.reader.is_alive()


def test_discovery_auth_notifications_and_monotonic_ids(service):
    client, fixture, http = service
    result = client.request("control.acquire")
    assert result["device_acknowledged"] is False
    client.request("input.tap", {"left": 1, "top": 2})
    assert [message["id"] for message in fixture.messages] == [1, 2]
    assert http.paths == ["/clicker/v1/Device/control"]
    assert http.keys == fixture.keys == ["test-key"]
    assert fixture.origins == [None]
    assert client.state == {"online": True}


@pytest.mark.parametrize("mode", ["disconnect", "timeout", "malformed"])
def test_unknown_outcome_closes_without_replay_or_reconnect(service, mode):
    client, fixture, _ = service
    fixture.mode = mode
    with pytest.raises(ControlError) as error:
        client.request("input.tap", {"left": 1, "top": 2})
    assert error.value.outcome == "unknown"
    with pytest.raises(ControlError):
        client.request("input.tap", {"left": 1, "top": 2})
    with pytest.raises(ControlError):
        client.connect()
    assert len(fixture.messages) == fixture.connections == 1


def test_refused_action_preserves_error_and_session(service):
    client, fixture, _ = service
    fixture.mode = "error"
    with pytest.raises(ControlError) as error:
        client.request("control.acquire")
    assert error.value.code == -32002 and error.value.outcome == "not_sent"
    fixture.mode = "normal"
    client.request("control.status")
    assert not client.closed


def test_concurrent_replies_correlate_by_id(service):
    client, fixture, _ = service
    fixture.mode = "reverse"
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(client.request, "control.status")
        assert fixture.received.wait(1)
        second = pool.submit(client.request, "control.ping")
        assert second.result(1)["method"] == "control.ping"
        assert first.result(1)["method"] == "control.status"
    assert not client.pending


def test_oversized_request_never_reaches_socket(service):
    client, fixture, _ = service
    with pytest.raises(ControlError) as error:
        client.request("input.text", {"text": "x" * 65536})
    assert error.value.outcome == "not_sent"
    assert not fixture.messages


def test_close_settles_in_flight_request(service):
    client, fixture, _ = service
    fixture.mode = "timeout"
    with ThreadPoolExecutor(1) as pool:
        future = pool.submit(client.request, "input.tap", {"left": 1, "top": 2})
        assert fixture.received.wait(1)
        client.close()
        with pytest.raises(ControlError) as error:
            future.result(1)
    assert error.value.outcome == "unknown"
