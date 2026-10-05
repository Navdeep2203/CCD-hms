from app.routers import auth as auth_router

from .conftest import headers_for, login


def test_login_ok_hides_password_and_internal_ids(client, tokens):
    user = tokens["customer"]["user"]
    assert "password_hash" not in user
    assert user["roles"] == ["ROLE_CUSTOMER"] and "staff_id" not in user and "manager_id" not in user


def test_bad_credentials_are_401_not_422(client):
    assert login(client, "admin@hotel.com", "abc12").status_code == 401  # short wrong password
    assert login(client, "nobody@hotel.com", "Whatever1").status_code == 401


def test_register_and_duplicate_email_case_insensitive(client):
    body = {"name": "Test Guest", "email": "Guest.One@Example.com", "password": "Passw0rdOK"}
    first = client.post("/api/auth/register", json=body)
    assert first.status_code == 201 and first.json()["user"]["email"] == "guest.one@example.com"
    assert client.post("/api/auth/register", json={**body, "email": "guest.one@EXAMPLE.com"}).status_code == 409
    assert login(client, "GUEST.ONE@example.com", "Passw0rdOK").status_code == 200


def test_register_validation_messages_are_readable(client):
    base = {"name": "X", "email": "x1@example.com", "password": "Passw0rdOK"}
    short = client.post("/api/auth/register", json={**base, "password": "a1"})
    assert short.status_code == 422 and isinstance(short.json()["detail"], str) and "Password" in short.json()["detail"]
    assert client.post("/api/auth/register", json={**base, "password": "onlyletters"}).status_code == 422
    assert client.post("/api/auth/register", json={**base, "phone_number": "12"}).status_code == 422
    assert client.post("/api/auth/register", json={**base, "name": "   "}).status_code == 422
    assert client.post("/api/auth/register", json={**base, "role": "ROLE_ADMIN"}).status_code == 422  # extra field


def test_registered_user_can_never_become_staff(client):
    r = client.post("/api/auth/register", json={"name": "Eve", "email": "eve@example.com", "password": "Passw0rdOK"})
    assert r.json()["user"]["roles"] == ["ROLE_CUSTOMER"]


def test_lockout_after_repeated_failures(client):
    client.post("/api/auth/register", json={"name": "Lock", "email": "lock@example.com", "password": "Passw0rdOK"})
    for _ in range(5):
        assert login(client, "lock@example.com", "wrongpass1").status_code == 401
    assert login(client, "lock@example.com", "Passw0rdOK").status_code == 429
    auth_router._attempts.clear()
    assert login(client, "lock@example.com", "Passw0rdOK").status_code == 200


def test_change_password_flow(client):
    client.post("/api/auth/register", json={"name": "Pw", "email": "pw@example.com", "password": "Passw0rdOK"})
    h = headers_for(login(client, "pw@example.com", "Passw0rdOK"))
    assert client.post("/api/auth/change-password", headers=h,
                       json={"current_password": "nope12345", "new_password": "NewPassw0rd"}).status_code == 400
    assert client.post("/api/auth/change-password", headers=h,
                       json={"current_password": "Passw0rdOK", "new_password": "Passw0rdOK"}).status_code == 422
    assert client.post("/api/auth/change-password", headers=h,
                       json={"current_password": "Passw0rdOK", "new_password": "NewPassw0rd"}).status_code == 200
    assert login(client, "pw@example.com", "Passw0rdOK").status_code == 401
    assert login(client, "pw@example.com", "NewPassw0rd").status_code == 200


def test_profile_update_rules(client, H):
    ok = client.put("/api/auth/profile", headers=H("customer"), json={"address": "12 Park Street", "nationality": "Indian"})
    assert ok.status_code == 200 and ok.json()["address"] == "12 Park Street"
    assert client.put("/api/auth/profile", headers=H("staff"), json={"address": "x"}).status_code == 400
    assert client.put("/api/auth/profile", headers=H("staff"), json={"phone_number": "9876543210"}).status_code == 200
    assert client.put("/api/auth/profile", headers=H("staff"), json={}).status_code == 400


def test_no_token_and_garbage_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_health_endpoints(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    assert client.get("/api/health/ready").json()["database"] == "ok"
