"""
routers/auth.py — login + current-user endpoints.

Browser path:  POST /api/auth/login    →  FastAPI sees POST /auth/login
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from db import get_conn
from deps import get_current_user, issue_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


class LoginOut(BaseModel):
    token: str
    role: str
    display_name: str
    user_id: str


@router.post("/login", response_model=LoginOut)
def login(body: LoginIn):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, email, password_hash, role, display_name, is_active
              FROM app_users
             WHERE email = ?
            """,
            (body.email.strip().lower(),),
        )
        row = cur.fetchone()

    if not row or not row.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")
    if not verify_password(body.password, row.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    token = issue_token(user_id=str(row.id), role=row.role, name=row.display_name or "")
    return LoginOut(
        token=token,
        role=row.role,
        display_name=row.display_name or "",
        user_id=str(row.id),
    )


@router.get("/me")
def me(user=Depends(get_current_user)):
    return user
