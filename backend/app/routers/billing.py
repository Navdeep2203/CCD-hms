from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import get_current_user, require_roles
from app.database import execute_returning_id, fetch_all, fetch_one
from app.schemas import PaymentRequest


router = APIRouter()


INVOICE_SELECT = """
SELECT i.invoice_id, i.booking_id, i.total_amount, i.tax, i.generated_date,
       u.name AS customer_name, r.room_number, b.check_in_date, b.check_out_date,
       b.booking_status, NVL(paid.amount_paid, 0) AS amount_paid,
       (i.total_amount + i.tax - NVL(paid.amount_paid, 0)) AS balance_due
FROM invoices i
JOIN bookings b ON b.booking_id = i.booking_id
JOIN customers c ON c.customer_id = b.customer_id
JOIN users u ON u.user_id = c.user_id
JOIN rooms r ON r.room_id = b.room_id
LEFT JOIN (
    SELECT booking_id, SUM(amount) AS amount_paid
    FROM payments
    WHERE status = 'COMPLETED'
    GROUP BY booking_id
) paid ON paid.booking_id = i.booking_id
"""


@router.get("/invoices")
def list_invoices(mine: bool = False, user: dict = Depends(get_current_user)) -> list[dict]:
    params = {}
    sql = INVOICE_SELECT
    if mine or ("ROLE_CUSTOMER" in user.get("roles", []) and not {"ROLE_ADMIN", "ROLE_MANAGER"}.intersection(user.get("roles", []))):
        sql += " WHERE c.customer_id = :customer_id"
        params["customer_id"] = user.get("customer_id")
    sql += " ORDER BY i.invoice_id DESC"
    return fetch_all(sql, params)


@router.post("/invoices/{booking_id}/generate", dependencies=[Depends(require_roles("ROLE_ADMIN", "ROLE_MANAGER", "ROLE_STAFF"))])
def generate_invoice(booking_id: int) -> dict:
    existing = fetch_one(INVOICE_SELECT + " WHERE i.booking_id = :booking_id", {"booking_id": booking_id})
    if existing:
        return existing
    booking = fetch_one(
        """
        SELECT b.booking_id,
               ((b.check_out_date - b.check_in_date) * rt.price_per_night) AS room_total,
               NVL((SELECT SUM(total_price) FROM service_usage su WHERE su.booking_id = b.booking_id), 0) AS service_total
        FROM bookings b
        JOIN rooms r ON r.room_id = b.room_id
        JOIN room_types rt ON rt.room_type_id = r.room_type_id
        WHERE b.booking_id = :booking_id
        """,
        {"booking_id": booking_id},
    )
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    subtotal = float(booking["room_total"] or 0) + float(booking["service_total"] or 0)
    tax = round(subtotal * 0.12, 2)
    invoice_id = execute_returning_id(
        """
        INSERT INTO invoices (booking_id, total_amount, tax, generated_date)
        VALUES (:booking_id, :total_amount, :tax, SYSDATE)
        RETURNING invoice_id INTO :new_id
        """,
        {"booking_id": booking_id, "total_amount": subtotal, "tax": tax},
    )
    return fetch_one(INVOICE_SELECT + " WHERE i.invoice_id = :invoice_id", {"invoice_id": invoice_id})


@router.get("/methods")
def payment_methods(user: dict = Depends(get_current_user)) -> list[dict]:
    return fetch_all("SELECT * FROM payment_methods ORDER BY method_name")


@router.get("/payments/{booking_id}")
def payments_for_booking(booking_id: int, user: dict = Depends(get_current_user)) -> list[dict]:
    return fetch_all(
        """
        SELECT p.payment_id, p.booking_id, p.method_id, pm.method_name, p.amount, p.payment_date, p.status
        FROM payments p
        JOIN payment_methods pm ON pm.method_id = p.method_id
        WHERE p.booking_id = :booking_id
        ORDER BY p.payment_date DESC
        """,
        {"booking_id": booking_id},
    )


@router.post("/payments")
def create_payment(payload: PaymentRequest, user: dict = Depends(get_current_user)) -> dict:
    payment_id = execute_returning_id(
        """
        INSERT INTO payments (booking_id, method_id, amount, payment_date, status)
        VALUES (:booking_id, :method_id, :amount, SYSDATE, 'COMPLETED')
        RETURNING payment_id INTO :new_id
        """,
        payload.model_dump(),
    )
    return fetch_one(
        """
        SELECT p.payment_id, p.booking_id, p.method_id, pm.method_name, p.amount, p.payment_date, p.status
        FROM payments p
        JOIN payment_methods pm ON pm.method_id = p.method_id
        WHERE p.payment_id = :payment_id
        """,
        {"payment_id": payment_id},
    )

