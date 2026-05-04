r"""
sheets_sync.py  —  Google Sheets → SQL Server sync
Place at: C:\ai\ggapi\sheets_sync.py

Reads the TODAY tab from the GG PICK UP LIST sheet and
inserts/replaces today's rows in greige_pickup_requests.
"""

import os
from datetime import date

import pyodbc
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build

load_dotenv()

SHEET_ID   = os.getenv("SHEET_ID", "1TSJNTWouAV1x4W6Ouh3uTKM-PDNJL9952eYqYcjoPAA")
SHEET_TAB  = os.getenv("SHEET_TAB", "TODAY")
CREDS_FILE = os.getenv("GOOGLE_CREDENTIALS_PATH", r"C:\ai\ggapi\google-credentials.json")
SCOPES     = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

_SERVER   = os.getenv("SQL_SERVER", "localhost")
_DATABASE = os.getenv("SQL_DATABASE", "ggpickup")
_USER     = os.getenv("SQL_USER", "sa")
_PASSWORD = os.getenv("SQL_PASSWORD")
_DRIVER   = os.getenv("SQL_DRIVER", "{ODBC Driver 17 for SQL Server}")

if not _PASSWORD:
    raise RuntimeError(
        "SQL_PASSWORD must be set in ggapi/.env (see ggapi/.env.example)."
    )

SQL_CONN_STR = (
    f"DRIVER={_DRIVER};"
    f"SERVER={_SERVER};"
    f"DATABASE={_DATABASE};"
    f"UID={_USER};"
    f"PWD={_PASSWORD};"
)


def get_sheet_service():
    creds = service_account.Credentials.from_service_account_file(
        CREDS_FILE, scopes=SCOPES
    )
    return build("sheets", "v4", credentials=creds)


def parse_today_tab(values):
    """
    Sheet layout:
      Row 1: Date header (skip)
      Row 2: KNITTER | CUSTOMER | Qty | LOT NUMBER (headers, skip)
      Row 3+: data

    Knitter column uses merged cells — carry forward last seen value.
    """
    rows = []
    last_knitter = ""

    for i, row in enumerate(values):
        if i < 2:          # skip date row + header row
            continue

        # Pad row to 4 columns
        while len(row) < 4:
            row.append("")

        knitter   = str(row[0]).strip()
        customer  = str(row[1]).strip()
        qty_raw   = str(row[2]).strip()
        lot       = str(row[3]).strip()

        # Carry forward knitter (merged cells come back as empty)
        if knitter:
            last_knitter = knitter
        else:
            knitter = last_knitter

        # Skip completely empty rows
       # Skip empty rows and summary rows
        if not knitter and not customer:
            continue
        if 'TOTAL' in knitter.upper() or 'TOTAL' in customer.upper():
            continue

        # Parse qty
        try:
            qty = int(qty_raw) if qty_raw else 0
        except ValueError:
            qty = 0

        rows.append({
            "knitter":    knitter.upper(),
            "customer":   customer.upper(),
            "qty":        qty,
            "lot_number": lot if lot else None,
        })

    return rows


def sync_today():
    """
    Main sync function. Called by the FastAPI /sync endpoint.
    Returns a summary dict.
    """
    today = date.today().isoformat()

    # 1. Fetch sheet data
    service = get_sheet_service()
    result = service.spreadsheets().values().get(
        spreadsheetId=SHEET_ID,
        range=f"{SHEET_TAB}!A1:D200",
    ).execute()
    values = result.get("values", [])

    # 2. Parse rows
    rows = parse_today_tab(values)
    if not rows:
        return {"synced": 0, "request_date": today, "message": "No data found in sheet"}

    # 3. Write to SQL Server
    conn = pyodbc.connect(SQL_CONN_STR)
    cur  = conn.cursor()

    # Delete today's existing rows first (clean replace)
    cur.execute(
        "DELETE FROM greige_pickup_requests WHERE request_date = ? AND status = 'Pending'",
        today,
    )
    deleted = cur.rowcount

    # Insert fresh rows
    for r in rows:
        cur.execute(
            """
            INSERT INTO greige_pickup_requests
                (request_date, knitter, customer, lot_number, qty, status)
            VALUES (?, ?, ?, ?, ?, 'Pending')
            """,
            today,
            r["knitter"],
            r["customer"],
            r["lot_number"],
            r["qty"],
        )

    conn.commit()
    conn.close()

    return {
        "synced":       len(rows),
        "replaced":     deleted,
        "request_date": today,
        "message":      f"Inserted {len(rows)} rows for {today}",
    }
