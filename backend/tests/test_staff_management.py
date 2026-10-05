from app.database import fetch_one

from .conftest import headers_for, login

NEW = {"name": "Priya Nair", "email": "priya@hotel.com", "department_id": 1, "salary": 30000,
       "job_description": "Housekeeper", "temporary_password": "Temp@1234"}


def staff_body(email, **extra):
    return {**NEW, "email": email, **extra}


def test_admin_must_choose_manager(client, H):
    assert client.post("/api/staff", headers=H("admin"), json=staff_body("a1@hotel.com")).status_code == 400
    ok = client.post("/api/staff", headers=H("admin"), json=staff_body("a2@hotel.com", manager_id=1))
    assert ok.status_code == 201 and ok.json()["manager_id"] == 1 and "password_hash" not in ok.json()


def test_manager_creates_staff_under_self_ignoring_client_manager_id(client, H, tokens):
    own = tokens["manager"]["user"]["manager_id"]
    created = client.post("/api/staff", headers=H("manager"), json=staff_body("m1@hotel.com", manager_id=own + 50))
    assert created.status_code == 201 and created.json()["manager_id"] == own


def test_staff_must_change_temporary_password_first(client, H):
    client.post("/api/staff", headers=H("admin"), json=staff_body("temp@hotel.com", manager_id=1))
    response = login(client, "temp@hotel.com", "Temp@1234")
    assert response.status_code == 200 and response.json()["user"]["must_change_password"] is True
    h = headers_for(response)
    assert client.get("/api/bookings", headers=h).status_code == 403
    assert client.get("/api/auth/me", headers=h).status_code == 200
    assert client.post("/api/auth/change-password", headers=h,
                       json={"current_password": "Temp@1234", "new_password": "Brand@New99"}).status_code == 200
    assert client.get("/api/bookings", headers=h).status_code == 200


def test_manager_cannot_create_or_assign_managers(client, H):
    body = {"name": "M", "email": "mm@hotel.com", "department_id": 1, "salary": 1, "temporary_password": "Passw0rd1"}
    assert client.post("/api/managers", headers=H("manager"), json=body).status_code == 403
    staff_id = client.post("/api/staff", headers=H("manager"), json=staff_body("mv@hotel.com")).json()["staff_id"]
    assert client.put(f"/api/staff/{staff_id}", headers=H("manager"), json={"manager_id": 1}).status_code == 403
    assert client.put(f"/api/staff/{staff_id}", headers=H("manager"), json={"salary": 41000, "job_description": "Lead"}).status_code == 200


def test_team_isolation_between_managers(client, H):
    mgr = client.post("/api/managers", headers=H("admin"), json={
        "name": "Second Boss", "email": "boss2@hotel.com", "department_id": 2, "salary": 80000,
        "temporary_password": "Boss@12345", "reports_to_manager_id": 1})
    assert mgr.status_code == 201
    other_mgr_id = mgr.json()["manager_id"]
    theirs = client.post("/api/staff", headers=H("admin"), json=staff_body("theirs@hotel.com", manager_id=other_mgr_id)).json()["staff_id"]
    # first manager cannot see, edit, deactivate or reset staff of the second
    assert client.get(f"/api/staff/{theirs}", headers=H("manager")).status_code == 404
    assert client.put(f"/api/staff/{theirs}", headers=H("manager"), json={"salary": 1}).status_code == 404
    assert client.patch(f"/api/staff/{theirs}/active", headers=H("manager"), json={"active": False}).status_code == 404
    assert client.post(f"/api/staff/{theirs}/reset-password", headers=H("manager"), json={"temporary_password": "Passw0rd1"}).status_code == 404
    assert theirs not in [s["staff_id"] for s in client.get("/api/staff", headers=H("manager")).json()]
    assert theirs in [s["staff_id"] for s in client.get("/api/staff", headers=H("admin")).json()]
    # admin can move staff between managers
    assert client.put(f"/api/staff/{theirs}", headers=H("admin"), json={"manager_id": 1}).json()["manager_id"] == 1


def test_duplicate_email_any_case(client, H):
    client.post("/api/staff", headers=H("admin"), json=staff_body("dup@hotel.com", manager_id=1))
    assert client.post("/api/staff", headers=H("admin"), json=staff_body("DUP@Hotel.com", manager_id=1)).status_code == 409
    assert client.post("/api/auth/register", json={"name": "D", "email": "dup@hotel.com", "password": "Passw0rdOK"}).status_code == 409


