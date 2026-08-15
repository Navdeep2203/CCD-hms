from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import get_current_user, require_roles
from app.database import execute, execute_returning_id, fetch_all, fetch_one
from app.schemas import BookingRequest, StatusRequest


router = APIRouter()


BOOKING_SELECT = """
SELECT b.booking_id, b.customer_id, b.room_id, b.booking_date, b.check_in_date, b.check_out_date,
       b.booking_status, u.name AS customer_name, r.room_number, rt.type_name, rt.price_per_night
FROM bookings b
JOIN customers c ON c.customer_id = b.customer_id
JOIN users u ON u.user_id = c.user_id
JOIN rooms r ON r.room_id = b.room_id
JOIN room_types rt ON rt.room_type_id = r.room_type_id
"""


@router.get("")
def list_bookings(
    status_filter: str | None = Query(default=None, alias="status"),
    mine: bool = False,
    user: dict = Depends(get_current_user),
) -> list[dict]:
    params = {}
    where = []
    if mine or ("ROLE_CUSTOMER" in user.get("roles", []) and not {"ROLE_ADMIN", "ROLE_MANAGER"}.intersection(user.get("roles", []))):
        where.append("b.customer_id = :customer_id")
        params["customer_id"] = user.get("customer_id")
    if status_filter:
        where.append("b.booking_status = :status")
        params["status"] = status_filter
    sql = BOOKING_SELECT
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY b.booking_id DESC"
    return fetch_all(sql, params)


@router.post("")
def create_booking(payload: BookingRequest, user: dict = Depends(require_roles("ROLE_CUSTOMER", "ROLE_ADMIN", "ROLE_MANAGER"))) -> dict:
    customer_id = user.get("customer_id")
    if not customer_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only customer accounts can book rooms")
    overlap = fetch_one(
        """
        SELECT 1
        FROM bookings
        WHERE room_id = :room_id
          AND booking_status IN ('APPROVED', 'CHECKED_IN', 'CHECKIN_PENDING')
          AND NOT (check_out_date <= CAST(:check_in_date AS DATE)
                   OR check_in_date >= CAST(:check_out_date AS DATE))
        """,
        payload.model_dump(),
    )
    room = fetch_one("SELECT status FROM rooms WHERE room_id = :room_id", {"room_id": payload.room_id})
    if not room or room["status"] not in ("AVAILABLE", "RESERVED"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room is not available")
    if overlap:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room already has a booking for those dates")

    booking_id = execute_returning_id(
        """
        INSERT INTO bookings (customer_id, room_id, booking_date, check_in_date, check_out_date, booking_status)
        VALUES (:customer_id, :room_id, CURRENT_DATE, CAST(:check_in_date AS DATE),
                CAST(:check_out_date AS DATE), 'PENDING')
        RETURNING booking_id
        """,
        {**payload.model_dump(), "customer_id": customer_id},
    )
    return fetch_one(BOOKING_SELECT + " WHERE b.booking_id = :booking_id", {"booking_id": booking_id})


@router.patch("/{booking_id}/status")
def update_booking_status(booking_id: int, payload: StatusRequest, user: dict = Depends(get_current_user)) -> dict:
    allowed_customer = {"CHECKIN_PENDING", "CHECKOUT_PENDING", "CANCELLED"}
    allowed_admin = {"APPROVED", "REJECTED", "CHECKED_IN", "CHECKED_OUT", "CANCELLED", "PENDING"}
    booking = fetch_one("SELECT * FROM bookings WHERE booking_id = :booking_id", {"booking_id": booking_id})
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    roles = set(user.get("roles", []))
    if "ROLE_CUSTOMER" in roles and booking["customer_id"] != user.get("customer_id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot update this booking")
    if roles.intersection({"ROLE_ADMIN", "ROLE_MANAGER", "ROLE_STAFF"}):
        allowed = allowed_admin
    else:
        allowed = allowed_customer
    if payload.status not in allowed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status transition is not allowed")

    execute("UPDATE bookings SET booking_status = :status WHERE booking_id = :booking_id", {"status": payload.status, "booking_id": booking_id})
    if payload.status == "APPROVED":
        execute("UPDATE rooms SET status = 'RESERVED' WHERE room_id = :room_id", {"room_id": booking["room_id"]})
    elif payload.status == "CHECKED_IN":
        execute("UPDATE rooms SET status = 'OCCUPIED' WHERE room_id = :room_id", {"room_id": booking["room_id"]})
    elif payload.status in ("CHECKED_OUT", "CANCELLED", "REJECTED"):
        execute("UPDATE rooms SET status = 'AVAILABLE' WHERE room_id = :room_id", {"room_id": booking["room_id"]})
    return fetch_one(BOOKING_SELECT + " WHERE b.booking_id = :booking_id", {"booking_id": booking_id})
