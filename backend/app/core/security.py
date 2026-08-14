from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext

from app.core.config import settings
from app.database import fetch_one


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def verify_password(plain_password: str, password_hash: str) -> bool:
    if not password_hash:
        return False
    return password_context.verify(plain_password, password_hash)


def hash_password(password: str) -> str:
    return password_context.hash(password)


def create_access_token(subject: str, claims: dict[str, Any]) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    payload = {"sub": subject, "exp": expires_at, **claims}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def get_current_user(token: str = Depends(oauth2_scheme)) -> dict[str, Any]:
    payload = decode_token(token)
    user = fetch_one(
        """
        SELECT user_id, email, name, phone_country_code, phone_number, is_active, created_at
        FROM users
        WHERE user_id = :user_id
        """,
        {"user_id": int(payload["sub"])},
    )
    if not user or int(user.get("is_active", 0)) != 1:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive")
    user["roles"] = payload.get("roles", [])
    user["customer_id"] = payload.get("customer_id")
    user["staff_id"] = payload.get("staff_id")
    user["manager_id"] = payload.get("manager_id")
    return user


def require_roles(*allowed_roles: str):
    def dependency(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        roles = set(user.get("roles", []))
        if not roles.intersection(allowed_roles):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return user

    return dependency

