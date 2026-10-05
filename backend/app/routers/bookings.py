from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.billing_logic import ensure_invoice
from app.core.audit import audit
from app.core.security import (
    CUSTOMER,
    get_current_user,
    has_role,
    is_management,
    is_ops,
)
from app.database import (
    execute,
    execute_returning_id,
    fetch_all,
    fetch_one,
    transaction,
)
from app.schemas import BookingRequest, BookingStatusRequest

router = APIRouter()

BOOKING_SELECT = """
SELECT b.booking_id, b.customer_id, b.room_id, b.booking_date, b.check_in_date, b.check_out_date,
       b.booking_status, b.rejection_reason, u.name AS customer_name, r.room_number, rt.type_name,
       rt.price_per_night, (b.check_out_date - b.check_in_date) AS nights,
       ((b.check_out_date - b.check_in_date) * rt.price_per_night) AS room_total
FROM bookings b
JOIN customers c ON c.customer_id = b.customer_id
JOIN users u ON u.user_id = c.user_id
JOIN rooms r ON r.room_id = b.room_id
JOIN room_types rt ON rt.room_type_id = r.room_type_id
"""
ACTIVE = "('APPROVED', 'CHECKIN_PENDING', 'CHECKED_IN', 'CHECKOUT_PENDING')"

# current status -> {new status: who may do it}  ("ops" = staff/manager/admin, "guest" = booking owner)
TRANSITIONS: dict[str, dict[str, str]] = {
    "PENDING": {"APPROVED": "ops", "REJECTED": "ops", "CANCELLED": "both"},
    "APPROVED": {"CHECKIN_PENDING": "guest", "CHECKED_IN": "ops", "CANCELLED": "both"},
    "CHECKIN_PENDING": {"CHECKED_IN": "ops", "CANCELLED": "both"},
    "CHECKED_IN": {"CHECKOUT_PENDING": "guest", "CHECKED_OUT": "ops"},
    "CHECKOUT_PENDING": {"CHECKED_OUT": "ops"},
}


@router.get("")
def list_bookings(
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    where, params = [], {"limit": limit, "offset": offset}
    if not is_ops(user):
        where.append("b.customer_id = :customer_id")
        params["customer_id"] = user.get("customer_id") or -1
    if status_filter:
        where.append("b.booking_status = :status")
        params["status"] = status_filter
    if search:
        where.append("(u.name ILIKE :q OR CAST(r.room_number AS TEXT) ILIKE :q OR CAST(b.booking_id AS TEXT) = :exact)")
        params.update({"q": f"%{search}%", "exact": search})
    sql = BOOKING_SELECT + (" WHERE " + " AND ".join(where) if where else "")
    return fetch_all(sql + " ORDER BY b.booking_id DESC LIMIT :limit OFFSET :offset", params)


def _get_visible(booking_id: int, user: dict, conn=None) -> dict:
    row = fetch_one(BOOKING_SELECT + " WHERE b.booking_id = :id", {"id": booking_id}, conn=conn)
    if not row or (not is_ops(user) and row["customer_id"] != user.get("customer_id")):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    return row


@router.get("/{booking_id}")
def get_booking(booking_id: int, user: dict = Depends(get_current_user)) -> dict:
    return _get_visible(booking_id, user)


@router.post("", status_code=201)
def create_booking(payload: BookingRequest, user: dict = Depends(get_current_user)) -> dict:
    ops = is_ops(user)
    if ops:
        if not payload.customer_id:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose the guest this booking is for")
        customer_id = payload.customer_id
    else:
        if not has_role(user, CUSTOMER) or not user.get("customer_id"):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only guest accounts can book rooms")
        if payload.customer_id and payload.customer_id != user["customer_id"]:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "You can only book for yourself")
        customer_id = user["customer_id"]
    with transaction() as conn:
        if not fetch_one("SELECT 1 FROM customers WHERE customer_id = :id", {"id": customer_id}, conn=conn):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Guest not found")
        room = fetch_one("SELECT status FROM rooms WHERE room_id = :id FOR UPDATE", {"id": payload.room_id}, conn=conn)
        if not room:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Room not found")
        if room["status"] == "MAINTENANCE":
            raise HTTPException(status.HTTP_409_CONFLICT, "Room is under maintenance")
        overlap = fetch_one(
            f"""SELECT 1 FROM bookings WHERE room_id = :room_id AND booking_status IN {ACTIVE}
                AND check_in_date < :check_out AND check_out_date > :check_in""",
            {"room_id": payload.room_id, "check_in": payload.check_in_date, "check_out": payload.check_out_date},
            conn=conn,
        )
        if overlap:
            raise HTTPException(status.HTTP_409_CONFLICT, "Room already has a booking for those dates")
        booking_id = execute_returning_id(
            """INSERT INTO bookings (customer_id, room_id, booking_date, check_in_date, check_out_date,
                                     booking_status, approved_by)
               VALUES (:customer_id, :room_id, CURRENT_DATE, :check_in, :check_out, :booking_status, :approved_by)
               RETURNING booking_id""",
            {
                "customer_id": customer_id,
                "room_id": payload.room_id,
                "check_in": payload.check_in_date,
                "check_out": payload.check_out_date,
                "booking_status": "APPROVED" if ops else "PENDING",  # staff-made bookings are pre-approved
                "approved_by": user["user_id"] if ops else None,
            },
            conn=conn,
        )
        audit(user["user_id"], "booking_created", booking_id=booking_id, walk_in=ops)
        return fetch_one(BOOKING_SELECT + " WHERE b.booking_id = :id", {"id": booking_id}, conn=conn)


