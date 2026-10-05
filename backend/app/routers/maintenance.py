from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.audit import audit
from app.core.security import ADMIN, MANAGER, STAFF, is_management, require_roles
from app.core.sqlutil import build_set
from app.database import (
    execute,
    execute_returning_id,
    fetch_all,
    fetch_one,
    transaction,
)
from app.schemas import MaintenanceCreateRequest, MaintenanceUpdateRequest

router = APIRouter()
ops_user = Depends(require_roles(ADMIN, MANAGER, STAFF))

MAINT_SELECT = """
SELECT rm.maintenance_id, rm.room_id, r.room_number, rm.staff_id, u.name AS staff_name,
       rm.description, rm.maintenance_date, rm.status
FROM room_maintenance rm
JOIN rooms r ON r.room_id = rm.room_id
LEFT JOIN staff s ON s.staff_id = rm.staff_id
LEFT JOIN users u ON u.user_id = s.user_id
"""


def _occupied(room_id: int, conn) -> bool:
    return bool(fetch_one(
        "SELECT 1 FROM bookings WHERE room_id = :id AND booking_status IN ('CHECKED_IN', 'CHECKOUT_PENDING')",
        {"id": room_id}, conn=conn,
    ))


@router.get("")
def list_maintenance(
    status_filter: str | None = Query(default=None, alias="status"),
    mine: bool = False,
    user: dict = ops_user,
) -> list[dict]:
    where, params = [], {}
    if mine or not is_management(user):  # front-line staff only see tasks assigned to them
        where.append("rm.staff_id = :sid")
        params["sid"] = user.get("staff_id") or -1
    if status_filter:
        where.append("rm.status = :status")
        params["status"] = status_filter
    sql = MAINT_SELECT + (" WHERE " + " AND ".join(where) if where else "")
    return fetch_all(sql + " ORDER BY rm.maintenance_id DESC LIMIT 200", params)


@router.post("", status_code=201)
def create_request(payload: MaintenanceCreateRequest, user: dict = ops_user) -> dict:
    if payload.staff_id and not is_management(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a manager or admin can assign maintenance work")
    with transaction() as conn:
        room = fetch_one("SELECT status FROM rooms WHERE room_id = :id FOR UPDATE", {"id": payload.room_id}, conn=conn)
        if not room:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")
        maint_id = execute_returning_id(
            """INSERT INTO room_maintenance (room_id, staff_id, description, maintenance_date, status)
               VALUES (:room_id, :staff_id, :description, CURRENT_DATE, 'PENDING') RETURNING maintenance_id""",
            payload.model_dump(), conn=conn,
        )
        if not _occupied(payload.room_id, conn):  # never pull a room from a guest who is in it
            execute("UPDATE rooms SET status = 'MAINTENANCE' WHERE room_id = :id", {"id": payload.room_id}, conn=conn)
        audit(user["user_id"], "maintenance_created", maintenance_id=maint_id, room_id=payload.room_id)
        return fetch_one(MAINT_SELECT + " WHERE rm.maintenance_id = :id", {"id": maint_id}, conn=conn)


@router.put("/{maintenance_id}")
def update_request(maintenance_id: int, payload: MaintenanceUpdateRequest, user: dict = ops_user) -> dict:
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")
    if data.get("status", 0) is None or data.get("description", 0) is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Status and description cannot be empty")
    management_user = is_management(user)
    if not management_user and set(data) - {"status"}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Staff can only update the status of their own tasks")
    with transaction() as conn:
        row = fetch_one("SELECT * FROM room_maintenance WHERE maintenance_id = :id FOR UPDATE", {"id": maintenance_id}, conn=conn)
        if not row or (not management_user and row["staff_id"] != user.get("staff_id")):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Maintenance task not found")
        if data.get("staff_id") and not fetch_one(
            "SELECT 1 FROM staff s JOIN users u ON u.user_id = s.user_id WHERE s.staff_id = :id AND u.is_active",
            {"id": data["staff_id"]}, conn=conn,
        ):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Staff member does not exist or is inactive")
        set_sql, params = build_set(data, {"status", "staff_id", "description"})
        execute(f"UPDATE room_maintenance SET {set_sql} WHERE maintenance_id = :id", {**params, "id": maintenance_id}, conn=conn)
        room_id = row["room_id"]
        if data.get("status") == "COMPLETED":
            others_open = fetch_one(
                "SELECT 1 FROM room_maintenance WHERE room_id = :r AND maintenance_id <> :m AND status <> 'COMPLETED'",
                {"r": room_id, "m": maintenance_id}, conn=conn,
            )
            if not others_open and not _occupied(room_id, conn):
                execute("UPDATE rooms SET status = 'AVAILABLE' WHERE room_id = :id AND status = 'MAINTENANCE'", {"id": room_id}, conn=conn)
        elif data.get("status") in ("PENDING", "IN_PROGRESS") and not _occupied(room_id, conn):
            execute("UPDATE rooms SET status = 'MAINTENANCE' WHERE room_id = :id", {"id": room_id}, conn=conn)
        audit(user["user_id"], "maintenance_updated", maintenance_id=maintenance_id, fields=",".join(sorted(data)))
        return fetch_one(MAINT_SELECT + " WHERE rm.maintenance_id = :id", {"id": maintenance_id}, conn=conn)
