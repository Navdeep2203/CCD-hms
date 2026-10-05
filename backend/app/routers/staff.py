from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.audit import audit
from app.core.security import (
    ADMIN,
    MANAGER,
    STAFF,
    get_current_user,
    has_role,
    hash_password,
    require_roles,
)
from app.core.sqlutil import build_set
from app.database import (
    execute,
    execute_returning_id,
    fetch_all,
    fetch_one,
    transaction,
)
from app.schemas import (
    ActiveRequest,
    ResetPasswordRequest,
    StaffCreateRequest,
    StaffUpdateRequest,
)

router = APIRouter(dependencies=[Depends(require_roles(ADMIN, MANAGER))])

STAFF_SELECT = """
SELECT s.staff_id, s.user_id, u.name, u.email, u.phone_country_code, u.phone_number, u.is_active,
       s.department_id, d.department_name, s.manager_id, mu.name AS manager_name,
       s.job_description, s.salary
FROM staff s
JOIN users u ON u.user_id = s.user_id
JOIN departments d ON d.department_id = s.department_id
LEFT JOIN managers m ON m.manager_id = s.manager_id
LEFT JOIN users mu ON mu.user_id = m.user_id
"""


def _scope_manager_id(user: dict) -> int | None:
    """None = admin (sees everyone). A manager only ever sees and touches their own team."""
    if has_role(user, ADMIN):
        return None
    if not user.get("manager_id"):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Manager profile not found")
    return user["manager_id"]


def _get_scoped(staff_id: int, user: dict, conn=None) -> dict:
    scope = _scope_manager_id(user)
    sql = STAFF_SELECT + " WHERE s.staff_id = :id" + (" AND s.manager_id = :mid" if scope else "")
    row = fetch_one(sql, {"id": staff_id, **({"mid": scope} if scope else {})}, conn=conn)
    if not row:  # 404 (not 403) so managers cannot probe other teams' ids
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Staff member not found")
    return row


def _require_department(department_id: int, conn) -> None:
    if not fetch_one("SELECT 1 FROM departments WHERE department_id = :id", {"id": department_id}, conn=conn):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Department does not exist")


def _require_active_manager(manager_id: int, conn) -> None:
    ok = fetch_one(
        "SELECT 1 FROM managers m JOIN users u ON u.user_id = m.user_id WHERE m.manager_id = :id AND u.is_active",
        {"id": manager_id}, conn=conn,
    )
    if not ok:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Manager does not exist or is inactive")


@router.get("")
def list_staff(
    search: str | None = Query(default=None, max_length=100),
    department_id: int | None = None,
    active: bool | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(get_current_user),
) -> list[dict]:
    scope = _scope_manager_id(user)
    where, params = [], {"limit": limit, "offset": offset}
    if scope:
        where.append("s.manager_id = :mid")
        params["mid"] = scope
    if search:
        where.append("(u.name ILIKE :q OR u.email ILIKE :q OR s.job_description ILIKE :q)")
        params["q"] = f"%{search}%"
    if department_id:
        where.append("s.department_id = :dept")
        params["dept"] = department_id
    if active is not None:
        where.append("u.is_active = :active")
        params["active"] = active
    sql = STAFF_SELECT + (" WHERE " + " AND ".join(where) if where else "")
    return fetch_all(sql + " ORDER BY s.staff_id DESC LIMIT :limit OFFSET :offset", params)


@router.get("/{staff_id}")
def get_staff(staff_id: int, user: dict = Depends(get_current_user)) -> dict:
    return _get_scoped(staff_id, user)


