"""
routers/auth.py — login + current-user endpoints.

Mirrors production C:\\ai\\ggapi\\main.py exactly:
    POST /auth/login   →  {access_token, user: {id, email, full_name, role}}
    GET  /auth/me      →  {id, email, full_name, role, title, phone}

Browser path:  POST /api/auth/login    →  FastAPI sees POST /auth/login
"""
from fastapi import APIRouter, Depends, HTTPException

from db import get_conn
from deps import get_current_user, issue_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(body: dict):
    email    = body.get("email", "").strip().lower()
    password = body.get("password", "")

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, full_name, role, password_hash, is_active "
            "FROM app_users WHERE email = ?",
            email,
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user_id, db_email, full_name, role, pw_hash, is_active = row
        if not is_active:
            raise HTTPException(status_code=403, detail="Account disabled")
        if not verify_password(password, pw_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        cur.execute(
            "UPDATE app_users SET last_signed_in_at = GETDATE() WHERE id = ?",
            str(user_id),
        )

    return {
        "access_token": issue_token(str(user_id), role, full_name),
        "user": {
            "id":        str(user_id),
            "email":     db_email,
            "full_name": full_name,
            "role":      role,
        },
    }


@router.get("/me")
def me(user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, full_name, role, title, phone "
            "FROM app_users WHERE id = ?",
            user["sub"],
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return dict(zip(["id", "email", "full_name", "role", "title", "phone"], row))
