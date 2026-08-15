from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import require_roles
from app.database import execute, execute_returning_id, fetch_all, fetch_one
from app.schemas import DepartmentRequest


router = APIRouter(dependencies=[Depends(require_roles("ROLE_ADMIN", "ROLE_MANAGER"))])


@router.get("/departments")
def departments() -> list[dict]:
    return fetch_all(
        """
        SELECT d.department_id, d.department_name, d.head_manager_id, u.name AS head_manager_name
        FROM departments d
        LEFT JOIN managers m ON m.manager_id = d.head_manager_id
        LEFT JOIN users u ON u.user_id = m.user_id
        ORDER BY d.department_name
        """
    )


@router.post("/departments")
def create_department(payload: DepartmentRequest) -> dict:
    department_id = execute_returning_id(
        """
        INSERT INTO departments (department_name, head_manager_id)
        VALUES (:department_name, :head_manager_id)
        RETURNING department_id
        """,
        payload.model_dump(),
    )
    return fetch_one("SELECT * FROM departments WHERE department_id = :department_id", {"department_id": department_id})


@router.put("/departments/{department_id}")
def update_department(department_id: int, payload: DepartmentRequest) -> dict:
    affected = execute(
        """
        UPDATE departments
        SET department_name = :department_name, head_manager_id = :head_manager_id
        WHERE department_id = :department_id
        """,
        {**payload.model_dump(), "department_id": department_id},
    )
    if affected == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return fetch_one("SELECT * FROM departments WHERE department_id = :department_id", {"department_id": department_id})


@router.get("/staff")
def staff() -> list[dict]:
    return fetch_all(
        """
        SELECT s.staff_id, s.user_id, u.name, u.email, d.department_name,
               mgr.name AS manager_name, s.job_description, s.salary
        FROM staff s
        JOIN users u ON u.user_id = s.user_id
        JOIN departments d ON d.department_id = s.department_id
        LEFT JOIN managers m ON m.manager_id = s.manager_id
        LEFT JOIN users mgr ON mgr.user_id = m.user_id
        ORDER BY s.staff_id DESC
        """
    )


@router.get("/customers")
def customers() -> list[dict]:
    return fetch_all(
        """
        SELECT c.customer_id, c.user_id, u.name, u.email, u.phone_country_code, u.phone_number,
               c.address, c.id_proof, c.nationality, c.loyalty_points
        FROM customers c
        JOIN users u ON u.user_id = c.user_id
        ORDER BY c.customer_id DESC
        """
    )


@router.get("/managers")
def managers() -> list[dict]:
    return fetch_all(
        """
        SELECT m.manager_id, m.user_id, u.name, u.email, d.department_name,
               m.reports_to_manager_id, m.job_description, m.salary
        FROM managers m
        JOIN users u ON u.user_id = m.user_id
        JOIN departments d ON d.department_id = m.department_id
        ORDER BY m.manager_id DESC
        """
    )


@router.get("/maintenance")
def maintenance() -> list[dict]:
    return fetch_all(
        """
        SELECT rm.maintenance_id, rm.room_id, r.room_number, rm.staff_id,
               u.name AS staff_name, rm.description, rm.maintenance_date, rm.status
        FROM room_maintenance rm
        JOIN rooms r ON r.room_id = rm.room_id
        LEFT JOIN staff s ON s.staff_id = rm.staff_id
        LEFT JOIN users u ON u.user_id = s.user_id
        ORDER BY rm.maintenance_id DESC
        """
    )
