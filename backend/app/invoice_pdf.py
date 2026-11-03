
"""
Professional invoice PDF generator.

Uses ReportLab and returns PDF bytes.
All monetary totals are supplied by the existing billing logic.
"""

from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from typing import Any, Mapping, Sequence

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import simpleSplit
from reportlab.pdfgen import canvas


# ---------------------------------------------------------
# Page and styling configuration
# ---------------------------------------------------------

PAGE_WIDTH, PAGE_HEIGHT = A4

MARGIN = 48
CONTENT_WIDTH = PAGE_WIDTH - (2 * MARGIN)

NAVY = colors.HexColor("#172B4D")
BLUE = colors.HexColor("#315E9B")
LIGHT_BLUE = colors.HexColor("#EEF3F9")
LIGHT_GREY = colors.HexColor("#F3F5F8")
MID_GREY = colors.HexColor("#667085")
DARK_GREY = colors.HexColor("#344054")
BORDER = colors.HexColor("#DCE2EA")
WHITE = colors.white
GREEN = colors.HexColor("#16803C")
RED = colors.HexColor("#B42318")


# ---------------------------------------------------------
# Value formatting
# ---------------------------------------------------------

def _decimal(value: Any) -> Decimal:
    """Safely convert a database or API numeric value to Decimal."""
    try:
        return Decimal(str(value if value is not None else 0))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("Invalid monetary value supplied to invoice PDF") from exc


def _money(value: Any) -> str:
    """Format currency consistently without relying on system locale."""
    amount = _decimal(value)
    return f"INR {amount:,.2f}"


def _date_label(value: Any) -> str:
    """Format ISO dates and Python date objects for display."""
    if value is None:
        return "N/A"

    if isinstance(value, datetime):
        return value.strftime("%d %b %Y")

    if isinstance(value, date):
        return value.strftime("%d %b %Y")

    raw = str(value)

    try:
        return date.fromisoformat(raw[:10]).strftime("%d %b %Y")
    except ValueError:
        return raw


def _nights(check_in: Any, check_out: Any) -> int:
    """Calculate stay duration from booking dates."""
    try:
        start = (
            check_in
            if isinstance(check_in, date)
            else date.fromisoformat(str(check_in)[:10])
        )
        end = (
            check_out
            if isinstance(check_out, date)
            else date.fromisoformat(str(check_out)[:10])
        )

        if isinstance(start, datetime):
            start = start.date()

        if isinstance(end, datetime):
            end = end.date()

        return max((end - start).days, 0)
    except (TypeError, ValueError):
        return 0


# ---------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------

def _draw_wrapped(
    pdf: canvas.Canvas,
    text: str,
    x: float,
    y: float,
    max_width: float,
    *,
    font: str = "Helvetica",
    size: int = 9,
    leading: int = 12,
) -> float:
    """Draw wrapped text and return the next vertical position."""
    lines = simpleSplit(str(text), font, size, max_width)

    pdf.setFont(font, size)
    pdf.setFillColor(DARK_GREY)

    for line in lines:
        pdf.drawString(x, y, line)
        y -= leading

    return y


def _draw_label_value(
    pdf: canvas.Canvas,
    label: str,
    value: Any,
    x: float,
    y: float,
    width: float,
) -> None:
    """Draw a small label/value pair."""
    pdf.setFillColor(MID_GREY)
    pdf.setFont("Helvetica", 8)
    pdf.drawString(x, y, label.upper())

    pdf.setFillColor(NAVY)
    pdf.setFont("Helvetica-Bold", 10)

    lines = simpleSplit(str(value or "N/A"), "Helvetica-Bold", 10, width)
    for index, line in enumerate(lines[:2]):
        pdf.drawString(x, y - 15 - (index * 12), line)


