"""
routers/shipping.py — shipping schedule endpoints (Phase 3).

Browser paths (IIS strips /api):
    GET    /api/shipping/today               →  GET /shipping/today
    GET    /api/shipping/day/{yyyy-mm-dd}    →  GET /shipping/day/...
    POST   /api/shipping/deliveries          →  POST /shipping/deliveries
    PATCH  /api/shipping/deliveries/{id}
    POST   /api/shipping/stops
    POST   /api/shipping/stops/reorder
    DELETE /api/shipping/stops/{id}

Combines pickup_requests + delivery_requests into daily schedule_days /
schedule_stops. Admin-only for mutations; schedule reads any logged-in user.
"""
from __future__ import annotations

import uuid
from datetime import date as date_cls
from datetime import datetime as dt_cls
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from db import get_conn
from deps import admin_only, get_current_user

router = APIRouter(prefix="/shipping", tags=["shipping"])


PICKUP_COLUMNS = (
    "id, request_date, knitter, customer, lot_number, qty, status, notes, "
    "created_at, picked_up_at, picked_up_by, lat, lng"
)

DELIVERY_COLUMNS = (
    "id, request_date, customer_code, lot_number, qty, status, source, dyeserver_ref, "
    "delivered_at, delivered_by, lat, lng, notes, created_at"
)

STOP_COLUMNS = (
    "id, schedule_day_id, stop_type, pickup_request_id, delivery_request_id, "
    "sequence, driver_id, eta, completed_at"
)


def _serialize_cell(val):
    if val is None:
        return None
    if isinstance(val, Decimal):
        return float(val)
    if isinstance(val, uuid.UUID):
        return str(val)
    if hasattr(val, "isoformat"):
        return val.isoformat()
    return val


def _serialize_row(row: dict) -> dict:
    return {k: _serialize_cell(v) for k, v in row.items()}


def _fetch_rows(cur, sql: str, params) -> list[dict]:
    if not isinstance(params, (list, tuple)):
        flat = (params,)
    else:
        flat = tuple(params)
    cur.execute(sql, flat)
    cols = [c[0] for c in cur.description]
    rows = [dict(zip(cols, r)) for r in cur.fetchall()]
    return [_serialize_row(r) for r in rows]


def _schedule_date_today_sql(cur):
    cur.execute("SELECT CAST(GETDATE() AS DATE)")
    return cur.fetchone()[0]


def _schedule_day_id_for_date(cur, schedule_date) -> int | None:
    cur.execute(
        "SELECT id FROM schedule_days WHERE schedule_date = ?",
        schedule_date,
    )
    row = cur.fetchone()
    return int(row[0]) if row else None


def _stops_sql_and_params(schedule_day_id: int | None, user: dict):
    """Admins see all stops for the day; drivers only stops assigned to them."""
    if schedule_day_id is None:
        return None, ()
    role = user.get("role")
    if role == "admin":
        sql = (
            f"SELECT {STOP_COLUMNS} FROM schedule_stops "
            "WHERE schedule_day_id = ? ORDER BY sequence"
        )
        return sql, (schedule_day_id,)
    sql = (
        f"SELECT {STOP_COLUMNS} FROM schedule_stops "
        "WHERE schedule_day_id = ? AND driver_id = ? ORDER BY sequence"
    )
    return sql, (schedule_day_id, user["sub"])


def _build_schedule_payload(cur, schedule_date, schedule_day_id: int | None, user: dict) -> dict:
    pickups_sql = (
        f"SELECT {PICKUP_COLUMNS} FROM greige_pickup_requests "
        "WHERE request_date = ? AND status = 'Pending' ORDER BY knitter, id"
    )
    pickups = _fetch_rows(cur, pickups_sql, (schedule_date,))

    deliveries_sql = (
        f"SELECT {DELIVERY_COLUMNS} FROM delivery_requests "
        "WHERE request_date = ? AND status = 'Pending' ORDER BY customer_code, id"
    )
    deliveries = _fetch_rows(cur, deliveries_sql, (schedule_date,))

    stops_sql, stops_params = _stops_sql_and_params(schedule_day_id, user)
    stops = _fetch_rows(cur, stops_sql, stops_params) if stops_sql else []

    sd = schedule_date.isoformat() if hasattr(schedule_date, "isoformat") else schedule_date
    return {
        "schedule_date": sd,
        "schedule_day_id": schedule_day_id,
        "pickups": pickups,
        "deliveries": deliveries,
        "stops": stops,
    }


