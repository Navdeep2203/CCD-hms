from decimal import ROUND_HALF_UP

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.billing_logic import BILLABLE_STATUSES, D, ensure_invoice
from app.core.audit import audit
from app.core.config import settings
from app.core.security import get_current_user, is_ops
from app.database import (
    execute,
    execute_returning_id,
    fetch_all,
    fetch_one,
    transaction,
)
from app.schemas import PaymentRequest

router = APIRouter()

INVOICE_SELECT = """
SELECT i.invoice_id, i.booking_id, i.total_amount, i.tax, (i.total_amount + i.tax) AS grand_total,
       i.generated_date, u.name AS customer_name, r.room_number, b.check_in_date, b.check_out_date,
       b.booking_status, COALESCE(paid.amount_paid, 0) AS amount_paid,
       (i.total_amount + i.tax - COALESCE(paid.amount_paid, 0)) AS balance_due,
       CASE WHEN COALESCE(paid.amount_paid, 0) >= i.total_amount + i.tax THEN 'PAID'
            WHEN COALESCE(paid.amount_paid, 0) > 0 THEN 'PARTIAL' ELSE 'UNPAID' END AS payment_state
FROM invoices i
JOIN bookings b ON b.booking_id = i.booking_id
JOIN customers c ON c.customer_id = b.customer_id
JOIN users u ON u.user_id = c.user_id
JOIN rooms r ON r.room_id = b.room_id
LEFT JOIN (SELECT booking_id, SUM(amount) AS amount_paid FROM payments
           WHERE status = 'COMPLETED' GROUP BY booking_id) paid ON paid.booking_id = i.booking_id
"""


def _booking_for(booking_id: int, user: dict, conn=None) -> dict:
    row = fetch_one("SELECT booking_id, customer_id, booking_status FROM bookings WHERE booking_id = :id", {"id": booking_id}, conn=conn)
    if not row or (not is_ops(user) and row["customer_id"] != user.get("customer_id")):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    return row


