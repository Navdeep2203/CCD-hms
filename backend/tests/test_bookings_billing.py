from datetime import date, timedelta

import pytest

from app.database import fetch_one


def iso(offset: int) -> str:
    return (date.today() + timedelta(days=offset)).isoformat()


def book(client, headers, room, start, end, **extra):
    return client.post("/api/bookings", headers=headers,
                       json={"room_id": room, "check_in_date": iso(start), "check_out_date": iso(end), **extra})


def status_of(client, H, role, booking_id, status, **extra):
    return client.patch(f"/api/bookings/{booking_id}/status", headers=H(role), json={"status": status, **extra})


# ---------- validation ----------
def test_date_validation(client, H, new_room):
    room = new_room()
    assert book(client, H("customer"), room, -1, 2).status_code == 422
    assert book(client, H("customer"), room, 3, 3).status_code == 422
    assert book(client, H("customer"), room, 3, 1).status_code == 422
    assert book(client, H("customer"), room, 1, 40).status_code == 422
    bad = client.post("/api/bookings", headers=H("customer"),
                      json={"room_id": room, "check_in_date": "abc", "check_out_date": iso(2)})
    assert bad.status_code == 422 and isinstance(bad.json()["detail"], str)


def test_cannot_book_maintenance_or_unknown_room(client, H):
    maintenance_room = client.get("/api/rooms?status=MAINTENANCE", headers=H("admin")).json()[0]["room_id"]
    assert book(client, H("customer"), maintenance_room, 1, 2).status_code == 409
    assert book(client, H("customer"), 999999, 1, 2).status_code == 404


# ---------- double booking ----------
def test_overlap_rules(client, H, new_room, tokens):
    room = new_room()
    first = book(client, H("customer"), room, 10, 13)
    assert first.status_code == 201 and first.json()["booking_status"] == "PENDING"
    client.post("/api/auth/register", json={"name": "Rival", "email": "rival@example.com", "password": "Passw0rdOK"})
    rival = {"Authorization": "Bearer " + client.post("/api/auth/login", json={"email": "rival@example.com", "password": "Passw0rdOK"}).json()["access_token"]}
    second = book(client, rival, room, 11, 14)  # pending requests may overlap...
    assert second.status_code == 201
    assert status_of(client, H, "manager", first.json()["booking_id"], "APPROVED").status_code == 200
    # ...but only one can be approved (database exclusion constraint -> 409)
    assert status_of(client, H, "manager", second.json()["booking_id"], "APPROVED").status_code == 409
    assert book(client, rival, room, 12, 15).status_code == 409  # now blocked at creation too
    assert book(client, rival, room, 13, 15).status_code == 201  # back-to-back stay is fine


def test_date_search_excludes_booked_rooms(client, H, new_room):
    room = new_room()
    b = book(client, H("manager"), room, 20, 22, customer_id=client.get("/api/customers", headers=H("manager")).json()[0]["customer_id"])
    assert b.status_code == 201
    free = client.get(f"/api/rooms?check_in={iso(20)}&check_out={iso(22)}", headers=H("customer")).json()
    assert room not in [r["room_id"] for r in free]
    later = client.get(f"/api/rooms?check_in={iso(22)}&check_out={iso(24)}", headers=H("customer")).json()
    assert room in [r["room_id"] for r in later]


# ---------- transitions & roles ----------
def test_transition_rules(client, H, new_room):
    room = new_room()
    bid = book(client, H("customer"), room, 30, 32).json()["booking_id"]
    assert status_of(client, H, "customer", bid, "APPROVED").status_code == 403
    assert status_of(client, H, "customer", bid, "CHECKED_IN").status_code == 400
    assert status_of(client, H, "staff", bid, "CHECKED_OUT").status_code == 400
    assert status_of(client, H, "staff", bid, "REJECTED", rejection_reason="Fully booked").status_code == 200
    assert client.get(f"/api/bookings/{bid}", headers=H("customer")).json()["rejection_reason"] == "Fully booked"
    assert status_of(client, H, "admin", bid, "APPROVED").status_code == 400  # terminal state
    assert client.patch(f"/api/bookings/{bid}/status", headers=H("staff"),
                        json={"status": "APPROVED", "rejection_reason": "x"}).status_code == 422


def test_customer_cancel_own_pending_booking(client, H, new_room):
    bid = book(client, H("customer"), new_room(), 40, 41).json()["booking_id"]
    assert status_of(client, H, "customer", bid, "CANCELLED").status_code == 200


def test_cannot_check_in_before_arrival_date(client, H, new_room):
    bid = book(client, H("customer"), new_room(), 50, 52).json()["booking_id"]
    assert status_of(client, H, "staff", bid, "APPROVED").status_code == 200
    assert status_of(client, H, "staff", bid, "CHECKED_IN").status_code == 400


