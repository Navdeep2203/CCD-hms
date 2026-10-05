from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.audit import audit
from app.core.security import (
    ADMIN,
    MANAGER,
    STAFF,
    get_current_user,
    is_ops,
    require_roles,
)
from app.database import (
    execute,
    execute_returning_id,
    fetch_all,
    fetch_one,
    transaction,
)
from app.schemas import RoomRequest, RoomStatusRequest, RoomTypeRequest

router = APIRouter()
management = Depends(require_roles(ADMIN, MANAGER))

ROOM_SELECT = """
SELECT r.room_id, r.room_number, r.floor, r.status,
       rt.room_type_id, rt.type_name, rt.capacity, rt.price_per_night, rt.description
FROM rooms r
JOIN room_types rt ON rt.room_type_id = r.room_type_id
"""
# Guests only ever see what they need to choose and book a room (no internal status).
GUEST_ROOM_SELECT = """
SELECT r.room_id, r.room_number, r.floor,
       rt.room_type_id, rt.type_name, rt.capacity, rt.price_per_night, rt.description
FROM rooms r
JOIN room_types rt ON rt.room_type_id = r.room_type_id
"""
ACTIVE_STAY = "('CHECKED_IN', 'CHECKOUT_PENDING')"


def _has_active_stay(room_id: int, conn) -> bool:
    return bool(fetch_one(
        f"SELECT 1 FROM bookings WHERE room_id = :id AND booking_status IN {ACTIVE_STAY}", {"id": room_id}, conn=conn
    ))


@router.get("")
def list_rooms(
    status_filter: str | None = Query(default=None, alias="status"),
    check_in: date | None = None,
    check_out: date | None = None,
    user: dict = Depends(get_current_user),
) -> list[dict]:
    ops = is_ops(user)
    if (check_in is None) != (check_out is None):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provide both check_in and check_out")
    if check_in and check_out and check_out <= check_in:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Check-out must be after check-in")
    if not ops and check_in is None:
        check_in, check_out = date.today(), date.fromordinal(date.today().toordinal() + 1)
    where, params = [], {}
    if status_filter and ops:
        where.append("r.status = :status")
        params["status"] = status_filter
    if check_in and check_out:
        where.append("r.status <> 'MAINTENANCE'")
        where.append(
            """NOT EXISTS (
                SELECT 1 FROM bookings b
                WHERE b.room_id = r.room_id
                  AND b.booking_status IN ('APPROVED', 'CHECKIN_PENDING', 'CHECKED_IN', 'CHECKOUT_PENDING')
                  AND b.check_in_date < :check_out AND b.check_out_date > :check_in)"""
        )
        params.update({"check_in": check_in, "check_out": check_out})
    sql = (ROOM_SELECT if ops else GUEST_ROOM_SELECT) + (" WHERE " + " AND ".join(where) if where else "")
    return fetch_all(sql + " ORDER BY r.room_number", params)


@router.get("/types")
def list_room_types(user: dict = Depends(get_current_user)) -> list[dict]:
    return fetch_all("SELECT * FROM room_types ORDER BY price_per_night, type_name")


@router.post("/types", status_code=201, dependencies=[management])
def create_room_type(payload: RoomTypeRequest) -> dict:
    new_id = execute_returning_id(
        """INSERT INTO room_types (type_name, capacity, price_per_night, description)
           VALUES (:type_name, :capacity, :price_per_night, :description) RETURNING room_type_id""",
        payload.model_dump(),
    )
    return fetch_one("SELECT * FROM room_types WHERE room_type_id = :id", {"id": new_id})


@router.put("/types/{room_type_id}", dependencies=[management])
def update_room_type(room_type_id: int, payload: RoomTypeRequest) -> dict:
    affected = execute(
        """UPDATE room_types SET type_name = :type_name, capacity = :capacity,
           price_per_night = :price_per_night, description = :description WHERE room_type_id = :id""",
        {**payload.model_dump(), "id": room_type_id},
    )
    if not affected:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room type not found")
    return fetch_one("SELECT * FROM room_types WHERE room_type_id = :id", {"id": room_type_id})


@router.delete("/types/{room_type_id}", dependencies=[management])
def delete_room_type(room_type_id: int) -> dict:
    if not execute("DELETE FROM room_types WHERE room_type_id = :id", {"id": room_type_id}):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room type not found")
    return {"deleted": True}


@router.post("", status_code=201)
def create_room(payload: RoomRequest, user: dict = management) -> dict:
    if payload.status not in ("AVAILABLE", "MAINTENANCE"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A new room can only start as AVAILABLE or MAINTENANCE")
    room_id = execute_returning_id(
        """INSERT INTO rooms (room_number, room_type_id, floor, status)
           VALUES (:room_number, :room_type_id, :floor, :status) RETURNING room_id""",
        payload.model_dump(),
    )
    return fetch_one(ROOM_SELECT + " WHERE r.room_id = :id", {"id": room_id})


def _guard_status_change(current: str, new: str, room_id: int, conn) -> None:
    if new == current:
        return
    if new == "OCCUPIED":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A room becomes OCCUPIED automatically at check-in")
    if _has_active_stay(room_id, conn):
        raise HTTPException(status.HTTP_409_CONFLICT, "A guest is currently staying in this room")


@router.put("/{room_id}")
def update_room(room_id: int, payload: RoomRequest, user: dict = management) -> dict:
    with transaction() as conn:
        room = fetch_one("SELECT status FROM rooms WHERE room_id = :id FOR UPDATE", {"id": room_id}, conn=conn)
        if not room:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")
        _guard_status_change(room["status"], payload.status, room_id, conn)
        execute(
            """UPDATE rooms SET room_number = :room_number, room_type_id = :room_type_id,
               floor = :floor, status = :status WHERE room_id = :id""",
            {**payload.model_dump(), "id": room_id},
            conn=conn,
        )
        return fetch_one(ROOM_SELECT + " WHERE r.room_id = :id", {"id": room_id}, conn=conn)


@router.patch("/{room_id}/status")
def update_room_status(
    room_id: int, payload: RoomStatusRequest, user: dict = Depends(require_roles(ADMIN, MANAGER, STAFF))
) -> dict:
    with transaction() as conn:
        room = fetch_one("SELECT status FROM rooms WHERE room_id = :id FOR UPDATE", {"id": room_id}, conn=conn)
        if not room:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")
        _guard_status_change(room["status"], payload.status, room_id, conn)
        execute("UPDATE rooms SET status = :status WHERE room_id = :id", {"status": payload.status, "id": room_id}, conn=conn)
        audit(user["user_id"], "room_status", room_id=room_id, status=payload.status)
        return fetch_one(ROOM_SELECT + " WHERE r.room_id = :id", {"id": room_id}, conn=conn)


@router.delete("/{room_id}")
def delete_room(room_id: int, user: dict = management) -> dict:
    if not execute("DELETE FROM rooms WHERE room_id = :id", {"id": room_id}):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")
    audit(user["user_id"], "room_deleted", room_id=room_id)
    return {"deleted": True}
