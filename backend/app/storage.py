
"""
Centralized Supabase Storage integration.

All backend file operations should go through this module.
Raw storage keys must never be returned in API responses.
"""

from collections.abc import Iterable, Mapping
from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from app.core.config import settings


# ---------------------------------------------------------
# Configuration and client
# ---------------------------------------------------------

def enabled() -> bool:
    """Return whether Supabase Storage is configured."""
    return settings.storage_enabled


@lru_cache(maxsize=1)
def _client() -> Client:
    """Create and cache the Supabase client."""
    if not enabled():
        raise RuntimeError("Supabase Storage is not configured")

    return create_client(
        settings.supabase_url,
        settings.supabase_service_key,
    )


def _bucket():
    """Return the configured storage bucket."""
    return _client().storage.from_(settings.supabase_bucket)


# ---------------------------------------------------------
# Helpers
# ---------------------------------------------------------

def _clean_key(path: str) -> str:
    """Validate and normalize a relative storage object key."""
    if not isinstance(path, str):
        raise TypeError("Storage key must be a string")

    key = path.strip()

    if (
        not key
        or key.startswith("/")
        or "\\" in key
        or "\x00" in key
    ):
        raise ValueError("Invalid storage object key")

    parts = key.split("/")

    if any(part in ("", ".", "..") for part in parts):
        raise ValueError("Invalid storage object key")

    return key


def _validate_expiry(expires_in: int) -> None:
    """Validate signed URL expiry."""
    if (
        isinstance(expires_in, bool)
        or not isinstance(expires_in, int)
        or expires_in <= 0
    ):
        raise ValueError("expires_in must be a positive integer")


def _extract_signed_url(response: Any) -> str | None:
    """
    Extract the signed URL from the SDK response.

    Supports both signedURL and signedUrl.
    """
    if isinstance(response, Mapping):
        url = response.get("signedURL") or response.get("signedUrl")
    else:
        url = (
            getattr(response, "signedURL", None)
            or getattr(response, "signedUrl", None)
        )

    return url if isinstance(url, str) and url else None


def _absolute_signed_url(url: str) -> str:
    """Convert a relative Supabase signed URL into an absolute URL."""
    if url.startswith(("https://", "http://")):
        return url

    if url.startswith("//"):
        return "https:" + url

    base_url = settings.supabase_url.rstrip("/")

    if url.startswith("/storage/v1/"):
        return base_url + url

    if url.startswith("/"):
        return base_url + "/storage/v1" + url

    if url.startswith("storage/v1/"):
        return base_url + "/" + url

    return base_url + "/storage/v1/" + url.lstrip("/")


# ---------------------------------------------------------
# Upload
# ---------------------------------------------------------

def save(
    path: str,
    data: bytes,
    content_type: str,
    *,
    upsert: bool = True,
) -> str:
    """
    Upload bytes to Supabase Storage.

    Args:
        path: Relative object key inside the bucket.
        data: File contents.
        content_type: MIME type of the file.
        upsert: Whether to replace an existing object.

    Returns:
        The stored object key.
    """
    if not enabled():
        raise RuntimeError("Supabase Storage is disabled")

    key = _clean_key(path)

    if not isinstance(data, bytes):
        raise TypeError("File data must be bytes")

    if not data:
        raise ValueError("Cannot upload an empty file")

    if not isinstance(content_type, str) or not content_type.strip():
        raise ValueError("A valid content type is required")

    response = _bucket().upload(
        key,
        data,
        file_options={
            "content-type": content_type,
            "cache-control": "3600",
            "upsert": "true" if upsert else "false",
        },
    )

    # UploadResponse in storage3 2.33.0 exposes .path.
    uploaded_path = getattr(response, "path", None)

    return _clean_key(uploaded_path or key)


# ---------------------------------------------------------
# Signed URLs
# ---------------------------------------------------------

def signed_url(
    path: str | None,
    expires_in: int = 3600,
) -> str | None:
    """
    Generate a temporary signed URL for one stored object.
    """
    if not path or not enabled():
        return None

    _validate_expiry(expires_in)
    key = _clean_key(path)

    response = _bucket().create_signed_url(
        key,
        expires_in,
    )

    url = _extract_signed_url(response)

    if not url:
        raise RuntimeError("Supabase did not return a signed URL")

    return _absolute_signed_url(url)


def signed_urls(
    paths: Iterable[str],
    expires_in: int = 3600,
) -> dict[str, str]:
    """
    Generate temporary signed URLs for multiple objects.

    Returns:
        A mapping of storage key to absolute signed URL.
    """
    if not enabled():
        return {}

    _validate_expiry(expires_in)

    # Remove duplicates while preserving order.
    unique_keys = list(dict.fromkeys(
        _clean_key(path)
        for path in paths
        if path
    ))

    if not unique_keys:
        return {}

    responses = _bucket().create_signed_urls(
        unique_keys,
        expires_in,
    )

    result: dict[str, str] = {}

    for index, response in enumerate(responses or []):
        if not isinstance(response, Mapping):
            continue

        # The SDK provides both path and error fields.
        if response.get("error"):
            continue

        response_path = response.get("path")

        if response_path:
            key = response_path
        elif index < len(unique_keys):
            key = unique_keys[index]
        else:
            continue

        if key not in unique_keys:
            continue

        url = _extract_signed_url(response)

        if url:
            result[key] = _absolute_signed_url(url)

    return result


# ---------------------------------------------------------
# Delete
# ---------------------------------------------------------

def delete(path: str | None) -> None:
    """Delete one object from Supabase Storage."""
    if not path or not enabled():
        return

    key = _clean_key(path)

    _bucket().remove([key])


# ---------------------------------------------------------
# Attach signed URLs to API responses
# ---------------------------------------------------------

def attach(
    row: Mapping[str, Any] | None,
    key_field: str,
    url_field: str,
    *,
    expires_in: int = 3600,
) -> dict[str, Any] | None:
    """
    Attach a signed URL to one response dictionary.

    The raw storage key is always removed.
    """
    if row is None:
        return None

    result = dict(row)

    key = result.pop(key_field, None)

    result[url_field] = (
        signed_url(key, expires_in)
        if key
        else None
    )

    return result


def attach_many(
    rows: Iterable[Mapping[str, Any]],
    key_field: str,
    url_field: str,
    *,
    expires_in: int = 3600,
) -> list[dict[str, Any]]:
    """
    Attach signed URLs to multiple response dictionaries.

    Uses one batch signed-URL request instead of one request
    per database row.
    """
    results: list[dict[str, Any]] = []
    row_keys: list[str | None] = []

    for row in rows:
        result = dict(row)

        # Remove raw key so it cannot leak into the response.
        key = result.pop(key_field, None)

        row_keys.append(key)
        results.append(result)

    # Generate links only for unique, non-empty keys.
    keys = [
        key
        for key in row_keys
        if isinstance(key, str) and key
    ]

    urls = signed_urls(keys, expires_in) if enabled() else {}

    for result, key in zip(results, row_keys):
        result[url_field] = urls.get(key) if key else None

    return results
