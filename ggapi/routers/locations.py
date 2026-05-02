"""
routers/locations.py — ship-to locations (read-only for now).

Browser path:  GET /api/locations  →  FastAPI sees GET /locations
"""
from fastapi import APIRouter, Depends

from db import get_conn
from deps import get_current_user

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("")
def list_locations(user=Depends(get_current_user)):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT id, code, name, street, city, state, zip, phone, lat, lng, is_active
              FROM ship_to_locations
             WHERE is_active = 1
             ORDER BY code
            """
        )
        rows = cur.fetchall()
    return [
        {
            "id":     r.id,
            "code":   r.code,
            "name":   r.name,
            "street": r.street,
            "city":   r.city,
            "state":  r.state,
            "zip":    r.zip,
            "phone":  r.phone,
            "lat":    float(r.lat) if r.lat is not None else None,
            "lng":    float(r.lng) if r.lng is not None else None,
        }
        for r in rows
    ]