@router.patch("/{booking_id}/status")
def update_booking_status(booking_id: int, payload: BookingStatusRequest, user: dict = Depends(get_current_user)) -> dict:
    ops = is_ops(user)
    new = payload.status
    if payload.override_balance and not is_management(user):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a manager or admin can override an outstanding balance")
    today = date.today()
    with transaction() as conn:
        booking = fetch_one("SELECT * FROM bookings WHERE booking_id = :id FOR UPDATE", {"id": booking_id}, conn=conn)
        owner = bool(user.get("customer_id")) and booking is not None and booking["customer_id"] == user["customer_id"]
        if not booking or not (ops or owner):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
        current = booking["booking_status"]
        who = TRANSITIONS.get(current, {}).get(new)
        if who is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"A {current} booking cannot be changed to {new}")
        if who == "ops" and not ops:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only staff can do this")
        if who == "guest" and not owner:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the guest can request this")
        check_in = date.fromisoformat(booking["check_in_date"])
        check_out = date.fromisoformat(booking["check_out_date"])
        room_id = booking["room_id"]
        room = fetch_one("SELECT status FROM rooms WHERE room_id = :id FOR UPDATE", {"id": room_id}, conn=conn)

        if new == "CANCELLED" and not ops and current != "PENDING" and today > check_in:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "A booking cannot be cancelled after its check-in date")
        if new == "APPROVED":
            if check_out <= today:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "This stay is already in the past")
            if room["status"] == "MAINTENANCE":
                raise HTTPException(status.HTTP_409_CONFLICT, "Room is under maintenance")
        if new == "CHECKED_IN":
            if not (check_in <= today < check_out):
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Check-in is only possible between the booked dates")
            if room["status"] == "MAINTENANCE":
                raise HTTPException(status.HTTP_409_CONFLICT, "Room is under maintenance")
            if fetch_one(
                "SELECT 1 FROM bookings WHERE room_id = :r AND booking_id <> :b AND booking_status IN ('CHECKED_IN', 'CHECKOUT_PENDING')",
                {"r": room_id, "b": booking_id}, conn=conn,
            ):
                raise HTTPException(status.HTTP_409_CONFLICT, "The previous guest has not checked out of this room yet")
        if new == "CHECKED_OUT":
            amounts = ensure_invoice(booking_id, conn)
            if amounts["balance"] > 0:
                if not payload.override_balance:
                    raise HTTPException(
                        status.HTTP_409_CONFLICT,
                        f"An outstanding balance of {amounts['balance']} must be paid before check-out",
                    )
                audit(user["user_id"], "checkout_balance_override", booking_id=booking_id, balance=amounts["balance"])

        execute(
            """UPDATE bookings SET booking_status = :status,
                      approved_by = CASE WHEN :decided THEN :uid ELSE approved_by END,
                      rejection_reason = CASE WHEN :rejected THEN :reason ELSE rejection_reason END
               WHERE booking_id = :id""",
            {"status": new, "decided": new in ("APPROVED", "REJECTED"), "rejected": new == "REJECTED",
             "uid": user["user_id"], "reason": payload.rejection_reason, "id": booking_id},
            conn=conn,
        )
        if new == "CHECKED_IN":
            execute("UPDATE rooms SET status = 'OCCUPIED' WHERE room_id = :id", {"id": room_id}, conn=conn)
        elif new == "CHECKED_OUT":
            still_occupied = fetch_one(
                "SELECT 1 FROM bookings WHERE room_id = :r AND booking_id <> :b AND booking_status IN ('CHECKED_IN', 'CHECKOUT_PENDING')",
                {"r": room_id, "b": booking_id}, conn=conn,
            )
            if not still_occupied:
                execute("UPDATE rooms SET status = 'AVAILABLE' WHERE room_id = :id AND status = 'OCCUPIED'", {"id": room_id}, conn=conn)
        audit(user["user_id"], "booking_status", booking_id=booking_id, old=current, new=new)
        return fetch_one(BOOKING_SELECT + " WHERE b.booking_id = :id", {"id": booking_id}, conn=conn)
