from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user, require_roles
from app.database import execute_returning_id, fetch_all, fetch_one
from app.schemas import ServiceRequest


router = APIRouter()


@router.get("")
def list_services(user: dict = Depends(get_current_user)) -> list[dict]:
    return fetch_all("SELECT service_id, service_name, price FROM services ORDER BY service_name")


@router.get("/usage")
def list_service_usage(mine: bool = False, user: dict = Depends(get_current_user)) -> list[dict]:
    params = {}
    sql = """
        SELECT su.usage_id, su.booking_id, su.service_id, s.service_name, su.quantity,
               su.total_price, u.name AS customer_name, r.room_number, b.booking_status
        FROM service_usage su
        JOIN services s ON s.service_id = su.service_id
        JOIN bookings b ON b.booking_id = su.booking_id
        JOIN customers c ON c.customer_id = b.customer_id
        JOIN users u ON u.user_id = c.user_id
        JOIN rooms r ON r.room_id = b.room_id
    """
    if mine or ("ROLE_CUSTOMER" in user.get("roles", []) and not {"ROLE_ADMIN", "ROLE_MANAGER", "ROLE_STAFF"}.intersection(user.get("roles", []))):
        sql += " WHERE c.customer_id = :customer_id"
        params["customer_id"] = user.get("customer_id")
    sql += " ORDER BY su.usage_id DESC"
    return fetch_all(sql, params)


@router.post("/usage")
def create_service_usage(payload: ServiceRequest, user: dict = Depends(get_current_user)) -> dict:
    booking = fetch_one("SELECT customer_id FROM bookings WHERE booking_id = :booking_id", {"booking_id": payload.booking_id})
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if "ROLE_CUSTOMER" in user.get("roles", []) and booking["customer_id"] != user.get("customer_id"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot add services to this booking")
    service = fetch_one("SELECT price FROM services WHERE service_id = :service_id", {"service_id": payload.service_id})
    if not service:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Service not found")
    total_price = float(service["price"]) * payload.quantity
    usage_id = execute_returning_id(
        """
        INSERT INTO service_usage (booking_id, service_id, quantity, total_price)
        VALUES (:booking_id, :service_id, :quantity, :total_price)
        RETURNING usage_id
        """,
        {**payload.model_dump(), "total_price": total_price},
    )
    return fetch_one(
        """
        SELECT su.usage_id, su.booking_id, su.service_id, s.service_name, su.quantity, su.total_price
        FROM service_usage su
        JOIN services s ON s.service_id = su.service_id
        WHERE su.usage_id = :usage_id
        """,
        {"usage_id": usage_id},
    )


@router.post("", dependencies=[Depends(require_roles("ROLE_ADMIN", "ROLE_MANAGER"))])
def create_service(payload: dict) -> dict:
    service_id = execute_returning_id(
        """
        INSERT INTO services (service_name, price)
        VALUES (:service_name, :price)
        RETURNING service_id
        """,
        payload,
    )
    return fetch_one("SELECT * FROM services WHERE service_id = :service_id", {"service_id": service_id})

