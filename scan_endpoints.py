"""
scan_endpoints.py — OCR scan pipeline for GG Pickup
Paste this block into C:\ai\ggapi\main.py.

BEFORE PASTING:
  1. Replace every occurrence of `<ADMIN_DEP>` with the actual admin dependency
     already used in main.py  (e.g. `require_admin`, `get_admin_user`, etc.).
  2. Replace `get_db_cursor()` calls with however main.py obtains a cursor/connection.
     See the stub function at the bottom — adapt to match your pattern.
  3. Add to requirements.txt / pip install if not already present:
       pytesseract
       Pillow

SEARCH in main.py for these patterns to find the right names:
  - Admin dep:    grep -n "require_admin\|def get_admin\|Depends(" main.py
  - DB cursor:    grep -n "cursor\|pyodbc\|get_db\|conn\." main.py
  - Existing /scan: grep -n "scan" main.py
"""

# ── Imports (add to top of main.py if missing) ─────────────────────────────
import os
import uuid
import re
import shutil
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile

try:
    import pytesseract
    from PIL import Image
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
except ImportError:
    pytesseract = None  # handled at call-site with a 503

# ── Constants ───────────────────────────────────────────────────────────────
SCAN_INCOMING = Path(r"D:\scan\incoming")

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png"}
ALLOWED_EXTS = {".jpg", ".jpeg", ".png"}

# ── Lot# extraction ──────────────────────────────────────────────────────────

def expand_lot_candidates(text: str) -> list:
    """
    Extract lot# candidates from OCR text.

    Handles:
      "K-22728"                         → ["K-22728"]
      "DUC-8840"                        → ["DUC-8840"]
      "JCC-10171, 172, 173, 174, 175"   → ["JCC-10171","JCC-10172","JCC-10173","JCC-10174","JCC-10175"]
      "EN-11068, 11001, 10998"          → ["EN-11068","EN-11001","EN-10998"]
      "OT-04945"                        → ["OT-04945"]
    """
    out = []
    seen = set()

    # Normalise: collapse whitespace, uppercase
    t = re.sub(r"\s+", " ", text).upper()

    for m in re.finditer(r"\b([A-Z]{1,4})-(\d{3,6})\b", t):
        prefix, num = m.group(1), m.group(2)
        full = f"{prefix}-{num}"
        if full not in seen:
            seen.add(full)
            out.append(full)

        # Look ahead from m.end() for ", 172, 173" shorthand bare numbers
        tail = t[m.end():]
        tail_match = re.match(r"(\s*,\s*\d{3,6})+", tail)
        if tail_match:
            for extra in re.findall(r"\d{3,6}", tail_match.group(0)):
                # Two candidates: bare extra AND prefix-padded (e.g. "10" + "172" = "10172")
                variants = {extra}
                if len(extra) < len(num):
                    variants.add(num[: len(num) - len(extra)] + extra)
                for v in sorted(variants):
                    cand = f"{prefix}-{v}"
                    if cand not in seen:
                        seen.add(cand)
                        out.append(cand)

    return out


# ── DB helper stub (replace with main.py's actual pattern) ──────────────────
#
# If main.py uses a pyodbc connection pool, it might look like:
#
#   conn = pyodbc.connect(CONNECTION_STRING, autocommit=False)
#   def get_cursor():
#       return conn.cursor()
#
# Or a context-manager style:
#
#   @contextmanager
#   def get_cursor():
#       with pyodbc.connect(CONNECTION_STRING) as c:
#           yield c.cursor()
#           c.commit()
#
# Adapt the two endpoints below to match whichever pattern is already used.
# The placeholder below raises immediately so you notice it:

def _placeholder_get_cursor():
    raise NotImplementedError(
        "Replace _placeholder_get_cursor() with the DB cursor pattern from main.py"
    )

# Alias — change the right-hand side to match your actual helper name
get_db_cursor = _placeholder_get_cursor


# ── Admin dependency placeholder ─────────────────────────────────────────────
#
# Change `<ADMIN_DEP>` in the two endpoints below to whatever admin dependency
# main.py already uses, e.g.:
#
#   current_user: dict = Depends(require_admin)
#   current_user: dict = Depends(get_current_admin)
#   current_user = Depends(get_current_user)   # then check role inline
#


# ── Endpoints ─────────────────────────────────────────────────────────────────
# If main.py uses a Router: replace `app` with your router variable.
# If it uses the app directly: keep `app`.

# router = APIRouter(prefix="")  # uncomment and use router.post if needed


