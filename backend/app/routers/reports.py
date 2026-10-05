from fastapi import APIRouter, Depends

from app.core.security import ADMIN, MANAGER, require_roles
from app.database import fetch_all

router = APIRouter(dependencies=[Depends(require_roles(ADMIN, MANAGER))])


@router.get("/summary")
def report_summary() -> dict:
    return {
        "revenue": fetch_all(
            """SELECT TO_CHAR(payment_date, 'YYYY-MM') AS label, SUM(amount) AS value
               FROM payments WHERE status = 'COMPLETED' GROUP BY 1 ORDER BY 1"""
        ),
        "bookings": fetch_all(
            "SELECT TO_CHAR(booking_date, 'YYYY-MM') AS label, COUNT(*) AS value FROM bookings GROUP BY 1 ORDER BY 1"
        ),
        "status_breakdown": fetch_all(
            "SELECT booking_status AS label, COUNT(*) AS value FROM bookings GROUP BY 1 ORDER BY value DESC"
        ),
        "room_types": fetch_all(
            """SELECT rt.type_name AS label, COUNT(r.room_id) AS value FROM room_types rt
               LEFT JOIN rooms r ON r.room_type_id = rt.room_type_id GROUP BY rt.type_name ORDER BY value DESC"""
        ),
        "services": fetch_all(
            """SELECT s.service_name AS label, COALESCE(SUM(su.quantity), 0) AS value FROM services s
               LEFT JOIN service_usage su ON su.service_id = s.service_id GROUP BY s.service_name ORDER BY value DESC"""
        ),
    }
