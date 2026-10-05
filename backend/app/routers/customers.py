from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.audit import audit
from app.core.security import (
    ADMIN,
    CUSTOMER,
    MANAGER,
    STAFF,
    hash_password,
    is_management,
    require_roles,
)
from app.database import (
    execute,
    execute_returning_id,
    fetch_all,
    fetch_one,
    transaction,
)
from app.schemas import CustomerCreateRequest

router = APIRouter(dependencies=[Depends(require_roles(ADMIN, MANAGER, STAFF))])


@router.get("")
def list_customers(
    search: str | None = Query(default=None, max_length=100),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: dict = Depends(require_roles(ADMIN, MANAGER, STAFF)),
) -> list[dict]:
    # Front-line staff get just what they need to book a walk-in; ID proof / address are management-only.
    extra = ", c.address, c.id_proof" if is_management(user) else ""
    where, params = "", {"limit": limit, "offset": offset}
    if search:
        where = " WHERE u.name ILIKE :q OR u.email ILIKE :q OR u.phone_number ILIKE :q"
        params["q"] = f"%{search}%"
    return fetch_all(
        f"""SELECT c.customer_id, c.user_id, u.name, u.email, u.phone_country_code, u.phone_number,
                   u.is_active, c.nationality, c.loyalty_points{extra}
            FROM customers c JOIN users u ON u.user_id = c.user_id{where}
            ORDER BY c.customer_id DESC LIMIT :limit OFFSET :offset""",
        params,
    )


@router.post("", status_code=201)
def create_customer(payload: CustomerCreateRequest, user: dict = Depends(require_roles(ADMIN, MANAGER, STAFF))) -> dict:
    """Register a walk-in guest; they must change the temporary password on first login."""
    with transaction() as conn:
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
            {"uid": user_id, "role": CUSTOMER}, conn=conn,
        )
        customer_id = execute_returning_id(
            "INSERT INTO customers (user_id, loyalty_points) VALUES (:uid, 0) RETURNING customer_id",
            {"uid": user_id}, conn=conn,
        )
    audit(user["user_id"], "customer_created", customer_id=customer_id)
    return {"customer_id": customer_id, "user_id": user_id, "name": payload.name, "email": payload.email}