def _draw_page_header(
    pdf: canvas.Canvas,
    invoice: Mapping[str, Any],
) -> float:
    """Draw the invoice heading and guest/booking information."""
    pdf.setFillColor(LIGHT_BLUE)
    pdf.rect(
        0,
        PAGE_HEIGHT - 112,
        PAGE_WIDTH,
        112,
        fill=1,
        stroke=0,
    )

    pdf.setFillColor(NAVY)
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(MARGIN, PAGE_HEIGHT - 52, "INVOICE")

    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(MID_GREY)
    pdf.drawString(
        MARGIN,
        PAGE_HEIGHT - 70,
        "HOTEL MANAGEMENT SYSTEM",
    )

    pdf.setFillColor(NAVY)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawRightString(
        PAGE_WIDTH - MARGIN,
        PAGE_HEIGHT - 43,
        f"Invoice #{invoice.get('invoice_id', 'N/A')}",
    )

    pdf.setFont("Helvetica", 9)
    pdf.setFillColor(MID_GREY)
    pdf.drawRightString(
        PAGE_WIDTH - MARGIN,
        PAGE_HEIGHT - 60,
        f"Booking #{invoice.get('booking_id', 'N/A')}",
    )
    pdf.drawRightString(
        PAGE_WIDTH - MARGIN,
        PAGE_HEIGHT - 76,
        f"Generated: {_date_label(invoice.get('generated_date'))}",
    )

    top = PAGE_HEIGHT - 142

    # Guest and room information.
    pdf.setFillColor(NAVY)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(MARGIN, top, "GUEST DETAILS")

    pdf.setStrokeColor(BORDER)
    pdf.line(MARGIN, top - 9, PAGE_WIDTH - MARGIN, top - 9)

    col_gap = 28
    col_width = (CONTENT_WIDTH - col_gap) / 2

    _draw_label_value(
        pdf,
        "Guest name",
        invoice.get("customer_name"),
        MARGIN,
        top - 31,
        col_width,
    )

    _draw_label_value(
        pdf,
        "Room number",
        invoice.get("room_number"),
        MARGIN + col_width + col_gap,
        top - 31,
        col_width,
    )

    y = top - 91

    pdf.setFillColor(NAVY)
    pdf.setFont("Helvetica-Bold", 11)
    pdf.drawString(MARGIN, y, "STAY DETAILS")

    pdf.setStrokeColor(BORDER)
    pdf.line(MARGIN, y - 9, PAGE_WIDTH - MARGIN, y - 9)

    _draw_label_value(
        pdf,
        "Check-in",
        _date_label(invoice.get("check_in_date")),
        MARGIN,
        y - 31,
        col_width,
    )

    _draw_label_value(
        pdf,
        "Check-out",
        _date_label(invoice.get("check_out_date")),
        MARGIN + col_width + col_gap,
        y - 31,
        col_width,
    )

    return y - 83


def _draw_footer(pdf: canvas.Canvas, booking_id: Any) -> None:
    """Draw a simple page footer."""
    pdf.setStrokeColor(BORDER)
    pdf.line(
        MARGIN,
        38,
        PAGE_WIDTH - MARGIN,
        38,
    )

    pdf.setFont("Helvetica", 8)
    pdf.setFillColor(MID_GREY)
    pdf.drawString(
        MARGIN,
        25,
        f"Generated by Hotel Management System | Booking #{booking_id}",
    )


# ---------------------------------------------------------
# Main PDF generation function
# ---------------------------------------------------------

