from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import oracledb
from fastapi import HTTPException, status

from app.core.config import settings


_pool: oracledb.ConnectionPool | None = None


def _normalize_dsn(dsn: str) -> str:
    if dsn.startswith("jdbc:oracle:thin:@"):
        return dsn.replace("jdbc:oracle:thin:@", "", 1)
    return dsn


def init_pool() -> None:
    global _pool
    if _pool is not None:
        return
    if not settings.database_user or not settings.database_password or not settings.database_dsn:
        raise RuntimeError("DATABASE_USER, DATABASE_PASSWORD and DATABASE_DSN must be configured")
    _pool = oracledb.create_pool(
        user=settings.database_user,
        password=settings.database_password,
        dsn=_normalize_dsn(settings.database_dsn),
        min=1,
        max=5,
        increment=1,
    )


def close_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
        _pool = None


@contextmanager
def connection():
    init_pool()
    assert _pool is not None
    conn = _pool.acquire()
    try:
        yield conn
    finally:
        _pool.release(conn)


def _convert(value: Any) -> Any:
    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value


def _rows(cursor: oracledb.Cursor) -> list[dict[str, Any]]:
    columns = [column[0].lower() for column in cursor.description or []]
    return [{columns[i]: _convert(value) for i, value in enumerate(row)} for row in cursor.fetchall()]


def fetch_all(sql: str, params: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    try:
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or {})
                return _rows(cursor)
    except oracledb.Error as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


def fetch_one(sql: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    rows = fetch_all(sql, params)
    return rows[0] if rows else None


def execute(sql: str, params: dict[str, Any] | None = None) -> int:
    try:
        with connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, params or {})
                affected = cursor.rowcount
            conn.commit()
            return affected
    except oracledb.Error as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


def execute_returning_id(sql: str, params: dict[str, Any], out_name: str = "new_id") -> int:
    try:
        with connection() as conn:
            with conn.cursor() as cursor:
                out_var = cursor.var(oracledb.NUMBER)
                cursor.execute(sql, {**params, out_name: out_var})
                value = int(out_var.getvalue()[0])
            conn.commit()
            return value
    except oracledb.Error as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc

