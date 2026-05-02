"""
routers/sync.py — Google Sheets → SQL Server sync (already exists in production).

Browser path:  POST /api/sync  →  FastAPI sees POST /sync

The actual sync logic lives in C:\\ai\\ggapi\\sheets_sync.py on WEBSERVER.
This file is the route stub for the workspace; pull the real implementation
into the repo when you mirror prod.
"""
from fastapi import APIRouter, Depends, HTTPException

from deps import require_role

router = APIRouter(prefix="/sync", tags=["sync"])


@router.post("", dependencies=[Depends(require_role("admin"))])
def sync_from_sheet():
    """
    Pull rows 3+ from sheet `1TSJNTWouAV1x4W6Ouh3uTKM-PDNJL9952eYqYcjoPAA`,
    tab TODAY. Carries forward merged Knitter cells, filters TOTAL rows,
    deletes today's Pending rows then re-inserts.

    Reuse the production implementation from C:\\ai\\ggapi\\sheets_sync.py.
    """
    raise HTTPException(501, "Mirror production C:\\ai\\ggapi\\sheets_sync.py here")
