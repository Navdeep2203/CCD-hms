from typing import Any


def build_set(data: dict[str, Any], allowed: set[str]) -> tuple[str, dict[str, Any]]:
    """Build 'col = :col, ...' from a fixed whitelist of column names (never from client keys)."""
    cols = [key for key in data if key in allowed]
    return ", ".join(f"{col} = :{col}" for col in cols), {col: data[col] for col in cols}
