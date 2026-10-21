import json
import math
from concurrent.futures import Future, TimeoutError as FutureTimeout
from threading import Lock, Thread, current_thread
from typing import Any
from urllib.parse import quote, urlsplit

import requests
import websocket

from .environment import get_api_key, get_api_url

MAX_MESSAGE_BYTES = 65536
MAX_REQUEST_ID = 9007199254740991
MAX_PENDING = 32


class ControlError(RuntimeError):
    code: int
    outcome: str

    def __init__(self, code: int, message: str, outcome: str = "not_sent"):
        super().__init__(message)
        self.code = code
        self.outcome = outcome


class ControlSession:
    device_id: str
    api_key: str
    api_url: str
    timeout: float
    socket: websocket.WebSocket | None
    reader: Thread | None
    lock: Any
    send_lock: Any
    lifecycle: Any
    pending: dict[int, Future]
    last_id: int
    state: dict
    closed: bool

    def __init__(self, device_id: str, *, api_key: str | None = None, api_url: str | None = None, timeout: float = 10):
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError("timeout must be positive")
        self.device_id = device_id
        self.api_key = get_api_key() if api_key is None else api_key
        self.api_url = (get_api_url() if api_url is None else api_url).rstrip("/")
        self.timeout = timeout
        self.socket = None
        self.reader = None
        self.lock = Lock()
        self.send_lock = Lock()
        self.lifecycle = Lock()
        self.pending = {}
        self.last_id = 0
        self.state = {}
        self.closed = False

    def connect(self) -> None:
        with self.lifecycle:
            if self.closed:
                raise ControlError(-32004, "Create a new session after disconnect")
            if self.socket is not None:
                return
            with requests.Session() as session:
                response = session.get(
                    f"{self.api_url}/{quote(self.device_id, safe='')}/control",
                    headers={"X-API-Key": self.api_key}, timeout=self.timeout,
                )
                response.raise_for_status()
                endpoint = response.json()
            url = endpoint.get("websocket_url") if isinstance(endpoint, dict) else None
            if not isinstance(url, str) or endpoint.get("protocol_version") != 1 or urlsplit(url).scheme not in ("ws", "wss"):
                raise ControlError(-32600, "Unsupported control endpoint")
            try:
                socket = websocket.create_connection(
                    url, header={"X-API-Key": self.api_key}, timeout=self.timeout,
                    suppress_origin=True, redirect_limit=0, enable_multithread=True,
                )
            except (OSError, websocket.WebSocketException):
                self.closed = True
                raise ControlError(-32004, "Control connection could not be opened") from None
            with self.lock:
                if self.closed:
                    socket.shutdown()
                    raise ControlError(-32004, "Control session closed while connecting")
                self.socket = socket
                self.reader = Thread(target=self.read, name="nomix-control", daemon=True)
                self.reader.start()

    def close(self) -> None:
        with self.lock:
            self.closed = True
            pending, self.pending = self.pending, {}
            socket, self.socket = self.socket, None
            reader = self.reader
        for future in pending.values():
            future.set_exception(ControlError(-32007, "Control connection closed", "unknown"))
        if socket is not None:
            socket.abort()
            socket.shutdown()
        if reader is not None and reader is not current_thread():
            reader.join(self.timeout + 1)

    def request(self, method: str, params: dict | None = None, *, timeout: float | None = None) -> dict:
        deadline = self.timeout if timeout is None else timeout
        if not math.isfinite(deadline) or deadline <= 0:
            raise ValueError("timeout must be positive")
        with self.send_lock:
            with self.lock:
                if self.closed or self.socket is None:
                    raise ControlError(-32004, "Connect and acquire control before sending commands")
                capacity = MAX_PENDING + 4 if method.startswith("control.") else MAX_PENDING
                if len(self.pending) >= capacity:
                    raise ControlError(-32003, "Too many pending control requests")
                if self.last_id >= MAX_REQUEST_ID:
                    raise ControlError(-32600, "Control session exhausted its request ids")
                self.last_id += 1
                request_id = self.last_id
                message = json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}, allow_nan=False)
                if len(message.encode("utf-8")) > MAX_MESSAGE_BYTES:
                    raise ControlError(-32600, "Control request is too large")
                future: Future = Future()
                self.pending[request_id] = future
                socket = self.socket
            try:
                socket.send(message)
            except (OSError, websocket.WebSocketException):
                self.close()
                raise ControlError(-32007, "Control request outcome is unknown", "unknown") from None
            except KeyboardInterrupt:
                self.close()
                raise
        try:
            return future.result(timeout=deadline)
        except FutureTimeout:
            self.close()
            raise ControlError(-32007, "Control request timed out; outcome is unknown", "unknown") from None
        except KeyboardInterrupt:
            self.close()
            raise

    def read(self) -> None:
        socket = self.socket
        if socket is None:
            return
        try:
            while not self.closed:
                try:
                    message = socket.recv()
                except websocket.WebSocketTimeoutException:
                    continue
                if not isinstance(message, str) or not message or len(message.encode("utf-8")) > MAX_MESSAGE_BYTES:
                    break
                self.receive(json.loads(message))
        except (OSError, websocket.WebSocketException, ValueError, ControlError):
            pass
        finally:
            self.close()

    def receive(self, payload: Any) -> None:
        if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
            raise ControlError(-32600, "Invalid control response")
        if "method" in payload and "id" not in payload:
            if payload["method"] == "control.state" and isinstance(payload.get("params"), dict):
                self.state = payload["params"]
            return
        request_id = payload.get("id")
        if type(request_id) is not int or ("result" in payload) == ("error" in payload):
            raise ControlError(-32600, "Invalid control response")
        with self.lock:
            future = self.pending.get(request_id)
            if future is None:
                raise ControlError(-32600, "Unexpected control response")
            if "result" in payload:
                if not isinstance(payload["result"], dict):
                    raise ControlError(-32600, "Invalid control result")
                self.pending.pop(request_id)
                future.set_result(payload["result"])
            else:
                error = payload["error"]
                if not isinstance(error, dict) or type(error.get("code")) is not int or not isinstance(error.get("message"), str):
                    raise ControlError(-32600, "Invalid control error")
                data = error.get("data", {})
                outcome = data.get("outcome", "unknown") if isinstance(data, dict) else "unknown"
                if outcome not in ("not_sent", "partial", "unknown"):
                    outcome = "unknown"
                self.pending.pop(request_id)
                future.set_exception(ControlError(error["code"], error["message"], outcome))
