from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from fastapi import HTTPException, status

from app.core.config import settings
from app.database import execute, execute_returning_id, fetch_one

CENT = Decimal("0.01")
BILLABLE_STATUSES = ("CHECKED_IN", "CHECKOUT_PENDING", "CHECKED_OUT")


def D(value: Any) -> Decimal:
    return Decimal(str(value or 0))


def compute_amounts(booking_id: int, conn) -> dict[str, Decimal]:
    row = fetch_one(
        """
        SELECT (b.check_out_date - b.check_in_date) * rt.price_per_night AS room_total,
               COALESCE((SELECT SUM(su.total_price) FROM service_usage su
                         WHERE su.booking_id = b.booking_id), 0) AS service_total,
               COALESCE((SELECT SUM(p.amount) FROM payments p
                         WHERE p.booking_id = b.booking_id AND p.status = 'COMPLETED'), 0) AS paid
        FROM bookings b
        JOIN rooms r ON r.room_id = b.room_id
        JOIN room_types rt ON rt.room_type_id = r.room_type_id
        WHERE b.booking_id = :booking_id
        """,
        {"booking_id": booking_id},
        conn=conn,
    )
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")
    subtotal = D(row["room_total"]) + D(row["service_total"])
    tax = (subtotal * settings.tax_rate).quantize(CENT, ROUND_HALF_UP)
    total = subtotal + tax
    paid = D(row["paid"])
    return {"subtotal": subtotal, "tax": tax, "total": total, "paid": paid, "balance": total - paid}


def ensure_invoice(booking_id: int, conn, *, create: bool = True) -> dict[str, Decimal]:
    """Create the invoice, or recalculate it from the current room + service charges."""
    amounts = compute_amounts(booking_id, conn)
    existing = fetch_one("SELECT invoice_id FROM invoices WHERE booking_id = :id", {"id": booking_id}, conn=conn)
    params = {"id": booking_id, "subtotal": amounts["subtotal"], "tax": amounts["tax"]}
    if existing:
        execute(
            "UPDATE invoices SET total_amount = :subtotal, tax = :tax WHERE booking_id = :id",
            params,
            conn=conn,
        )
    elif create:
        execute_returning_id(
            """
            INSERT INTO invoices (booking_id, total_amount, tax, generated_date)
            VALUES (:id, :subtotal, :tax, CURRENT_DATE)
            RETURNING invoice_id
            """,
            params,
            conn=conn,
        )
    return amounts
