
"""
Centralized file upload and deletion API.

Supported purposes:
- room_image
- id_proof
- maintenance_photo

All files are stored in the private Supabase bucket.
Raw storage keys are never returned to clients.
"""

import logging
from dataclasses import dataclass
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app import storage
from app.core.audit import audit
from app.core.config import settings
from app.core.security import (
    ADMIN,
    CUSTOMER,
    MANAGER,
    STAFF,
    get_current_user,
    has_role,
    is_management,
)
from app.database import execute, fetch_one, transaction


logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------
# Upload purpose configuration
# ---------------------------------------------------------

IMAGE_TYPES = frozenset({
    "image/jpeg",
    "image/png",
    "image/webp",
})

EXTENSIONS = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "application/pdf": "pdf",
}


@dataclass(frozen=True)
class UploadTarget:
    table: str
    id_column: str
    key_column: str
    prefix: str
    allowed_types: frozenset[str]


PURPOSES = {
    "room_image": UploadTarget(
        table="room_types",
        id_column="room_type_id",
        key_column="image_key",
        prefix="room_images",
        allowed_types=IMAGE_TYPES,
    ),
    "id_proof": UploadTarget(
        table="customers",
        id_column="customer_id",
        key_column="id_proof_key",
        prefix="id_proofs",
        allowed_types=IMAGE_TYPES | {"application/pdf"},
    ),
    "maintenance_photo": UploadTarget(
        table="room_maintenance",
        id_column="maintenance_id",
        key_column="photo_key",
        prefix="maintenance_photos",
        allowed_types=IMAGE_TYPES,
    ),
}


# ---------------------------------------------------------
# Validation
# ---------------------------------------------------------

def _get_target(purpose: str) -> UploadTarget:
    """Return a configured upload purpose."""
    target = PURPOSES.get(purpose)

    if target is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Unknown upload purpose",
        )

    return target


def _require_storage() -> None:
    """Ensure Supabase Storage is configured."""
    if not storage.enabled():
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "File storage is not configured",
        )


async def _read_upload(file: UploadFile) -> bytes:
    """Read a file while enforcing the configured maximum size."""
    max_bytes = settings.upload_max_bytes

    if max_bytes <= 0:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Invalid upload size configuration",
        )

    try:
        data = await file.read(max_bytes + 1)
    finally:
        await file.close()

    if not data:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Uploaded file is empty",
        )

    if len(data) > max_bytes:
        raise HTTPException(
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            f"File exceeds the {max_bytes}-byte upload limit",
        )

    return data


