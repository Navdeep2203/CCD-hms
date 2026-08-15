from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_current_user, require_roles
from app.database import execute, execute_returning_id, fetch_all, fetch_one
from app.schemas import RoomRequest, RoomTypeRequest, StatusRequest


router = APIRouter()


ROOM_SELECT = """
SELECT r.room_id, r.room_number, r.floor, r.status,
       rt.room_type_id, rt.type_name, rt.capacity, rt.price_per_night, rt.description
FROM rooms r
JOIN room_types rt ON rt.room_type_id = r.room_type_id
"""


@router.get("")
def list_rooms(
    status_filter: str | None = Query(default=None, alias="status"),
    check_in: str | None = None,
    check_out: str | None = None,
    user: dict = Depends(get_current_user),
) -> list[dict]:
    params = {}
    where = []
    if status_filter:
        where.append("r.status = :status")
        params["status"] = status_filter
    if check_in and check_out:
        where.append(
            """
            NOT EXISTS (
                SELECT 1 FROM bookings b
                WHERE b.room_id = r.room_id
                  AND b.booking_status IN ('APPROVED', 'CHECKED_IN', 'CHECKIN_PENDING')
                  AND NOT (b.check_out_date <= CAST(:check_in AS DATE)
                           OR b.check_in_date >= CAST(:check_out AS DATE))
            )
            """
        )
        params.update({"check_in": check_in, "check_out": check_out})
    sql = ROOM_SELECT
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY r.room_number"
    return fetch_all(sql, params)


@router.get("/types")
def list_room_types(user: dict = Depends(get_current_user)) -> list[dict]:
    return fetch_all("SELECT * FROM room_types ORDER BY price_per_night, type_name")


@router.post("/types", dependencies=[Depends(require_roles("ROLE_ADMIN", "ROLE_MANAGER"))])
def create_room_type(payload: RoomTypeRequest) -> dict:
    room_type_id = execute_returning_id(
        """
        INSERT INTO room_types (type_name, capacity, price_per_night, description)
        VALUES (:type_name, :capacity, :price_per_night, :description)
        RETURNING room_type_id
        """,
        payload.model_dump(),
    )
    return fetch_one("SELECT * FROM room_types WHERE room_type_id = :id", {"id": room_type_id})


@router.post("", dependencies=[Depends(require_roles("ROLE_ADMIN", "ROLE_MANAGER"))])
def create_room(payload: RoomRequest) -> dict:
    room_id = execute_returning_id(
        """
        INSERT INTO rooms (room_number, room_type_id, floor, status)
        VALUES (:room_number, :room_type_id, :floor, :status)
        RETURNING room_id
        """,
        payload.model_dump(),
    )
    return fetch_one(ROOM_SELECT + " WHERE r.room_id = :room_id", {"room_id": room_id})


@router.put("/{room_id}", dependencies=[Depends(require_roles("ROLE_ADMIN", "ROLE_MANAGER"))])
def update_room(room_id: int, payload: RoomRequest) -> dict:
    affected = execute(
        """
        UPDATE rooms
        SET room_number = :room_number, room_type_id = :room_type_id, floor = :floor, status = :status
        WHERE room_id = :room_id
        """,
        {**payload.model_dump(), "room_id": room_id},
    )
    if affected == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return fetch_one(ROOM_SELECT + " WHERE r.room_id = :room_id", {"room_id": room_id})


@router.patch("/{room_id}/status", dependencies=[Depends(require_roles("ROLE_ADMIN", "ROLE_MANAGER", "ROLE_STAFF"))])
def update_room_status(room_id: int, payload: StatusRequest) -> dict:
    affected = execute("UPDATE rooms SET status = :status WHERE room_id = :room_id", {"status": payload.status, "room_id": room_id})
    if affected == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return fetch_one(ROOM_SELECT + " WHERE r.room_id = :room_id", {"room_id": room_id})


@router.delete("/{room_id}", dependencies=[Depends(require_roles("ROLE_ADMIN", "ROLE_MANAGER"))])
def delete_room(room_id: int) -> dict:
    affected = execute("DELETE FROM rooms WHERE room_id = :room_id", {"room_id": room_id})
    if affected == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return {"deleted": True}