@router.get("/today")
def schedule_today(user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        cur = conn.cursor()
        today = _schedule_date_today_sql(cur)
        day_id = _schedule_day_id_for_date(cur, today)
        return _build_schedule_payload(cur, today, day_id, user)


@router.get("/day/{day}")
def schedule_day(day: date_cls, user: dict = Depends(get_current_user)):
    with get_conn() as conn:
        cur = conn.cursor()
        day_id = _schedule_day_id_for_date(cur, day)
        return _build_schedule_payload(cur, day, day_id, user)


@router.post("/deliveries")
def create_delivery(body: dict, user: dict = Depends(admin_only)):
    req_date = body.get("request_date")
    customer_code = body.get("customer_code")
    if not req_date or not customer_code:
        raise HTTPException(
            status_code=400,
            detail="request_date and customer_code are required",
        )
    qty = body.get("qty", 1)
    try:
        qty = int(qty)
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="qty must be an integer")

    status_val = body.get("status", "Pending")
    if status_val not in ("Pending", "Delivered", "Cancelled"):
        raise HTTPException(status_code=400, detail="Invalid status")

    source_val = body.get("source", "manual")
    if source_val not in ("manual", "dyeserver"):
        raise HTTPException(status_code=400, detail="Invalid source")

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO delivery_requests "
            "(request_date, customer_code, lot_number, qty, status, source, "
            "dyeserver_ref, delivered_at, delivered_by, lat, lng, notes) "
            "OUTPUT INSERTED.id "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            req_date,
            customer_code.strip()[:10],
            body.get("lot_number"),
            qty,
            status_val,
            source_val,
            body.get("dyeserver_ref"),
            body.get("delivered_at"),
            body.get("delivered_by"),
            body.get("lat"),
            body.get("lng"),
            body.get("notes"),
        )
        new_id = cur.fetchone()[0]
    return {"id": int(new_id), "status": status_val}


_PATCH_DELIVERY_ALLOWED = [
    "request_date",
    "customer_code",
    "lot_number",
    "qty",
    "status",
    "notes",
    "delivered_at",
    "delivered_by",
    "lat",
    "lng",
]


@router.patch("/deliveries/{delivery_id}")
def update_delivery(delivery_id: int, body: dict, user: dict = Depends(admin_only)):
    sets: list[str] = []
    params: list = []
    for field in _PATCH_DELIVERY_ALLOWED:
        if field not in body:
            continue
        val = body[field]
        if field == "customer_code" and val is not None:
            val = str(val).strip()[:10]
        if field == "qty":
            try:
                val = int(val)
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail="qty must be an integer")
        if field == "status":
            if val is None:
                raise HTTPException(status_code=400, detail="status cannot be null")
            if val not in ("Pending", "Delivered", "Cancelled"):
                raise HTTPException(status_code=400, detail="Invalid status")
        sets.append(f"{field} = ?")
        params.append(val)
    if not sets:
        raise HTTPException(status_code=400, detail="Nothing to update")
    params.append(delivery_id)

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f"UPDATE delivery_requests SET {', '.join(sets)} WHERE id = ?",
            params,
        )
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Not found")
    return {"success": True}


def _ensure_schedule_day(cur, schedule_date, created_by=None) -> int:
    cur.execute(
        "SELECT id FROM schedule_days WHERE schedule_date = ?",
        schedule_date,
    )
    row = cur.fetchone()
    if row:
        return int(row[0])
    cur.execute(
        "INSERT INTO schedule_days (schedule_date, created_by) OUTPUT INSERTED.id "
        "VALUES (?, ?)",
        schedule_date,
        created_by,
    )
    return int(cur.fetchone()[0])


def _next_stop_sequence(cur, schedule_day_id: int) -> int:
    cur.execute(
        "SELECT ISNULL(MAX(sequence), 0) + 1 FROM schedule_stops WHERE schedule_day_id = ?",
        schedule_day_id,
    )
    return int(cur.fetchone()[0])


