from fastapi import APIRouter, Depends

from app.core.security import get_current_user
from app.database import fetch_all, fetch_one


router = APIRouter()


@router.get("/overview")
def overview(user: dict = Depends(get_current_user)) -> dict:
    total_rooms = fetch_one("SELECT COUNT(*) AS value FROM rooms")["value"]
    available_rooms = fetch_one("SELECT COUNT(*) AS value FROM rooms WHERE status = 'AVAILABLE'")["value"]
    occupied_rooms = fetch_one("SELECT COUNT(*) AS value FROM rooms WHERE status = 'OCCUPIED'")["value"]
    maintenance_rooms = fetch_one("SELECT COUNT(*) AS value FROM rooms WHERE status = 'MAINTENANCE'")["value"]
    pending_bookings = fetch_one("SELECT COUNT(*) AS value FROM bookings WHERE booking_status = 'PENDING'")["value"]
    today_revenue = fetch_one(
        "SELECT NVL(SUM(amount), 0) AS value FROM payments WHERE TRUNC(payment_date) = TRUNC(SYSDATE)"
    )["value"]
    month_revenue = fetch_one(
        "SELECT NVL(SUM(amount), 0) AS value FROM payments WHERE TRUNC(payment_date, 'MM') = TRUNC(SYSDATE, 'MM')"
    )["value"]
    recent_bookings = fetch_all(
        """
        SELECT b.booking_id, u.name AS customer_name, r.room_number, rt.type_name,
               b.check_in_date, b.check_out_date, b.booking_status
        FROM bookings b
        JOIN customers c ON c.customer_id = b.customer_id
        JOIN users u ON u.user_id = c.user_id
        JOIN rooms r ON r.room_id = b.room_id
        JOIN room_types rt ON rt.room_type_id = r.room_type_id
        ORDER BY b.booking_id DESC
        FETCH FIRST 8 ROWS ONLY
        """
    )
    return {
        "total_rooms": total_rooms,
        "available_rooms": available_rooms,
        "occupied_rooms": occupied_rooms,
        "maintenance_rooms": maintenance_rooms,
        "pending_bookings": pending_bookings,
        "today_revenue": today_revenue,
        "month_revenue": month_revenue,
        "recent_bookings": recent_bookings,
    }

