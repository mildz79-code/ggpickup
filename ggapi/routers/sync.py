"""
routers/sync.py — Google Sheets → SQL Server sync.

Mirrors production C:\\ai\\ggapi\\main.py:
    POST /sync    →  admin-only; delegates to sheets_sync.sync_today().

Browser path:  POST /api/sync  →  FastAPI sees POST /sync
"""
from fastapi import APIRouter, Depends, HTTPException

from deps import admin_only

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("")
def sync_from_sheet(user: dict = Depends(admin_only)):
    try:
        from sheets_sync import sync_today
        return sync_today()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