@router.post("/stops")
def add_stop(body: dict, user: dict = Depends(admin_only)):
    schedule_date = body.get("schedule_date")
    stop_type = body.get("stop_type")
    if not schedule_date or stop_type not in ("pickup", "delivery"):
        raise HTTPException(
            status_code=400,
            detail="schedule_date (yyyy-mm-dd) and stop_type (pickup|delivery) are required",
        )

    p_id = body.get("pickup_request_id")
    d_id = body.get("delivery_request_id")
    if stop_type == "pickup":
        if p_id is None or d_id is not None:
            raise HTTPException(
                status_code=400,
                detail="pickup stops require pickup_request_id and must not set delivery_request_id",
            )
    else:
        if d_id is None or p_id is not None:
            raise HTTPException(
                status_code=400,
                detail="delivery stops require delivery_request_id and must not set pickup_request_id",
            )

    try:
        p_id_int = int(p_id) if p_id is not None else None
        d_id_int = int(d_id) if d_id is not None else None
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Invalid request id")

    driver_uuid = None
    if body.get("driver_id") not in (None, ""):
        try:
            driver_uuid = uuid.UUID(str(body["driver_id"]))
        except (ValueError, TypeError, AttributeError):
            raise HTTPException(status_code=400, detail="Invalid driver_id")

    eta_raw = body.get("eta")
    eta_val = None
    if eta_raw is not None and eta_raw != "":
        if isinstance(eta_raw, dt_cls):
            eta_val = eta_raw
        else:
            try:
                eta_val = dt_cls.fromisoformat(str(eta_raw).replace("Z", "+00:00"))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid eta datetime")

    seq = body.get("sequence")
    with get_conn() as conn:
        cur = conn.cursor()
        day_pk = _ensure_schedule_day(cur, schedule_date, user.get("sub"))
        if seq is None:
            seq = _next_stop_sequence(cur, day_pk)
        else:
            try:
                seq = int(seq)
            except (TypeError, ValueError):
                raise HTTPException(status_code=400, detail="sequence must be an integer")

        cur.execute(
            "INSERT INTO schedule_stops "
            "(schedule_day_id, stop_type, pickup_request_id, delivery_request_id, "
            "sequence, driver_id, eta) "
            "OUTPUT INSERTED.id "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            day_pk,
            stop_type,
            p_id_int,
            d_id_int,
            seq,
            str(driver_uuid) if driver_uuid is not None else None,
            eta_val,
        )
        new_id = cur.fetchone()[0]
    return {"id": int(new_id), "schedule_day_id": day_pk, "sequence": seq}


def _normalize_reorder_pairs(body: list) -> list[tuple[int, int]]:
    if not isinstance(body, list):
        raise HTTPException(status_code=400, detail="Expected a JSON array of {id, sequence}")
    out: list[tuple[int, int]] = []
    seen_ids: set[int] = set()
    for item in body:
        if not isinstance(item, dict):
            raise HTTPException(status_code=400, detail="Each item must be an object")
        sid = item.get("id")
        seq = item.get("sequence")
        try:
            sid_i = int(sid)
            seq_i = int(seq)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="id and sequence must be integers")
        if sid_i in seen_ids:
            raise HTTPException(status_code=400, detail="Duplicate stop id in payload")
        seen_ids.add(sid_i)
        out.append((sid_i, seq_i))
    return out


@router.post("/stops/reorder")
def reorder_stops(body: list, user: dict = Depends(admin_only)):
    pairs = _normalize_reorder_pairs(body)
    if not pairs:
        raise HTTPException(status_code=400, detail="Nothing to reorder")

    stop_ids = [p[0] for p in pairs]
    placeholders = ",".join("?" * len(stop_ids))

    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute(
            f"SELECT id, schedule_day_id FROM schedule_stops WHERE id IN ({placeholders})",
            stop_ids,
        )
        found = {int(r[0]): int(r[1]) for r in cur.fetchall()}
        missing = [i for i in stop_ids if i not in found]
        if missing:
            raise HTTPException(status_code=404, detail=f"Unknown stop id(s): {missing}")

        day_ids = list({found[i] for i in stop_ids})
        if len(day_ids) != 1:
            raise HTTPException(
                status_code=400,
                detail="All stops must belong to the same schedule_day_id",
            )
        schedule_day_id = day_ids[0]

        seq_by_stop = dict(pairs)
        n = len(pairs)
        expected = set(range(1, n + 1))
        got = set(seq_by_stop.values())
        if got != expected:
            raise HTTPException(
                status_code=400,
                detail="sequence values must be 1 through n with no gaps or duplicates",
            )

        for sid in stop_ids:
            cur.execute(
                "UPDATE schedule_stops SET sequence = ? WHERE id = ? AND schedule_day_id = ?",
                -sid,
                sid,
                schedule_day_id,
            )

        for sid, seq in pairs:
            cur.execute(
                "UPDATE schedule_stops SET sequence = ? WHERE id = ? AND schedule_day_id = ?",
                seq,
                sid,
                schedule_day_id,
            )

    return {"success": True, "schedule_day_id": schedule_day_id}


@router.delete("/stops/{stop_id}")
def remove_stop(stop_id: int, user: dict = Depends(admin_only)):
    with get_conn() as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM schedule_stops WHERE id = ?", stop_id)
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Not found")
    return {"success": True}
