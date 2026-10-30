import asyncio
import math
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from time import monotonic

import aiohttp
import requests

from .environment import get_api_key, get_api_url


async def fetch_media(
        method: str, url: str, headers: dict[str, str], deadline: float,
        data: aiohttp.FormData | None,
) -> dict:
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise requests.Timeout("Media request timed out")
    timeout = aiohttp.ClientTimeout(total=remaining, ceil_threshold=math.inf)
    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=True) as client:
            async with client.request(method, url, headers=headers, data=data) as response:
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


def run_media_request(loop: asyncio.AbstractEventLoop, task: asyncio.Task) -> dict:
    try:
        return loop.run_until_complete(task)
    finally:
        pending = asyncio.all_tasks(loop)
        for pending_task in pending:
            pending_task.cancel()
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()


def media_request(method: str, path: str, timeout: float, data: aiohttp.FormData | None = None) -> dict:
    deadline = monotonic() + timeout
    url = f"{get_api_url()}{path}"
    headers = {"X-API-Key": get_api_key()}
    loop = asyncio.new_event_loop()
    task = loop.create_task(fetch_media(method, url, headers, deadline, data))
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return run_media_request(loop, task)
    with ThreadPoolExecutor(max_workers=1) as executor:
        try:
            return executor.submit(run_media_request, loop, task).result()
        except KeyboardInterrupt:
            try:
                loop.call_soon_threadsafe(task.cancel)
            except RuntimeError:
                if not loop.is_closed():
                    raise
            raise
