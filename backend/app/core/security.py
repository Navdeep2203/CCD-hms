from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from app.core.config import settings
from app.database import fetch_one

ADMIN = "ROLE_ADMIN"
MANAGER = "ROLE_MANAGER"
STAFF = "ROLE_STAFF"
CUSTOMER = "ROLE_CUSTOMER"

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

USER_SQL = """
SELECT u.user_id, u.email, u.name, u.phone_country_code, u.phone_number, u.is_active,
       u.must_change_password, u.created_at,
       c.customer_id, c.address, c.id_proof, c.nationality, c.loyalty_points,
       s.staff_id, m.manager_id,
       COALESCE((SELECT array_agg(r.role_name ORDER BY r.role_name)
                 FROM user_roles ur JOIN roles r ON r.role_id = ur.role_id
                 WHERE ur.user_id = u.user_id), ARRAY[]::text[]) AS roles
FROM users u
LEFT JOIN customers c ON c.user_id = u.user_id
LEFT JOIN staff s ON s.user_id = u.user_id
LEFT JOIN managers m ON m.user_id = u.user_id
WHERE u.user_id = :user_id
"""


def verify_password(plain_password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    return password_context.verify(plain_password, password_hash)


def hash_password(password: str) -> str:
    return password_context.hash(password)


def create_access_token(user_id: int) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode({"sub": str(user_id), "exp": expires_at}, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def load_user(user_id: int) -> dict[str, Any] | None:
    return fetch_one(USER_SQL, {"user_id": user_id})


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    """What the client is allowed to see about the logged-in account."""
    result = {
        key: user[key]
        for key in ("user_id", "email", "name", "phone_country_code", "phone_number", "is_active",
                    "must_change_password", "created_at", "roles")
    }
    if user.get("customer_id"):
        for key in ("customer_id", "address", "id_proof", "nationality", "loyalty_points"):
            result[key] = user[key]
    if user.get("staff_id"):
        result["staff_id"] = user["staff_id"]
    if user.get("manager_id"):
        result["manager_id"] = user["manager_id"]
    return result


def _authenticate(token: str, *, allow_password_change: bool) -> dict[str, Any]:
    payload = decode_token(token)
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid access token") from exc
    user = load_user(user_id)
    if not user or not user["is_active"]:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User is inactive")
    if user["must_change_password"] and not allow_password_change:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You must change your temporary password before continuing")
    return user


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    return _authenticate(token, allow_password_change=False)


def get_user_allow_password_change(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    return _authenticate(token, allow_password_change=True)


def has_role(user: dict[str, Any], *roles: str) -> bool:
    return bool(set(user.get("roles", [])).intersection(roles))


def is_ops(user: dict[str, Any]) -> bool:
    return has_role(user, ADMIN, MANAGER, STAFF)


def is_management(user: dict[str, Any]) -> bool:
    return has_role(user, ADMIN, MANAGER)


def require_roles(*allowed_roles: str):
    def dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if not has_role(user, *allowed_roles):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient role")
        return user

    return dependency
