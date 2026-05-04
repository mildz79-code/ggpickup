"""
routers/users.py — admin user list.

Mirrors production C:\\ai\\ggapi\\main.py:
    GET /users    →  admin-only, returns app_users with extended columns.

Browser path:  GET /api/users    →  FastAPI sees GET /users
"""
from fastapi import APIRouter, Depends

from db import get_conn
from deps import admin_only

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(user: dict = Depends(admin_only)):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, full_name, role, is_active, phone, title, "
            "created_at, last_signed_in_at "
            "FROM app_users ORDER BY role, full_name"
        )
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    for r in rows:
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                r[k] = v.isoformat()
    return rows