@app.post("/scan")  # noqa: F821  (app defined in main.py)
async def scan_image(
    file: UploadFile = File(...),
    current_user=Depends(<ADMIN_DEP>),  # <── REPLACE <ADMIN_DEP>
):
    """
    Upload an image (JPG/PNG) → OCR → match lot# → auto-attach if single match.

    Returns:
      {
        "ocr_text": str,
        "candidates": [str, ...],
        "saved_path": str,          # /scans/YYYY-MM-DD/<uuid>.ext
        "matches": [...],
        "status": "auto_attached" | "multiple_matches" | "no_match",
        "attached_to": int          # only when auto_attached
      }
    """
    if pytesseract is None:
        raise HTTPException(503, "pytesseract / Pillow not installed on server")

    # 1. Reject PDF immediately
    ext = Path(file.filename or "").suffix.lower()
    if file.content_type == "application/pdf" or ext == ".pdf":
        raise HTTPException(415, "PDF support pending Poppler install")

    # 2. Validate file type
    if file.content_type not in ALLOWED_CONTENT_TYPES or ext not in ALLOWED_EXTS:
        raise HTTPException(400, f"Unsupported file type: {file.content_type or ext}")

    # 3. Save raw upload to D:\scan\incoming\YYYY-MM-DD\<uuid>.<ext>
    today_str = date.today().isoformat()
    folder = SCAN_INCOMING / today_str
    folder.mkdir(parents=True, exist_ok=True)
    saved_name = f"{uuid.uuid4().hex}{ext}"
    saved_path = folder / saved_name
    try:
        with saved_path.open("wb") as f_out:
            shutil.copyfileobj(file.file, f_out)
    except OSError as e:
        raise HTTPException(500, f"Could not save upload: {e}")

    # 4. Run Tesseract
    try:
        img = Image.open(saved_path)
        ocr_text = pytesseract.image_to_string(img)
    except Exception as e:
        raise HTTPException(500, f"OCR failed: {e}")

    # 5. Extract + expand candidates
    candidates = expand_lot_candidates(ocr_text)

    # 6. Match against today's Pending requests
    # relative URL path served via IIS /scans/*
    relative_path = "/scans/" + today_str + "/" + saved_name

    matches = []
    if candidates:
        cur = get_db_cursor()  # <── REPLACE with actual cursor pattern
        placeholders = " OR ".join(["lot_number LIKE ?" for _ in candidates])
        like_params = [f"%{c}%" for c in candidates]
        sql = f"""
            SELECT id, knitter, customer, qty, lot_number, status
            FROM greige_pickup_requests
            WHERE request_date = CAST(GETDATE() AS DATE)
              AND status = 'Pending'
              AND ({placeholders})
        """
        cur.execute(sql, like_params)
        cols = [c[0] for c in cur.description]
        rows = cur.fetchall()
        # Deduplicate by id (multiple candidates can match the same row)
        seen_ids: set = set()
        for row in rows:
            d = dict(zip(cols, row))
            if d["id"] not in seen_ids:
                seen_ids.add(d["id"])
                matches.append(d)

    # 7. Resolve
    result = {
        "ocr_text": ocr_text.strip(),
        "candidates": candidates,
        "saved_path": relative_path,
        "matches": matches,
    }

    if len(matches) == 0:
        result["status"] = "no_match"

    elif len(matches) == 1:
        req = matches[0]
        cur = get_db_cursor()  # <── REPLACE

        # Auto-attach photo
        cur.execute(
            """
            INSERT INTO greige_pickup_photos
                (pickup_request_id, storage_path, uploaded_by, created_at)
            VALUES (?, ?, ?, SYSUTCDATETIME())
            """,
            req["id"],
            relative_path,
            current_user["id"],
        )

        # Mark Picked Up — idempotent (only if still Pending)
        cur.execute(
            """
            UPDATE greige_pickup_requests
               SET status = 'Picked Up',
                   picked_up_at = SYSUTCDATETIME(),
                   picked_up_by = ?
             WHERE id = ? AND status = 'Pending'
            """,
            current_user["id"],
            req["id"],
        )

        # Commit — replace with your actual commit call if using a context manager
        # conn.commit()  or  cur.connection.commit()
        cur.connection.commit()  # <── adjust if needed

        result["status"] = "auto_attached"
        result["attached_to"] = req["id"]

    else:
        result["status"] = "multiple_matches"

    return result


@app.post("/scan/attach")  # noqa: F821
async def attach_scan(
    saved_path: str = Body(..., embed=True),
    request_id: int = Body(..., embed=True),
    mark_picked_up: bool = Body(False, embed=True),
    current_user=Depends(<ADMIN_DEP>),  # <── REPLACE <ADMIN_DEP>
):
    """
    Attach an already-saved scan file to a specific pickup request.
    Used by the frontend picker when the admin manually selects a match.

    Body (JSON):
      saved_path     – "/scans/YYYY-MM-DD/<uuid>.ext"
      request_id     – integer PK
      mark_picked_up – bool, default false; if true also sets status='Picked Up'
    """
    # Validate that saved_path is inside our controlled scan directory
    if not saved_path.startswith("/scans/"):
        raise HTTPException(400, "Invalid saved_path — must start with /scans/")

    # Reconstruct absolute path: strip leading "/scans/" then join to SCAN_INCOMING
    rel = saved_path[len("/scans/"):]  # e.g. "2026-04-23/abcdef.jpg"
    abs_path = SCAN_INCOMING / rel
    if not abs_path.exists():
        raise HTTPException(404, "Scan file no longer on disk")

    cur = get_db_cursor()  # <── REPLACE

    cur.execute(
        """
        INSERT INTO greige_pickup_photos
            (pickup_request_id, storage_path, uploaded_by, created_at)
        VALUES (?, ?, ?, SYSUTCDATETIME())
        """,
        request_id,
        saved_path,
        current_user["id"],
    )

    if mark_picked_up:
        cur.execute(
            """
            UPDATE greige_pickup_requests
               SET status = 'Picked Up',
                   picked_up_at = SYSUTCDATETIME(),
                   picked_up_by = ?
             WHERE id = ? AND status = 'Pending'
            """,
            current_user["id"],
            request_id,
        )

    cur.connection.commit()  # <── adjust if needed

    return {"ok": True, "request_id": request_id}
