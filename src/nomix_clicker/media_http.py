import asyncio
import math
import os
import ssl
from collections.abc import Coroutine
from concurrent.futures import Future, ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from time import monotonic

import aiohttp
import requests

from .environment import get_api_key, get_api_url


async def fetch_media(
        method: str, url: str, headers: dict[str, str], deadline: float,
        data: aiohttp.FormData | None, ssl_context: ssl.SSLContext | bool,
) -> dict:
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise requests.Timeout("Media request timed out")
    timeout = aiohttp.ClientTimeout(total=remaining, ceil_threshold=math.inf)
    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as client:
            async with client.request(method, url, headers=headers, data=data, ssl=ssl_context) as response:
                result = requests.Response()
                result.status_code = response.status
                result.reason = response.reason
                result.url = str(response.url)
                result.headers.update(response.headers)
                result.raw = BytesIO(await response.read())
                result.raise_for_status()
                body = result.json() if response.status != 204 else {}
                if not isinstance(body, dict):
                    raise requests.RequestException("Expected a JSON object from the media API")
                return body
    except asyncio.TimeoutError as error:
        raise requests.Timeout("Media request timed out") from error
    except aiohttp.ClientError as error:
        raise requests.ConnectionError(str(error)) from error


def run_media_request(coroutine: Coroutine, ready: Future | None = None) -> dict:
    loop = asyncio.new_event_loop()
    try:
        task = loop.create_task(coroutine)
        if ready is not None:
            ready.set_result((loop, task))
        return loop.run_until_complete(task)
    finally:
        pending = asyncio.all_tasks(loop)
        for pending_task in pending:
            pending_task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


def cancel_media_request(ready: Future) -> None:
    loop, task = ready.result()
    try:
        loop.call_soon_threadsafe(task.cancel)
    except RuntimeError:
        if not loop.is_closed():
            raise


def media_request(method: str, path: str, timeout: float, data: aiohttp.FormData | None = None) -> dict:
    deadline = monotonic() + timeout
    url = f"{get_api_url()}{path}"
    headers = {"X-API-Key": get_api_key()}
    bundle = os.environ.get("REQUESTS_CA_BUNDLE") or os.environ.get("CURL_CA_BUNDLE")
    ssl_context: ssl.SSLContext | bool = True
    if bundle:
        try:
            if Path(bundle).is_dir():
                ssl_context = ssl.create_default_context(capath=bundle)
            else:
                ssl_context = ssl.create_default_context(cafile=bundle)
        except ssl.SSLError as error:
            raise requests.exceptions.SSLError(str(error)) from error
    coroutine = fetch_media(method, url, headers, deadline, data, ssl_context)
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return run_media_request(coroutine)
    ready = Future()
    with ThreadPoolExecutor(max_workers=1) as executor:
        try:
            return executor.submit(run_media_request, coroutine, ready).result()
        except KeyboardInterrupt:
            ready.add_done_callback(cancel_media_request)
            raise
