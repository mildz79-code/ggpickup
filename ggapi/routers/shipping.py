"""
routers/shipping.py — shipping schedule endpoints (Phase 3, not started).

Browser paths (IIS strips /api):
    GET    /api/shipping/today               →  GET /shipping/today
    GET    /api/shipping/day/{yyyy-mm-dd}    →  GET /shipping/day/...
    POST   /api/shipping/deliveries          →  POST /shipping/deliveries
    PATCH  /api/shipping/deliveries/{id}
    POST   /api/shipping/stops
    POST   /api/shipping/stops/reorder
    DELETE /api/shipping/stops/{id}

Combines pickup_requests + delivery_requests into daily schedule_days /
schedule_stops. Admin-only for mutations; reads are admin or assigned driver.
"""
from datetime import date as date_cls

from fastapi import APIRouter, Depends, HTTPException

from deps import get_current_user, require_role

router = APIRouter(prefix="/shipping", tags=["shipping"])


@router.get("/today")
def schedule_today(user=Depends(get_current_user)):
    """Unified schedule for today. Response shape:

    {
      "schedule_date": "2026-04-23",
      "pickups":    [...rows from greige_pickup_requests where request_date = today],
      "deliveries": [...rows from delivery_requests where request_date = today],
      "stops":      [...rows from schedule_stops joined to schedule_days for today]
    }
    """
    raise HTTPException(501, "Phase 3.2 — not implemented")


@router.get("/day/{day}")
def schedule_day(day: date_cls, user=Depends(get_current_user)):
    raise HTTPException(501, "Phase 3.2 — not implemented")


@router.post("/deliveries", dependencies=[Depends(require_role("admin"))])
def create_delivery():
    raise HTTPException(501, "Phase 3.2 — not implemented")


@router.patch("/deliveries/{delivery_id}", dependencies=[Depends(require_role("admin"))])
def update_delivery(delivery_id: int):
    raise HTTPException(501, "Phase 3.2 — not implemented")


@router.post("/stops", dependencies=[Depends(require_role("admin"))])
def add_stop():
    raise HTTPException(501, "Phase 3.2 — not implemented")


@router.post("/stops/reorder", dependencies=[Depends(require_role("admin"))])
def reorder_stops():
    raise HTTPException(501, "Phase 3.2 — not implemented")


@router.delete("/stops/{stop_id}", dependencies=[Depends(require_role("admin"))])
def remove_stop(stop_id: int):
    raise HTTPException(501, "Phase 3.2 — not implemented")
