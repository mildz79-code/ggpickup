"""
ggapi — Color Fashion operations API.

Runs on WEBSERVER at localhost:8001. IIS reverse-proxies /api/* requests
from gg.colorfashiondnf.com (and shipping-web.colorfashiondnf.com) by
STRIPPING the /api/ prefix before forwarding. So the browser hits
    GET /api/auth/login
and FastAPI sees
    GET /auth/login
That's why no router below uses an /api prefix.

See docs/PROJECT_CONTEXT.md for full infrastructure details.
See docs/PHASES.md for the build sequence.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from db import verify_connection
from routers import auth, locations, pickup_requests, scan, shipping, sync, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Fail fast if SQL Server is unreachable.
    version = verify_connection()
    print(f"Connected to SQL Server: {version[:80]}")
    yield


app = FastAPI(
    title="ggapi",
    description="Color Fashion operations backend (pickups + shipping)",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — frontends call /api/* on their own origin via IIS rewrite, so this
# mostly matters for local dev where you'd hit localhost:8001 directly.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://gg.colorfashiondnf.com",
        "http://gg.colorfashiondnf.com",
        "https://shipping-web.colorfashiondnf.com",
        "http://shipping-web.colorfashiondnf.com",
        "http://localhost",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Routers -----
# All paths below are AFTER IIS strips /api/, so they look like "/auth/login"
# even though the browser actually requests "/api/auth/login".
app.include_router(auth.router)              # /auth/*
app.include_router(pickup_requests.router)   # /pickup-requests/*
app.include_router(users.router)             # /users
app.include_router(locations.router)         # /locations
app.include_router(sync.router)              # /sync          (Google Sheets)
app.include_router(scan.router)              # /scan          (Tesseract OCR)
app.include_router(shipping.router)          # /shipping/*    (Phase 3)

# ----- Static files -----
# Photos written by /pickup-requests/{id}/photos endpoint.
# IIS proxies /api/photos/* through to here, then we strip /photos to find files.
import os
PHOTO_DIR = os.getenv("PHOTO_DIR", r"C:\ai\ggapi\photos")
os.makedirs(PHOTO_DIR, exist_ok=True)
app.mount("/photos", StaticFiles(directory=PHOTO_DIR), name="photos")


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
