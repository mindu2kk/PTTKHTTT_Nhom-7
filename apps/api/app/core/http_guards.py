import asyncio
import time
from collections import OrderedDict

from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send


class BoundedBody:
    """Bound raw bytes including chunked bodies before multipart parsing/spooling."""

    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] in {"GET", "HEAD", "OPTIONS"}:
            await self.app(scope, receive, send)
            return
        path = scope["path"]
        limit = (
            6 * 1024 * 1024
            if path.endswith("/search/image")
            else 3 * 1024 * 1024
            if path.endswith("/search/voice")
            else 128 * 1024
        )
        headers = dict(scope["headers"])
        try:
            declared = int(headers.get(b"content-length", b"0"))
        except ValueError:
            declared = limit + 1
        chunks = []
        total = 0
        if declared <= limit:
            try:
                async with asyncio.timeout(15):
                    while True:
                        message = await receive()
                        if message["type"] == "http.disconnect":
                            return
                        body = message.get("body", b"")
                        total += len(body)
                        if total > limit:
                            break
                        chunks.append(body)
                        if not message.get("more_body", False):
                            break
            except TimeoutError:
                await JSONResponse({"detail": "Tải lên quá thời gian."}, 408)(scope, receive, send)
                return
        if declared > limit or total > limit:
            await JSONResponse({"detail": "Dữ liệu vượt quá dung lượng cho phép."}, 413)(
                scope, receive, send
            )
            return
        delivered = False

        async def replay() -> Message:
            nonlocal delivered
            if not delivered:
                delivered = True
                return {"type": "http.request", "body": b"".join(chunks), "more_body": False}
            return await receive()

        await self.app(scope, replay, send)


class LocalRateLimit:
    """One API process in the local deployment; no unbounded key growth."""

    def __init__(self) -> None:
        self.windows: OrderedDict[tuple[str, str], tuple[float, int]] = OrderedDict()

    def allow(self, host: str, bucket: str, limit: int) -> bool:
        key = (host, bucket)
        now = time.monotonic()
        started, count = self.windows.pop(key, (now, 0))
        if now - started >= 60:
            started, count = now, 0
        self.windows[key] = (started, count + 1)
        while len(self.windows) > 2000:
            self.windows.popitem(last=False)
        return count < limit
