from fastapi import APIRouter, Depends, HTTPException, status

from app.core.audit import audit
from app.core.security import ADMIN, MANAGER, require_roles
from app.database import execute, execute_returning_id, fetch_all, fetch_one
from app.schemas import DepartmentRequest

router = APIRouter(dependencies=[Depends(require_roles(ADMIN, MANAGER))])

DEPT_SELECT = """
SELECT d.department_id, d.department_name, d.head_manager_id, u.name AS head_manager_name
FROM departments d
LEFT JOIN managers m ON m.manager_id = d.head_manager_id
LEFT JOIN users u ON u.user_id = m.user_id
"""


@router.get("")
def list_departments() -> list[dict]:
    return fetch_all(DEPT_SELECT + " ORDER BY d.department_name")


@router.post("", status_code=201)
def create_department(payload: DepartmentRequest, user: dict = Depends(require_roles(ADMIN))) -> dict:
    new_id = execute_returning_id(
        "INSERT INTO departments (department_name, head_manager_id) VALUES (:department_name, :head_manager_id) RETURNING department_id",
        payload.model_dump(),
    )
    audit(user["user_id"], "department_created", department_id=new_id)
    return fetch_one(DEPT_SELECT + " WHERE d.department_id = :id", {"id": new_id})


@router.put("/{department_id}")
def update_department(department_id: int, payload: DepartmentRequest, user: dict = Depends(require_roles(ADMIN))) -> dict:
    affected = execute(
        "UPDATE departments SET department_name = :department_name, head_manager_id = :head_manager_id WHERE department_id = :id",
        {**payload.model_dump(), "id": department_id},
    )
    if not affected:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Department not found")
    return fetch_one(DEPT_SELECT + " WHERE d.department_id = :id", {"id": department_id})


@router.delete("/{department_id}")
def delete_department(department_id: int, user: dict = Depends(require_roles(ADMIN))) -> dict:
    if not execute("DELETE FROM departments WHERE department_id = :id", {"id": department_id}):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Department not found")
    audit(user["user_id"], "department_deleted", department_id=department_id)
    return {"deleted": True}