@router.post("", status_code=201)
def create_staff(payload: StaffCreateRequest, user: dict = Depends(get_current_user)) -> dict:
    scope = _scope_manager_id(user)
    if scope is None:
        if payload.manager_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose the manager this staff member reports to")
        manager_id = payload.manager_id
    else:
        manager_id = scope  # a manager's own id always wins; anything sent by the client is ignored
    with transaction() as conn:
        _require_department(payload.department_id, conn)
        _require_active_manager(manager_id, conn)
        if fetch_one("SELECT 1 FROM users WHERE LOWER(email) = LOWER(:e)", {"e": payload.email}, conn=conn):
            raise HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")
        user_id = execute_returning_id(
            """INSERT INTO users (email, password_hash, name, phone_country_code, phone_number, is_active, must_change_password)
               VALUES (:email, :hash, :name, :cc, :phone, TRUE, TRUE) RETURNING user_id""",
            {"email": payload.email, "hash": hash_password(payload.temporary_password), "name": payload.name,
             "cc": payload.phone_country_code, "phone": payload.phone_number},
            conn=conn,
        )
        execute(
            "INSERT INTO user_roles (user_id, role_id) SELECT :uid, role_id FROM roles WHERE role_name = :role",
            {"uid": user_id, "role": STAFF}, conn=conn,
        )
        staff_id = execute_returning_id(
            """INSERT INTO staff (user_id, department_id, manager_id, job_description, salary)
               VALUES (:uid, :dept, :mid, :job, :salary) RETURNING staff_id""",
            {"uid": user_id, "dept": payload.department_id, "mid": manager_id,
             "job": payload.job_description, "salary": payload.salary},
            conn=conn,
        )
        result = fetch_one(STAFF_SELECT + " WHERE s.staff_id = :id", {"id": staff_id}, conn=conn)
    audit(user["user_id"], "staff_created", staff_id=staff_id, manager_id=manager_id)
    return result


@router.put("/{staff_id}")
def update_staff(staff_id: int, payload: StaffUpdateRequest, user: dict = Depends(get_current_user)) -> dict:
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")
    if any(data.get(k, 0) is None for k in ("name", "department_id", "manager_id", "salary")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Name, department, manager and salary cannot be empty")
    if "manager_id" in data and _scope_manager_id(user) is not None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only an admin can move staff to another manager")
    with transaction() as conn:
        row = _get_scoped(staff_id, user, conn)
        if "department_id" in data:
            _require_department(data["department_id"], conn)
        if "manager_id" in data:
            _require_active_manager(data["manager_id"], conn)
        user_set, user_params = build_set(data, {"name", "phone_country_code", "phone_number"})
        if user_set:
            execute(f"UPDATE users SET {user_set} WHERE user_id = :uid", {**user_params, "uid": row["user_id"]}, conn=conn)
        staff_set, staff_params = build_set(data, {"department_id", "manager_id", "job_description", "salary"})
        if staff_set:
            execute(f"UPDATE staff SET {staff_set} WHERE staff_id = :id", {**staff_params, "id": staff_id}, conn=conn)
        result = fetch_one(STAFF_SELECT + " WHERE s.staff_id = :id", {"id": staff_id}, conn=conn)
    audit(user["user_id"], "staff_updated", staff_id=staff_id, fields=",".join(sorted(data)))
    return result


@router.patch("/{staff_id}/active")
def set_staff_active(staff_id: int, payload: ActiveRequest, user: dict = Depends(get_current_user)) -> dict:
    with transaction() as conn:
        row = _get_scoped(staff_id, user, conn)
        if row["user_id"] == user["user_id"]:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot change your own account status")
        execute("UPDATE users SET is_active = :a WHERE user_id = :uid", {"a": payload.active, "uid": row["user_id"]}, conn=conn)
        result = fetch_one(STAFF_SELECT + " WHERE s.staff_id = :id", {"id": staff_id}, conn=conn)
    audit(user["user_id"], "staff_activated" if payload.active else "staff_deactivated", staff_id=staff_id)
    return result


@router.post("/{staff_id}/reset-password")
def reset_staff_password(staff_id: int, payload: ResetPasswordRequest, user: dict = Depends(get_current_user)) -> dict:
    with transaction() as conn:
        row = _get_scoped(staff_id, user, conn)
        execute(
            "UPDATE users SET password_hash = :h, must_change_password = TRUE WHERE user_id = :uid",
            {"h": hash_password(payload.temporary_password), "uid": row["user_id"]}, conn=conn,
        )
    audit(user["user_id"], "staff_password_reset", staff_id=staff_id)
    return {"reset": True}
