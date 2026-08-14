from fastapi import APIRouter, Depends, HTTPException, status

from app.core.security import create_access_token, get_current_user, hash_password, verify_password
from app.database import execute, execute_returning_id, fetch_all, fetch_one
from app.schemas import LoginRequest, RegisterCustomerRequest, TokenResponse


router = APIRouter()


def _roles_for_user(user_id: int) -> list[str]:
    rows = fetch_all(
        """
        SELECT r.role_name
        FROM roles r
        JOIN user_roles ur ON ur.role_id = r.role_id
        WHERE ur.user_id = :user_id
        ORDER BY r.role_name
        """,
        {"user_id": user_id},
    )
    return [row["role_name"] for row in rows]


def _identity_claims(user_id: int) -> dict:
    customer = fetch_one("SELECT customer_id FROM customers WHERE user_id = :user_id", {"user_id": user_id})
    staff = fetch_one("SELECT staff_id FROM staff WHERE user_id = :user_id", {"user_id": user_id})
    manager = fetch_one("SELECT manager_id FROM managers WHERE user_id = :user_id", {"user_id": user_id})
    return {
        "roles": _roles_for_user(user_id),
        "customer_id": customer["customer_id"] if customer else None,
        "staff_id": staff["staff_id"] if staff else None,
        "manager_id": manager["manager_id"] if manager else None,
    }


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = fetch_one(
        """
        SELECT user_id, email, password_hash, name, phone_country_code, phone_number, is_active, created_at
        FROM users
        WHERE LOWER(email) = LOWER(:email)
        """,
        {"email": payload.email},
    )
    if not user or int(user.get("is_active", 0)) != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    claims = _identity_claims(int(user["user_id"]))
    token = create_access_token(str(user["user_id"]), claims)
    user.pop("password_hash", None)
    user.update(claims)
    return TokenResponse(access_token=token, user=user)


@router.get("/me")
def me(user: dict = Depends(get_current_user)) -> dict:
    return user


@router.post("/register", response_model=TokenResponse)
def register_customer(payload: RegisterCustomerRequest) -> TokenResponse:
    exists = fetch_one("SELECT 1 FROM users WHERE LOWER(email) = LOWER(:email)", {"email": payload.email})
    if exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email is already registered")

    user_id = execute_returning_id(
        """
        INSERT INTO users (email, password_hash, name, phone_country_code, phone_number, is_active)
        VALUES (:email, :password_hash, :name, :phone_country_code, :phone_number, 1)
        RETURNING user_id INTO :new_id
        """,
        {
            "email": payload.email,
            "password_hash": hash_password(payload.password),
            "name": payload.name,
            "phone_country_code": payload.phone_country_code,
            "phone_number": payload.phone_number,
        },
    )
    execute(
        """
        INSERT INTO user_roles (user_id, role_id)
        VALUES (:user_id, (SELECT role_id FROM roles WHERE role_name = 'ROLE_CUSTOMER'))
        """,
        {"user_id": user_id},
    )
    execute("INSERT INTO customers (user_id, loyalty_points) VALUES (:user_id, 0)", {"user_id": user_id})

    user = fetch_one(
        """
        SELECT user_id, email, name, phone_country_code, phone_number, is_active, created_at
        FROM users
        WHERE user_id = :user_id
        """,
        {"user_id": user_id},
    )
    claims = _identity_claims(user_id)
    token = create_access_token(str(user_id), claims)
    user.update(claims)
    return TokenResponse(access_token=token, user=user)

