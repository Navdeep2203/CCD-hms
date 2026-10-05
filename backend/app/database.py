from __future__ import annotations

import logging
import re
from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any, NoReturn

import psycopg
from fastapi import HTTPException, status
from psycopg.conninfo import make_conninfo
from psycopg.errors import (
    CheckViolation,
    DataError,
    ExclusionViolation,
    ForeignKeyViolation,
    NotNullViolation,
    UniqueViolation,
)
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from app.core.config import settings

logger = logging.getLogger(__name__)

# SQL in this project uses ":name" bind parameters; they are translated to psycopg's %(name)s.
_BIND_PATTERN = re.compile(r"(?<!:):([A-Za-z_][A-Za-z0-9_]*)")

_pool: ConnectionPool | None = None


def _conninfo() -> str:
    if settings.database_url:
        return settings.database_url
    return make_conninfo(
        host=settings.database_host,
        port=settings.database_port,
        dbname=settings.database_name,
        user=settings.database_user,
        password=settings.database_password,
    )


def init_pool() -> None:
    global _pool
    if _pool is None:
        _pool = ConnectionPool(
            _conninfo(),
            min_size=settings.db_pool_min,
            max_size=settings.db_pool_max,
            kwargs={"row_factory": dict_row},
            open=True,
        )
        _pool.wait(timeout=15)


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


def ping() -> bool:
    try:
        with connection() as conn, conn.cursor() as cursor:
            cursor.execute("SELECT 1")
            return True
    except Exception:
        logger.exception("Database ping failed")
        return False


@contextmanager
def connection():
    if _pool is not None:
        with _pool.connection() as conn:
            yield conn
    else:
        conn = psycopg.connect(_conninfo(), row_factory=dict_row)
        try:
            yield conn
        finally:
            conn.close()


@contextmanager
def transaction():
    """One connection, committed at the end or rolled back on any error.

    Pass ``conn=conn`` to every helper call made inside the block.
    """
    try:
        with connection() as conn:
            yield conn
            conn.commit()
    except psycopg.Error as exc:
        handle_database_error(exc)


def _translate_sql(sql: str) -> str:
    return _BIND_PATTERN.sub(r"%(\1)s", sql)


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
        raise HTTPException(status.HTTP_409_CONFLICT, "That record already exists")
    if isinstance(exc, ExclusionViolation):
        raise HTTPException(status.HTTP_409_CONFLICT, "That room is already booked for those dates")
    if isinstance(exc, ForeignKeyViolation):
        message = (getattr(getattr(exc, "diag", None), "message_primary", "") or "").lower()
        if "still referenced" in message:
            raise HTTPException(status.HTTP_409_CONFLICT, "This record is used by other data and cannot be removed")
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A referenced record does not exist")
    if isinstance(exc, CheckViolation):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid value")
    if isinstance(exc, NotNullViolation):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A required field is missing")
    if isinstance(exc, DataError):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid input")
    logger.error("Database error", exc_info=exc)
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Something went wrong")


def _run(sql: str, params: dict[str, Any] | None, conn, *, rows: bool):
    def work(active):
        with active.cursor() as cursor:
            cursor.execute(_translate_sql(sql), params or {})
            if rows:
                return [_normalize_row(row) for row in cursor.fetchall()]
            return cursor.rowcount

    try:
        if conn is not None:
            return work(conn)
        with connection() as active:
            result = work(active)
            active.commit()
            return result
    except psycopg.Error as exc:
        handle_database_error(exc)


def fetch_all(sql: str, params: dict[str, Any] | None = None, conn=None) -> list[dict[str, Any]]:
    return _run(sql, params, conn, rows=True)


def fetch_one(sql: str, params: dict[str, Any] | None = None, conn=None) -> dict[str, Any] | None:
    result = fetch_all(sql, params, conn=conn)
    return result[0] if result else None


def execute(sql: str, params: dict[str, Any] | None = None, conn=None) -> int:
    return _run(sql, params, conn, rows=False)


def execute_returning_id(sql: str, params: dict[str, Any], conn=None) -> int:
    """Run an INSERT ... RETURNING <id> and return that single value."""
    result = _run(sql, params, conn, rows=True)
    if not result:
        logger.error("INSERT did not return an id")
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Something went wrong")
    return int(next(iter(result[0].values())))
