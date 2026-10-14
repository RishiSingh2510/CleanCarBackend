import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import get_settings
from app.database import open_db
from app.deps import get_store
from app.errors import AppError
from app.routers import account, auth, bookings, catalog, vehicles
from app.seed import seed_demo

settings = get_settings()
log = logging.getLogger("cleancar")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.is_production and "*" in settings.cors_origins:
        log.warning(
            "CORS_ORIGINS is '*' in production — restrict it to your web origins."
        )
    if settings.seed_demo:
        with open_db() as conn:
            seed_demo(get_store(), conn)
    yield


app = FastAPI(
    title="CleanCar API",
    version="1.0.0",
    description="CleanCar API backed by PostgreSQL and in-memory booking/session state.",
    lifespan=lifespan,
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---- every error becomes {"message": "...", "code": "..."} — the shape the mobile app reads ----
@app.exception_handler(AppError)
async def handle_app_error(_: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status,
        content={"message": exc.message, "code": exc.code},
        headers=exc.headers,
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, exc: RequestValidationError):
    errors = exc.errors()
    first = errors[0] if errors else {}
    field = ".".join(
        str(p) for p in first.get("loc", ()) if p not in ("body", "query", "path")
    )
    msg = str(first.get("msg", "Invalid request")).removeprefix("Value error, ")
    message = f"{field}: {msg}" if field else msg
    return JSONResponse(
        status_code=422, content={"message": message, "code": "VALIDATION_ERROR"}
    )


@app.exception_handler(StarletteHTTPException)
async def handle_http_error(_: Request, exc: StarletteHTTPException):
    friendly = {
        404: "That resource does not exist.",
        405: "That method is not allowed here.",
    }
    message = friendly.get(exc.status_code) or (
        exc.detail if isinstance(exc.detail, str) else "Request failed."
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": message, "code": "HTTP_ERROR"},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def handle_unexpected(_: Request, exc: Exception):
    log.exception("Unhandled error", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={
            "message": "Something went wrong on our side. Please try again.",
            "code": "INTERNAL_ERROR",
        },
    )


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


for r in (
    auth.router,
    account.router,
    catalog.router,
    vehicles.router,
    bookings.router,
):
    app.include_router(r)
