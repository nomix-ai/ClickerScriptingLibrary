import math
import mimetypes
import os
from contextlib import ExitStack
from http.client import parse_headers
from io import BytesIO
from pathlib import Path
from time import monotonic

import pycurl
import requests

from .environment import get_api_key, get_api_url


def media_progress(download_total: int, downloaded: int, upload_total: int, uploaded: int) -> int:
    # Let Python process interrupts while libcurl waits.
    return 0


def media_request(method: str, path: str, timeout: float, file: Path | None = None) -> dict:
    deadline = monotonic() + timeout
    url = f"{get_api_url()}{path}"
    headers = [f"X-API-Key: {get_api_key()}".encode("utf-8")]
    proxy = requests.utils.select_proxy(url, requests.utils.get_environ_proxies(url))
    bundle = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("CURL_CA_BUNDLE") or requests.certs.where()
    body = BytesIO()
    response_headers = BytesIO()
    try:
        with pycurl.Curl() as client, ExitStack() as resources:
            client.setopt(pycurl.URL, url.encode("utf-8"))
            if method == "POST":
                client.setopt(pycurl.POST, True)
            else:
                client.setopt(pycurl.CUSTOMREQUEST, method)
            client.setopt(pycurl.HTTPHEADER, headers)
            client.setopt(pycurl.WRITEDATA, body)
            client.setopt(pycurl.WRITEHEADER, response_headers)
            client.setopt(pycurl.FOLLOWLOCATION, True)
            client.setopt(pycurl.MAXREDIRS, 30)
            client.setopt(pycurl.ACCEPT_ENCODING, "")
            client.setopt(pycurl.NOSIGNAL, True)
            client.setopt(pycurl.NOPROGRESS, False)
            client.setopt(pycurl.XFERINFOFUNCTION, media_progress)
            client.setopt(pycurl.PROXY, (proxy or "").encode("utf-8"))
            client.setopt(pycurl.NOPROXY, "")
            if Path(bundle).is_dir():
                client.setopt(pycurl.CAINFO, None)
                client.setopt(pycurl.PROXY_CAINFO, None)
                client.setopt(pycurl.CAPATH, os.fsencode(bundle))
                client.setopt(pycurl.PROXY_CAPATH, os.fsencode(bundle))
            else:
                client.setopt(pycurl.CAINFO, os.fsencode(bundle))
                client.setopt(pycurl.PROXY_CAINFO, os.fsencode(bundle))
            if file is not None:
                form = resources.enter_context(pycurl.CurlMime(client))
                content_type = mimetypes.guess_type(file.name)[0] or "application/octet-stream"
                form.add_file("file", os.fsencode(file), filename=file.name.encode("utf-8"), content_type=content_type)
                client.setopt(pycurl.MIMEPOST, form)
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise requests.Timeout("Media request timed out")
            client.setopt(pycurl.TIMEOUT_MS, max(1, math.ceil(remaining * 1000)))
            client.perform()
            result = requests.Response()
            result.status_code = client.getinfo(pycurl.RESPONSE_CODE)
            result.url = client.getinfo(pycurl.EFFECTIVE_URL)
    except pycurl.error as error:
        code = error.args[0]
        if code == pycurl.E_OPERATION_TIMEDOUT:
            raise requests.Timeout(str(error)) from error
        if code in (pycurl.E_SSL_CACERT_BADFILE, pycurl.E_PEER_FAILED_VERIFICATION, pycurl.E_SSL_CONNECT_ERROR):
            raise requests.exceptions.SSLError(str(error)) from error
        raise requests.ConnectionError(str(error)) from error
    blocks = response_headers.getvalue().split(b"\r\n\r\n")
    last_headers = next(block for block in reversed(blocks) if block.startswith(b"HTTP/"))
    status_line, separator, header_lines = last_headers.partition(b"\r\n")
    status_parts = status_line.split(b" ", 2)
    result.reason = status_parts[2].decode("latin-1") if len(status_parts) == 3 else ""
    result.headers.update(parse_headers(BytesIO(header_lines)))
    result.raw = body
    body.seek(0)
    result.raise_for_status()
    payload = result.json() if result.status_code != 204 else {}
    if not isinstance(payload, dict):
        raise requests.RequestException("Expected a JSON object from the media API")
    return payload
