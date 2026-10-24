import asyncio
import json
import logging
import re
import secrets
import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

from app.api.v1.assistant import router as assistant_router
from app.api.v1.catalog import router
from app.api.v1.commerce import router as commerce_router
from app.api.v1.media import router as media_router
from app.api.v1.search import router as search_router
from app.core.config import get_settings
from app.core.dependencies import CATALOG_MEDIA_ROOT, FIXTURE_ROOT, database_ready, maintenance_loop
from app.core.http_guards import BoundedBody, LocalRateLimit
from app.domain.commerce import BusinessError
from app.infrastructure.database import engine

logger = logging.getLogger("hoodoomart.http")
logging.basicConfig(level=logging.INFO, format="%(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    cleanup = asyncio.create_task(maintenance_loop())
    yield
    cleanup.cancel()
    with suppress(asyncio.CancelledError):
        await cleanup
    await engine.dispose()


app = FastAPI(title="HoodooMart API", version="0.1.0", lifespan=lifespan)
app.add_middleware(BoundedBody)
rate = LocalRateLimit()
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["X-Request-ID"],
    expose_headers=["X-Request-ID"],
)


@app.middleware("http")
async def request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    supplied = request.headers.get("x-request-id", "")
    request_id = supplied if re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", supplied) else uuid.uuid4().hex
    request.state.request_id = request_id
    start = time.perf_counter()
    rejection_headers = {
        "X-Request-ID": request_id,
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-store",
    }
    path = request.url.path
    if path.startswith("/api/v1"):
        bucket = (
            "auth"
            if path in {"/api/v1/auth/login", "/api/v1/auth/register"}
            else "model"
            if path in {"/api/v1/search/image", "/api/v1/search/voice", "/api/v1/search/describe"}
            else "general"
        )
        if not rate.allow(
            request.client.host if request.client else "local",
            bucket,
            {"auth": 50, "model": 60, "general": 1800}[bucket],
        ):
            return JSONResponse(
                {"detail": "Quá nhiều yêu cầu. Hãy thử lại sau một phút."},
                429,
                headers={**rejection_headers, "Retry-After": "60"},
            )
        if request.method not in {"GET", "HEAD", "OPTIONS"} and not path.startswith(
            "/api/v1/search/"
        ):
            token = request.headers.get("x-csrf-token", "")
            cookie = request.cookies.get("hm_csrf", "")
            if (
                request.headers.get("origin") not in get_settings().cors_origins
                or len(token) < 32
                or not secrets.compare_digest(token, cookie)
            ):
                return JSONResponse(
                    {"detail": "Phiên biểu mẫu không hợp lệ. Hãy tải lại trang."},
                    403,
                    headers=rejection_headers,
                )
    try:
        async with asyncio.timeout(
            60
            if request.url.path
            in {"/api/v1/search/image", "/api/v1/search/voice", "/api/v1/search/describe"}
            else 5
        ):
            response = await call_next(request)
    except TimeoutError:
        response = JSONResponse({"detail": "Yêu cầu quá thời gian. Vui lòng thử lại."}, 504)
    except Exception:
        # Do not log request bodies, query strings, SQL parameters or credentials.
        response = JSONResponse({"detail": "Dịch vụ gặp lỗi. Vui lòng thử lại."}, 500)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = (
        "public, max-age=0, must-revalidate" if path.startswith("/media/catalog/") else "no-store"
    )
    logger.info(
        json.dumps(
            {
                "request_id": request_id,
                "method": request.method,
                "status": response.status_code,
                "duration_ms": round((time.perf_counter() - start) * 1000, 3),
            }
        )
    )
    return response


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Thông tin không hợp lệ. Vui lòng kiểm tra bộ lọc và khoảng giá.",
            "fields": [".".join(str(part) for part in err["loc"]) for err in exc.errors()],
        },
    )


@app.exception_handler(StarletteHTTPException)
async def http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    defaults = {404: "Không tìm thấy đường dẫn.", 405: "Phương thức này không được hỗ trợ."}
    detail = defaults.get(exc.status_code, "Yêu cầu không hợp lệ.")
    if isinstance(exc.detail, str) and exc.detail not in ("Not Found", "Method Not Allowed"):
        detail = exc.detail
    return JSONResponse({"detail": detail}, exc.status_code, headers=exc.headers)


@app.exception_handler(SQLAlchemyError)
async def database_error(_: Request, __: SQLAlchemyError) -> JSONResponse:
    return JSONResponse({"detail": "Danh mục tạm thời chưa sẵn sàng. Vui lòng thử lại."}, 503)


@app.exception_handler(BusinessError)
async def business_error(_: Request, exc: BusinessError) -> JSONResponse:
    return JSONResponse({"detail": exc.message}, exc.status)


@app.get("/health/live", tags=["Vận hành"])
async def live() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


@app.get("/health/ready", tags=["Vận hành"])
async def ready() -> JSONResponse:
    try:
        available = await database_ready()
    except SQLAlchemyError:
        available = False
    return JSONResponse(
        {"status": "ready" if available else "not_ready"}, 200 if available else 503
    )


app.include_router(router)
app.include_router(search_router)
app.include_router(media_router)
app.include_router(commerce_router)
app.include_router(assistant_router)
# Only committed, original public SVG illustrations; user uploads must never use this directory.
app.mount("/media/catalog", StaticFiles(directory=CATALOG_MEDIA_ROOT), name="catalog-media")
app.mount("/media", StaticFiles(directory=FIXTURE_ROOT / "images"), name="media")
