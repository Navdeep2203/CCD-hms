"""Role-access matrix: every sensitive endpoint against every role."""
import pytest

ROLES = ["admin", "manager", "staff", "customer"]

# (method, path, expected status per role in ROLES order); 200 means "allowed"
GET_MATRIX = [
    ("/api/staff", [200, 200, 403, 403]),
    ("/api/managers", [200, 403, 403, 403]),
    ("/api/customers", [200, 200, 200, 403]),
    ("/api/departments", [200, 200, 403, 403]),
    ("/api/reports/summary", [200, 200, 403, 403]),
    ("/api/maintenance", [200, 200, 200, 403]),
    ("/api/dashboard/overview", [200, 200, 200, 200]),
    ("/api/rooms", [200, 200, 200, 200]),
    ("/api/bookings", [200, 200, 200, 200]),
    ("/api/billing/invoices", [200, 200, 200, 200]),
    ("/api/billing/payable", [200, 200, 200, 200]),
    ("/api/services/usage", [200, 200, 200, 200]),
]


@pytest.mark.parametrize("path,expected", GET_MATRIX)
def test_get_matrix(client, H, path, expected):
    for role, code in zip(ROLES, expected):
        assert client.get(path, headers=H(role)).status_code == code, f"{role} {path}"


DENIED_WRITES = [
    ("post", "/api/rooms", {"room_number": 5000, "room_type_id": 1}, ["staff", "customer"]),
    ("post", "/api/rooms/types", {"type_name": "Zed", "price_per_night": 10}, ["staff", "customer"]),
    ("post", "/api/services", {"service_name": "Zed", "price": 10}, ["staff", "customer"]),
    ("post", "/api/managers", {"name": "A", "email": "a@x.com", "department_id": 1, "salary": 1,
                               "temporary_password": "Passw0rd1"}, ["manager", "staff", "customer"]),
    ("post", "/api/staff", {"name": "A", "email": "a@x.com", "department_id": 1, "salary": 1,
                            "temporary_password": "Passw0rd1"}, ["staff", "customer"]),
    ("post", "/api/maintenance", {"room_id": 1, "description": "x"}, ["customer"]),
    ("post", "/api/customers", {"name": "A", "email": "a@x.com", "temporary_password": "Passw0rd1"}, ["customer"]),
    ("delete", "/api/rooms/1", None, ["staff", "customer"]),
    ("patch", "/api/rooms/1/status", {"status": "AVAILABLE"}, ["customer"]),
]


@pytest.mark.parametrize("method,path,body,denied", DENIED_WRITES)
def test_denied_writes(client, H, method, path, body, denied):
    for role in denied:
        kwargs = {"json": body} if body is not None else {}
        assert getattr(client, method)(path, headers=H(role), **kwargs).status_code == 403, f"{role} {method} {path}"


def test_customer_cannot_create_payment_for_unknown_booking(client, H):
    r = client.post("/api/billing/payments", headers=H("customer"), json={"booking_id": 999999, "method_id": 1, "amount": 10})
    assert r.status_code == 404
