import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_PLACEHOLDER_HINTS = ("change", "replace", "secret-here", "dev-only", "example", "placeholder")


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"{name} must be an integer, got {raw!r}") from exc


def _decimal(name: str, default: str) -> Decimal:
    raw = os.getenv(name, default)
    try:
        return Decimal(raw)
    except InvalidOperation as exc:
        raise RuntimeError(f"{name} must be a decimal number, got {raw!r}") from exc


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "")
    database_host: str = os.getenv("DATABASE_HOST", "localhost")
    database_port: int = _int("DATABASE_PORT", 5432)
    database_name: str = os.getenv("DATABASE_NAME", os.getenv("POSTGRES_DB", "hotel_management"))
    database_user: str = os.getenv("DATABASE_USER", "")
    database_password: str = os.getenv("DATABASE_PASSWORD", "")
    db_pool_min: int = _int("DB_POOL_MIN", 1)
    db_pool_max: int = _int("DB_POOL_MAX", 10)

    jwt_secret: str = os.getenv("JWT_SECRET", "").strip()
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_minutes: int = _int("ACCESS_TOKEN_MINUTES", 480)
    login_max_attempts: int = _int("LOGIN_MAX_ATTEMPTS", 5)
    login_lock_minutes: int = _int("LOGIN_LOCK_MINUTES", 15)

    tax_rate: Decimal = _decimal("TAX_RATE", "0.12")
    loyalty_unit: int = _int("LOYALTY_UNIT", 100)

    cors_origins: list[str] = None

    def __post_init__(self):
        if self.cors_origins is None:
            object.__setattr__(
                self,
                "cors_origins",
                _csv(os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")),
            )
        if not self.jwt_secret:
            raise RuntimeError("JWT_SECRET is required (set it in backend/.env)")
        lowered = self.jwt_secret.lower()
        if any(hint in lowered for hint in _PLACEHOLDER_HINTS):
            raise RuntimeError("JWT_SECRET still looks like a placeholder; generate a real one")
        if len(self.jwt_secret) < 32:
            raise RuntimeError("JWT_SECRET must be at least 32 characters long")
        if not self.database_url and not (self.database_user and self.database_password and self.database_name):
            raise RuntimeError("Set DATABASE_URL or DATABASE_USER, DATABASE_PASSWORD and DATABASE_NAME")


settings = Settings()
