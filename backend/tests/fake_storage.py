
"""In-memory fake implementation of the Supabase storage module."""

from collections.abc import Iterable, Mapping
from typing import Any
from urllib.parse import quote


class FakeStorage:
    """Storage test double with upload, signed URL and delete support."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.content_types: dict[str, str] = {}
        self.deleted: list[str] = []
        self.enabled_value = True

    def enabled(self) -> bool:
        return self.enabled_value

    def save(
        self,
        path: str,
        data: bytes,
        content_type: str,
        *,
        upsert: bool = True,
    ) -> str:
        if not self.enabled():
            raise RuntimeError("Fake storage is disabled")

        if not path or not isinstance(path, str):
            raise ValueError("Invalid storage key")

        if not isinstance(data, bytes) or not data:
            raise ValueError("File data must be non-empty bytes")

        if not upsert and path in self.objects:
            raise FileExistsError(path)

        self.objects[path] = bytes(data)
        self.content_types[path] = content_type

        return path

    def signed_url(
        self,
        path: str | None,
        expires_in: int = 3600,
    ) -> str | None:
        if not self.enabled() or not path:
            return None

        if path not in self.objects:
            return None

        if expires_in <= 0:
            raise ValueError("expires_in must be positive")

        safe_path = quote(path, safe="/")

        return (
            f"https://fake-storage.test/{safe_path}"
            f"?token=fake-token&expires={expires_in}"
        )

    def signed_urls(
        self,
        paths: Iterable[str],
        expires_in: int = 3600,
    ) -> dict[str, str]:
        result: dict[str, str] = {}

        for path in dict.fromkeys(paths):
            url = self.signed_url(path, expires_in)

            if url:
                result[path] = url

        return result

    def delete(self, path: str | None) -> None:
        if not path or not self.enabled():
            return

        self.objects.pop(path, None)
        self.content_types.pop(path, None)
        self.deleted.append(path)

    def attach(
        self,
        row: Mapping[str, Any] | None,
        key_field: str,
        url_field: str,
        *,
        expires_in: int = 3600,
    ) -> dict[str, Any] | None:
        if row is None:
            return None

        result = dict(row)
        key = result.pop(key_field, None)

        result[url_field] = (
            self.signed_url(key, expires_in)
            if key
            else None
        )

        return result

    def attach_many(
        self,
        rows: Iterable[Mapping[str, Any]],
        key_field: str,
        url_field: str,
        *,
        expires_in: int = 3600,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        keys: list[str] = []

        for row in rows:
            result = dict(row)
            key = result.pop(key_field, None)

            if isinstance(key, str) and key:
                keys.append(key)

            results.append(result)

        urls = self.signed_urls(keys, expires_in)

        for result, row in zip(results, rows):
            # The raw key was removed above. The URL is looked up
            # from the original key without adding it to the result.
            key = row.get(key_field)
            result[url_field] = urls.get(key) if key else None

        return results
