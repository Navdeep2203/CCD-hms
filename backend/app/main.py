import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.database import close_pool, init_pool, ping
from app.routers import (
    auth,
    billing,
    bookings,
    customers,
    dashboard,
    departments,
    maintenance,
    managers,
    reports,
    rooms,
    services,
    staff,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_pool()
    yield
    close_pool()


app = FastAPI(title="Hotel Management API", version="2.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_MESSAGES = {"Field required": "is required", "Extra inputs are not permitted": "is not allowed"}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    if not errors:
        return JSONResponse(status_code=422, content={"detail": "Invalid request"})
    first = errors[0]
    parts = [str(p) for p in first["loc"] if p not in ("body", "query", "path")]
    message = first["msg"].removeprefix("Value error, ")
    message = _MESSAGES.get(message, message)
    field = parts[-1].replace("_", " ").capitalize() if parts else ""
    return JSONResponse(status_code=422, content={"detail": f"{field}: {message}" if field else message})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, HTTPException):  # pragma: no cover - handled by FastAPI itself
        raise exc
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Something went wrong"})


@app.middleware("http")
async def log_requests(request: Request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    logger.info("%s %s -> %s (%.0f ms)", request.method, request.url.path, response.status_code,
                (time.perf_counter() - started) * 1000)
    return response


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/health/ready")
def ready():
    if ping():
        return {"status": "ready", "database": "ok"}
    return JSONResponse(status_code=503, content={"status": "unavailable", "database": "down"})


for module, prefix in (
    (auth, "auth"), (dashboard, "dashboard"), (rooms, "rooms"), (bookings, "bookings"),
    (billing, "billing"), (services, "services"), (staff, "staff"), (managers, "managers"),
    (customers, "customers"), (departments, "departments"), (maintenance, "maintenance"),
    (reports, "reports"),
):
    app.include_router(module.router, prefix=f"/api/{prefix}", tags=[prefix])