def test_failed_creation_leaves_nothing_behind(client, H):
    bad = client.post("/api/staff", headers=H("admin"), json=staff_body("ghost@hotel.com", manager_id=1, department_id=9999))
    assert bad.status_code == 400
    assert fetch_one("SELECT 1 FROM users WHERE email = 'ghost@hotel.com'") is None
    bad_mgr = client.post("/api/staff", headers=H("admin"), json=staff_body("ghost2@hotel.com", manager_id=9999))
    assert bad_mgr.status_code == 400 and fetch_one("SELECT 1 FROM users WHERE email = 'ghost2@hotel.com'") is None


def test_deactivate_blocks_login_and_reactivate_restores(client, H):
    sid = client.post("/api/staff", headers=H("admin"), json=staff_body("off@hotel.com", manager_id=1)).json()["staff_id"]
    token = headers_for(login(client, "off@hotel.com", "Temp@1234"))
    assert client.patch(f"/api/staff/{sid}/active", headers=H("admin"), json={"active": False}).json()["is_active"] is False
    assert login(client, "off@hotel.com", "Temp@1234").status_code == 401
    assert client.get("/api/auth/me", headers=token).status_code == 401  # existing token dies immediately
    assert client.patch(f"/api/staff/{sid}/active", headers=H("admin"), json={"active": True}).status_code == 200
    assert login(client, "off@hotel.com", "Temp@1234").status_code == 200


def test_reset_password_forces_change(client, H):
    sid = client.post("/api/staff", headers=H("admin"), json=staff_body("rp@hotel.com", manager_id=1)).json()["staff_id"]
    assert client.post(f"/api/staff/{sid}/reset-password", headers=H("manager"), json={"temporary_password": "Passw0rd1"}).status_code in (200, 404)
    assert client.post(f"/api/staff/{sid}/reset-password", headers=H("admin"), json={"temporary_password": "Reset@5678"}).status_code == 200
    r = login(client, "rp@hotel.com", "Reset@5678")
    assert r.status_code == 200 and r.json()["user"]["must_change_password"] is True


def test_manager_deactivation_guards(client, H):
    assert client.patch("/api/managers/1/active", headers=H("admin"), json={"active": False}).status_code == 409  # has staff / heads a department
    assert client.patch("/api/managers/1/active", headers=H("manager"), json={"active": False}).status_code == 403


def test_validation_on_update(client, H):
    sid = client.post("/api/staff", headers=H("admin"), json=staff_body("val@hotel.com", manager_id=1)).json()["staff_id"]
    assert client.put(f"/api/staff/{sid}", headers=H("admin"), json={}).status_code == 400
    assert client.put(f"/api/staff/{sid}", headers=H("admin"), json={"salary": -5}).status_code == 422
    assert client.put(f"/api/staff/{sid}", headers=H("admin"), json={"email": "x@y.com"}).status_code == 422  # not editable
    assert client.put(f"/api/staff/{sid}", headers=H("admin"), json={"department_id": 9999}).status_code == 400


def test_maintenance_workflow(client, H, tokens, new_room):
    room = new_room()
    staff_sid = tokens["staff"]["user"]["staff_id"]
    created = client.post("/api/maintenance", headers=H("manager"), json={"room_id": room, "description": "Leaking tap", "staff_id": staff_sid})
    assert created.status_code == 201
    mid = created.json()["maintenance_id"]
    assert fetch_one("SELECT status FROM rooms WHERE room_id = :r", {"r": room})["status"] == "MAINTENANCE"
    assert mid in [m["maintenance_id"] for m in client.get("/api/maintenance", headers=H("staff")).json()]
    assert client.put(f"/api/maintenance/{mid}", headers=H("staff"), json={"description": "hack"}).status_code == 403
    assert client.put(f"/api/maintenance/{mid}", headers=H("staff"), json={"status": "IN_PROGRESS"}).status_code == 200
    assert client.put(f"/api/maintenance/{mid}", headers=H("staff"), json={"status": "COMPLETED"}).status_code == 200
    assert fetch_one("SELECT status FROM rooms WHERE room_id = :r", {"r": room})["status"] == "AVAILABLE"
    unassigned = client.post("/api/maintenance", headers=H("staff"), json={"room_id": room, "description": "Paint"}).json()["maintenance_id"]
    assert unassigned not in [m["maintenance_id"] for m in client.get("/api/maintenance", headers=H("staff")).json()]
    assert client.put(f"/api/maintenance/{unassigned}", headers=H("staff"), json={"status": "COMPLETED"}).status_code == 404
