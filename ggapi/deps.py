"""
deps.py — FastAPI dependencies + auth helpers.

Production uses bcrypt for password hashing and PyJWT for tokens.
This module mirrors that.
"""
import os
from datetime import datetime, timedelta, timezone

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

def issue_token(user_id: str, role: str, name: str = "") -> str:
    payload = {
        "sub":  user_id,
        "role": role,
        "name": name,
        "exp":  datetime.now(timezone.utc) + timedelta(hours=_JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


# ---------- request-scoped helpers ----------

def get_current_user(creds: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if not creds:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")
    try:
        payload = jwt.decode(creds.credentials, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid token")

    if not payload.get("sub") or not payload.get("role"):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Malformed token")

    return {
        "id":           payload["sub"],
        "role":         payload["role"],
        "display_name": payload.get("name", ""),
    }


def require_role(required: str):
    """Usage:  @router.get(..., dependencies=[Depends(require_role("admin"))])"""
    def _check(user=Depends(get_current_user)):
        if user["role"] != required:
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Requires role={required}")
        return user
    return _check