def build_invoice_pdf(
    invoice: Mapping[str, Any],
    service_lines: Sequence[Mapping[str, Any]],
) -> bytes:
    """
    Build and return a complete invoice PDF.

    Expected invoice fields:
        invoice_id
        booking_id
        customer_name
        room_number
        check_in_date
        check_out_date
        generated_date
        total_amount
        room_total
        tax
        grand_total
        amount_paid
        balance_due
        payment_state

    Expected service-line fields:
        service_name
        quantity
        total_price

    Monetary totals must come from the existing billing system.
    """
    required_fields = (
        "invoice_id",
        "booking_id",
        "customer_name",
        "total_amount",
    )

    missing = [
        field for field in required_fields
        if invoice.get(field) is None
    ]

    if missing:
        raise ValueError(
            f"Missing invoice fields: {', '.join(missing)}"
        )

    # Convert service rows into a stable list.
    lines = list(service_lines)

    # The invoice subtotal is authoritative and comes from
    # billing_logic.ensure_invoice().
    subtotal = _decimal(invoice["total_amount"])
    tax = _decimal(invoice.get("tax"))
    grand_total = _decimal(
        invoice.get("grand_total", subtotal + tax)
    )
    amount_paid = _decimal(invoice.get("amount_paid"))
    balance_due = _decimal(
        invoice.get("balance_due", grand_total - amount_paid)
    )

    service_total = sum(
        (_decimal(line.get("total_price")) for line in lines),
        Decimal("0"),
    )

    # Prefer the room total supplied by the billing endpoint.
    # The fallback derives the room charge from the existing
    # subtotal and service totals, without recalculating tax.
    room_total = invoice.get("room_total")

    if room_total is None:
        room_total = subtotal - service_total

    room_total = _decimal(room_total)

    nights = _nights(
        invoice.get("check_in_date"),
        invoice.get("check_out_date"),
    )

    buffer = BytesIO()

    pdf = canvas.Canvas(
        buffer,
        pagesize=A4,
        pageCompression=1,
    )

    pdf.setTitle(f"Invoice #{invoice['invoice_id']}")
    pdf.setAuthor("Hotel Management System")
    pdf.setSubject(
        f"Invoice for booking #{invoice['booking_id']}"
    )

    # First page.
    y = _draw_page_header(pdf, invoice)

    # -----------------------------------------------------
    # Item table
    # -----------------------------------------------------

    def draw_table_header(current_y: float) -> float:
        pdf.setFillColor(LIGHT_GREY)
        pdf.roundRect(
            MARGIN,
            current_y - 21,
            CONTENT_WIDTH,
            25,
            4,
            fill=1,
            stroke=0,
        )

        pdf.setFillColor(NAVY)
        pdf.setFont("Helvetica-Bold", 8)

        pdf.drawString(MARGIN + 9, current_y - 12, "DESCRIPTION")
        pdf.drawRightString(
            PAGE_WIDTH - MARGIN - 105,
            current_y - 12,
            "QTY",
        )
        pdf.drawRightString(
            PAGE_WIDTH - MARGIN - 9,
            current_y - 12,
            "AMOUNT",
        )

        return current_y - 39

    y = draw_table_header(y)

    def draw_item(
        description: str,
        quantity: Any,
        amount: Any,
    ) -> float:
        nonlocal y

        text_width = CONTENT_WIDTH - 180
        description_lines = simpleSplit(
            description,
            "Helvetica",
            9,
            text_width,
        )

        row_height = max(
            28,
            len(description_lines) * 12 + 12,
        )

        # Start another page if the current page is nearly full.
        if y - row_height < 105:
            _draw_footer(pdf, invoice["booking_id"])
            pdf.showPage()
            y = _draw_page_header(pdf, invoice)
            y = draw_table_header(y)

        pdf.setFillColor(DARK_GREY)
        pdf.setFont("Helvetica", 9)

        text_y = y

        for line in description_lines:
            pdf.drawString(MARGIN + 9, text_y, line)
            text_y -= 12

        pdf.setFont("Helvetica", 9)
        pdf.drawRightString(
            PAGE_WIDTH - MARGIN - 105,
            y,
            str(quantity),
        )

        pdf.setFont("Helvetica-Bold", 9)
        pdf.drawRightString(
            PAGE_WIDTH - MARGIN - 9,
            y,
            _money(amount),
        )

        y -= row_height

        pdf.setStrokeColor(BORDER)
        pdf.line(
            MARGIN,
            y + 4,
            PAGE_WIDTH - MARGIN,
            y + 4,
        )

        return y

    room_description = (
        f"Room accommodation | {nights} night(s)"
    )

    draw_item(room_description, nights, room_total)

    for line in lines:
        description = str(
            line.get("service_name") or "Additional service"
        )

        draw_item(
            description,
            line.get("quantity", 1),
            line.get("total_price", 0),
        )

    # -----------------------------------------------------
    # Invoice totals
    # -----------------------------------------------------

    if y < 190:
        _draw_footer(pdf, invoice["booking_id"])
        pdf.showPage()
        y = _draw_page_header(pdf, invoice)

    y -= 14

    totals_x = PAGE_WIDTH - MARGIN - 220
    value_x = PAGE_WIDTH - MARGIN - 9

    def draw_total(label: str, value: Any, *, bold: bool = False) -> None:
        nonlocal y

        pdf.setFillColor(NAVY if bold else DARK_GREY)
        pdf.setFont(
            "Helvetica-Bold" if bold else "Helvetica",
            10 if bold else 9,
        )

        pdf.drawString(totals_x, y, label)
        pdf.drawRightString(value_x, y, _money(value))

        y -= 19

    draw_total("Subtotal", subtotal)
    draw_total("Tax", tax)

    pdf.setStrokeColor(BORDER)
    pdf.line(totals_x, y + 7, value_x, y + 7)

    draw_total("Grand total", grand_total, bold=True)
    draw_total("Amount paid", amount_paid)

    pdf.setFillColor(BLUE)
    pdf.roundRect(
        totals_x - 9,
        y - 10,
        229,
        31,
        5,
        fill=1,
        stroke=0,
    )

    pdf.setFillColor(WHITE)
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(totals_x, y + 1, "BALANCE DUE")
    pdf.drawRightString(value_x, y + 1, _money(balance_due))

    y -= 37

    # Payment status.
    payment_state = str(
        invoice.get("payment_state") or "UNPAID"
    ).upper()

    state_color = (
        GREEN if payment_state == "PAID"
        else RED if payment_state == "UNPAID"
        else BLUE
    )

    pdf.setFillColor(state_color)
    pdf.setFont("Helvetica-Bold", 9)
    pdf.drawString(
        totals_x,
        y,
        f"PAYMENT STATUS: {payment_state}",
    )

    # Footer and final PDF serialization.
    _draw_footer(pdf, invoice["booking_id"])

    pdf.save()

    buffer.seek(0)

    return buffer.getvalue()
