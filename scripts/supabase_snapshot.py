#!/usr/bin/env python3
"""
supabase_snapshot.py — final data snapshot before Supabase retirement.

Pulls all relevant tables from Supabase project cgsmzkafagnmsuzzkfnv as JSON
and writes a timestamped archive file. Does NOT touch the live SQL Server.

Usage:
    python supabase_snapshot.py --out snapshots/supabase_20261231.sql

Requires: pip install supabase python-dotenv
Requires: .env with SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

try:
    from supabase import create_client
    from dotenv import load_dotenv
except ImportError:
    print("Missing deps. Run: pip install supabase python-dotenv")
    sys.exit(1)

TABLES = [
    "app_users",
    "greige_pickup_requests",
    "greige_pickup_photos",
    "ship_to_locations",
    "pl_line_items",
    "pl_monthly",
    "meter_reading",
]

def fetch_all(client, table):
    """Page through a table 1000 rows at a time."""
    rows = []
    offset = 0
    page = 1000
    while True:
        resp = client.table(table).select("*").range(offset, offset + page - 1).execute()
        data = resp.data or []
        rows.extend(data)
        if len(data) < page:
            break
        offset += page
    return rows

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="Output file path (.sql or .json)")
    parser.add_argument("--format", choices=["json", "sql"], default="sql")
    args = parser.parse_args()

    load_dotenv()
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        print("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set in .env")
        sys.exit(1)

    # Sanity check — refuse to run against Onetex
    if "mtxokbgpmkggolyfeehz" in url:
        print("REFUSING: this URL points at Onetex, not Color Fashion. Aborting.")
        sys.exit(1)
    if "cgsmzkafagnmsuzzkfnv" not in url:
        print(f"WARNING: URL does not contain the expected Color Fashion project id.")
        confirm = input("Continue anyway? (yes/no): ")
        if confirm.lower() != "yes":
            sys.exit(1)

    client = create_client(url, key)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    snapshot = {}
    for t in TABLES:
        print(f"  fetching {t}...", end=" ", flush=True)
        try:
            rows = fetch_all(client, t)
            snapshot[t] = rows
            print(f"{len(rows)} rows")
        except Exception as e:
            print(f"ERROR: {e}")
            snapshot[t] = {"error": str(e)}

    if args.format == "json":
        out_path.write_text(json.dumps(snapshot, indent=2, default=str))
    else:
        # SQL dump: one INSERT per row, per table. For archival, not replay.
        lines = [
            f"-- Supabase snapshot of cgsmzkafagnmsuzzkfnv",
            f"-- Taken: {datetime.utcnow().isoformat()}Z",
            f"-- For archival only. DO NOT replay blindly — use scripts/migrate_from_supabase.py",
            "",
        ]
        for table, rows in snapshot.items():
            lines.append(f"-- === {table} ({len(rows) if isinstance(rows, list) else 'ERROR'} rows) ===")
            if isinstance(rows, dict):
                lines.append(f"-- {rows}")
                continue
            for row in rows:
                cols = ", ".join(row.keys())
                vals = ", ".join(sql_literal(v) for v in row.values())
                lines.append(f"INSERT INTO {table} ({cols}) VALUES ({vals});")
            lines.append("")
        out_path.write_text("\n".join(lines))

    print(f"\nSnapshot written: {out_path} ({out_path.stat().st_size:,} bytes)")

def sql_literal(v):
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "1" if v else "0"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, (dict, list)):
        s = json.dumps(v)
    else:
        s = str(v)
    return "'" + s.replace("'", "''") + "'"

if __name__ == "__main__":
    main()
