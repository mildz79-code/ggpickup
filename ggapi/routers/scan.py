"""
routers/scan.py — Tesseract OCR scan (already exists in production).

Browser path:  POST /api/scan  →  FastAPI sees POST /scan

Tesseract is at C:\\Program Files\\Tesseract-OCR\\tesseract.exe (v5.5).
Pending: Poppler install for PDF support (currently JPG/PNG only).
"""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from deps import require_role

router = APIRouter(prefix="/scan", tags=["scan"])


@router.post("", dependencies=[Depends(require_role("admin"))])
async def scan_image(file: UploadFile = File(...)):
    """
    OCR an uploaded packing-list image. Parser looks for known knitter names,
    lot# patterns, qty, customer codes.

    Reuse the production implementation.
    """
    raise HTTPException(501, "Mirror production scan implementation here")
