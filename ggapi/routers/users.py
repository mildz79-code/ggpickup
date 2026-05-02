"""
routers/users.py — admin user list.

Browser path:  GET /api/users    →  FastAPI sees GET /users
"""
from fastapi import APIRouter, Depends

from db import get_conn
from deps import require_role

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", dependencies=[Depends(require_role("admin"))])
def list_users():
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, email, role, display_name, is_active, created_at
              FROM app_users
             ORDER BY display_name
            """
        )
        rows = cur.fetchall()
    return [
        {
            "id": str(r.id),
            "email": r.email,
            "role": r.role,
            "display_name": r.display_name,
            "is_active": bool(r.is_active),
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]
