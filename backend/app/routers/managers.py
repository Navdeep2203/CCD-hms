from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.audit import audit
from app.core.security import (
    ADMIN,
    MANAGER,
    get_current_user,
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
    ManagerCreateRequest,
    ManagerUpdateRequest,
    ResetPasswordRequest,
)

router = APIRouter(dependencies=[Depends(require_roles(ADMIN))])

MANAGER_SELECT = """
SELECT m.manager_id, m.user_id, u.name, u.email, u.phone_country_code, u.phone_number, u.is_active,
       m.department_id, d.department_name, m.reports_to_manager_id, ru.name AS reports_to_name,
       m.job_description, m.salary,
       (SELECT COUNT(*) FROM staff s JOIN users su ON su.user_id = s.user_id
        WHERE s.manager_id = m.manager_id AND su.is_active) AS active_staff
FROM managers m
JOIN users u ON u.user_id = m.user_id
JOIN departments d ON d.department_id = m.department_id
LEFT JOIN managers rm ON rm.manager_id = m.reports_to_manager_id
LEFT JOIN users ru ON ru.user_id = rm.user_id
"""


def _get(manager_id: int, conn=None) -> dict:
    row = fetch_one(MANAGER_SELECT + " WHERE m.manager_id = :id", {"id": manager_id}, conn=conn)
    if not row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Manager not found")
    return row


def _require_department(department_id: int, conn) -> None:
    if not fetch_one("SELECT 1 FROM departments WHERE department_id = :id", {"id": department_id}, conn=conn):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Department does not exist")


def _require_manager(manager_id: int, conn) -> None:
    if not fetch_one("SELECT 1 FROM managers WHERE manager_id = :id", {"id": manager_id}, conn=conn):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The manager this person reports to does not exist")


@router.get("")
def list_managers(
    search: str | None = Query(default=None, max_length=100),
    active: bool | None = None,
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[dict]:
    where, params = [], {"limit": limit, "offset": offset}
    if search:
        where.append("(u.name ILIKE :q OR u.email ILIKE :q OR m.job_description ILIKE :q)")
        params["q"] = f"%{search}%"
    if active is not None:
        where.append("u.is_active = :active")
        params["active"] = active
    sql = MANAGER_SELECT + (" WHERE " + " AND ".join(where) if where else "")
    return fetch_all(sql + " ORDER BY m.manager_id DESC LIMIT :limit OFFSET :offset", params)


@router.get("/{manager_id}")
def get_manager(manager_id: int) -> dict:
    return _get(manager_id)


@router.post("", status_code=201)
def create_manager(payload: ManagerCreateRequest, user: dict = Depends(get_current_user)) -> dict:
    with transaction() as conn:
        _require_department(payload.department_id, conn)
        if payload.reports_to_manager_id:
            _require_manager(payload.reports_to_manager_id, conn)
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
            {"uid": user_id, "role": MANAGER}, conn=conn,
        )
        manager_id = execute_returning_id(
            """INSERT INTO managers (user_id, department_id, reports_to_manager_id, job_description, salary)
               VALUES (:uid, :dept, :rep, :job, :salary) RETURNING manager_id""",
            {"uid": user_id, "dept": payload.department_id, "rep": payload.reports_to_manager_id,
             "job": payload.job_description, "salary": payload.salary},
            conn=conn,
        )
        result = _get(manager_id, conn)
    audit(user["user_id"], "manager_created", manager_id=manager_id)
    return result


@router.put("/{manager_id}")
def update_manager(manager_id: int, payload: ManagerUpdateRequest, user: dict = Depends(get_current_user)) -> dict:
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")
    if any(data.get(k, 0) is None for k in ("name", "department_id", "salary")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Name, department and salary cannot be empty")
    if data.get("reports_to_manager_id") == manager_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "A manager cannot report to themselves")
    with transaction() as conn:
        row = _get(manager_id, conn)
        if "department_id" in data:
            _require_department(data["department_id"], conn)
        if data.get("reports_to_manager_id"):
            _require_manager(data["reports_to_manager_id"], conn)
        user_set, user_params = build_set(data, {"name", "phone_country_code", "phone_number"})
        if user_set:
            execute(f"UPDATE users SET {user_set} WHERE user_id = :uid", {**user_params, "uid": row["user_id"]}, conn=conn)
        mgr_set, mgr_params = build_set(data, {"department_id", "reports_to_manager_id", "job_description", "salary"})
        if mgr_set:
            execute(f"UPDATE managers SET {mgr_set} WHERE manager_id = :id", {**mgr_params, "id": manager_id}, conn=conn)
        result = _get(manager_id, conn)
    audit(user["user_id"], "manager_updated", manager_id=manager_id, fields=",".join(sorted(data)))
    return result


@router.patch("/{manager_id}/active")
def set_manager_active(manager_id: int, payload: ActiveRequest, user: dict = Depends(get_current_user)) -> dict:
    with transaction() as conn:
        row = _get(manager_id, conn)
        if row["user_id"] == user["user_id"]:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "You cannot change your own account status")
        if not payload.active:
            if row["active_staff"]:
                raise HTTPException(status.HTTP_409_CONFLICT, "Reassign this manager's active staff before deactivating")
            if fetch_one("SELECT 1 FROM departments WHERE head_manager_id = :id", {"id": manager_id}, conn=conn):
                raise HTTPException(status.HTTP_409_CONFLICT, "This manager heads a department; assign a new head first")
        execute("UPDATE users SET is_active = :a WHERE user_id = :uid", {"a": payload.active, "uid": row["user_id"]}, conn=conn)
        result = _get(manager_id, conn)
    audit(user["user_id"], "manager_activated" if payload.active else "manager_deactivated", manager_id=manager_id)
    return result


@router.post("/{manager_id}/reset-password")
def reset_manager_password(manager_id: int, payload: ResetPasswordRequest, user: dict = Depends(get_current_user)) -> dict:
    with transaction() as conn:
        row = _get(manager_id, conn)
        execute(
            "UPDATE users SET password_hash = :h, must_change_password = TRUE WHERE user_id = :uid",
            {"h": hash_password(payload.temporary_password), "uid": row["user_id"]}, conn=conn,
        )
    audit(user["user_id"], "manager_password_reset", manager_id=manager_id)
    return {"reset": True}