@router.get("/invoices")
def list_invoices(
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    where, params = [], {"limit": limit, "offset": offset}
    if not is_ops(user):
        where.append("c.customer_id = :customer_id")
        params["customer_id"] = user.get("customer_id") or -1
    if search:
        where.append("(u.name ILIKE :q OR CAST(r.room_number AS TEXT) ILIKE :q OR CAST(i.invoice_id AS TEXT) = :exact)")
        params.update({"q": f"%{search}%", "exact": search})
    sql = INVOICE_SELECT + (" WHERE " + " AND ".join(where) if where else "")
    return fetch_all(sql + " ORDER BY i.invoice_id DESC LIMIT :limit OFFSET :offset", params)


@router.post("/invoices/{booking_id}/generate")
def generate_invoice(booking_id: int, user: dict = Depends(get_current_user)) -> dict:
    """Create the invoice, or recalculate it so late-added services are included."""
    with transaction() as conn:
        booking = _booking_for(booking_id, user, conn)
        if booking["booking_status"] not in BILLABLE_STATUSES:
            raise HTTPException(status.HTTP_409_CONFLICT, "An invoice can only be created once the guest has checked in")
        ensure_invoice(booking_id, conn)
        return fetch_one(INVOICE_SELECT + " WHERE i.booking_id = :id", {"id": booking_id}, conn=conn)


@router.get("/methods")
def payment_methods(user: dict = Depends(get_current_user)) -> list[dict]:
    return fetch_all("SELECT method_id, method_name FROM payment_methods ORDER BY method_name")


@router.get("/payable")
def payable_bookings(user: dict = Depends(get_current_user)) -> list[dict]:
    """Bookings that can take a payment right now, with the live balance (no free-text booking ids)."""
    params = {"rate": settings.tax_rate}
    scope = ""
    if not is_ops(user):
        scope = " AND b.customer_id = :customer_id"
        params["customer_id"] = user.get("customer_id") or -1
    rows = fetch_all(
        f"""
        SELECT b.booking_id, u.name AS customer_name, r.room_number, b.booking_status,
               ((b.check_out_date - b.check_in_date) * rt.price_per_night
                 + COALESCE((SELECT SUM(su.total_price) FROM service_usage su WHERE su.booking_id = b.booking_id), 0)) AS subtotal,
               COALESCE((SELECT SUM(p.amount) FROM payments p
                         WHERE p.booking_id = b.booking_id AND p.status = 'COMPLETED'), 0) AS paid
        FROM bookings b
        JOIN customers c ON c.customer_id = b.customer_id
        JOIN users u ON u.user_id = c.user_id
        JOIN rooms r ON r.room_id = b.room_id
        JOIN room_types rt ON rt.room_type_id = r.room_type_id
        WHERE b.booking_status IN ('CHECKED_IN', 'CHECKOUT_PENDING', 'CHECKED_OUT'){scope}
        ORDER BY b.booking_id DESC
        """,
        params,
    )
    result = []
    for row in rows:
        subtotal = D(row["subtotal"])
        total = subtotal + (subtotal * settings.tax_rate).quantize(D("0.01"), ROUND_HALF_UP)
        balance = total - D(row["paid"])
        if balance > 0:
            result.append({**{k: row[k] for k in ("booking_id", "customer_name", "room_number", "booking_status")},
                           "balance_due": float(balance)})
    return result


@router.get("/payments/{booking_id}")
def payments_for_booking(booking_id: int, user: dict = Depends(get_current_user)) -> list[dict]:
    _booking_for(booking_id, user)
    return fetch_all(
        """
        SELECT p.payment_id, p.booking_id, p.method_id, pm.method_name, p.amount, p.payment_date, p.status
        FROM payments p JOIN payment_methods pm ON pm.method_id = p.method_id
        WHERE p.booking_id = :booking_id ORDER BY p.payment_id DESC
        """,
        {"booking_id": booking_id},
    )


@router.post("/payments", status_code=201)
def create_payment(payload: PaymentRequest, user: dict = Depends(get_current_user)) -> dict:
    with transaction() as conn:
        fetch_one("SELECT 1 FROM bookings WHERE booking_id = :id FOR UPDATE", {"id": payload.booking_id}, conn=conn)
        booking = _booking_for(payload.booking_id, user, conn)
        if booking["booking_status"] not in BILLABLE_STATUSES:
            raise HTTPException(status.HTTP_409_CONFLICT, "Payments are accepted once the guest has checked in")
        amounts = ensure_invoice(payload.booking_id, conn)
        if amounts["balance"] <= 0:
            raise HTTPException(status.HTTP_409_CONFLICT, "This booking is already fully paid")
        if payload.amount > amounts["balance"]:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Amount exceeds the balance due ({amounts['balance']})")
        payment_id = execute_returning_id(
            """INSERT INTO payments (booking_id, method_id, amount, payment_date, status)
               VALUES (:booking_id, :method_id, :amount, CURRENT_DATE, 'COMPLETED') RETURNING payment_id""",
            payload.model_dump(),
            conn=conn,
        )
        points = int(payload.amount // settings.loyalty_unit)
        if points:
            execute(
                "UPDATE customers SET loyalty_points = loyalty_points + :p WHERE customer_id = :c",
                {"p": points, "c": booking["customer_id"]},
                conn=conn,
            )
        audit(user["user_id"], "payment_recorded", payment_id=payment_id, booking_id=payload.booking_id, amount=payload.amount)
        return fetch_one(
            """SELECT p.payment_id, p.booking_id, p.method_id, pm.method_name, p.amount, p.payment_date, p.status
               FROM payments p JOIN payment_methods pm ON pm.method_id = p.method_id WHERE p.payment_id = :id""",
            {"id": payment_id},
            conn=conn,
        )