def _detect_mime(data: bytes) -> str:
    """Detect MIME type using file signatures, not filenames."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"

    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"

    if (
        len(data) >= 12
        and data[:4] == b"RIFF"
        and data[8:12] == b"WEBP"
    ):
        return "image/webp"

    if data.startswith(b"%PDF-"):
        return "application/pdf"

    raise HTTPException(
        status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        "Unsupported or invalid file format",
    )


def _validate_upload(file: UploadFile, data: bytes, target: UploadTarget) -> str:
    """Validate detected MIME type against the upload purpose."""
    detected = _detect_mime(data)

    declared = (file.content_type or "").lower().split(";", 1)[0].strip()

    # Normalize a common alternative JPEG MIME declaration.
    if declared == "image/jpg":
        declared = "image/jpeg"

    # The file signature is authoritative. A generic browser MIME
    # declaration is allowed, but conflicting declarations are rejected.
    if declared and declared != "application/octet-stream" and declared != detected:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "File content does not match its declared MIME type",
        )

    if detected not in target.allowed_types:
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            "This file type is not allowed for the selected upload purpose",
        )

    return detected


# ---------------------------------------------------------
# Authorization and record locking
# ---------------------------------------------------------

def _lock_target_record(
    purpose: str,
    record_id: int,
    user: dict,
    conn,
) -> dict:
    """
    Lock the target database record and enforce ownership.

    Management can manage all supported files.
    Customers can manage only their own ID proof.
    Staff can manage maintenance photos only for assigned tasks.
    """
    target = PURPOSES[purpose]
    management_user = is_management(user)

    if purpose == "room_image" and not management_user:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Only an admin or manager can manage room images",
        )

    if purpose == "id_proof" and not management_user:
        owns_record = (
            has_role(user, CUSTOMER)
            and user.get("customer_id") == record_id
        )

        if not owns_record:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "Customer record not found",
            )

    extra_columns = ", staff_id" if purpose == "maintenance_photo" else ""

    row = fetch_one(
        f"""
        SELECT {target.key_column}{extra_columns}
        FROM {target.table}
        WHERE {target.id_column} = :record_id
        FOR UPDATE
        """,
        {"record_id": record_id},
        conn=conn,
    )

    if not row:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Upload target not found",
        )

    if purpose == "maintenance_photo" and not management_user:
        assigned_to_user = (
            has_role(user, STAFF)
            and row["staff_id"] == user.get("staff_id")
        )

        if not assigned_to_user:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "Maintenance task not found",
            )

    return row


# ---------------------------------------------------------
# Object cleanup
# ---------------------------------------------------------

def _cleanup_object(key: str, *, reason: str) -> None:
    """Best-effort cleanup without hiding the original failure."""
    try:
        storage.delete(key)
    except Exception:
        logger.exception(
            "Supabase object cleanup failed: reason=%s key=%s",
            reason,
            key,
        )


# ---------------------------------------------------------
# Upload API
# ---------------------------------------------------------

@router.post("/{purpose}/{record_id}")
async def upload_file(
    purpose: str,
    record_id: int,
    file: UploadFile = File(...),
    user: dict = Depends(get_current_user),
) -> dict:
    """
    Upload a file and associate it with a database record.

    Multipart field name: file
    """
    target = _get_target(purpose)
    _require_storage()

    data = await _read_upload(file)
    content_type = _validate_upload(file, data, target)

    extension = EXTENSIONS[content_type]

    new_key = None
    old_key = None
    file_url = None

    object_key = (
        f"{target.prefix}/{record_id}/{uuid4().hex}.{extension}"
    )

    try:
        with transaction() as conn:
            row = _lock_target_record(
                purpose,
                record_id,
                user,
                conn,
            )

            old_key = row.get(target.key_column)

            # Upload first, then update the database pointer.
            new_key = storage.save(
                object_key,
                data,
                content_type,
                upsert=False,
            )

            file_url = storage.signed_url(
                new_key,
                expires_in=3600,
            )

            if not file_url:
                raise RuntimeError("Failed to generate signed download URL")

            execute(
                f"""
                UPDATE {target.table}
                SET {target.key_column} = :key
                WHERE {target.id_column} = :record_id
                """,
                {
                    "key": new_key,
                    "record_id": record_id,
                },
                conn=conn,
            )

    except HTTPException:
        if new_key:
            _cleanup_object(new_key, reason="upload_rollback")
        raise

    except Exception as exc:
        if new_key:
            _cleanup_object(new_key, reason="upload_rollback")

        logger.exception(
            "File upload failed: purpose=%s record_id=%s",
            purpose,
            record_id,
        )

        raise HTTPException(
            status.HTTP_502_BAD_GATEWAY,
            "File storage operation failed",
        ) from exc

    # The database now references the new object.
    # Only now is it safe to remove the previous object.
    cleanup_pending = False

    if old_key and old_key != new_key:
        try:
            storage.delete(old_key)
        except Exception:
            cleanup_pending = True
            logger.exception(
                "Replaced file cleanup failed: purpose=%s record_id=%s key=%s",
                purpose,
                record_id,
                old_key,
            )

    audit(
        user["user_id"],
        "file_uploaded",
        purpose=purpose,
        record_id=record_id,
        replaced=bool(old_key),
        cleanup_pending=cleanup_pending,
    )

    # Never return the raw storage key.
    return {
        "purpose": purpose,
        "record_id": record_id,
        "url": file_url,
        "content_type": content_type,
        "cleanup_pending": cleanup_pending,
    }


# ---------------------------------------------------------
# Delete API
# ---------------------------------------------------------

@router.delete("/{purpose}/{record_id}")
def delete_file(
    purpose: str,
    record_id: int,
    user: dict = Depends(get_current_user),
) -> dict:
    """Remove a file reference and delete its stored object."""
    target = _get_target(purpose)
    _require_storage()

    old_key = None

    with transaction() as conn:
        row = _lock_target_record(
            purpose,
            record_id,
            user,
            conn,
        )

        old_key = row.get(target.key_column)

        if old_key:
            execute(
                f"""
                UPDATE {target.table}
                SET {target.key_column} = NULL
                WHERE {target.id_column} = :record_id
                """,
                {"record_id": record_id},
                conn=conn,
            )

    if not old_key:
        return {
            "deleted": False,
            "purpose": purpose,
            "record_id": record_id,
            "cleanup_pending": False,
        }

    cleanup_pending = False

    try:
        storage.delete(old_key)
    except Exception:
        cleanup_pending = True
        logger.exception(
            "File deletion cleanup failed: purpose=%s record_id=%s key=%s",
            purpose,
            record_id,
            old_key,
        )

    audit(
        user["user_id"],
        "file_deleted",
        purpose=purpose,
        record_id=record_id,
        cleanup_pending=cleanup_pending,
    )

    return {
        "deleted": True,
        "purpose": purpose,
        "record_id": record_id,
        "cleanup_pending": cleanup_pending,
    }
