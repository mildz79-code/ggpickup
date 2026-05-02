"""
routers/pickup_requests.py — the heart of the GG Pickup app.

Browser paths (IIS strips /api):
    GET    /api/pickup-requests?date=YYYY-MM-DD&status=...&knitter=...
    POST   /api/pickup-requests                        (admin)
    GET    /api/pickup-requests/{id}
    PATCH  /api/pickup-requests/{id}                   (admin)
    DELETE /api/pickup-requests/{id}                   (admin)
    PATCH  /api/pickup-requests/{id}/pickup            (any logged-in user)
    POST   /api/pickup-requests/{id}/photos            (any logged-in user, multipart)
    GET    /api/pickup-requests/{id}/photos
"""
from datetime import date as date_cls

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from deps import get_current_user, require_role

router = APIRouter(prefix="/pickup-requests", tags=["pickup-requests"])


@router.get("")
def list_requests(
    date: date_cls | None = None,
    status: str | None = None,
    knitter: str | None = None,
    user=Depends(get_current_user),
):
    """
    Filtered list of pickup requests.

    Drivers see Pending requests + their own Picked Up rows (server-side filter).
    Admins see everything.

    Returns the rows in the SAME shape Mockup 1 expects. The frontend
    re-groups by `knitter` for display; this endpoint does NOT pre-group,
    because admin views often want flat tables.
    """
    # TODO: read this code from production (C:\ai\ggapi\main.py) and paste here
    # so the workspace and prod stay in lockstep. For now, this is a stub
    # that exists so the router mounts cleanly.
    raise HTTPException(501, "Mirror the production implementation from C:\\ai\\ggapi\\main.py")


@router.post("", dependencies=[Depends(require_role("admin"))])
def create_request():
    raise HTTPException(501, "Mirror production implementation")


@router.get("/{req_id}")
def get_one(req_id: int, user=Depends(get_current_user)):
    raise HTTPException(501, "Mirror production implementation")


@router.patch("/{req_id}", dependencies=[Depends(require_role("admin"))])
def update_request(req_id: int):
    raise HTTPException(501, "Mirror production implementation")


@router.delete("/{req_id}", dependencies=[Depends(require_role("admin"))])
def delete_request(req_id: int):
    raise HTTPException(501, "Mirror production implementation")


@router.patch("/{req_id}/pickup")
def mark_picked_up(
    req_id: int,
    lat: float | None = None,
    lng: float | None = None,
    user=Depends(get_current_user),
):
    """Driver-side action: mark this request picked up + capture GPS."""
    raise HTTPException(501, "Mirror production implementation")


@router.post("/{req_id}/photos")
async def upload_photo(
    req_id: int,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    raise HTTPException(501, "Mirror production implementation")


@router.get("/{req_id}/photos")
def list_photos(req_id: int, user=Depends(get_current_user)):
    raise HTTPException(501, "Mirror production implementation")
