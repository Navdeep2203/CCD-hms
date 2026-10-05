from datetime import date, timedelta


def test_guest_dashboard_has_no_hotel_wide_data(client, H):
    data = client.get("/api/dashboard/overview", headers=H("customer")).json()
    assert data["kind"] == "guest"
    for leaked in ("total_rooms", "today_revenue", "month_revenue", "recent_bookings", "occupied_rooms"):
        assert leaked not in data


def test_staff_dashboard_has_no_revenue_but_management_does(client, H):
    staff = client.get("/api/dashboard/overview", headers=H("staff")).json()
    assert staff["kind"] == "staff" and "month_revenue" not in staff and "today_revenue" not in staff
    mgmt = client.get("/api/dashboard/overview", headers=H("manager")).json()
    assert mgmt["kind"] == "management" and "month_revenue" in mgmt


def test_guest_room_list_hides_internal_status_and_maintenance_rooms(client, H):
    rooms = client.get("/api/rooms", headers=H("customer")).json()
    assert rooms and all("status" not in room for room in rooms)
    numbers = {room["room_number"] for room in rooms}
    assert 202 not in numbers  # under maintenance in the seed data


def test_guest_only_sees_own_bookings_and_invoices(client, H):
    client.post("/api/auth/register", json={"name": "Other", "email": "other@example.com", "password": "Passw0rdOK"})
    other = client.post("/api/auth/login", json={"email": "other@example.com", "password": "Passw0rdOK"}).json()
    h = {"Authorization": f"Bearer {other['access_token']}"}
    assert client.get("/api/bookings", headers=h).json() == []
    assert client.get("/api/billing/invoices", headers=h).json() == []
    seeded = client.get("/api/bookings", headers=H("customer")).json()
    assert seeded
    # cannot read, pay or change somebody else's booking
    bid = seeded[0]["booking_id"]
    assert client.get(f"/api/bookings/{bid}", headers=h).status_code == 404
    assert client.get(f"/api/billing/payments/{bid}", headers=h).status_code == 404
    assert client.patch(f"/api/bookings/{bid}/status", headers=h, json={"status": "CANCELLED"}).status_code == 404
    assert client.post("/api/billing/payments", headers=h, json={"booking_id": bid, "method_id": 1, "amount": 1}).status_code == 404
    assert client.post("/api/services/usage", headers=h, json={"booking_id": bid, "service_id": 1}).status_code == 404


def test_guest_cannot_book_for_someone_else_or_use_ops_fields(client, H, tokens, new_room):
    room = new_room()
    d = date.today() + timedelta(days=5)
    body = {"room_id": room, "check_in_date": d.isoformat(), "check_out_date": (d + timedelta(days=1)).isoformat()}
    other_id = tokens["customer"]["user"]["customer_id"] + 99
    assert client.post("/api/bookings", headers=H("customer"), json={**body, "customer_id": other_id}).status_code == 400
    assert client.post("/api/bookings", headers=H("customer"), json=body).status_code == 201


def test_staff_customer_list_hides_id_proof(client, H):
    staff_view = client.get("/api/customers", headers=H("staff")).json()[0]
    assert "id_proof" not in staff_view and "address" not in staff_view
    assert "id_proof" in client.get("/api/customers", headers=H("manager")).json()[0]
