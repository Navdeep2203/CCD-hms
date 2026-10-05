from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.audit import audit
from app.core.config import settings
from app.core.security import (
    CUSTOMER,
    create_access_token,
    get_user_allow_password_change,
    hash_password,
    load_user,
    public_user,
    verify_password,
)
from app.core.sqlutil import build_set
from app.database import execute, execute_returning_id, fetch_one, transaction
from app.schemas import (
    ChangePasswordRequest,
    LoginRequest,
    ProfileUpdateRequest,
    RegisterCustomerRequest,
    TokenResponse,
)

router = APIRouter()

# Simple in-memory brute-force protection (per email). Use Redis or similar if you run several instances.
_attempts: dict[str, dict] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _check_lock(key: str) -> None:
    entry = _attempts.get(key)
    if not entry or not entry.get("locked_until"):
        return
    if entry["locked_until"] > _now():
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Too many failed attempts. Try again later.")
    _attempts.pop(key, None)


def _record_failure(key: str) -> None:
    entry = _attempts.setdefault(key, {"count": 0, "locked_until": None})
    entry["count"] += 1
    if entry["count"] >= settings.login_max_attempts:
        entry["locked_until"] = _now() + timedelta(minutes=settings.login_lock_minutes)
        entry["count"] = 0


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    key = payload.email
    _check_lock(key)
    row = fetch_one(
        "SELECT user_id, password_hash, is_active FROM users WHERE LOWER(email) = LOWER(:email)",
        {"email": payload.email},
    )
    if not row or not row["is_active"] or not verify_password(payload.password, row["password_hash"]):
        _record_failure(key)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    _attempts.pop(key, None)
    user = load_user(int(row["user_id"]))
    return TokenResponse(access_token=create_access_token(int(row["user_id"])), user=public_user(user))


@router.get("/me")
def me(user: dict = Depends(get_user_allow_password_change)) -> dict:
    return public_user(user)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_customer(payload: RegisterCustomerRequest) -> TokenResponse:
    with transaction() as conn:
        if fetch_one("SELECT 1 FROM users WHERE LOWER(email) = LOWER(:email)", {"email": payload.email}, conn=conn):
            raise HTTPException(status.HTTP_409_CONFLICT, "Email is already registered")
        user_id = execute_returning_id(
            """
            INSERT INTO users (email, password_hash, name, phone_country_code, phone_number, is_active)
            VALUES (:email, :password_hash, :name, :phone_country_code, :phone_number, TRUE)
            RETURNING user_id
            """,
            {
                "email": payload.email,
                "password_hash": hash_password(payload.password),
                "name": payload.name,
                "phone_country_code": payload.phone_country_code,
                "phone_number": payload.phone_number,
            },
            conn=conn,
        )
        execute(
            "INSERT INTO user_roles (user_id, role_id) SELECT :user_id, role_id FROM roles WHERE role_name = :role",
            {"user_id": user_id, "role": CUSTOMER},
            conn=conn,
        )
        execute("INSERT INTO customers (user_id, loyalty_points) VALUES (:user_id, 0)", {"user_id": user_id}, conn=conn)
    user = load_user(user_id)
    return TokenResponse(access_token=create_access_token(user_id), user=public_user(user))


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, user: dict = Depends(get_user_allow_password_change)) -> dict:
    row = fetch_one("SELECT password_hash FROM users WHERE user_id = :id", {"id": user["user_id"]})
    if not row or not verify_password(payload.current_password, row["password_hash"]):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Current password is incorrect")
    execute(
        "UPDATE users SET password_hash = :hash, must_change_password = FALSE WHERE user_id = :id",
        {"hash": hash_password(payload.new_password), "id": user["user_id"]},
    )
    audit(user["user_id"], "password_changed")
    return public_user(load_user(user["user_id"]))


@router.put("/profile")
def update_profile(payload: ProfileUpdateRequest, user: dict = Depends(get_user_allow_password_change)) -> dict:
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "No fields to update")
    if "name" in data and data["name"] is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Name cannot be empty")
    customer_fields = {"address", "id_proof", "nationality"} & set(data)
    if customer_fields and not user.get("customer_id"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only guest accounts have address and ID details")
    with transaction() as conn:
        user_set, user_params = build_set(data, {"name", "phone_country_code", "phone_number"})
        if user_set:
            execute(f"UPDATE users SET {user_set} WHERE user_id = :uid", {**user_params, "uid": user["user_id"]}, conn=conn)
        cust_set, cust_params = build_set({k: (data[k] or "") for k in customer_fields}, customer_fields)
        if cust_set:
            execute(f"UPDATE customers SET {cust_set} WHERE user_id = :uid", {**cust_params, "uid": user["user_id"]}, conn=conn)
    return public_user(load_user(user["user_id"]))
