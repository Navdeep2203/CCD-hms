from __future__ import annotations

import re
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any
import logging
from psycopg.errors import (
    UniqueViolation,
    ExclusionViolation,
    ForeignKeyViolation,
    CheckViolation,
    NotNullViolation,
    DataError
)

import psycopg
from fastapi import HTTPException, status
from psycopg.rows import dict_row

from app.core.config import settings


_BIND_PATTERN = re.compile(r"(?<!:):([A-Za-z_][A-Za-z0-9_]*)")
_RETURNING_INTO_PATTERN = re.compile(
    r"RETURNING\s+([A-Za-z_][A-Za-z0-9_.]*)\s+INTO\s+:new_id",
    re.IGNORECASE,
)

logger = logging.getLogger(__name__)


def _connect_kwargs() -> dict[str, Any]:
    if settings.database_url:
        return {"conninfo": settings.database_url}
    if not settings.database_user or not settings.database_password or not settings.database_name:
        raise RuntimeError("PostgreSQL DATABASE_USER, DATABASE_PASSWORD and DATABASE_NAME must be configured")
    return {
        "host": settings.database_host,
        "port": settings.database_port,
        "dbname": settings.database_name,
        "user": settings.database_user,
        "password": settings.database_password,
    }


def init_pool() -> None:
    # Kept for FastAPI lifecycle compatibility. Connections are opened per request operation.
    return None


def close_pool() -> None:
    return None


@contextmanager
def connection():
    conn = psycopg.connect(**_connect_kwargs(), row_factory=dict_row)
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def transaction():
    conn = psycopg.connect(
        **_connect_kwargs(),
        row_factory=dict_row,
    )

    try:
        yield conn

        try:
            conn.commit()

        except psycopg.Error as exc:
            conn.rollback()
            handle_database_error(exc)

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()

def _translate_sql(sql: str) -> str:
    return _BIND_PATTERN.sub(r"%(\1)s", sql)


def _translate_returning_sql(sql: str) -> str:
    sql = _RETURNING_INTO_PATTERN.sub(r"RETURNING \1", sql)
    return _translate_sql(sql)


def _convert(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {key.lower(): _convert(value) for key, value in row.items()}

def handle_database_error(exc: Exception) -> NoReturn:
    if isinstance(exc, UniqueViolation):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That record already exists",
        )

    if isinstance(exc, ExclusionViolation):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="That room is already booked for those dates",
        )

    if isinstance(exc, ForeignKeyViolation):
        message = ""

        if getattr(exc, "diag", None):
            message = (
                getattr(exc.diag, "message_primary", "")
                or ""
            ).lower()

        if "not present" in message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referenced record does not exist",
            )

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This record is referenced by other data",
        )

    if isinstance(exc, CheckViolation):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid value",
        )

    if isinstance(exc, NotNullViolation):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A required field is missing",
        )

    if isinstance(exc, DataError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid input",
        )

    logger.exception("Database error")

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Something went wrong",
    )
def fetch_all(
    sql: str,
    params: dict[str, Any] | None = None,
    conn=None,
) -> list[dict[str, Any]]:

    try:
        if conn is not None:
            with conn.cursor() as cursor:
                cursor.execute(_translate_sql(sql), params or {})
                return [
                    _normalize_row(row)
                    for row in cursor.fetchall()
                ]

        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(_translate_sql(sql), params or {})
                return [
                    _normalize_row(row)
                    for row in cursor.fetchall()
                ]

    except psycopg.Error as exc:
        handle_database_error(exc)


def fetch_one(
    sql: str,
    params: dict[str, Any] | None = None,
    conn=None,
) -> dict[str, Any] | None:

    rows = fetch_all(
        sql,
        params,
        conn=conn,
    )

    return rows[0] if rows else None


def execute(
    sql: str,
    params: dict[str, Any] | None = None,
    conn=None,
) -> int:

    try:
        if conn is not None:
            with conn.cursor() as cursor:
                cursor.execute(
                    _translate_sql(sql),
                    params or {},
                )

                return cursor.rowcount

        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    _translate_sql(sql),
                    params or {},
                )

                affected = cursor.rowcount

            conn.commit()

            return affected

    except psycopg.Error as exc:
        handle_database_error(exc)

def _execute_query(
    conn,
    sql: str,
    params: dict[str, Any] | None = None,
):
    with conn.cursor() as cursor:
        cursor.execute(
            _translate_sql(sql),
            params or {},
        )
        return cursor


def execute_returning_id(
    sql: str,
    params: dict[str, Any],
    out_name: str = "new_id",
    conn=None,
) -> int:

    params = {
        key: value
        for key, value in params.items()
        if key != out_name
    }

    try:
        if conn is not None:
            with conn.cursor() as cursor:
                cursor.execute(
                    _translate_returning_sql(sql),
                    params,
                )

                value = cursor.fetchone()

                if value is None:
                    raise RuntimeError(
                        "INSERT did not return an id"
                    )

                return int(
                    next(iter(value.values()))
                )

        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    _translate_returning_sql(sql),
                    params,
                )

                value = cursor.fetchone()

                if value is None:
                    raise RuntimeError(
                        "INSERT did not return an id"
                    )

                new_id = int(
                    next(iter(value.values()))
                )

            conn.commit()

            return new_id

    except psycopg.Error as exc:
        handle_database_error(exc)

    except RuntimeError:
        logger.exception(
            "Failed to obtain returned id"
        )

        raise HTTPException(
            status_code=500,
            detail="Something went wrong",
        )