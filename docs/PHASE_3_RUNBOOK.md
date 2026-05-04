# Phase 3 migration runbook — `003_shipping_schema.sql`

**Target:** WEBSERVER · SQL Server 2008 R2 · database `ggpickup` · `sa`  

**Artifacts:** Creates `delivery_requests`, `schedule_days`, `schedule_stops` per `ggapi/sql/003_shipping_schema.sql` (do not edit that file as part of this step).

---

## Pre-flight checks

Run these connected to **`localhost`** in SSMS **or** via `sqlcmd` as `sa` once you’ve loaded `SQL_PASSWORD` (see § PowerShell migration command).

### 1. Connectivity

- Ping or RDP confirms you are on **WEBSERVER** (or tunnel to it).
- `sqlcmd`/SSMS connects to **`localhost`** (same box as FastAPI).

### 2. Database exists

```sql
SELECT name FROM sys.databases WHERE name = 'ggpickup';
```

Expect one row: `ggpickup`.

### 3. Phase 0 baseline tables (from `PROJECT_CONTEXT.md`)

Confirm all five tables exist:

```sql
SELECT t.name
FROM sys.tables AS t
WHERE t.name IN (
    N'app_users',
    N'greige_pickup_requests',
    N'greige_pickup_photos',
    N'ship_to_locations',
    N'packing_memos'
)
ORDER BY t.name;
```

Expect **5** rows before migration.

### 4. Phase 3 tables must not exist yet

```sql
SELECT name
FROM sys.tables
WHERE name IN ('delivery_requests', 'schedule_days', 'schedule_stops');
```

Expect **zero** rows. If any appear, investigate or run `ggapi/sql/003_rollback.sql` (after stopping the API — see rollback section) before a clean apply.

---

## Apply migration — sqlcmd with password from `.env`

**Never** paste the literal `SQL_PASSWORD` into chat, scripts in git, or command history unnecessarily.

Production path for secrets: **`C:\ai\ggapi\.env`** (`SQL_PASSWORD=...`).  

Adjust the `-i` path if your workspace copy lives elsewhere.

From **PowerShell on WEBSERVER** (reads `SQL_PASSWORD` at invocation time):

```powershell
# Production ggapi checkout (adjust if your SQL file lives elsewhere):
$sqlPath = "C:\ai\ggapi\sql\003_shipping_schema.sql"
$p = ""
Get-Content "C:\ai\ggapi\.env" | ForEach-Object {
  if ($_ -match '^\s*SQL_PASSWORD\s*=\s*(.+)\s*$') { $p = $Matches[1].Trim('"').Trim("'") }
}
if ([string]::IsNullOrWhiteSpace($p)) { throw "SQL_PASSWORD not found in C:\ai\ggapi\.env" }
sqlcmd -S localhost -U sa -P "$p" -d ggpickup -b -i $sqlPath
```

- **`-b`:** batch abort on first error (`sqlcmd` exits non-zero sooner).
- If `sqlcmd` exits **0**, check the Messages pane or console for:  
  `Phase 3 shipping schema applied.` (printed by the migration).

If you are deploying from another folder, point `$sqlPath` at the synced `003_shipping_schema.sql` on disk.

---

## Apply migration — SSMS (alternative)

1. Open **SSMS** → connect to **`localhost`** → database **`ggpickup`**.
2. **File → Open → File…** → `003_shipping_schema.sql`.
3. Confirm the editor’s database dropdown shows **`ggpickup`**.
4. Press **F5** (Execute).
5. In **Messages**, confirm **`Phase 3 shipping schema applied.`**

Still treat credentials as secrets; SSMS remembers connections — sign in with `sa` only on this secured host.

---

## Post-migration verification

### (a) New tables exist

```sql
SELECT name
FROM sys.tables
WHERE name IN ('delivery_requests', 'schedule_days', 'schedule_stops')
ORDER BY name;
```

Expect **3** rows.

### (b) Row count baseline

```sql
SELECT COUNT(*) AS delivery_requests_rows FROM dbo.delivery_requests;
```

Expect **0** immediately after DDL (unless something else populated it).

### (c) FK relationships touching new objects

Lists every FK touching one of `delivery_requests`, `schedule_days`, or `schedule_stops` whether that table is the child or parent (includes `schedule_stops` → `greige_pickup_requests`):

```sql
SELECT
    OBJECT_NAME(fk.parent_object_id)     AS referencing_table,
    COL_NAME(fc.parent_object_id, fc.parent_column_id) AS referencing_column,
    OBJECT_NAME(fk.referenced_object_id) AS referenced_table,
    COL_NAME(fc.referenced_object_id, fc.referenced_column_id) AS referenced_column,
    fk.name AS fk_name
FROM sys.foreign_keys AS fk
INNER JOIN sys.foreign_key_columns AS fc ON fk.object_id = fc.constraint_object_id
WHERE OBJECT_NAME(fk.parent_object_id) IN ('delivery_requests','schedule_days','schedule_stops')
   OR OBJECT_NAME(fk.referenced_object_id) IN ('delivery_requests','schedule_days','schedule_stops')
ORDER BY referencing_table, fk.name;
```

---

## Rollback (`003_rollback.sql`)

1. **Stop FastAPI** so nothing holds connections or inserts into the new tables:  
   e.g. `taskkill /F /IM python.exe` (same as described in `docs/PRODUCTION_INVENTORY.md`).
2. Run **`ggapi/sql/003_rollback.sql`** in SSMS (**F5**) or via `sqlcmd` with the same `.env`-sourced `-P` pattern.
3. **Restart** ggapi (`start_ggapi.bat` or uvicorn command).

Rollback drops only the Phase 3 tables in FK-safe order; it does **not** touch baseline Phase 0 tables.

---

## If migration fails partway — transactions and cleanup

The migration script is **not** wrapped in one `BEGIN TRAN` / `COMMIT`. **SQLCMD batch defaults** (`ON`) **auto-commit each batch** terminated by **`GO`**.

Implications:

- After a failure you may see a **mixed state** (for example **`delivery_requests` created**, **`schedule_stops` missing**).
- **Do not** assume “nothing changed.” Query `sys.tables` for `delivery_requests`, `schedule_days`, `schedule_stops`.
- Safe recovery pattern:
  1. Stop the API.
  2. Run **`003_rollback.sql`** to drop whichever of the three exist (script is **idempotent**).
  3. Fix root cause (permissions, typo, connectivity, **`greige_pickup_requests` missing**, etc.).
  4. Re-run **`003_shipping_schema.sql`** from a clean slate (baseline tables intact).

Individual `CREATE TABLE` statements are guarded with `IF OBJECT_ID(...) IS NULL`, so repeating the migration after a rollback is intentional and safe once children are dropped.
