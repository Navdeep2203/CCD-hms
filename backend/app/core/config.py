import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _get_int_env(name: str, default: str) -> int:
    value = os.getenv(name, default)

    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(
            f"{name} must be a valid integer. Current value: {value!r}"
        ) from exc


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv("DATABASE_URL", "").strip()
    database_host: str = os.getenv("DATABASE_HOST", "localhost").strip()

    database_port: int = _get_int_env(
        "DATABASE_PORT",
        "5432",
    )

    database_name: str = os.getenv(
        "DATABASE_NAME",
        os.getenv("POSTGRES_DB", "hotel_management"),
    ).strip()

    database_user: str = os.getenv(
        "DATABASE_USER",
        "",
    ).strip()

    database_password: str = os.getenv(
        "DATABASE_PASSWORD",
        "",
    ).strip()

    jwt_secret: str = os.getenv(
        "JWT_SECRET",
        "",
    ).strip()

    jwt_algorithm: str = os.getenv(
        "JWT_ALGORITHM",
        "HS256",
    ).strip()

    access_token_minutes: int = _get_int_env(
        "ACCESS_TOKEN_MINUTES",
        "480",
    )

    tax_rate: Decimal = Decimal(
        os.getenv("TAX_RATE", "0.12")
    )

    cors_origins: list[str] = None

    def __post_init__(self):
        if self.cors_origins is None:
            object.__setattr__(
                self,
                "cors_origins",
                _csv(
                    os.getenv(
                        "CORS_ORIGINS",
                        "http://localhost:5173,http://127.0.0.1:5173",
                    )
                ),
            )

        # Fail fast on missing DB config
        if not self.database_url:
            missing = []

            if not self.database_user:
                missing.append("DATABASE_USER")

            if not self.database_password:
                missing.append("DATABASE_PASSWORD")

            if not self.database_name:
                missing.append("DATABASE_NAME")

            if missing:
                raise RuntimeError(
                    f"Missing required database configuration: {', '.join(missing)}"
                )

        # JWT validation
        if not self.jwt_secret:
            raise RuntimeError(
                "JWT_SECRET is required in .env"
            )

        secret_lower = self.jwt_secret.lower()

        placeholder_markers = (
            "change",
            "replace",
            "secret-here",
            "dev-only",
            "example",
            "placeholder",
        )

        if any(
            marker in secret_lower
            for marker in placeholder_markers
        ):
            raise RuntimeError(
                "JWT_SECRET is still using a placeholder value"
            )

        if len(self.jwt_secret) < 32:
            raise RuntimeError(
                "JWT_SECRET must be at least 32 characters long"
            )


settings = Settings()