# ---------- full stay: check-in, services, invoice, payments, check-out ----------
def test_full_stay_lifecycle(client, H, new_room, customer_id):
    room = new_room()
    price = next(t for t in client.get("/api/rooms/types", headers=H("admin")).json())["price_per_night"]
    before = client.get("/api/auth/me", headers=H("customer")).json()["loyalty_points"]
    walk_in = book(client, H("staff"), room, 0, 2, customer_id=customer_id)
    assert walk_in.status_code == 201 and walk_in.json()["booking_status"] == "APPROVED"  # staff bookings are pre-approved
    bid = walk_in.json()["booking_id"]
    assert book(client, H("staff"), room, 0, 2).status_code == 400  # staff must pick the guest

    assert client.post("/api/services/usage", headers=H("customer"),
                       json={"booking_id": bid, "service_id": 1}).status_code == 409  # not checked in yet
    assert status_of(client, H, "staff", bid, "CHECKED_IN").status_code == 200
    assert fetch_one("SELECT status FROM rooms WHERE room_id = :r", {"r": room})["status"] == "OCCUPIED"

    svc = client.post("/api/services/usage", headers=H("customer"), json={"booking_id": bid, "service_id": 1, "quantity": 2})
    assert svc.status_code == 201

    inv = client.post(f"/api/billing/invoices/{bid}/generate", headers=H("staff")).json()
    subtotal = float(price) * 2 + 850 * 2
    assert inv["total_amount"] == pytest.approx(subtotal) and inv["tax"] == pytest.approx(subtotal * 0.12)
    assert inv["payment_state"] == "UNPAID"

    # a service added after the invoice was generated is picked up automatically
    client.post("/api/services/usage", headers=H("staff"), json={"booking_id": bid, "service_id": 2})
    inv = client.post(f"/api/billing/invoices/{bid}/generate", headers=H("staff")).json()
    assert inv["total_amount"] == pytest.approx(subtotal + 450)
    balance = inv["balance_due"]

    assert client.post("/api/billing/payments", headers=H("customer"),
                       json={"booking_id": bid, "method_id": 1, "amount": balance + 1}).status_code == 400  # overpayment
    assert client.post("/api/billing/payments", headers=H("customer"),
                       json={"booking_id": bid, "method_id": 1, "amount": 0}).status_code == 422
    part = client.post("/api/billing/payments", headers=H("customer"), json={"booking_id": bid, "method_id": 3, "amount": 1000})
    assert part.status_code == 201
    assert client.get("/api/billing/invoices", headers=H("customer")).json()[0]["payment_state"] in ("PARTIAL", "UNPAID", "PAID")

    # checkout is blocked until the balance is cleared; only management may override
    assert status_of(client, H, "staff", bid, "CHECKED_OUT").status_code == 409
    assert status_of(client, H, "staff", bid, "CHECKED_OUT", override_balance=True).status_code == 403
    payable = [p for p in client.get("/api/billing/payable", headers=H("customer")).json() if p["booking_id"] == bid]
    assert payable and payable[0]["balance_due"] == pytest.approx(balance - 1000)
    assert client.post("/api/billing/payments", headers=H("staff"),
                       json={"booking_id": bid, "method_id": 1, "amount": payable[0]["balance_due"]}).status_code == 201
    assert status_of(client, H, "staff", bid, "CHECKED_OUT").status_code == 200
    assert fetch_one("SELECT status FROM rooms WHERE room_id = :r", {"r": room})["status"] == "AVAILABLE"
    assert client.get("/api/auth/me", headers=H("customer")).json()["loyalty_points"] > before
    assert client.post("/api/billing/payments", headers=H("staff"),
                       json={"booking_id": bid, "method_id": 1, "amount": 1}).status_code == 409  # fully paid
    assert client.post("/api/services/usage", headers=H("staff"), json={"booking_id": bid, "service_id": 1}).status_code == 409


def test_manager_can_override_outstanding_balance(client, H, new_room, customer_id):
    room = new_room()
    bid = book(client, H("staff"), room, 0, 1, customer_id=customer_id).json()["booking_id"]
    status_of(client, H, "staff", bid, "CHECKED_IN")
    assert status_of(client, H, "manager", bid, "CHECKED_OUT", override_balance=True).status_code == 200


def test_invoice_requires_check_in(client, H, new_room, customer_id):
    bid = book(client, H("staff"), new_room(), 60, 62, customer_id=customer_id).json()["booking_id"]
    assert client.post(f"/api/billing/invoices/{bid}/generate", headers=H("staff")).status_code == 409
    assert client.post("/api/billing/payments", headers=H("customer"),
                       json={"booking_id": bid, "method_id": 1, "amount": 10}).status_code == 409


def test_cannot_occupy_room_until_previous_guest_leaves(client, H, new_room, customer_id):
    room = new_room()
    first = book(client, H("staff"), room, 0, 1, customer_id=customer_id).json()["booking_id"]
    assert status_of(client, H, "staff", first, "CHECKED_IN").status_code == 200
    # an occupied room cannot be flipped to AVAILABLE by hand while a guest is inside
    assert client.patch(f"/api/rooms/{room}/status", headers=H("staff"), json={"status": "AVAILABLE"}).status_code == 409
    fresh = new_room()  # OCCUPIED can never be set by hand, only by a check-in
    assert client.patch(f"/api/rooms/{fresh}/status", headers=H("staff"), json={"status": "OCCUPIED"}).status_code == 400
