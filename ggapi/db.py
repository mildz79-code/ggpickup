"""
db.py — pyodbc connection helper for SQL Server 2008 R2.

Production reality:
    Database lives on WEBSERVER itself (localhost, not idserver).
    Auth: SQL auth as 'sa'.
    Driver: ODBC Driver 17 for SQL Server (already installed on WEBSERVER).

Connection string is loaded from .env. Defaults below match production
so the API runs out-of-the-box on WEBSERVER once .env exists.

Usage:
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT TOP 1 * FROM greige_pickup_requests")
        row = cursor.fetchone()
"""
import os
from contextlib import contextmanager

import pyodbc
from dotenv import load_dotenv

load_dotenv()

# Production defaults: SQL Server 2008 R2 on the same machine as FastAPI.
_SERVER   = os.getenv("SQL_SERVER", "localhost")
_DATABASE = os.getenv("SQL_DATABASE", "ggpickup")
_USER     = os.getenv("SQL_USER", "sa")
_PASSWORD = os.getenv("SQL_PASSWORD")
_DRIVER   = os.getenv("SQL_DRIVER", "{ODBC Driver 17 for SQL Server}")

if not _PASSWORD:
    raise RuntimeError(
        "SQL_PASSWORD must be set in ggapi/.env (see ggapi/.env.example). "
        "Production password is in the team password vault."
    )

_CONN_STR = (
    f"DRIVER={_DRIVER};"
    f"SERVER={_SERVER};"
    f"DATABASE={_DATABASE};"
    f"UID={_USER};"
    f"PWD={_PASSWORD};"
    f"TrustServerCertificate=yes;"
)


@contextmanager
def get_conn():
    """Auto-commit on success, rollback on exception, always close."""
    conn = pyodbc.connect(_CONN_STR, autocommit=False)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def verify_connection():
    """Called on FastAPI startup. Fails loudly if SQL Server is unreachable."""
    with get_conn() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        # Sanity check we're really on 2008 R2 — if production is upgraded later,
        # update .cursor/rules/30-sql-server-2008.mdc to relax T-SQL compat.
        if "10.50" not in version and "10.0" not in version:
            print(f"WARNING: SQL Server version is not 2008 R2: {version[:80]}")
        return version
