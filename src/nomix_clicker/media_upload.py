import asyncio
import logging
import math
import mimetypes
from pathlib import Path
from threading import Event
from time import monotonic
from typing import BinaryIO

import aiohttp

from .environment import get_api_key, get_api_url

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 15.0
CLEANUP_TIMEOUT = 5.0
CLEANUP_FRACTION = 0.1


class MediaUpload:
    device_id: str
    path: Path
    handle: BinaryIO
    timeout: float
    interval: float
    deadline: float
    work_deadline: float
    item: dict | None
    upload_started: bool
    upload_rejected: bool
    loop: asyncio.AbstractEventLoop | None
    task: asyncio.Task | None
    cancelled: Event

    def __init__(
            self, device_id: str, path: Path, handle: BinaryIO,
            timeout: float, interval: float, deadline: float,
    ) -> None:
        self.device_id = device_id
        self.path = path
        self.handle = handle
        self.timeout = timeout
        self.interval = interval
        self.deadline = deadline
        self.work_deadline = deadline - min(CLEANUP_TIMEOUT, timeout * CLEANUP_FRACTION)
        self.item = None
        self.upload_started = False
        self.upload_rejected = False
        self.loop = None
        self.task = None
        self.cancelled = Event()

    def run(self) -> dict | None:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(self.execute())
        finally:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.run_until_complete(loop.shutdown_asyncgens())
            loop.close()

    def cancel(self) -> None:
        self.cancelled.set()
        if self.loop is not None and self.task is not None and not self.loop.is_closed():
            try:
                self.loop.call_soon_threadsafe(self.task.cancel)
            except RuntimeError:
                if not self.loop.is_closed():
                    raise

    async def request(
            self, session: aiohttp.ClientSession, method: str, deadline: float,
            suffix: str = "", data: aiohttp.FormData | None = None,
    ) -> dict:
        base_url = await asyncio.to_thread(get_api_url)
        api_key = await asyncio.to_thread(get_api_key)
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise asyncio.TimeoutError
        budget = remaining if method == "POST" else min(REQUEST_TIMEOUT, remaining)
        timeout = aiohttp.ClientTimeout(total=budget, ceil_threshold=math.inf)
        async with session.request(
                method, f"{base_url}/{self.device_id}/media{suffix}",
                headers={"X-API-Key": api_key}, data=data, timeout=timeout,
        ) as response:
            if response.status >= 400:
                if method == "POST":
                    self.upload_rejected = True
                try:
                    body = await response.json(content_type=None)
                except ValueError:
                    body = None
                detail = body.get("detail") if isinstance(body, dict) else None
                raise aiohttp.ClientResponseError(
                    response.request_info, response.history, status=response.status,
                    message=str(detail or response.reason), headers=response.headers,
                )
            if response.status == 204:
                return {}
            body = await response.json(content_type=None)
            if not isinstance(body, dict):
                raise ValueError("Expected a JSON object from the media API")
            return body

    async def send_and_wait(self, session: aiohttp.ClientSession) -> dict | None:
        guessed_type, encoding = await asyncio.to_thread(mimetypes.guess_type, self.path.name)
        content_type = guessed_type or "application/octet-stream"
        data = aiohttp.FormData()
        data.add_field("file", self.handle, filename=self.path.name, content_type=content_type)
        logger.info("Uploading '%s'...", self.path.name)
        self.upload_started = True
        item = await self.request(session, "POST", self.work_deadline, data=data)
        if not item.get("id") or item.get("status") not in ("queued", "saved", "failed"):
            raise ValueError("Invalid media item returned by the media API")
        self.item = item
        media_id = item["id"]
        logger.info("Waiting for the phone to save '%s'...", self.path.name)
        while self.item.get("status") not in ("saved", "failed"):
            await asyncio.sleep(min(self.interval, max(0, self.work_deadline - monotonic())))
            if monotonic() >= self.work_deadline:
                raise asyncio.TimeoutError
            try:
                result = await self.request(session, "GET", self.work_deadline)
                items = result.get("items")
                if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
                    raise ValueError("Invalid media list returned by the media API")
            except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
                logger.warning("Media status check failed (%s), retrying", str(error) or type(error).__name__)
                continue
            self.item = next((item for item in items if item.get("id") == media_id), self.item)
        if self.item["status"] == "failed":
            logger.error("The phone could not save '%s': %s", self.path.name, self.item.get("error"))
            return None
        logger.info("'%s' saved to Photos", self.path.name)
        return self.item

    async def withdraw(self, session: aiohttp.ClientSession) -> None:
        deadline = min(self.deadline, monotonic() + CLEANUP_TIMEOUT)
        try:
            await asyncio.wait_for(
                self.request(session, "DELETE", deadline, f"/{self.item['id']}"),
                max(0, deadline - monotonic()),
            )
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
            logger.warning("Could not withdraw '%s' (%s), it may still appear in Photos",
                           self.path.name, str(error) or type(error).__name__)

    async def execute(self) -> dict | None:
        self.loop = asyncio.get_running_loop()
        self.task = asyncio.current_task()
        if self.cancelled.is_set():
            raise asyncio.CancelledError
        async with aiohttp.ClientSession(trust_env=True) as session:
            try:
                remaining = max(0, self.work_deadline - monotonic())
                return await asyncio.wait_for(self.send_and_wait(session), remaining)
            except asyncio.TimeoutError:
                logger.error("Upload of '%s' did not finish within %.3gs", self.path.name, self.timeout)
            except (aiohttp.ClientError, ValueError) as error:
                logger.error("Upload of '%s' rejected: %s", self.path.name, error)
            finally:
                if self.item is not None and self.item.get("status") == "queued":
                    await self.withdraw(session)
                elif self.item is None and self.upload_started and not self.upload_rejected:
                    logger.warning("No media ID received for '%s'; if the server accepted it, it may still appear in Photos", self.path.name)
        return None
