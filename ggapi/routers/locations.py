"""
routers/locations.py — ship-to locations (read-only).

Mirrors production C:\\ai\\ggapi\\main.py:
    GET /locations    →  any logged-in user, active rows only.

Browser path:  GET /api/locations  →  FastAPI sees GET /locations
"""
from fastapi import APIRouter, Depends

from db import get_conn
from deps import get_current_user

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("")
def list_locations(user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, code, name, street, city, state, zip, phone, lat, lng "
            "FROM ship_to_locations WHERE is_active = 1 ORDER BY name"
        )
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchall()]
