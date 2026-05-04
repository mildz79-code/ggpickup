"""
routers/pickup_requests.py — the heart of the GG Pickup app.

Mirrors production C:\\ai\\ggapi\\main.py exactly. Browser paths
(IIS strips /api before forwarding to FastAPI):

    GET    /api/pickup-requests?date=YYYY-MM-DD&status=...&knitter=...
    POST   /api/pickup-requests                      (admin)
    GET    /api/pickup-requests/{id}
    PATCH  /api/pickup-requests/{id}                 (admin)
    DELETE /api/pickup-requests/{id}                 (admin)
    PATCH  /api/pickup-requests/{id}/pickup          (any logged-in user)
    POST   /api/pickup-requests/{id}/photos          (any logged-in user, multipart)
    GET    /api/pickup-requests/{id}/photos
"""
import os
import shutil
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from db import get_conn
from deps import admin_only, get_current_user

router = APIRouter(prefix="/pickup-requests", tags=["pickup-requests"])

# Production hardcodes C:\ggphotos. Repo + PRODUCTION_INVENTORY.md prefer
# C:\ai\ggapi\photos. Env-driven so prod can override either way.
PHOTO_DIR = Path(os.getenv("PHOTO_DIR", r"C:\ai\ggapi\photos"))
PHOTO_DIR.mkdir(parents=True, exist_ok=True)


@router.get("")
def list_requests(
    date: Optional[str]    = None,
    status: Optional[str]  = None,
    knitter: Optional[str] = None,
    user: dict = Depends(get_current_user),
):
    where, params = [], []
    if date:
        where.append("request_date = ?")
        params.append(date)
    if status:
        where.append("status = ?")
        params.append(status)
    if knitter:
        where.append("knitter = ?")
        params.append(knitter)
    if user["role"] == "driver":
        where.append("(status = 'Pending' OR picked_up_by = ?)")
        params.append(user["sub"])

    sql = (
        "SELECT id, request_date, knitter, customer, lot_number, qty, status, "
        "notes, created_at, picked_up_at, picked_up_by, lat, lng "
        "FROM greige_pickup_requests"
    )
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY knitter, id"

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    for r in rows:
        for k, v in r.items():
            if hasattr(v, "isoformat"):
                r[k] = v.isoformat()
    return rows


@router.get("/{req_id}")
def get_request(req_id: int, user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, request_date, knitter, customer, lot_number, qty, status, "
            "notes, created_at, picked_up_at, picked_up_by, lat, lng "
            "FROM greige_pickup_requests WHERE id = ?",
            req_id,
        )
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        cols = [c[0] for c in cur.description]
        result = dict(zip(cols, row))

    for k, v in result.items():
        if hasattr(v, "isoformat"):
            result[k] = v.isoformat()
    return result


@router.post("")
def create_request(body: dict, user: dict = Depends(admin_only)):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO greige_pickup_requests "
            "(request_date, knitter, customer, lot_number, qty, status, notes) "
            "OUTPUT INSERTED.id "
            "VALUES (?, ?, ?, ?, ?, 'Pending', ?)",
            body.get("request_date"),
            body["knitter"],
            body.get("customer", ""),
            body.get("lot_number"),
            body.get("qty", 1),
            body.get("notes"),
        )
        new_id = cur.fetchone()[0]
    return {"id": new_id, "status": "Pending"}


@router.patch("/{req_id}/pickup")
def mark_picked_up(
    req_id: int,
    body: dict,
    user: dict = Depends(get_current_user),
):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "UPDATE greige_pickup_requests "
            "SET status='Picked Up', picked_up_by=?, picked_up_at=GETDATE(), "
            "    lat=?, lng=? "
            "WHERE id=? AND status='Pending'",
            user["sub"],
            body.get("lat"),
            body.get("lng"),
            req_id,
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Not found or already picked up")
    return {"success": True}


@router.patch("/{req_id}")
def update_request(req_id: int, body: dict, user: dict = Depends(admin_only)):
    allowed = ["knitter", "customer", "lot_number", "qty", "status", "notes", "request_date"]
    sets, params = [], []
    for field in allowed:
        if field in body:
            sets.append(f"{field} = ?")
            params.append(body[field])
    if not sets:
        raise HTTPException(status_code=400, detail="Nothing to update")
    params.append(req_id)

    with get_conn() as conn:
        conn.cursor().execute(
            f"UPDATE greige_pickup_requests SET {', '.join(sets)} WHERE id = ?",
            params,
        )
    return {"success": True}


@router.delete("/{req_id}")
def delete_request(req_id: int, user: dict = Depends(admin_only)):
    with get_conn() as conn:
        conn.cursor().execute(
            "DELETE FROM greige_pickup_requests WHERE id = ?",
            req_id,
        )
    return {"success": True}


@router.post("/{req_id}/photos")
async def upload_photo(
    req_id: int,
    file: UploadFile = File(...),
    lat: Optional[float] = None,
    lng: Optional[float] = None,
    user: dict = Depends(get_current_user),
):
    ext = Path(file.filename).suffix or ".jpg"
    filename = f"{req_id}_{uuid.uuid4().hex}{ext}"
    dest = PHOTO_DIR / filename
    with dest.open("wb") as f:
        shutil.copyfileobj(file.file, f)
    storage_path = f"/photos/{filename}"

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO greige_pickup_photos "
            "(pickup_request_id, storage_path, uploaded_by, lat, lng) "
            "OUTPUT INSERTED.id "
            "VALUES (?, ?, ?, ?, ?)",
            req_id,
            storage_path,
            user["sub"],
            lat,
            lng,
        )
        photo_id = cur.fetchone()[0]

    return {"id": photo_id, "url": f"http://gg.colorfashiondnf.com{storage_path}"}


@router.get("/{req_id}/photos")
def list_photos(req_id: int, user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, storage_path, caption, lat, lng, created_at "
            "FROM greige_pickup_photos "
            "WHERE pickup_request_id = ? "
            "ORDER BY created_at",
            req_id,
        )
        cols = [c[0] for c in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    for r in rows:
        r["url"] = f"http://gg.colorfashiondnf.com{r['storage_path']}"
        if hasattr(r.get("created_at"), "isoformat"):
            r["created_at"] = r["created_at"].isoformat()
    return rows
