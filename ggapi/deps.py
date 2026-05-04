"""
deps.py — FastAPI dependencies + auth helpers.

Mirrors production C:\\ai\\ggapi\\main.py auth helpers exactly:
    - JWT payload: {sub, role, full_name, exp}
    - get_current_user returns the raw decoded payload
      (so routes use user["sub"], user["role"], user["full_name"])
    - require_role("admin") gates admin-only routes

Production hardcodes the JWT secret in main.py; this repo loads it from
ggapi/.env per the rule "no committed secrets".
"""
import os
from datetime import datetime, timedelta

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_JWT_SECRET       = os.getenv("JWT_SECRET", "")
_JWT_ALGORITHM    = os.getenv("JWT_ALGORITHM", "HS256")
_JWT_EXPIRE_HOURS = int(os.getenv("JWT_EXPIRE_HOURS", "12"))

if not _JWT_SECRET:
    raise RuntimeError("JWT_SECRET must be set in ggapi/.env")

bearer = HTTPBearer(auto_error=False)


# ---------- password ----------

def hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


# ---------- tokens ----------

def issue_token(user_id: str, role: str, full_name: str = "") -> str:
    """Mirrors prod make_token(): payload = {sub, role, full_name, exp}."""
    payload = {
        "sub":       user_id,
        "role":      role,
        "full_name": full_name,
        "exp":       datetime.utcnow() + timedelta(hours=_JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


# ---------- request-scoped helpers ----------

def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)):
    """
    Returns the raw JWT payload dict so routes can do user["sub"], user["role"],
    user["full_name"] — matching the prod main.py contract.
    """
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        return jwt.decode(creds.credentials, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")


def admin_only(user: dict = Depends(get_current_user)) -> dict:
    """Mirrors prod admin_only(): 403 if role != 'admin'."""
    if user.get("role") != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    return user


def require_role(required: str):
    """Usage:  @router.get(..., dependencies=[Depends(require_role("admin"))])"""
    def _check(user=Depends(get_current_user)):
        if user.get("role") != required:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role={required}")
        return user
    return _check
