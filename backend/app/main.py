from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.database import close_pool, init_pool
from app.routers import admin, auth, billing, bookings, dashboard, reports, rooms, services


app = FastAPI(
    title="Hotel Management API",
    version="1.0.0",
    description="FastAPI backend converted from the JavaFX hotel management system.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_pool()


@app.on_event("shutdown")
def shutdown() -> None:
    close_pool()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(dashboard.router, prefix="/api/dashboard", tags=["dashboard"])
app.include_router(rooms.router, prefix="/api/rooms", tags=["rooms"])
app.include_router(bookings.router, prefix="/api/bookings", tags=["bookings"])
app.include_router(billing.router, prefix="/api/billing", tags=["billing"])
app.include_router(services.router, prefix="/api/services", tags=["services"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])

