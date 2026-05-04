"""
routers/scan.py — Tesseract OCR scan.

Mirrors production C:\\ai\\ggapi\\main.py:
    POST /scan    →  admin-only; saves upload to SCAN_DIR, runs OCR,
                     returns {raw_text, parsed, filename}.

Browser path:  POST /api/scan  →  FastAPI sees POST /scan

Tesseract is at C:\\Program Files\\Tesseract-OCR\\tesseract.exe (v5.5).
"""
import os
import re
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from deps import admin_only

router = APIRouter(prefix="/scan", tags=["scan"])

# Production hardcodes C:\ggscans. Env-driven so prod can override.
SCAN_DIR = Path(os.getenv("SCAN_DIR", r"C:\ai\ggapi\scans"))
SCAN_DIR.mkdir(parents=True, exist_ok=True)

TESSERACT_CMD = os.getenv("TESSERACT_CMD", r"C:\Program Files\Tesseract-OCR\tesseract.exe")


@router.post("")
async def scan_document(file: UploadFile = File(...), user: dict = Depends(admin_only)):
    try:
        import pytesseract
        from PIL import Image
        import cv2
        import numpy as np

        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

        ext = Path(file.filename).suffix or ".png"
        filename = f"scan_{uuid.uuid4().hex}{ext}"
        dest = SCAN_DIR / filename
        contents = await file.read()
        with dest.open("wb") as f:
            f.write(contents)

        img_array = np.frombuffer(contents, np.uint8)
        img_cv = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)
        pil_img = Image.fromarray(thresh)
        raw_text = pytesseract.image_to_string(pil_img)
        parsed = parse_ocr_text(raw_text)

        return {"raw_text": raw_text, "parsed": parsed, "filename": filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


def parse_ocr_text(text: str) -> list:
    known_knitters = [
        "BONATEX", "WE", "STYLE KNIT", "HANTEX", "CAPITAL", "LAFAYETTE",
        "LAGUNA", "WALNUT", "DRIFTER", "SAS", "SHAITEX", "YK TEXTILE",
        "PACIFIC SOURCE GROUP",
    ]
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    results = []
    current_knitter = ""
    for line in lines:
        for k in known_knitters:
            if k in line.upper():
                current_knitter = k
                break
        qty_match = re.search(r'\b([1-9][0-9]?)\b', line)
        qty = int(qty_match.group(1)) if qty_match else 0
        lot_match = re.search(r'[A-Z]{1,5}-?\d{4,6}', line.upper())
        lot = lot_match.group(0) if lot_match else None
        cust_match = re.search(r'\b([A-Z]{2,4})\b', line.upper())
        customer = cust_match.group(1) if cust_match else ""
        if current_knitter and (qty > 0 or lot):
            results.append({
                "knitter":    current_knitter,
                "customer":   customer,
                "qty":        qty,
                "lot_number": lot,
                "raw_line":   line,
            })
    return results
