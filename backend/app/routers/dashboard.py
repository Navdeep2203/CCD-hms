from datetime import date

from fastapi import APIRouter, Depends

from app.core.security import ADMIN, MANAGER, get_current_user, has_role, is_ops
from app.database import fetch_all, fetch_one

router = APIRouter()

BOOKING_ROWS = """
SELECT b.booking_id, u.name AS customer_name, r.room_number, rt.type_name,
       b.check_in_date, b.check_out_date, b.booking_status
FROM bookings b
JOIN customers c ON c.customer_id = b.customer_id
JOIN users u ON u.user_id = c.user_id
JOIN rooms r ON r.room_id = b.room_id
JOIN room_types rt ON rt.room_type_id = r.room_type_id
"""


def _count(sql: str, params: dict | None = None) -> int:
    return fetch_one(sql, params)["value"]


def _guest_overview(user: dict) -> dict:
    cid = user.get("customer_id") or -1
    mine = BOOKING_ROWS.replace("u.name AS customer_name, ", "") + " WHERE b.customer_id = :cid"
    current = fetch_all(mine + " AND b.booking_status IN ('CHECKED_IN', 'CHECKOUT_PENDING') ORDER BY b.check_in_date LIMIT 1", {"cid": cid})
    upcoming = fetch_all(
        mine + " AND b.booking_status IN ('PENDING', 'APPROVED', 'CHECKIN_PENDING') ORDER BY b.check_in_date LIMIT 5", {"cid": cid}
    )
    balance = fetch_one(
        """
        SELECT COALESCE(SUM(i.total_amount + i.tax - COALESCE(p.paid, 0)), 0) AS value
        FROM invoices i JOIN bookings b ON b.booking_id = i.booking_id
        LEFT JOIN (SELECT booking_id, SUM(amount) AS paid FROM payments WHERE status = 'COMPLETED' GROUP BY booking_id) p
               ON p.booking_id = i.booking_id
        WHERE b.customer_id = :cid
        """,
        {"cid": cid},
    )["value"]
    stays = _count("SELECT COUNT(*) AS value FROM bookings WHERE customer_id = :cid AND booking_status = 'CHECKED_OUT'", {"cid": cid})
    return {
        "kind": "guest",
        "current_stay": current[0] if current else None,
        "upcoming": upcoming,
        "balance_due": balance,
        "loyalty_points": user.get("loyalty_points") or 0,
        "completed_stays": stays,
    }


@router.get("/overview")
def overview(user: dict = Depends(get_current_user)) -> dict:
    if not is_ops(user):
        return _guest_overview(user)
    today = date.today()
    data = {
        "kind": "management" if has_role(user, ADMIN, MANAGER) else "staff",
        "total_rooms": _count("SELECT COUNT(*) AS value FROM rooms"),
        "available_rooms": _count("SELECT COUNT(*) AS value FROM rooms WHERE status = 'AVAILABLE'"),
        "occupied_rooms": _count("SELECT COUNT(*) AS value FROM rooms WHERE status = 'OCCUPIED'"),
        "maintenance_rooms": _count("SELECT COUNT(*) AS value FROM rooms WHERE status = 'MAINTENANCE'"),
        "pending_bookings": _count("SELECT COUNT(*) AS value FROM bookings WHERE booking_status = 'PENDING'"),
        "arrivals_today": fetch_all(
            BOOKING_ROWS + " WHERE b.booking_status IN ('APPROVED', 'CHECKIN_PENDING') AND b.check_in_date = :d ORDER BY r.room_number",
            {"d": today},
        ),
        "departures_today": fetch_all(
            BOOKING_ROWS + " WHERE b.booking_status IN ('CHECKED_IN', 'CHECKOUT_PENDING') AND b.check_out_date <= :d ORDER BY r.room_number",
            {"d": today},
        ),
        "recent_bookings": fetch_all(BOOKING_ROWS + " ORDER BY b.booking_id DESC LIMIT 8"),
    }
    if data["kind"] == "management":  # revenue is not shown to front-line staff
        data["today_revenue"] = _count(
            "SELECT COALESCE(SUM(amount), 0) AS value FROM payments WHERE status = 'COMPLETED' AND payment_date = CURRENT_DATE"
        )
        data["month_revenue"] = _count(
            """SELECT COALESCE(SUM(amount), 0) AS value FROM payments
               WHERE status = 'COMPLETED' AND payment_date >= date_trunc('month', CURRENT_DATE)::date
                 AND payment_date < (date_trunc('month', CURRENT_DATE) + INTERVAL '1 month')::date"""
        )
    return data
