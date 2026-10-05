from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.billing_logic import ensure_invoice
from app.core.audit import audit
from app.core.security import ADMIN, MANAGER, get_current_user, is_ops, require_roles
from app.core.sqlutil import build_set
from app.database import (
    execute,
    execute_returning_id,
    fetch_all,
    fetch_one,
    transaction,
)
from app.schemas import ServiceCreateRequest, ServiceRequest, ServiceUpdateRequest

router = APIRouter()
management = Depends(require_roles(ADMIN, MANAGER))


@router.get("")
def list_services(user: dict = Depends(get_current_user)) -> list[dict]:
    return fetch_all("SELECT service_id, service_name, price FROM services ORDER BY service_name")


@router.get("/usage")
def list_service_usage(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    params = {"limit": limit, "offset": offset}
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
    if not is_ops(user):
        sql += " WHERE c.customer_id = :customer_id"
        params["customer_id"] = user.get("customer_id") or -1
    return fetch_all(sql + " ORDER BY su.usage_id DESC LIMIT :limit OFFSET :offset", params)


@router.post("/usage", status_code=201)
def create_service_usage(payload: ServiceRequest, user: dict = Depends(get_current_user)) -> dict:
    with transaction() as conn:
        booking = fetch_one(
            "SELECT customer_id, booking_status FROM bookings WHERE booking_id = :id FOR UPDATE",
            {"id": payload.booking_id}, conn=conn,
        )
        if not booking or (not is_ops(user) and booking["customer_id"] != user.get("customer_id")):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
        if booking["booking_status"] != "CHECKED_IN":
            raise HTTPException(status.HTTP_409_CONFLICT, "Services can only be added while the guest is checked in")
        service = fetch_one("SELECT price FROM services WHERE service_id = :id", {"id": payload.service_id}, conn=conn)
        if not service:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found")
        total_price = round(float(service["price"]) * payload.quantity, 2)
        usage_id = execute_returning_id(
            """INSERT INTO service_usage (booking_id, service_id, quantity, total_price)
               VALUES (:booking_id, :service_id, :quantity, :total_price) RETURNING usage_id""",
            {**payload.model_dump(), "total_price": total_price},
            conn=conn,
        )
        ensure_invoice(payload.booking_id, conn, create=False)  # keep an existing invoice in sync
        return fetch_one(
            """SELECT su.usage_id, su.booking_id, su.service_id, s.service_name, su.quantity, su.total_price
               FROM service_usage su JOIN services s ON s.service_id = su.service_id WHERE su.usage_id = :id""",
            {"id": usage_id}, conn=conn,
        )


@router.post("", status_code=201)
def create_service(payload: ServiceCreateRequest, user: dict = management) -> dict:
    service_id = execute_returning_id(
        "INSERT INTO services (service_name, price) VALUES (:service_name, :price) RETURNING service_id",
        payload.model_dump(),
    )
    audit(user["user_id"], "service_created", service_id=service_id)
    return fetch_one("SELECT service_id, service_name, price FROM services WHERE service_id = :id", {"id": service_id})


@router.put("/{service_id}")
def update_service(service_id: int, payload: ServiceUpdateRequest, user: dict = management) -> dict:
    data = payload.model_dump(exclude_unset=True)
    if not data or any(value is None for value in data.values()):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Provide a name and/or a price")
    set_sql, params = build_set(data, {"service_name", "price"})
    if not execute(f"UPDATE services SET {set_sql} WHERE service_id = :id", {**params, "id": service_id}):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found")
    return fetch_one("SELECT service_id, service_name, price FROM services WHERE service_id = :id", {"id": service_id})


@router.delete("/{service_id}")
def delete_service(service_id: int, user: dict = management) -> dict:
    if not execute("DELETE FROM services WHERE service_id = :id", {"id": service_id}):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Service not found")
    audit(user["user_id"], "service_deleted", service_id=service_id)
    return {"deleted": True}
